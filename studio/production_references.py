"""Hash-bound still references and human review in the existing Studio asset index."""

import base64
import copy
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import uuid

from . import asset_intake, production_store as store
from .production_bootstrap import json_bytes, reference_requirements

NAMESPACE = store.REFERENCE_BANK
IMAGE_ROLES = ('identity', 'wardrobe', 'location', 'prop')
DECISIONS = ('keep', 'wrong_face', 'wrong_outfit', 'characters_mixed_up', 'reject')


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def normalize_role(role):
    return 'location' if role == 'environment' else role


def requirements(document):
    entities = {e['id']: e for kind in ('characters', 'locations', 'props', 'voices', 'motions')
                for e in document.get(kind, [])}
    rows = reference_requirements(document)
    for row in rows:
        entity = entities[row['entity']]
        role = normalize_role(row['role'])
        row['role'] = role
        row['key'] = digest({k: row[k] for k in ('entity', 'role', 'wardrobe') if k in row})
        if role == 'wardrobe':
            outfit = next(w for w in entity['wardrobe'] if w['id'] == row['wardrobe'])
            context = {'name': entity['name'], 'appearance': entity['appearance'], 'outfit': outfit}
            row['label'] = entity['name'] + ' · ' + outfit['description']
        else:
            context = {k: v for k, v in entity.items() if k not in ('refs', 'wardrobe', 'platform_ids', 'voice')}
            row['label'] = entity['name']
        row['context'] = digest(context)
        row['supported'] = role in IMAGE_ROLES
    return rows


def source_path(loader_path, roots):
    if not isinstance(loader_path, str) or not loader_path or '\\' in loader_path or '\0' in loader_path:
        raise ValueError('Choose a native input or output image')
    name, kind = loader_path, 'input'
    if name.endswith(']'):
        for option in ('input', 'output'):
            suffix = ' [' + option + ']'
            if name.endswith(suffix):
                name, kind = name[:-len(suffix)], option
                break
        else:
            raise ValueError('Only input and output images can be references')
    path = Path(name)
    if path.is_absolute() or not path.parts or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('Reference path must stay inside the native media folder')
    if path.suffix.lower() not in asset_intake.FORMATS:
        raise ValueError('Choose a PNG, JPEG or WebP still image')
    return Path(roots[kind]) / path.parent, path.name, name + ' [' + kind + ']'


def inspect_source(loader_path, roots):
    folder, name, normalized = source_path(loader_path, roots)
    with asset_intake.directory(folder) as fd:
        data = asset_intake.read_stable(fd, name)
    with asset_intake.inspect_image(data, Path(name).suffix.lower()) as image:
        width, height = image.size
        image.thumbnail((384, 256))
        preview = io.BytesIO()
        image.convert('RGB').save(preview, format='PNG')
    return {'loader_path': normalized, 'sha256': hashlib.sha256(data).hexdigest(),
            'width': width, 'height': height, 'bytes': len(data),
            'thumbnail': 'data:image/png;base64,' + base64.b64encode(preview.getvalue()).decode()}


def checked_state(project_root, revision):
    state = store.read_project(project_root)
    if state['revision'] != revision:
        raise store.RevisionConflict('The project changed; reopen it before changing references')
    return state


def requirement_for(state, key):
    requirement = next((r for r in requirements(state['production']) if r['key'] == key), None)
    if requirement is None or not requirement['supported']:
        raise ValueError('Choose a current still-reference requirement')
    return requirement


def catalog(state):
    value = state['assets'].get(NAMESPACE, {'version': 1, 'sources': {}, 'bindings': {}})
    if not isinstance(value, dict) or value.get('version') != 1 or not all(isinstance(value.get(k), dict) for k in ('sources', 'bindings')):
        raise ValueError('Unsupported storyboard reference bank; existing assets were left intact')
    return copy.deepcopy(value)


def actor(reviewer):
    if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 120:
        raise ValueError('A reference reviewer is required')
    return reviewer.strip()


def bind(project_root, revision, key, candidate, authorized, reviewer, roots):
    state = checked_state(project_root, revision)
    requirement = requirement_for(state, key)
    if authorized is not True:
        raise ValueError('Confirm permission to use this image as a reference')
    reviewer = actor(reviewer)
    current = inspect_source(candidate['loader_path'], roots)
    if candidate != current:
        raise ValueError('Reference changed since preview; inspect it again')
    bank = catalog(state)
    sha = current['sha256']
    source = bank['sources'].setdefault(sha, {k: current[k] for k in ('sha256', 'width', 'height', 'bytes')})
    source.setdefault('locators', [])
    if current['loader_path'] not in source['locators']:
        source['locators'].append(current['loader_path'])
    binding = {k: requirement[k] for k in ('entity', 'role', 'wardrobe', 'context') if k in requirement}
    binding.update(id=str(uuid.uuid4()), source_sha256=sha, loader_path=current['loader_path'],
                   input_use_authorized=True, authorized_by=reviewer, authorized_at=datetime.now(timezone.utc).isoformat(), reviews=[])
    bank['bindings'][key] = binding
    assets = {**state['assets'], NAMESPACE: bank}
    return store.commit(project_root, revision, {'assets': assets}, 'Bind a storyboard reference; visual review pending')


def review(project_root, revision, key, binding_id, decision, reviewer, roots):
    state = checked_state(project_root, revision)
    requirement = requirement_for(state, key)
    bank = catalog(state)
    binding = bank['bindings'].get(key)
    if binding is None or binding['id'] != binding_id:
        raise ValueError('The reference selection changed; reopen it before reviewing')
    if binding['context'] != requirement['context']:
        raise ValueError('The character, outfit or place changed; bind a reference for the current requirement')
    source = inspect_source(binding['loader_path'], roots)
    if source['sha256'] != binding['source_sha256']:
        raise ValueError('Reference pixels changed; inspect and bind them again')
    if decision not in DECISIONS:
        raise ValueError('Choose a reference review action')
    binding['reviews'].append({'id': str(uuid.uuid4()), 'binding_id': binding_id, 'decision': decision,
        'reviewer': actor(reviewer), 'source_sha256': source['sha256'], 'context': requirement['context'],
        'at': datetime.now(timezone.utc).isoformat()})
    return store.commit(project_root, revision, {'assets': {**state['assets'], NAMESPACE: bank}}, 'Review a storyboard reference')


def bank(state, roots):
    values = catalog(state)
    rows = requirements(state['production'])
    for row in rows:
        binding = values['bindings'].get(row['key'])
        if not row['supported']:
            row['status'] = 'not_supported'
        elif binding:
            row['binding'] = binding
            try:
                source = inspect_source(binding['loader_path'], roots)
                if source['sha256'] != binding['source_sha256']:
                    row['status'] = 'source_changed'
                    continue
                row['source'] = source
            except (OSError, ValueError) as error:
                row.update(status='source_unavailable', problem=str(error))
                continue
            if binding['context'] != row['context']:
                row['status'] = 'needs_rebinding'
            else:
                reviews = binding['reviews']
                row['status'] = 'needs_review' if not reviews else 'ready' if reviews[-1]['decision'] == 'keep' else 'rejected'
    return {'requirements': rows, 'revision': state['revision'], 'render_ready': False}

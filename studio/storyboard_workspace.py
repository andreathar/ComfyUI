"""Small, local project operations used by the storyboard creator workspace."""

import re

from . import production_bootstrap as bootstrap
from . import master_studio_package, production_outline, production_references, production_store, still_recipe, storyboard


def selected(projects_root, slug):
    if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or len(slug) > 64:
        raise ValueError('Choose a valid project name')
    root = production_store.project_path(projects_root)
    return root / slug


def preview(source, title, slug, code, cast, location):
    """An explicit manual starting point, never a substitute for model story analysis."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError('Write your story first')
    paragraphs = [part.strip() for part in re.split(r'\n\s*\n', source) if part.strip()]
    if len(paragraphs) > 4:
        raise ValueError('The manual starting point supports up to four paragraphs; use the local planner for larger stories')
    if not isinstance(cast, list) or any(not isinstance(c, dict) or set(c) != {'name', 'wardrobe'} for c in cast):
        raise ValueError('Characters need a name and outfit')
    outline = {
        'place': {'name': location, 'kind': 'INT', 'time': 'day', 'description': 'Location details need review'},
        'cast': [{'name': c['name'], 'appearance': 'Identity reference needs review', 'wardrobe': c['wardrobe']} for c in cast],
        'props': [],
        'shots': [{'excerpt': paragraph, 'action': paragraph, 'cast': list(range(len(cast))), 'props': [], 'size': 'wide'}
                  for paragraph in paragraphs],
    }
    result = production_outline.expand(outline, source, code, title)
    if 'document' not in result:
        raise ValueError('\n'.join(result.get('problems', ['Review the story details'])))
    document = storyboard.upgrade(result['document'])
    return {'mode': 'story_paragraphs',
            'assumptions': ['Each paragraph is a draft shot in one scene; story interpretation has not run.',
                            'Interior, daytime, wide framing and three-second timing are editable starting choices.',
                            'Characters, outfits, props, geography and endpoint images need review.'],
            'proposal': bootstrap.preview(document, slug)}


def create(projects_root, proposal, approved_digest):
    bootstrap.create(projects_root, proposal, approved_digest)
    return open_project(projects_root, proposal['slug'])


def open_project(projects_root, slug):
    state = production_store.read_project(selected(projects_root, slug))
    return {**state, 'storyboard': storyboard.targets(state['production'], state.get('storyboard')),
            'project': slug, 'timeline': storyboard.timeline(state['production']), 'render_ready': False}


def save(projects_root, slug, revision, document):
    state = production_store.commit(selected(projects_root, slug), revision, {'production': document}, 'Edit storyboard plan')
    return {**state, 'storyboard': storyboard.targets(state['production'], state.get('storyboard')),
            'project': slug, 'timeline': storyboard.timeline(state['production']), 'render_ready': False}


def save_targets(projects_root, slug, revision, board):
    state = production_store.commit(selected(projects_root, slug), revision, {'storyboard': board}, 'Edit storyboard targets')
    return {**state, 'storyboard': storyboard.targets(state['production'], state.get('storyboard')),
            'project': slug, 'timeline': storyboard.timeline(state['production']), 'render_ready': False}


def reviewed_references(state, shot_id, reference_keys, media_roots, staged_inputs):
    if (not isinstance(reference_keys, list) or not reference_keys
            or any(not isinstance(key, str) for key in reference_keys)
            or len(set(reference_keys)) != len(reference_keys)):
        raise ValueError('Choose one or more distinct references')
    if staged_inputs is None:
        staged_inputs = {}
    if not isinstance(staged_inputs, dict) or any(key not in reference_keys for key in staged_inputs):
        raise ValueError('Choose staged inputs for the selected references')
    rows = {row['key']: row for row in production_references.bank(state, media_roots)['requirements']}
    references = []
    for key in reference_keys:
        row = rows.get(key)
        if (row is None or row['status'] != 'ready' or shot_id not in row['shots']
                or not row['binding'].get('input_use_authorized')):
            raise ValueError('Choose a reviewed, current reference for this shot')
        binding = row['binding']
        suffix = ' [input]'
        locator = staged_inputs.get(key, binding['loader_path'])
        if key not in staged_inputs and not locator.endswith(suffix):
            raise ValueError('Stage this reference in the native input folder before preparing the draft')
        staged = production_references.inspect_source(locator, media_roots)
        if not staged['loader_path'].endswith(suffix):
            raise ValueError('Stage this reference in the native input folder before preparing the draft')
        if staged['sha256'] != binding['source_sha256']:
            raise ValueError('Staged reference pixels do not match the reviewed reference')
        reference = {'name': staged['loader_path'][:-len(suffix)], 'sha256': binding['source_sha256'],
                     'role': row['role'], 'entity': row['entity'], 'authorized': True,
                     'binding_id': binding['id'], 'requirement_key': key, 'context': row['context']}
        if 'wardrobe' in row:
            reference['wardrobe'] = row['wardrobe']
        references.append(reference)
    return references, rows


def reference_coverage(rows, shot_id, reference_keys):
    return [{key: row[key] for key in ('key', 'role', 'label', 'shots')}
            | {'status': row.get('status', 'missing'), 'selected': row['key'] in reference_keys}
            for row in rows.values() if shot_id in row['shots']]


def draft_endpoint(projects_root, slug, revision, shot_id, endpoint, reference_keys, seed, media_roots, *, staged_inputs=None,
                   start_reference=None):
    root = selected(projects_root, slug)
    state = production_references.checked_state(root, revision)
    references, rows = reviewed_references(state, shot_id, reference_keys, media_roots, staged_inputs)
    if start_reference is not None:
        references.append(start_reference)
    board = storyboard.targets(state['production'], state.get('storyboard'))
    draft = still_recipe.compile_endpoint(state['production'], board, references, shot_id, endpoint, seed=seed)
    return {**draft, 'project': slug, 'revision': state['revision'],
            'reference_coverage': reference_coverage(rows, shot_id, reference_keys)}


def draft_master_handoff(projects_root, slug, revision, shot_id, reference_keys, seed, media_roots, workspace, recipe, *, staged_inputs=None):
    """Prepare a silent H3 draft; Builder saving and canvas handoff remain separate."""
    root = selected(projects_root, slug)
    state = production_references.checked_state(root, revision)
    references, rows = reviewed_references(state, shot_id, reference_keys, media_roots, staged_inputs)
    assets = {}
    for ref in references:
        asset = {'path': 'input/' + ref['name'], 'sha256': ref['sha256'], 'input_use_authorized': True,
                 'role': ref['role'], 'owner': ref['entity'], 'kind': 'picture',
                 'selection': {'kind': 'picture', 'file': ref['name'] + ' [input]'}}
        if ref['role'] == 'wardrobe':
            asset['wardrobe_id'] = ref['wardrobe']
        assets[ref['requirement_key']] = asset
    binding = {'assets': reference_keys, 'audio_mode': 'silent', 'seed': seed}
    package = master_studio_package.compile_project_shot_package(root, state, shot_id, workspace, recipe, binding, assets,
                                                                input_root=media_roots['input'])
    return {**package, 'reference_bindings': references,
            'reference_coverage': reference_coverage(rows, shot_id, reference_keys),
            'preflight_required': ['builder_save_not_connected', 'live_reference_map_not_verified',
                                   'runtime_and_model_availability_not_verified', 'creative_review_required']}


def projects(projects_root):
    root = production_store.project_path(projects_root)
    result = {'projects': [], 'problems': []}
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_dir() or not (path / 'project.json').exists():
            continue
        try:
            state = open_project(root, path.name)
            project = state['production']['project']
            result['projects'].append({'slug': path.name, 'title': project['title'], 'code': project['code'],
                                       'shots': len(state['timeline'])})
        except (ValueError, KeyError, TypeError, OSError) as error:
            result['problems'].append({'slug': path.name, 'error': str(error)})
    return result

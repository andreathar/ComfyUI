import copy
import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image, PngImagePlugin

from studio import production_bootstrap as bootstrap, production_store as store
from studio.production_validate import SPEC
from studio import production_validate


@pytest.fixture
def refs():
    return importlib.import_module('studio.production_references')


@pytest.fixture
def setup(tmp_path):
    document = json.loads((SPEC / 'example.production.json').read_text())
    first = document['characters'][0]
    second = copy.deepcopy(first)
    second['id'] = document['project']['code'] + '-CHR-SECOND'
    second['name'] = 'Second character'
    second['wardrobe'][0]['description'] = 'Red coat'
    document['characters'].append(second)
    document['scenes'][0]['characters'].append(second['id'])
    document['scenes'][0].setdefault('wardrobe', {})[second['id']] = second['wardrobe'][0]['id']
    proposal = bootstrap.preview(document, 'reference-test')
    bootstrap.create(tmp_path, proposal, proposal['digest'])
    root = tmp_path / 'reference-test'
    inputs, outputs = tmp_path / 'native-input', tmp_path / 'native-output'
    inputs.mkdir(); outputs.mkdir()
    metadata = PngImagePlugin.PngInfo(); metadata.add_text('workflow', 'preserve this metadata')
    Image.new('RGB', (64, 48), 'blue').save(inputs / 'face.png', pnginfo=metadata)
    return root, {'input': inputs, 'output': outputs}, document


def row(refs, document, role, owner=None):
    return next(r for r in refs.requirements(document) if r['role'] == role and (owner is None or r['entity'] == owner))


def bind(refs, setup, requirement=None, authorized=True):
    root, roots, doc = setup
    requirement = requirement or row(refs, doc, 'identity')
    candidate = refs.inspect_source('face.png [input]', roots)
    return refs.bind(root, store.read_project(root)['revision'], requirement['key'], candidate,
                     authorized, 'local-user', roots)


def test_inspection_is_read_only_and_retains_native_locator_hash_and_metadata(refs, setup):
    root, roots, _ = setup
    before = (roots['input'] / 'face.png').read_bytes()
    candidate = refs.inspect_source('face.png [input]', roots)
    assert candidate['loader_path'] == 'face.png [input]'
    assert candidate['width'] == 64 and candidate['height'] == 48
    assert len(candidate['sha256']) == 64 and candidate['thumbnail'].startswith('data:image/png;base64,')
    assert (roots['input'] / 'face.png').read_bytes() == before
    assert store.read_project(root)['assets'] == {}


def test_shared_pixels_have_independent_role_owner_and_outfit_bindings(refs, setup):
    root, roots, doc = setup
    identities = [r for r in refs.requirements(doc) if r['role'] == 'identity']
    first = bind(refs, setup, identities[0])
    bank = first['assets'][refs.NAMESPACE]
    first_binding = bank['bindings'][identities[0]['key']]
    approved = refs.review(root, first['revision'], identities[0]['key'], first_binding['id'], 'keep', 'local-user', roots)
    second = bind(refs, setup, identities[1])
    bank = second['assets'][refs.NAMESPACE]
    assert len(bank['sources']) == 1 and len(bank['bindings']) == 2
    statuses = {r['key']: r['status'] for r in refs.bank(second, roots)['requirements']}
    assert statuses[identities[0]['key']] == 'ready'
    assert statuses[identities[1]['key']] == 'needs_review'
    wardrobe = row(refs, doc, 'wardrobe', identities[1]['entity'])
    third = bind(refs, setup, wardrobe)
    assert len(third['assets'][refs.NAMESPACE]['bindings']) == 3
    assert refs.bank(third, roots)['render_ready'] is False
    assert approved['production'] == doc


def test_permission_does_not_grant_visual_approval_and_requires_explicit_use(refs, setup):
    root, roots, doc = setup
    initial = store.read_project(root)
    with pytest.raises(ValueError, match='permission'):
        bind(refs, setup, authorized=False)
    assert store.read_project(root) == initial
    bound = bind(refs, setup)
    requirement = row(refs, doc, 'identity')
    binding = bound['assets'][refs.NAMESPACE]['bindings'][requirement['key']]
    assert binding['input_use_authorized'] is True
    assert not binding['reviews']
    assert next(r for r in refs.bank(bound, roots)['requirements'] if r['key'] == requirement['key'])['status'] == 'needs_review'


def test_review_reopen_and_rejection_history_are_hash_bound(refs, setup):
    root, roots, doc = setup
    saved = bind(refs, setup)
    key = row(refs, doc, 'identity')['key']
    binding_id = saved['assets'][refs.NAMESPACE]['bindings'][key]['id']
    rejected = refs.review(root, saved['revision'], key, binding_id, 'wrong_face', 'local-user', roots)
    assert next(r for r in refs.bank(rejected, roots)['requirements'] if r['key'] == key)['status'] == 'rejected'
    kept = refs.review(root, rejected['revision'], key, binding_id, 'keep', 'local-user', roots)
    reopened = store.read_project(root)
    assert reopened == kept
    reviews = reopened['assets'][refs.NAMESPACE]['bindings'][key]['reviews']
    assert [r['decision'] for r in reviews] == ['wrong_face', 'keep']
    assert all(r['reviewer'] == 'local-user' and r['source_sha256'] for r in reviews)


def test_changed_bytes_cannot_be_bound_or_reviewed_as_old_pixels(refs, setup):
    root, roots, doc = setup
    candidate = refs.inspect_source('face.png', roots)
    key = row(refs, doc, 'identity')['key']
    Image.new('RGB', (64, 48), 'red').save(roots['input'] / 'face.png')
    with pytest.raises(ValueError, match='changed'):
        refs.bind(root, store.read_project(root)['revision'], key, candidate, True, 'local-user', roots)
    bound = bind(refs, setup)
    binding_id = bound['assets'][refs.NAMESPACE]['bindings'][key]['id']
    Image.new('RGB', (64, 48), 'green').save(roots['input'] / 'face.png')
    with pytest.raises(ValueError, match='changed'):
        refs.review(root, bound['revision'], key, binding_id, 'keep', 'local-user', roots)
    assert next(r for r in refs.bank(store.read_project(root), roots)['requirements'] if r['key'] == key)['status'] == 'source_changed'


def test_changed_outfit_invalidates_only_its_own_reference_review(refs, setup):
    root, roots, doc = setup
    requirement = row(refs, doc, 'wardrobe')
    bound = bind(refs, setup, requirement)
    binding_id = bound['assets'][refs.NAMESPACE]['bindings'][requirement['key']]['id']
    kept = refs.review(root, bound['revision'], requirement['key'], binding_id, 'keep', 'local-user', roots)
    edited = copy.deepcopy(doc)
    character = next(c for c in edited['characters'] if c['id'] == requirement['entity'])
    next(w for w in character['wardrobe'] if w['id'] == requirement['wardrobe'])['description'] += ' with a hat'
    changed = store.commit(root, kept['revision'], {'production': edited}, 'Change one outfit')
    assert next(r for r in refs.bank(changed, roots)['requirements'] if r['key'] == requirement['key'])['status'] == 'needs_rebinding'
    with pytest.raises(ValueError, match='changed'):
        refs.review(root, changed['revision'], requirement['key'], binding_id, 'keep', 'local-user', roots)


def test_stale_revision_and_late_review_cannot_replace_a_new_selection(refs, setup):
    root, roots, doc = setup
    initial = store.read_project(root)
    bound = bind(refs, setup)
    key = row(refs, doc, 'identity')['key']
    old_id = bound['assets'][refs.NAMESPACE]['bindings'][key]['id']
    with pytest.raises(store.RevisionConflict):
        refs.bind(root, initial['revision'], key, refs.inspect_source('face.png', roots), True, 'local-user', roots)
    rebound = bind(refs, setup)
    with pytest.raises(ValueError, match='selection'):
        refs.review(root, rebound['revision'], key, old_id, 'keep', 'local-user', roots)
    assert store.read_project(root) == rebound


@pytest.mark.parametrize('name', ['../face.png', '/etc/passwd', 'a/../../face.png', 'face.png [temp]', 'a\\face.png'])
def test_only_native_contained_image_paths_are_accepted(refs, setup, name):
    with pytest.raises((ValueError, OSError)):
        refs.inspect_source(name, setup[1])


def test_symlink_directories_and_non_images_are_rejected(refs, setup):
    _, roots, _ = setup
    (roots['input'] / 'link').symlink_to(roots['input'], target_is_directory=True)
    (roots['input'] / 'file.png').symlink_to(roots['input'] / 'face.png')
    (roots['input'] / 'text.png').write_text('not an image')
    for name in ('link/face.png', 'file.png', 'text.png'):
        with pytest.raises((ValueError, OSError)):
            refs.inspect_source(name, roots)


def test_binding_failure_is_atomic_and_preserves_legacy_assets(refs, setup):
    root, _, _ = setup
    legacy = {'existing-h3': {'role': 'identity', 'approved': False}}
    (root / 'assets.json').write_text(json.dumps(legacy))
    initial = store.read_project(root)
    with patch.object(store.os, 'replace', side_effect=OSError('disk full')):
        with pytest.raises(OSError, match='disk full'):
            bind(refs, setup)
    assert store.read_project(root) == initial
    bound = bind(refs, setup)
    assert bound['assets']['existing-h3'] == legacy['existing-h3']
    assert bound['bindings'] == initial['bindings']


def test_environment_role_is_translated_and_bad_owner_never_binds(refs, setup):
    root, roots, doc = setup
    assert refs.normalize_role('environment') == 'location'
    key = row(refs, doc, 'location')['key']
    candidate = refs.inspect_source('face.png', roots)
    with pytest.raises(ValueError, match='requirement'):
        refs.bind(root, store.read_project(root)['revision'], 'unknown-owner', candidate, True, 'local-user', roots)
    saved = refs.bind(root, store.read_project(root)['revision'], key, candidate, True, 'local-user', roots)
    assert saved['assets'][refs.NAMESPACE]['bindings'][key]['role'] == 'location'


@pytest.mark.parametrize('invalid', ['outfit', 'character', 'duplicate'])
def test_invalid_wardrobe_links_fail_before_creating_a_reference_project(setup, invalid):
    _, _, doc = setup
    edited = copy.deepcopy(doc)
    character = edited['characters'][0]
    wardrobe = edited['scenes'][0].setdefault('wardrobe', {})
    if invalid == 'outfit':
        wardrobe[character['id']] = 'does-not-exist'
    elif invalid == 'character':
        wardrobe['UNKNOWN-CHR-NOBODY'] = character['wardrobe'][0]['id']
    else:
        character['wardrobe'].append(copy.deepcopy(character['wardrobe'][0]))
    assert any('wardrobe' in problem for problem in production_validate.check(edited))

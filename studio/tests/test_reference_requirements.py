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


def test_changed_character_appearance_requires_identity_reference_rebinding(refs, setup):
    root, roots, doc = setup
    requirement = row(refs, doc, 'identity')
    bound = bind(refs, setup, requirement)
    binding_id = bound['assets'][refs.NAMESPACE]['bindings'][requirement['key']]['id']
    kept = refs.review(root, bound['revision'], requirement['key'], binding_id, 'keep', 'local-user', roots)
    edited = copy.deepcopy(doc)
    character = next(c for c in edited['characters'] if c['id'] == requirement['entity'])
    character['appearance'] += ' with brown hair'
    changed = store.commit(root, kept['revision'], {'production': edited}, 'Change appearance')
    current = next(r for r in refs.bank(changed, roots)['requirements'] if r['key'] == requirement['key'])
    assert current['status'] == 'needs_rebinding'
    assert current['binding']['id'] == binding_id


def test_moved_and_inaccessible_bound_image_is_reported(refs, setup):
    root, roots, doc = setup
    bound = bind(refs, setup)
    key = row(refs, doc, 'identity')['key']
    image = roots['input'] / 'face.png'
    moved = roots['input'] / 'moved.png'
    image.rename(moved)
    assert next(r for r in refs.bank(bound, roots)['requirements'] if r['key'] == key)['status'] == 'source_unavailable'
    image.symlink_to(moved)
    assert next(r for r in refs.bank(bound, roots)['requirements'] if r['key'] == key)['status'] == 'source_unavailable'


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


def test_draft_uses_reviewed_reference_bytes_from_saved_project(refs, setup):
    from studio import storyboard_workspace as workspace

    root, roots, doc = setup
    identity = row(refs, doc, 'identity')
    bound = bind(refs, setup, identity)
    binding = bound['assets'][refs.NAMESPACE]['bindings'][identity['key']]
    reviewed = refs.review(root, bound['revision'], identity['key'], binding['id'], 'keep', 'local-user', roots)
    opened = workspace.open_project(root.parent, root.name)
    board = copy.deepcopy(opened['storyboard'])
    shot = doc['shots'][0]['id']
    board['shots'][shot]['start']['description'] = 'The character waits at the door.'
    saved = workspace.save_targets(root.parent, root.name, reviewed['revision'], board)
    with patch.object(refs, 'bank', wraps=refs.bank) as bank:
        draft = workspace.draft_endpoint(root.parent, root.name, saved['revision'], shot, 'start',
                                         [identity['key']], 42, roots)
    assert bank.call_count == 1
    assert draft['status'] == 'draft'
    assert draft['references'][0]['name'] == 'face.png'
    assert draft['references'][0]['sha256'] == binding['source_sha256']
    assert draft['graph']['64']['inputs']['noise_seed'] == 42
    coverage = draft['reference_coverage']
    assert next(item for item in coverage if item['key'] == identity['key'])['selected'] is True
    assert any(item['status'] == 'missing' and not item['selected'] for item in coverage)
    assert all(shot in item['shots'] for item in coverage)
    Image.new('RGB', (64, 48), 'red').save(roots['input'] / 'face.png')
    with pytest.raises(ValueError, match='reference'):
        workspace.draft_endpoint(root.parent, root.name, saved['revision'], shot, 'start', [identity['key']], 42, roots)


def test_reviewed_storyboard_references_compile_to_master_package(refs, tmp_path):
    from studio import h3_recipe, storyboard_workspace as workspace

    document = json.loads((SPEC / 'example.production.json').read_text())
    document['shots'][0].pop('target', None)
    person = document['characters'][0]
    document['scenes'][0]['wardrobe'] = {person['id']: person['wardrobe'][0]['id']}
    proposal = bootstrap.preview(document, 'film')
    projects = tmp_path / 'projects'
    projects.mkdir()
    bootstrap.create(projects, proposal, proposal['digest'])
    root = projects / 'film'
    inputs, outputs = tmp_path / 'native-input', tmp_path / 'native-output'
    inputs.mkdir(); outputs.mkdir()
    roots = {'input': inputs, 'output': outputs}
    shot = document['shots'][0]['id']
    keys = []
    for role, color in [('identity', 'blue'), ('location', 'green'), ('wardrobe', 'yellow')]:
        Image.new('RGB', (64, 48), color).save(inputs / f'{role}.png')
        requirement = next(r for r in refs.requirements(document) if r['role'] == role and shot in r['shots'])
        state = store.read_project(root)
        state = refs.bind(root, state['revision'], requirement['key'], refs.inspect_source(f'{role}.png [input]', roots), True, 'tester', roots)
        binding = state['assets'][refs.NAMESPACE]['bindings'][requirement['key']]
        state = refs.review(root, state['revision'], requirement['key'], binding['id'], 'keep', 'tester', roots)
        keys.append(requirement['key'])
    before = store.read_project(root)
    package = workspace.draft_master_handoff(projects, 'film', before['revision'], shot, keys, 123, roots, tmp_path, h3_recipe.DIAGNOSTIC)
    assert package['project'] == 'film'
    assert package['project_revision'] == before['revision']
    assert package['seed'] == 123
    assert package['prompt_status'] == 'draft_uncommitted'
    assert 'builder_save_not_connected' in package['preflight_required']
    assert {item['key'] for item in package['reference_coverage'] if item['selected']} == set(keys)
    assert [x['file'] for x in package['media_state']] == ['identity.png [input]', 'location.png [input]', 'wardrobe.png [input]']
    assert package['stack_state']['picks'] == []
    assert '<Picture 1>' in package['prompt_text'] and '<Picture 2>' in package['prompt_text']
    assert store.read_project(root) == before

    Image.new('RGB', (64, 48), 'red').save(inputs / 'identity.png')
    with pytest.raises(ValueError, match='reference'):
        workspace.draft_master_handoff(projects, 'film', before['revision'], shot, keys, 123, roots, tmp_path, h3_recipe.DIAGNOSTIC)


def test_master_handoff_cannot_reuse_another_projects_review(refs, tmp_path):
    from studio import h3_recipe, storyboard_workspace as workspace

    projects, inputs = tmp_path / 'projects', tmp_path / 'input'
    projects.mkdir(); inputs.mkdir()
    roots = {'input': inputs, 'output': inputs}
    Image.new('RGB', (32, 32), 'blue').save(inputs / 'reference.png')
    projects_data = []
    for slug, code in [('first', 'FIRST'), ('second', 'SECOND')]:
        proposal = workspace.preview('A person waits.', slug, slug, code,
                                     [{'name': 'Person', 'wardrobe': 'Coat'}], 'Room')['proposal']
        state = workspace.create(projects, proposal, proposal['digest'])
        shot = state['production']['shots'][0]['id']
        keys = []
        for role in ('identity', 'location'):
            requirement = next(r for r in refs.requirements(state['production']) if r['role'] == role)
            state = refs.bind(projects / slug, state['revision'], requirement['key'],
                              refs.inspect_source('reference.png', roots), True, 'tester', roots)
            binding = state['assets'][refs.NAMESPACE]['bindings'][requirement['key']]
            state = refs.review(projects / slug, state['revision'], requirement['key'], binding['id'], 'keep', 'tester', roots)
            keys.append(requirement['key'])
        projects_data.append((slug, state, shot, keys))
    first, second = projects_data
    for slug, state, shot, keys in projects_data:
        package = workspace.draft_master_handoff(projects, slug, state['revision'], shot, keys, 42, roots, tmp_path, h3_recipe.DIAGNOSTIC)
        assert package['project'] == slug and package['project_code'] == state['manifest']['code']
        assert package['shot_id'] == shot and package['project_revision'] == state['revision']
    with pytest.raises(ValueError, match='reference'):
        workspace.draft_master_handoff(projects, second[0], second[1]['revision'], second[2], first[3], 42, roots, tmp_path, h3_recipe.DIAGNOSTIC)


def test_draft_refuses_unreviewed_and_stale_references(refs, setup):
    from studio import storyboard_workspace as workspace

    root, roots, doc = setup
    identity = row(refs, doc, 'identity')
    initial = store.read_project(root)
    bound = bind(refs, setup, identity)
    shot = doc['shots'][0]['id']
    with pytest.raises(store.RevisionConflict):
        workspace.draft_endpoint(root.parent, root.name, initial['revision'], shot, 'start', [identity['key']], 42, roots)
    with pytest.raises(ValueError, match='reference'):
        workspace.draft_endpoint(root.parent, root.name, bound['revision'], shot, 'start', [identity['key']], 42, roots)


def test_draft_requires_output_references_to_be_staged(refs, setup):
    from studio import storyboard_workspace as workspace

    root, roots, doc = setup
    Image.new('RGB', (64, 48), 'blue').save(roots['output'] / 'portrait.png')
    identity = row(refs, doc, 'identity')
    initial = store.read_project(root)
    candidate = refs.inspect_source('portrait.png [output]', roots)
    bound = refs.bind(root, initial['revision'], identity['key'], candidate, True, 'local-user', roots)
    binding = bound['assets'][refs.NAMESPACE]['bindings'][identity['key']]
    reviewed = refs.review(root, bound['revision'], identity['key'], binding['id'], 'keep', 'local-user', roots)
    with pytest.raises(ValueError, match='Stage'):
        workspace.draft_endpoint(root.parent, root.name, reviewed['revision'], doc['shots'][0]['id'], 'start',
                                 [identity['key']], 42, roots)
    Image.new('RGB', (64, 48), 'blue').save(roots['input'] / 'staged.png')
    opened = workspace.open_project(root.parent, root.name)
    board = copy.deepcopy(opened['storyboard'])
    shot = doc['shots'][0]['id']
    board['shots'][shot]['start']['description'] = 'The character waits.'
    saved = workspace.save_targets(root.parent, root.name, reviewed['revision'], board)
    staged = {identity['key']: 'staged.png'}
    result = workspace.draft_endpoint(root.parent, root.name, saved['revision'], shot, 'start',
                                      [identity['key']], 42, roots, staged_inputs=staged)
    assert result['references'][0]['name'] == 'staged.png'
    assert result['references'][0]['sha256'] == candidate['sha256']
    Image.new('RGB', (64, 48), 'red').save(roots['input'] / 'staged.png')
    with pytest.raises(ValueError, match='match'):
        workspace.draft_endpoint(root.parent, root.name, saved['revision'], shot, 'start',
                                 [identity['key']], 42, roots, staged_inputs=staged)


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

import copy
from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from studio import production_bootstrap as bootstrap
from studio.production_validate import SPEC


EXAMPLE = json.loads((SPEC / 'example.production.json').read_text())


def test_preview_and_create_preserve_source_and_leave_references_unapproved(tmp_path):
    proposal = bootstrap.preview(EXAMPLE, 'demo-film')
    assert not list(tmp_path.iterdir())
    result = bootstrap.create(tmp_path, proposal, proposal['digest'])
    project = tmp_path / 'demo-film'
    assert result['status'] == 'scaffold_created'
    assert (project / 'story/script-v001.md').read_bytes() == EXAMPLE['project']['source_text'].encode()
    plan = json.loads((project / 'reference-plan.json').read_text())
    assert {r['entity'] for r in plan if r['role'] == 'location'} == {loc['id'] for loc in EXAMPLE['locations']}
    assert all(r['status'] == 'missing' for r in plan)
    assert json.loads((project / 'bindings.json').read_text()) == {}
    assert bootstrap.create(tmp_path, proposal, proposal['digest'])['status'] == 'already_created'


def test_create_rejects_unreviewed_changes_and_conflicting_destinations(tmp_path):
    proposal = bootstrap.preview(EXAMPLE, 'demo-film')
    edited = copy.deepcopy(proposal)
    edited['production']['project']['title'] += ' edited'
    with pytest.raises(ValueError, match='digest'):
        bootstrap.create(tmp_path, edited, proposal['digest'])
    with pytest.raises(ValueError, match='slug'):
        bootstrap.preview(EXAMPLE, '../escape')
    destination = tmp_path / 'demo-film'
    destination.mkdir()
    with pytest.raises(FileExistsError):
        bootstrap.create(tmp_path, proposal, proposal['digest'])
    assert list(destination.iterdir()) == []


def test_project_code_cannot_be_reused_under_another_slug(tmp_path):
    proposal = bootstrap.preview(EXAMPLE, 'demo-film')
    bootstrap.create(tmp_path, proposal, proposal['digest'])
    other = bootstrap.preview(EXAMPLE, 'another-film')
    with pytest.raises(ValueError, match='project code'):
        bootstrap.create(tmp_path, other, other['digest'])
    assert not (tmp_path / 'another-film').exists()


def test_parallel_create_has_one_writer(tmp_path):
    proposal = bootstrap.preview(EXAMPLE, 'demo-film')
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(bootstrap.create, tmp_path, proposal, proposal['digest']) for _ in range(2)]
        assert {call.result()['status'] for call in calls} == {'scaffold_created', 'already_created'}
    assert [p.name for p in tmp_path.iterdir()] == ['demo-film']


def test_existing_symlink_is_not_followed(tmp_path):
    projects = tmp_path / 'projects'
    projects.mkdir()
    (projects / 'demo-film').symlink_to(tmp_path / 'outside', target_is_directory=True)
    proposal = bootstrap.preview(EXAMPLE, 'demo-film')
    with pytest.raises(FileExistsError):
        bootstrap.create(projects, proposal, proposal['digest'])
    assert not (tmp_path / 'outside').exists()

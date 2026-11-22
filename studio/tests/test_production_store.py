import copy
import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from studio import production_bootstrap as bootstrap
from studio import production_store as store
from studio.production_validate import SPEC


EXAMPLE = json.loads((SPEC / 'example.production.json').read_text())


@pytest.fixture
def project(tmp_path):
    proposal = bootstrap.preview(EXAMPLE, 'demo-film')
    bootstrap.create(tmp_path, proposal, proposal['digest'])
    return tmp_path / 'demo-film'


def edit(snapshot, seconds=4):
    doc = copy.deepcopy(snapshot['production'])
    doc['shots'][0]['duration_s'] = seconds
    return {'production': doc}


def test_read_edit_reopen_preserves_source_and_previous_revision(project):
    initial = store.read_project(project)
    assert initial['production'] == EXAMPLE
    assert initial['assets'] == initial['bindings'] == {}
    saved = store.commit(project, initial['revision'], edit(initial), 'Change pacing')
    reopened = store.read_project(project)
    assert saved == reopened
    assert reopened['production']['shots'][0]['duration_s'] == 4
    assert reopened['revision'] != initial['revision']
    assert reopened['production']['project']['source_text'] == EXAMPLE['project']['source_text']
    history = project / 'revisions' / (initial['revision'] + '.json')
    assert json.loads(history.read_text())['production'] == EXAMPLE


def test_stale_tab_cannot_overwrite_a_newer_edit(project):
    initial = store.read_project(project)
    store.commit(project, initial['revision'], edit(initial), 'First tab')
    with pytest.raises(store.RevisionConflict):
        store.commit(project, initial['revision'], edit(initial, 5), 'Stale tab')
    assert store.read_project(project)['production']['shots'][0]['duration_s'] == 4


def test_concurrent_tabs_have_one_writer(project):
    initial = store.read_project(project)

    def save(seconds):
        try:
            store.commit(project, initial['revision'], edit(initial, seconds), 'Concurrent edit')
            return 'saved'
        except store.RevisionConflict:
            return 'conflict'

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, (6, 7))) == ['conflict', 'saved']


def test_changed_reference_binding_invalidates_pending_save(project):
    initial = store.read_project(project)
    (project / 'bindings.json').write_text('{"new": "binding"}')
    with pytest.raises(store.RevisionConflict):
        store.commit(project, initial['revision'], edit(initial), 'Changed inputs')
    assert json.loads((project / 'production.json').read_text()) == EXAMPLE


@pytest.mark.parametrize('change', ['source', 'code', 'invalid', 'extra'])
def test_unreviewed_story_identity_and_invalid_edits_are_rejected(project, change):
    initial = store.read_project(project)
    changes = edit(initial)
    if change == 'source':
        changes['production']['project']['source_text'] += ' New story.'
    elif change == 'code':
        changes['production']['project']['code'] = 'OTHER'
    elif change == 'invalid':
        changes['production']['shots'][0]['duration_s'] = -1
    else:
        changes['assets'] = {}
    with pytest.raises(ValueError):
        store.commit(project, initial['revision'], changes, 'Invalid edit')
    assert store.read_project(project) == initial


def test_failed_atomic_replace_keeps_previous_document(project):
    initial = store.read_project(project)
    with patch.object(store.os, 'replace', side_effect=OSError('disk full')):
        with pytest.raises(OSError, match='disk full'):
            store.commit(project, initial['revision'], edit(initial), 'Failed save')
    assert store.read_project(project) == initial


def test_failed_history_flush_does_not_publish_an_incomplete_revision(project):
    initial = store.read_project(project)
    with patch.object(store.os, 'fsync', side_effect=OSError('disk full')):
        with pytest.raises(OSError, match='disk full'):
            store.commit(project, initial['revision'], edit(initial), 'Failed history save')
    assert list((project / 'revisions').glob('*.json')) == []
    assert store.read_project(project) == initial


def test_history_directories_are_durable_before_canonical_replace(project):
    initial = store.read_project(project)
    events = []
    fsync, replace = os.fsync, os.replace

    def track_sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            events.append(os.readlink(f'/proc/self/fd/{fd}'))
        fsync(fd)

    def track_replace(source, target):
        assert str(project / 'revisions') in events
        assert str(project) in events
        events.append('replace')
        replace(source, target)

    with patch.object(store.os, 'fsync', side_effect=track_sync), patch.object(store.os, 'replace', side_effect=track_replace):
        store.commit(project, initial['revision'], edit(initial), 'Durable history')
    assert events[-2:] == ['replace', str(project)]


def test_history_directory_sync_failure_keeps_canonical_document(project):
    initial = store.read_project(project)
    fsync = os.fsync

    def fail_history_sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode) and os.readlink(f'/proc/self/fd/{fd}') == str(project / 'revisions'):
            raise OSError('history directory flush failed')
        fsync(fd)

    with patch.object(store.os, 'fsync', side_effect=fail_history_sync):
        with pytest.raises(OSError, match='history directory flush failed'):
            store.commit(project, initial['revision'], edit(initial), 'Failed directory flush')
    assert store.read_project(project) == initial
    saved = store.commit(project, initial['revision'], edit(initial), 'Retry complete history')
    assert saved['production']['shots'][0]['duration_s'] == 4


def test_interruption_after_replace_keeps_the_project_and_previous_revision_readable(project):
    initial = store.read_project(project)
    sync = store.sync_directory

    def stop_after_replace(path):
        if path == project and store.read_project(project)['revision'] != initial['revision']:
            raise OSError('simulated interruption after replace')
        sync(path)

    with patch.object(store, 'sync_directory', side_effect=stop_after_replace):
        with pytest.raises(OSError, match='after replace'):
            store.commit(project, initial['revision'], edit(initial), 'Interrupted edit')
    assert store.read_project(project)['production']['shots'][0]['duration_s'] == 4
    previous = project / 'revisions' / (initial['revision'] + '.json')
    assert json.loads(previous.read_text())['production'] == EXAMPLE


def test_project_and_file_symlinks_are_rejected(project, tmp_path):
    alias = tmp_path / 'alias'
    alias.symlink_to(project, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        store.read_project(alias)
    data = project / 'production.json'
    outside = tmp_path / 'outside.json'
    data.rename(outside)
    data.symlink_to(outside)
    with pytest.raises((ValueError, OSError)):
        store.read_project(project)


def test_manifest_cannot_read_outside_project(project):
    manifest = json.loads((project / 'project.json').read_text())
    manifest['production'] = '../production.json'
    (project / 'project.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='path'):
        store.read_project(project)

import copy
import json

import pytest

from studio import storyboard
from studio.production_validate import SPEC


EXAMPLE = json.loads((SPEC / 'example.production.json').read_text())


def test_upgrade_preserves_existing_story_ids_references_and_selection():
    source = copy.deepcopy(EXAMPLE)
    source['shots'][0].update(start_frame='start.png', end_frame='end.png')
    upgraded = storyboard.upgrade(source)
    assert source['schema_version'] == 1
    assert upgraded['schema_version'] == 2
    assert upgraded['editorial'] == {'version': 1, 'gap_before_frames': {}}
    assert {k: v for k, v in upgraded.items() if k not in ('schema_version', 'editorial')} == {
        k: v for k, v in source.items() if k != 'schema_version'}
    assert storyboard.legacy(upgraded) == source


def test_legacy_projection_rejects_renumbering_or_lost_gap_meaning():
    upgraded = storyboard.upgrade(EXAMPLE)
    upgraded['shots'][0]['id'] = 'DEMO_S001_SH08'
    with pytest.raises(ValueError, match='legacy'):
        storyboard.legacy(upgraded)
    upgraded = storyboard.upgrade(EXAMPLE)
    upgraded['editorial']['gap_before_frames'][upgraded['shots'][0]['id']] = 1
    with pytest.raises(ValueError, match='gap'):
        storyboard.legacy(upgraded)


@pytest.mark.parametrize('fps', [24, 25, 30])
def test_timeline_uses_integer_frames_and_explicit_gaps(fps):
    doc = storyboard.upgrade(EXAMPLE)
    doc['project']['fps'] = fps
    doc['shots'][0]['duration_s'] = 1.02
    doc['shots'].append({**copy.deepcopy(doc['shots'][0]), 'id': 'DEMO_S001_SH09', 'duration_s': 2})
    doc['editorial']['gap_before_frames']['DEMO_S001_SH09'] = 7
    rows = storyboard.timeline(doc)
    frames = {24: 24, 25: 26, 30: 31}[fps]
    assert (rows[0]['start'], rows[0]['end']) == (0, frames)
    assert (rows[1]['start'], rows[1]['end']) == (frames + 7, frames + 7 + 2 * fps)
    assert all(type(r['start']) is int and type(r['end']) is int for r in rows)


def test_timeline_preserves_shot_order_and_does_not_assume_frames_are_reviewed():
    doc = storyboard.upgrade(EXAMPLE)
    doc['shots'][0].update(start_frame='start.png', end_frame='end.png')
    row = storyboard.timeline(doc)[0]
    assert row['shot_id'] == doc['shots'][0]['id']
    assert row['start_image'] == 'start.png' and row['end_image'] == 'end.png'
    assert row['review_status'] == 'needs_review'
    assert storyboard.timeline(EXAMPLE)[0]['review_status'] == 'missing_frames'


def test_empty_storyboard_has_two_independent_endpoint_targets_per_shot():
    board = storyboard.empty(EXAMPLE)
    first = board['shots'][EXAMPLE['shots'][0]['id']]
    assert set(first) == {'start', 'end'}
    assert first['start'] == {'description': '', 'candidates': []}
    first['start']['description'] = 'Face visible at the doorway'
    assert first['end']['description'] == ''
    assert 'selected' not in first


def test_unknown_versions_and_invalid_documents_are_rejected():
    doc = copy.deepcopy(EXAMPLE)
    doc['schema_version'] = 99
    for operation in (storyboard.upgrade, storyboard.legacy, storyboard.timeline, storyboard.empty):
        with pytest.raises(ValueError):
            operation(doc)

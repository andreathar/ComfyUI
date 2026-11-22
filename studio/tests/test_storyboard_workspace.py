import json

import pytest

from studio import storyboard_workspace as workspace


STORY = 'André waits at the door.\n\nHe opens the letter.'


def test_preview_is_explicitly_manual_and_preserves_every_story_byte(tmp_path):
    result = workspace.preview(STORY, 'A letter', 'a-letter', 'LET',
                               [{'name': 'André', 'wardrobe': 'Blue jacket'}], 'Station')
    assert result['mode'] == 'story_paragraphs'
    assert result['assumptions']
    proposal = result['proposal']
    assert proposal['production']['project']['source_text'] == STORY
    assert len(proposal['production']['shots']) == 2
    assert proposal['production']['schema_version'] == 2
    assert not proposal['render_ready']
    created = workspace.create(tmp_path, proposal, proposal['digest'])
    opened = workspace.open_project(tmp_path, 'a-letter')
    assert created['project'] == 'a-letter'
    assert opened['production']['project']['source_text'] == STORY
    assert len(opened['timeline']) == 2
    assert len(workspace.projects(tmp_path)['projects']) == 1


def test_reviewed_project_can_save_pacing_without_recreating_or_losing_story(tmp_path):
    proposal = workspace.preview(STORY, 'A letter', 'a-letter', 'LET', [], 'Station')['proposal']
    workspace.create(tmp_path, proposal, proposal['digest'])
    before = workspace.open_project(tmp_path, 'a-letter')
    before['production']['shots'][0]['duration_s'] = 5
    saved = workspace.save(tmp_path, 'a-letter', before['revision'], before['production'])
    assert saved['timeline'][0]['duration_frames'] == 120
    assert workspace.open_project(tmp_path, 'a-letter')['revision'] == saved['revision']
    assert (tmp_path / 'a-letter/story/script-v001.md').read_text() == STORY


def test_no_silent_truncation_for_more_than_four_paragraphs():
    with pytest.raises(ValueError, match='four'):
        workspace.preview('\n\n'.join(['A beat.'] * 5), 'Many beats', 'many', 'MANY', [], 'Station')


@pytest.mark.parametrize('slug', ['../escape', '/outside', 'a/b', 'Upper', ''])
def test_project_selector_rejects_paths(tmp_path, slug):
    with pytest.raises(ValueError):
        workspace.open_project(tmp_path, slug)


def test_creation_requires_the_exact_reviewed_digest(tmp_path):
    proposal = workspace.preview(STORY, 'A letter', 'a-letter', 'LET', [], 'Station')['proposal']
    with pytest.raises(ValueError, match='digest'):
        workspace.create(tmp_path, proposal, 'unreviewed')
    assert list(tmp_path.iterdir()) == []


def test_project_listing_reports_invalid_projects_without_hiding_valid_ones(tmp_path):
    broken = tmp_path / 'broken'
    broken.mkdir()
    (broken / 'project.json').write_text('{}')
    proposal = workspace.preview(STORY, 'A letter', 'a-letter', 'LET', [], 'Station')['proposal']
    workspace.create(tmp_path, proposal, proposal['digest'])
    listing = workspace.projects(tmp_path)
    assert [p['slug'] for p in listing['projects']] == ['a-letter']
    assert listing['problems'][0]['slug'] == 'broken'

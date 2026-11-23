import json
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from studio import production_bootstrap as bootstrap, production_generate as generate
from studio.production_validate import check


WALK = 'Ada walks toward the post with a red umbrella.'
STOP = 'Ada stops beside the post.'
STORY = 'EXT. PLATFORM - DUSK. Ada has short black hair and wears a navy coat.\n' + WALK + ' ' + STOP + '\n'
OUTLINE = {
    'place': {'name': 'Station platform', 'kind': 'EXT', 'time': 'dusk', 'description': 'Concrete platform and shelter'},
    'cast': [{'name': 'Ada', 'appearance': 'short black hair', 'wardrobe': 'navy coat'}],
    'props': [{'name': 'Umbrella', 'description': 'red umbrella'}],
    'shots': [
        {'excerpt': WALK, 'action': 'Ada walks toward the post holding a red umbrella.', 'cast': [0], 'props': [0], 'size': 'wide'},
        {'excerpt': STOP, 'action': STOP, 'cast': [0], 'props': [0], 'size': 'medium'},
    ],
}


def test_compact_reply_round_trips_through_the_existing_scaffold(tmp_path):
    def model(system, messages, name):
        assert 'Do not echo the whole story' in system
        assert '<schema>' not in messages[0]['content']
        return json.dumps(OUTLINE)

    result = generate.generate_outline(STORY, model, code='STN', title='Empty Platform')
    doc = result['document']
    assert isinstance(doc, dict)
    assert check(doc) == []
    assert doc['project']['source_text'] == STORY
    assert [sh['id'] for sh in doc['shots']] == ['STN_S001_SH01', 'STN_S001_SH02']
    assert [STORY[s['script_ref']['start']:s['script_ref']['end']] for s in doc['shots']] == [WALK, STOP]
    assert [s['duration_s'] for s in doc['shots']] == [3, 3]
    assert not any('target' in sh for sh in doc['shots'])
    proposal = bootstrap.preview(doc, 'empty-platform')
    result = bootstrap.create(tmp_path, proposal, proposal['digest'])
    assert (tmp_path/'empty-platform/story/script-v001.md').read_bytes() == STORY.encode()
    assert result['status'] == 'scaffold_created'
    assert {r['role'] for r in proposal['reference_plan']} == {'identity', 'wardrobe', 'prop', 'location'}
    assert all(r['status'] == 'missing' for r in proposal['reference_plan'])


def test_compact_cli_does_not_publish_unverified_excerpts_or_questions(tmp_path):
    source = tmp_path / 'story.txt'
    source.write_text(STORY)
    broken = deepcopy(OUTLINE)
    broken['shots'][1]['excerpt'] = 'An invented shot.'
    outputs = [json.dumps(broken), '{"shots":', json.dumps({'questions': [{'about': 'Wardrobe', 'ask': 'What does Ada wear?'}]})]
    for i, raw in enumerate(outputs):
        out = tmp_path / f'production-{i}.json'
        with (patch.object(generate, 'local_server', return_value=nullcontext((1234, 'local', 1))),
              patch.object(generate, 'local_completion', return_value=raw) as request):
            assert generate.main([str(source), '--out', str(out), '--log', str(tmp_path/f'worker-{i}.log'),
                                  '--outline', '--project-code', 'STN', '--title', 'Empty Platform']) == 1
        assert not out.exists()
        assert request.call_count == 1
        assert request.call_args.kwargs['max_tokens'] == 768


def test_compact_cli_keeps_original_line_endings(tmp_path):
    raw = STORY.replace('\n', '\r\n').encode()
    source = tmp_path / 'story.txt'
    source.write_bytes(raw)
    out = tmp_path / 'production.json'
    with (patch.object(generate, 'local_server', return_value=nullcontext((1234, 'local', 1))),
          patch.object(generate, 'local_completion', return_value=json.dumps(OUTLINE))):
        assert generate.main([str(source), '--out', str(out), '--log', str(tmp_path/'worker.log'),
                              '--outline', '--project-code', 'STN', '--title', 'Empty Platform']) == 0
    assert json.loads(out.read_bytes())['project']['source_text'].encode() == raw


def test_compact_rejects_unknown_fields_instead_of_silently_dropping_them():
    reply = dict(OUTLINE, voice='unreviewed')
    result = generate.generate_outline(STORY, lambda *_: json.dumps(reply), code='STN', title='Empty Platform')
    assert 'document' not in result
    problems = result['problems']
    assert isinstance(problems, list)
    assert 'voice' in problems[0]


@pytest.mark.parametrize('case', [case for case in json.loads(
    (Path(__file__).parent / 'fixtures/storyboard/cases.json').read_text())['cases'] if 'compact_outline' in case],
    ids=lambda case: case['id'])
def test_acceptance_sources_keep_exact_ordered_spans_and_bytes(tmp_path, case):
    result = generate.generate_outline(case['source_text'], lambda *_: json.dumps(case['compact_outline']),
                                       code='FIX', title=case['id'])
    doc = result['document']
    assert [shot['script_ref'] for shot in doc['shots']] == [
        {'start': fact['start'], 'end': fact['end']} for fact in case['source_facts']]
    proposal = bootstrap.preview(doc, case['id'])
    bootstrap.create(tmp_path, proposal, proposal['digest'])
    assert (tmp_path / case['id'] / 'story/script-v001.md').read_bytes() == case['source_text'].encode()

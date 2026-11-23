import copy
import json

import pytest

from studio import still_recipe, storyboard
from studio.production_validate import SPEC


DOCUMENT = json.loads((SPEC / 'example.production.json').read_text())
SHOT = DOCUMENT['shots'][0]['id']
REF = {'name': 'identity.png', 'sha256': 'a' * 64, 'role': 'identity',
       'entity': DOCUMENT['characters'][0]['id'], 'authorized': True}


def draft():
    board = storyboard.empty(DOCUMENT)
    board['shots'][SHOT]['start']['description'] = 'The person stands at the doorway.'
    return board


def test_native_recipe_binds_reference_and_effective_seed():
    result = still_recipe.compile_endpoint(DOCUMENT, draft(), [REF], SHOT, 'start', seed=42)
    graph = result['graph']
    assert graph['1']['class_type'] == 'UNETLoader'
    assert graph['1']['inputs']['unet_name'] == 'flux-2-klein-4b-fp8.safetensors'
    assert graph['64']['inputs']['noise_seed'] == 42
    assert graph['65']['inputs']['noise'] == ['64', 0]
    assert graph['10']['inputs']['image'] == 'identity.png'
    assert graph['10']['class_type'] == 'StudioStoryboardReference'
    assert graph['10']['inputs']['sha256'] == REF['sha256']
    assert graph['13']['inputs']['latent'] == ['12', 0]
    assert graph['60']['inputs']['positive'] == ['13', 0]
    assert result['references'] == [REF]
    assert result['endpoint'] == 'start'


def test_input_digest_tracks_reference_order_and_seed():
    other = {**REF, 'name': 'street.png', 'sha256': 'b' * 64, 'role': 'location',
             'entity': DOCUMENT['locations'][0]['id']}
    compile_endpoint = still_recipe.compile_endpoint
    original = compile_endpoint(DOCUMENT, draft(), [REF, other], SHOT, 'start', seed=42)
    reordered = compile_endpoint(DOCUMENT, draft(), [other, REF], SHOT, 'start', seed=42)
    reseeded = compile_endpoint(DOCUMENT, draft(), [REF, other], SHOT, 'start', seed=43)
    assert len({original['input_digest'], reordered['input_digest'], reseeded['input_digest']}) == 3


def test_missing_target_and_unauthorized_reference_are_not_submitted():
    compile_endpoint = still_recipe.compile_endpoint
    with pytest.raises(ValueError, match='description'):
        compile_endpoint(DOCUMENT, storyboard.empty(DOCUMENT), [REF], SHOT, 'start', seed=42)
    with pytest.raises(ValueError, match='permission'):
        compile_endpoint(DOCUMENT, draft(), [{**REF, 'authorized': False}], SHOT, 'start', seed=42)


def test_many_references_do_not_overwrite_sampler_nodes():
    refs = [{**REF, 'name': f'ref-{n}.png', 'sha256': f'{n:064x}'} for n in range(8)]
    result = still_recipe.compile_endpoint(copy.deepcopy(DOCUMENT), draft(), refs, SHOT, 'start', seed=42)
    graph = result['graph']
    assert graph['60']['class_type'] == 'CFGGuider'
    assert graph['65']['class_type'] == 'SamplerCustomAdvanced'
    assert [node['inputs']['image'] for node in graph.values() if node['class_type'] == 'StudioStoryboardReference'] == [r['name'] for r in refs]
    assert [node['inputs']['sha256'] for node in graph.values() if node['class_type'] == 'StudioStoryboardReference'] == [r['sha256'] for r in refs]


def test_reference_must_belong_to_this_shot():
    with pytest.raises(ValueError, match='shot'):
        still_recipe.compile_endpoint(DOCUMENT, draft(), [{**REF, 'entity': 'OTHER-CHR-01'}], SHOT, 'start', seed=42)


def test_draft_reports_that_file_hashes_and_review_are_not_verified():
    result = still_recipe.compile_endpoint(DOCUMENT, draft(), [REF], SHOT, 'start', seed=42)
    assert result['status'] == 'draft'
    assert 'source_hashes_not_verified' in result['preflight_required']
    assert 'creative_review_required' in result['preflight_required']
    assert 'master_studio_handoff_not_verified' in result['preflight_required']


def test_reference_labels_preserve_entity_and_image_order():
    other = {**REF, 'name': 'street.png', 'sha256': 'b' * 64, 'role': 'location',
             'entity': DOCUMENT['locations'][0]['id']}
    result = still_recipe.compile_endpoint(DOCUMENT, draft(), [REF, other], SHOT, 'start', seed=42)
    text = result['graph']['4']['inputs']['text']
    assert result['prompt'] == text
    assert 'Image 1: identity for Main' in text
    assert 'Image 2: location for Rainy street' in text


def test_prompt_review_shows_character_words_and_actual_reference_order():
    location = {**REF, 'name': 'street.png', 'sha256': 'b' * 64, 'role': 'location',
                'entity': DOCUMENT['locations'][0]['id']}
    result = still_recipe.compile_endpoint(DOCUMENT, draft(), [location, REF], SHOT, 'start', seed=42)
    sections = {section['label']: section['text'] for section in result['prompt_review']}
    assert DOCUMENT['characters'][0]['appearance'] in sections['Characters']
    assert 'Image 1: location for Rainy street' in sections['References']
    assert 'Image 2: identity for Main' in sections['References']
    assert 'The person stands at the doorway.' in sections['Frame action']
    assert result['prompt'] == result['graph']['4']['inputs']['text']


def test_outfit_reference_must_match_scene_wardrobe():
    wardrobe = {**REF, 'role': 'wardrobe', 'wardrobe': 'wrong'}
    with pytest.raises(ValueError, match='wardrobe'):
        still_recipe.compile_endpoint(DOCUMENT, draft(), [wardrobe], SHOT, 'start', seed=42)
    doc = copy.deepcopy(DOCUMENT)
    doc['scenes'][0]['wardrobe'] = {REF['entity']: 'W1'}
    result = still_recipe.compile_endpoint(doc, draft(), [{**wardrobe, 'wardrobe': 'W1'}], SHOT, 'start', seed=42)
    assert result['references'][0]['wardrobe'] == 'W1'


def test_changed_shot_action_invalidates_the_draft():
    compile_endpoint = still_recipe.compile_endpoint
    first = compile_endpoint(DOCUMENT, draft(), [REF], SHOT, 'start', seed=42)
    changed = copy.deepcopy(DOCUMENT)
    changed['shots'][0]['action'] = 'Main pauses before walking.'
    second = compile_endpoint(changed, draft(), [REF], SHOT, 'start', seed=42)
    assert first['input_digest'] != second['input_digest']


def test_editing_end_description_does_not_invalidate_start_draft():
    board = draft()
    first = still_recipe.compile_endpoint(DOCUMENT, board, [REF], SHOT, 'start', seed=42)
    board['shots'][SHOT]['end']['description'] = 'Later, the person enters the room.'
    second = still_recipe.compile_endpoint(DOCUMENT, board, [REF], SHOT, 'start', seed=42)
    assert first['input_digest'] == second['input_digest']


def test_prompt_uses_scene_outfit_and_visual_style():
    doc = copy.deepcopy(DOCUMENT)
    doc['scenes'][0]['wardrobe'] = {REF['entity']: 'W1'}
    text = still_recipe.compile_endpoint(doc, draft(), [REF], SHOT, 'start', seed=42)['graph']['4']['inputs']['text']
    assert 'navy textured blazer over dark shirt' in text
    assert 'Moody neo-noir, shallow depth of field' in text
    assert '24mm' in text


@pytest.mark.parametrize('name', ['../identity.png', '/tmp/identity.png', 'bad\x00name.png'])
def test_reference_name_must_be_a_contained_input_path(name):
    with pytest.raises(ValueError, match='staged input'):
        still_recipe.compile_endpoint(DOCUMENT, draft(), [{**REF, 'name': name}], SHOT, 'start', seed=42)


def test_changed_source_excerpt_invalidates_the_draft():
    first = still_recipe.compile_endpoint(DOCUMENT, draft(), [REF], SHOT, 'start', seed=42)
    changed = copy.deepcopy(DOCUMENT)
    changed['project']['source_text'] = changed['project']['source_text'].replace('rainy', 'sunny')
    second = still_recipe.compile_endpoint(changed, draft(), [REF], SHOT, 'start', seed=42)
    assert first['input_digest'] != second['input_digest']


def test_prompt_includes_declared_props_and_time():
    doc = copy.deepcopy(DOCUMENT)
    prop = {'id': 'DEMO-PRP-01', 'name': 'Letter', 'description': 'a folded blue letter'}
    doc['props'] = [prop]
    doc['scenes'][0]['props'] = [prop['id']]
    doc['shots'][0]['props'] = [prop['id']]
    text = still_recipe.compile_endpoint(doc, draft(), [REF], SHOT, 'start', seed=42)['graph']['4']['inputs']['text']
    assert 'a folded blue letter' in text
    assert 'night' in text


def test_end_frame_requires_a_reviewed_staged_start():
    board = draft()
    board['shots'][SHOT]['end']['description'] = 'The person has entered.'
    result = still_recipe.compile_endpoint(DOCUMENT, board, [REF], SHOT, 'end', seed=42)
    assert 'accepted_start_and_staging_required' in result['preflight_required']


def test_end_recipe_binds_start_frame_as_an_extra_reference():
    board = draft()
    board['shots'][SHOT]['end']['description'] = 'The person has entered.'
    start = {'name': 'start.png', 'sha256': 'c' * 64, 'role': 'start_frame',
             'entity': SHOT, 'authorized': True}
    result = still_recipe.compile_endpoint(DOCUMENT, board, [REF, start], SHOT, 'end', seed=42)
    assert result['references'][1] == start
    assert 'Image 2: starting frame for this shot.' in result['prompt']
    assert result['graph']['20']['inputs']['sha256'] == start['sha256']


def test_compiled_dependencies_do_not_change_when_project_is_edited():
    doc = copy.deepcopy(DOCUMENT)
    result = still_recipe.compile_endpoint(doc, draft(), [REF], SHOT, 'start', seed=42)
    action = result['dependencies']['shot']['action']
    doc['shots'][0]['action'] = 'A different action.'
    assert result['dependencies']['shot']['action'] == action

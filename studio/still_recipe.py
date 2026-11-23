"""Compile a local Klein reference-edit draft; submission and review are separate."""

import copy
import hashlib
import json
from pathlib import PurePosixPath
import re

from . import shot, storyboard, worker


def compile_endpoint(document, board, references, shot_id, endpoint, *, seed):
    storyboard.validate(document)
    if endpoint not in ('start', 'end'):
        raise ValueError('Choose the start or end frame')
    row = next((s for s in document['shots'] if s['id'] == shot_id), None)
    if row is None:
        raise ValueError('Choose a shot in this project')
    scene = next(s for s in document['scenes'] if s['id'] == row['scene'])
    target = board.get('shots', {}).get(shot_id, {}).get(endpoint, {})
    description = target.get('description', '')
    if not isinstance(description, str) or not description.strip():
        raise ValueError('Add an endpoint description before preparing a frame')
    if not references:
        raise ValueError('Choose at least one staged reference')
    refs = copy.deepcopy(references)
    for ref in refs:
        if ref.get('authorized') is not True:
            raise ValueError('Reference permission is required')
        name = ref.get('name', '')
        path = PurePosixPath(name)
        if not name or path.is_absolute() or '\\' in name or '\0' in name or any(part in ('', '.', '..') for part in name.split('/')):
            raise ValueError('Reference must be a staged input filename')
        if not re.fullmatch(r'[0-9a-f]{64}', ref.get('sha256', '')):
            raise ValueError('Reference needs a SHA-256 hash')
        if ref.get('role') not in ('identity', 'wardrobe', 'location', 'prop', 'start_frame') or not ref.get('entity'):
            raise ValueError('Reference needs a role and entity')
        allowed = {'identity': row['characters'], 'wardrobe': row['characters'],
                   'location': [row['location']], 'prop': row.get('props', []),
                   'start_frame': [shot_id] if endpoint == 'end' else []}
        if ref['entity'] not in allowed[ref['role']]:
            raise ValueError('Reference does not belong to this shot')
        if ref['role'] == 'wardrobe' and (
                not ref.get('wardrobe') or scene.get('wardrobe', {}).get(ref['entity']) != ref['wardrobe']):
            raise ValueError('Reference wardrobe does not match this scene')
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('Seed must be an unsigned 64-bit integer')

    width_ratio, height_ratio = (int(n) for n in document['project']['aspect'].split(':'))
    scale = (500_000 / (width_ratio * height_ratio)) ** 0.5
    width = max(16, round(width_ratio * scale / 16) * 16)
    height = max(16, round(height_ratio * scale / 16) * 16)
    location = next(item for item in document['locations'] if item['id'] == row['location'])
    entities = {item['id']: item['name'] for kind in ('characters', 'locations', 'props')
                for item in document.get(kind, [])}
    labels = ' '.join(f"Image {i}: starting frame for this shot." if ref['role'] == 'start_frame'
                      else f"Image {i}: {ref['role']} for {entities[ref['entity']]} ({ref['entity']})."
                      for i, ref in enumerate(refs, 1))
    people = []
    for person in document['characters']:
        if person['id'] not in row['characters']:
            continue
        outfit_id = scene.get('wardrobe', {}).get(person['id'])
        outfit = next((w['description'] for w in person.get('wardrobe', []) if w['id'] == outfit_id), '')
        people.append(f"{person['name']}: {person['appearance']}" + (f", {outfit}" if outfit else ''))
    scene_text = (f"Cinematic storyboard still, {row['shot_size']} shot, {row['angle']}, {row['lens']}, "
                  f"{row['subject']}, {location['description']}, {scene['time']}, {document['style_bible']['look']}.")
    prompt = scene_text + ' '
    if people:
        prompt += ' '.join(people) + '. '
    props = [f"{item['name']}: {item['description']}" for item in document.get('props', [])
             if item['id'] in row.get('props', [])]
    if props:
        prompt += ' '.join(props) + '. '
    prompt += f"{description.strip()} {labels}"
    values = {'gguf': 'unused', 'clip': 'qwen_3_4b.safetensors', 'clip_type': 'flux2',
              'vae': 'flux2-vae.safetensors', 'prompt': prompt, 'seed': seed,
              'output': f"storyboard_draft/{document['project']['code']}/{shot_id}/{endpoint}",
              'width': width, 'height': height, 'steps': 4, 'cfg': 1, 'sampler': 'euler'}
    graph = shot.fill(shot.load_template('flux2-t2i'), values)
    graph['1'] = {'class_type': 'UNETLoader', 'inputs': {
        'unet_name': 'flux-2-klein-4b-fp8.safetensors', 'weight_dtype': 'default'}}
    original_nodes = set(graph)
    worker.add_references(graph, [ref['name'] for ref in refs], 0.5)
    loaders = [node for key, node in graph.items() if key not in original_nodes and node['class_type'] == 'LoadImage']
    for node, ref in zip(loaders, refs, strict=True):
        node['class_type'] = 'StudioStoryboardReference'
        node['inputs']['sha256'] = ref['sha256']
    monitor_id = str(max(map(int, graph)) + 1)
    graph[monitor_id] = {'class_type': 'WorkflowMonitorBrain', 'inputs': {
        'enabled': True, 'run_label': f'storyboard:{shot_id}:{endpoint}', 'sample_interval': '2',
        'phase_overrides': '{}', 'analyze_when_finished': False}}
    entity_ids = {*row['characters'], *row.get('props', []), row['location']}
    source_span = scene['script_ref']
    dependencies = copy.deepcopy({'shot': row, 'scene': scene, 'style': document['style_bible'],
                    'scene_source': document['project']['source_text'][source_span['start']:source_span['end']],
                    'entities': [item for kind in ('characters', 'locations', 'props')
                                 for item in document.get(kind, [])
                                 if item['id'] in entity_ids]})
    payload = {'graph': graph, 'references': refs, 'shot_id': shot_id, 'endpoint': endpoint,
               'dependencies': dependencies}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    checks = ['source_hashes_not_verified', 'creative_review_required',
              'runtime_and_model_availability_not_verified', 'master_studio_handoff_not_verified']
    if endpoint == 'end':
        checks.append('accepted_start_and_staging_required')
    review = [{'label': 'Scene and camera', 'text': scene_text}]
    if people:
        review.append({'label': 'Characters', 'text': ' '.join(people)})
    if props:
        review.append({'label': 'Props', 'text': ' '.join(props)})
    review.extend([{'label': 'Frame action', 'text': description.strip()},
                   {'label': 'References', 'text': labels}])
    return {**payload, 'prompt': prompt, 'prompt_review': review, 'input_digest': digest,
            'status': 'draft', 'preflight_required': checks}

"""Deterministic Fantastic H3 shot preparation; no model loading or submission."""

import copy
import hashlib
import json
import re
from pathlib import Path

import production_validate


DIAGNOSTIC = {
    'id': 'h3-ref-diagnostic-v1', 'width': 608, 'height': 352, 'fps': 24,
    'steps': 20, 'scheduler': 'beta', 'sampler': 'sa_solver', 'denoise': 1,
    'shift_video': 12, 'shift_audio': 3, 'stack_pictures': 'every 4th',
    'stack_pictures_n': 8, 'ref_image_size': 'match', 'reference_fps': 24,
    'max_total_tokens': 0, 'voice_description_at_label': False,
    'models': {
        'diffusion_models': 'minimax_h3_ref2va_pruned_int8_convrot.safetensors',
        'text_encoders': 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors',
        'video_vae': 'minimax_h3_video_vae_int8_convrot.safetensors',
        'audio_vae': 'minimax_h3_audio_vae_fp32.safetensors',
    },
}

FOUR_VIEW_CANDIDATE = {
    **DIAGNOSTIC, 'id': 'h3-ref-four-view-candidate-v1',
    'stack_pictures': 'up to N', 'stack_pictures_n': 4,
}

SILENT_MEDIUM = {
    **FOUR_VIEW_CANDIDATE, 'id': 'h3-ref-silent-medium-v1',
    'width': 832, 'height': 480, 'delivery_audio': 'none',
}

FRAMING_PRESETS = {
    'establishing': {'shot_size': 'wide', 'lens': '35mm'},
    'environment_reaction': {'shot_size': 'medium-wide', 'lens': '35mm'},
    'character_action': {'shot_size': 'medium', 'lens': '50mm'},
    'portrait_reaction': {'shot_size': 'medium-close', 'lens': '85mm'},
    'prop_insert': {'shot_size': 'close-up', 'lens': '85mm'},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def asset_path(root, asset):
    path = Path(asset['path'])
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('asset path must be relative to the configured workspace')
    return Path(root) / path


def render_prompt(state):
    """Serialize the explicit-label fields emitted by this compiler, as Fantastic genRef does."""
    ref = state['ref']
    names = {re.match(r'<Subject \d+>', d['text'])[0]: d['name']
             for d in ref['subjectDefs'] if d.get('name') and d['text'].startswith('<Subject ')}
    definitions = []
    for definition in ref['subjectDefs']:
        line = definition['text'].strip()
        if definition.get('name') and line.startswith('<Subject '):
            line = line.rstrip('. ') + f". Their name is {definition['name']}."
        if line.startswith('<Audio ') and re.search(r'\(S\d+\)', line):
            subject = re.search(r'<Subject \d+>', line)
            if subject and subject[0] in names:
                line = line.rstrip('. ') + f". It is {names[subject[0]]}'s voice."
        definitions.append(line)
    return '\n\n'.join([
        'subject_definitions:\n' + '\n'.join(definitions),
        'summary:\n[' + ' + '.join(ref['summaryTypes']) + '] ' + ref['summaryText'].strip(),
        'retention_analysis:\n' + '\n'.join(
            x['label'] + (f" ({x['context'].strip()})" if x.get('context') else '') + f": {x['marker']} - {x['note'].strip()}"
            for x in ref['retention']),
        'detailed_description:\n' + '\n'.join(x.strip() for x in (ref['styleLine'], ref['detail']) if x.strip()),
        'overall_soundscape:\n' + ref['soundscape'].strip(),
        'non_diegetic_music:\n' + (ref['music'].strip() or 'N/A'),
    ])


def prompt_timing_warnings(state, duration_s):
    detail = state['ref']['detail'] if state['mode'] == 'REF' else state['imd']
    warnings = []
    for shot, minutes, seconds, milliseconds in re.findall(r'\[Shot (\d+)\]\s+At (\d{2}):(\d{2})\.(\d{3})', detail):
        cut = int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
        if cut >= duration_s:
            warnings.append(f'Shot {shot} starts at {cut:g}s, outside the {duration_s:.3f}s render; adjust the shot plan or duration.')
    return warnings


def compile_shot(doc, shot_id, binding, assets, recipe, root):
    problems = production_validate.check(doc)
    if problems:
        raise ValueError('\n'.join(problems))
    shot = next((s for s in doc['shots'] if s['id'] == shot_id), None)
    if shot is None:
        raise ValueError(f'unknown shot: {shot_id}')
    shot = copy.deepcopy(shot)
    controls = binding.get('shot_controls', {})
    unknown = set(controls) - {'framing', 'must_show', 'gaze_target', 'expression', 'screen_position', 'props'}
    if unknown:
        raise ValueError('unknown shot controls: ' + ', '.join(sorted(unknown)))
    if controls.get('framing'):
        if controls['framing'] not in FRAMING_PRESETS:
            raise ValueError('unknown framing preset: ' + controls['framing'])
        shot.update(FRAMING_PRESETS[controls['framing']])
    if shot.get('target'):
        raise ValueError('H3 binding cannot override a shot target; remove it explicitly')
    if recipe not in (DIAGNOSTIC, FOUR_VIEW_CANDIDATE, SILENT_MEDIUM) or doc['project']['fps'] != 24 or doc['project']['aspect'] != '16:9':
        raise ValueError('unsupported recipe; use a registered 24 fps, 16:9 H3 preset')
    mode = binding['audio_mode']
    if mode not in ('room_tone', 'generated_voiceover', 'visible_dialogue', 'silent'):
        raise ValueError(f'unsupported audio mode: {mode}')
    if shot.get('dialogue') and mode not in ('generated_voiceover', 'visible_dialogue'):
        raise ValueError('dialogue requires an explicit speech audio mode')
    selected = [(key, copy.deepcopy(assets[key])) for key in binding['assets']]
    if len(set(binding['assets'])) != len(selected):
        raise ValueError('duplicate asset binding')
    if recipe.get('delivery_audio') == 'none' and (mode != 'silent' or any(a['kind'] == 'audio' or a['role'] == 'voice' for _, a in selected)):
        raise ValueError('silent delivery cannot select voice references or an audio mode')
    prop_ids = set(shot.get('props', [])) | set(controls.get('props', []))
    for key, asset in selected:
        if asset.get('approved') is not True:
            raise ValueError(f'{key}: asset is not approved')
        path = asset_path(root, asset)
        if not path.is_file() or file_hash(path) != asset['sha256']:
            raise ValueError(f'{key}: missing asset or changed hash: {path}')
        if asset['kind'] not in ('picture', 'video', 'audio'):
            raise ValueError(f'{key}: unsupported reference kind')
        expected_kind = {'identity': 'video', 'voice': 'audio', 'location': 'picture', 'wardrobe': 'picture', 'prop': 'picture', 'background': 'video', 'ambience': 'video'}.get(asset['role'])
        if asset['kind'] != expected_kind or asset['selection']['kind'] != expected_kind:
            raise ValueError(f'{key}: unsupported role or selection kind')
        if asset['role'] in ('background', 'ambience') and asset['owner'] != shot['location']:
            raise ValueError(f"{key}: {asset['role']} does not belong to shot location")
        if asset['role'] in ('identity', 'wardrobe') and asset['owner'] not in shot['characters']:
            raise ValueError(f"{key}: {asset['role']} does not belong to shot cast")
        if asset['role'] == 'prop' and asset['owner'] not in prop_ids:
            raise ValueError(f'{key}: prop does not belong to shot')
        if expected_kind == 'picture':
            relative = Path(asset['path']).relative_to('input')
            filename = relative.as_posix() + ' [input]'
        else:
            filename = Path(asset['path']).relative_to('models/refmods').with_suffix('').as_posix()
        if asset['selection']['file'] != filename:
            raise ValueError(f'{key}: selection does not identify the hashed asset')
    media = [(k, a) for k, a in selected if a['kind'] == 'picture']
    mods = [(k, a) for k, a in selected if a['kind'] != 'picture']
    counts = {'picture': 0, 'video': 0, 'audio': 0}
    labels = {}
    for key, asset in media + mods:
        kind = asset['kind']
        counts[kind] += 1
        labels[key] = f'<{kind.title()} {counts[kind]}>'

    def resolve(role, owner):
        matches = [(k, a) for k, a in selected if a['role'] == role and a['owner'] == owner]
        if len(matches) != 1:
            raise ValueError(f'{owner}: exactly one {role} binding required')
        key, asset = matches[0]
        return labels[key], asset

    scene = next(s for s in doc['scenes'] if s['id'] == shot['scene'])
    characters = {c['id']: c for c in doc['characters']}
    subjects = {'characters': {cid: f'<Subject {i}>' for i, cid in enumerate(shot['characters'], 1)},
                'environment': f"<Subject {len(shot['characters']) + 1}>", 'wardrobe': {}}
    clothing_definitions = []
    defs, retention, character_text, speakers = [], [], [], {}
    for number, cid in enumerate(shot['characters'], 1):
        character = characters[cid]
        label, _ = resolve('identity', cid)
        subject = f'<Subject {number}>'
        defs.append({'text': f"{subject} is {character['name']}, whose identity is shown in {label}.", 'role': None, 'name': character['name']})
        retention.append({'label': subject, 'context': 'appears in [Shot 1]', 'marker': 'fully_preserved', 'note': f'Preserve facial identity from {label}; clothing follows the target outfit below.'})
        wardrobe_id = scene.get('wardrobe', {}).get(cid)
        wardrobes = {w['id']: w['description'] for w in character['wardrobe']}
        if wardrobe_id is None and len(wardrobes) == 1:
            wardrobe_id = next(iter(wardrobes))
        if wardrobe_id not in wardrobes:
            raise ValueError(f'{cid}: scene must select a valid wardrobe')
        wardrobe_refs = [(k, a) for k, a in selected if a['role'] == 'wardrobe' and a['owner'] == cid]
        clothing = wardrobes[wardrobe_id]
        for key, asset in wardrobe_refs:
            if asset.get('wardrobe_id') != wardrobe_id:
                raise ValueError(f'{cid}: wardrobe reference does not match the scene')
            clothing += f' as shown in {labels[key]}'
        if wardrobe_refs:
            clothing_subject = f"<Subject {len(shot['characters']) + 2 + len(clothing_definitions)}>"
            subjects['wardrobe'][cid] = clothing_subject
            clothing_definitions.append({'text': f'{clothing_subject} is the outfit: {clothing}.', 'role': None, 'name': ''})
            retention.append({'label': clothing_subject, 'context': 'appears in [Shot 1]', 'marker': 'attribute_transfer',
                              'note': f'Transfer its garments, colors and fit to {subject}; do not transfer the source person or background.'})
            clothing = f'{clothing_subject}, {clothing}'
        character_text.append(f"{subject}, {character['name']}, has the identity from {label}. {character['appearance']}. Wears {clothing}.")
    location, location_asset = resolve('location', shot['location'])
    environment = subjects['environment']
    location_record = next(loc for loc in doc['locations'] if loc['id'] == shot['location'])
    backgrounds = [(k, a) for k, a in selected if a['role'] in ('background', 'ambience')]
    sources = ', '.join([location] + [labels[k] for k, _ in backgrounds])
    defs.append({'text': f"{environment} is the {location_record['name']} environment shown in {sources}: {location_record['description']}",
                 'role': None, 'name': ''})
    defs.extend(clothing_definitions)
    defs.append({'text': f'{location} is the composition reference for [Shot 1]; it sets the viewpoint and framing of {environment}.',
                 'role': None, 'name': ''})
    retention.append({'label': environment, 'context': 'appears in [Shot 1]', 'marker': 'fully_preserved',
                      'note': f"Retain the room's visible layout, surfaces, furnishings and lighting. {location_record['description']} "
                              + ' '.join(a.get('instruction', '') for _, a in backgrounds)})
    retention.append({'label': location, 'context': '[Shot 1] composition', 'marker': 'weak_reference',
                      'note': location_asset.get('instruction', 'Follow its viewpoint and framing.')})
    dialogue = []
    for line in shot.get('dialogue', []):
        cid = line['character']
        if cid not in speakers:
            speakers[cid] = f'S{len(speakers) + 1}'
        voice, _ = resolve('voice', characters[cid]['voice'])
        voice_def = {'text': f"{voice} is the voice-timbre reference for {subjects['characters'][cid]} ({speakers[cid]}).", 'role': None, 'name': ''}
        if voice_def not in defs:
            defs.append(voice_def)
            retention.append({'label': voice, 'context': '', 'marker': 'reference', 'note': 'Preserve voice timbre and accent; do not copy the reference words or background sound.'})
        delivery = line.get('delivery', 'naturally and clearly')
        channel = 'in off-screen voiceover, with lips closed' if mode == 'generated_voiceover' else 'on screen, with synchronized speech'
        dialogue.append(f"{subjects['characters'][cid]} ({speakers[cid]}) says once {channel}, {delivery}: <d>[{doc['project'].get('language', 'en')}] {line['line']}</d>")
    lighting = shot.get('lighting', scene.get('lighting', doc['style_bible']['lighting_default']))
    composition = []
    if controls.get('must_show'):
        composition.append('Keep visible in the same frame: ' + '; '.join(controls['must_show']) + '. Frame wide enough to include these elements.')
    for key, title in [('gaze_target', 'Gaze target'), ('expression', 'Expression'), ('screen_position', 'Subject screen position')]:
        if controls.get(key):
            composition.append(f'{title}: {controls[key]}.')
    props = {p['id']: p for p in doc.get('props', [])}
    for prop_id in sorted(prop_ids):
        if prop_id not in props:
            raise ValueError(f'unknown shot prop: {prop_id}')
        composition.append(f"Recurring prop {props[prop_id]['name']}: {props[prop_id]['description']}.")
        prop_refs = [(k, a) for k, a in selected if a['role'] == 'prop' and a['owner'] == prop_id]
        if recipe == SILENT_MEDIUM and len(prop_refs) != 1:
            raise ValueError(f'{prop_id}: exactly one prop picture required for silent proof')
        for key, asset in prop_refs:
            composition.append(f"Match the prop reference {labels[key]} for shape, fold and color; do not transfer its background or camera viewpoint.")
    for key, asset in mods:
        if asset['role'] in ('background', 'ambience'):
            composition.append(f'{environment} uses the environment design from {labels[key]}; camera composition follows {location}.')
    move = shot['camera_move']
    description = ' '.join([
        f"[Shot 1] One continuous {shot['shot_size']} shot, {shot['angle']}, {shot['lens']} lens.",
        'Camera: ' + ' '.join(filter(None, [move.get('speed'), move['type']])) + '. ' + move.get('note', ''),
        f'The scene is inside {environment}, {location_record["description"]} Viewpoint and framing follow {location}.', *character_text, shot['action'], *composition, *dialogue,
        binding.get('blocking', ''), ' '.join(doc['style_bible'].get('camera_rules', [])),
        ' '.join(filter(None, [doc['style_bible'].get('negative_prompt'), shot.get('negative_prompt')])),
    ]).strip()
    sound = {'room_tone': 'Quiet indoor room tone. No speech or music.', 'silent': 'No speech, music or sound effects.',
             'generated_voiceover': 'One clear off-screen voice over faint room tone. No other words or music.',
             'visible_dialogue': 'Only the specified dialogue over faint room tone. No music.'}[mode]
    state = {'version': 1, 'mode': 'REF', 'off': {}, 'duration': shot['duration_s'], 'p2Shot': 1, 'lastShot': 1,
             'imd': '', 'soundscape': '', 'music': 'N/A', 'ref': {
                 'subjectDefs': defs, 'summaryTypes': ['reference generation'] + (['audio reference'] if dialogue else []),
                 'summaryText': f"{scene['summary']} The setting is {environment}, with the composition of {location}. "
                                + ('The visible cast is ' + ', '.join(subjects['characters'].values()) + '.' if shot['characters'] else 'The setting is unoccupied.'),
                 'retention': retention, 'styleLine': f"{doc['style_bible']['look']}. Lighting: {lighting['key']}, {lighting['quality']}.",
                 'detail': description, 'soundscape': sound, 'music': 'N/A'}}
    picks = []
    for number, (key, asset) in enumerate(mods, 1):
        selection = copy.deepcopy(asset['selection'])
        channel = 'audio' if asset['kind'] == 'audio' else 'visual'
        picks.append({'uid': number, 'name': selection['file'], 'label': key, 'on': True, 'preview': None,
                      channel: {**selection, 'mode': 'weight', 'w': 1, 's': 1, 'c': 1}})
    requested = max(5, round(shot['duration_s'] * recipe['fps']))
    frames = requested + (5 - requested % 17) % 17
    warnings = []
    warnings.extend(prompt_timing_warnings(state, frames / recipe['fps']))
    if recipe == FOUR_VIEW_CANDIDATE:
        warnings.append('Four-view candidate: text-encoder memory and likeness require runtime review; all identity latents remain intact.')
    if sum(len(d['line'].split()) for d in shot.get('dialogue', [])) > shot['duration_s'] * 2.5:
        warnings.append('Dialogue may not fit the requested duration; text was preserved.')
    if frames != 56:
        warnings.append('Duration differs from the 56-frame baseline; resource and quality qualification required.')
    if mode == 'visible_dialogue':
        warnings.append('Visible dialogue has not been lip-sync qualified.')
    warnings.extend(binding.get('warnings', []))
    result = {'schema_version': 1, 'shot_id': shot_id, 'source_sha256': digest(doc), 'shot': shot,
              'binding': binding, 'assets': dict(selected), 'recipe': recipe, 'labels': labels, 'subjects': subjects,
              'builder_state': state, 'prompt_text': render_prompt(state), 'frames': frames,
              'duration_actual_s': frames / recipe['fps'], 'seed': binding.get('seed', 0),
              'media_state': [a['selection'] for _, a in media], 'stack_state': {'picks': picks, 'budget': 0},
              'warnings': warnings, 'review_status': 'unreviewed'}
    result['fingerprint'] = digest(result)
    return result

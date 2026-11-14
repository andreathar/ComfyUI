"""Deterministic Fantastic H3 shot preparation; no model loading or submission."""

import copy
import hashlib
import json
import os
from pathlib import Path
import re

import yaml

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

FOUR_VIEW_CANDIDATE = {**DIAGNOSTIC, 'id': 'h3-ref-four-view-candidate-v1',
                       'stack_pictures': 'up to N', 'stack_pictures_n': 4}
SILENT_MEDIUM = {**FOUR_VIEW_CANDIDATE, 'id': 'h3-ref-silent-medium-v1',
                 'width': 832, 'height': 480, 'delivery_audio': 'none'}


def model_folders(root, category):
    root = Path(root).resolve()
    aliases = {'diffusion_models': ['unet', 'diffusion_models'], 'text_encoders': ['text_encoders', 'clip']}
    paths = [root / 'models' / name for name in aliases.get(category, [category])]
    config = root / 'extra_model_paths.yaml'
    for group in (yaml.safe_load(config.read_text()) or {}).values() if config.is_file() else []:
        if not group:
            continue
        base = Path(os.path.expandvars(os.path.expanduser(group.get('base_path', str(root)))))
        if not base.is_absolute():
            base = root / base
        for key, value in group.items():
            if {'unet': 'diffusion_models', 'clip': 'text_encoders'}.get(key, key) != category:
                continue
            for folder in value.splitlines():
                if not folder.strip():
                    continue
                path = Path(os.path.normpath(base / folder.strip()))
                if path in paths:
                    if not group.get('is_default'):
                        continue
                    paths.remove(path)
                if group.get('is_default'):
                    paths.insert(0, path)
                else:
                    paths.append(path)
    return paths


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
    if path.parts[:2] == ('models', 'refmods'):
        relative = path.relative_to('models/refmods')
        folders = model_folders(root, 'refmods')
        return next((p / relative for p in folders if (p / relative).is_file()), folders[0] / relative)
    return Path(root) / path


def render_prompt(state):
    ref = state['ref']
    definitions = []
    for item in ref['subjectDefs']:
        if item.get('off'):
            continue
        line = item['text'].strip()
        if item.get('name') and re.match(r'<Subject \d+>', line):
            line = line.rstrip('. ') + f". Their name is {item['name']}."
        definitions.append(line)
    return '\n\n'.join([
        'subject_definitions:\n' + '\n'.join(definitions),
        'summary:\n[' + ' + '.join(ref['summaryTypes']) + '] ' + ref['summaryText'],
        'retention_analysis:\n' + '\n'.join(f"{x['label']}" + (f" ({x['context']})" if x.get('context') else '') + f": {x['marker']} - {x['note'].strip()}" for x in ref['retention'] if not x.get('off')),
        'detailed_description:\n' + ref['styleLine'] + '\n' + ref['detail'],
        'overall_soundscape:\n' + ref['soundscape'],
        'non_diegetic_music:\n' + ref['music'],
    ])


def prompt_timing_warnings(state, duration):
    return [f'Shot {shot}: cut at {int(minutes) * 60 + float(seconds):g}s exceeds render duration {duration:g}s.'
            for shot, minutes, seconds in re.findall(r'\[Shot (\d+)\] At (\d+):([\d.]+)', state['ref']['detail'])
            if int(minutes) * 60 + float(seconds) >= duration]


def compile_shot(doc, shot_id, binding, assets, recipe, root):
    problems = production_validate.check(doc)
    if problems:
        raise ValueError('\n'.join(problems))
    shot = next((s for s in doc['shots'] if s['id'] == shot_id), None)
    if shot is None:
        raise ValueError(f'unknown shot: {shot_id}')
    if shot.get('target'):
        raise ValueError('H3 binding cannot override a shot target; remove it explicitly')
    shot = copy.deepcopy(shot)
    if recipe not in (DIAGNOSTIC, FOUR_VIEW_CANDIDATE, SILENT_MEDIUM) or doc['project']['fps'] != 24 or doc['project']['aspect'] != '16:9':
        raise ValueError('unregistered H3 recipe; candidate changes need explicit qualification')
    controls = binding.get('shot_controls', {})
    unknown = controls.keys() - {'framing', 'must_show', 'gaze_target', 'expression', 'screen_position', 'props', 'environment_override', 'reference_layout'}
    if unknown:
        raise ValueError(f'unknown shot control: {sorted(unknown)}')
    reference_layout = controls.get('reference_layout', 'composition')
    if reference_layout not in ('composition', 'setting', 'first_frame'):
        raise ValueError(f'unknown reference layout: {reference_layout}')
    if controls.get('framing') == 'environment_reaction':
        shot.update(shot_size='medium-wide', lens='35mm')
    elif controls.get('framing'):
        raise ValueError(f"unknown shot control framing: {controls['framing']}")
    mode = binding['audio_mode']
    if mode not in ('room_tone', 'generated_voiceover', 'visible_dialogue', 'silent'):
        raise ValueError(f'unsupported audio mode: {mode}')
    if shot.get('dialogue') and mode not in ('generated_voiceover', 'visible_dialogue'):
        raise ValueError('dialogue requires an explicit speech audio mode')
    selected = [(key, copy.deepcopy(assets[key])) for key in binding['assets']]
    if recipe.get('delivery_audio') == 'none' and mode != 'silent':
        raise ValueError('silent recipe requires silent audio mode')
    if len(set(binding['assets'])) != len(selected):
        raise ValueError('duplicate asset binding')
    for key, asset in selected:
        if asset.get('input_use_authorized', asset.get('approved')) is not True:
            raise ValueError(f'{key}: asset is not approved')
        path = asset_path(root, asset)
        if not path.is_file() or file_hash(path) != asset['sha256']:
            raise ValueError(f'{key}: missing asset or changed hash: {path}')
        if asset['kind'] not in ('picture', 'video', 'audio'):
            raise ValueError(f'{key}: unsupported reference kind')
        expected_kind = {'identity': 'video', 'voice': 'audio', 'location': 'picture', 'wardrobe': 'picture', 'prop': 'picture', 'background': 'video', 'ambience': 'video'}.get(asset['role'])
        if mode == 'silent' and asset['role'] == 'voice':
            raise ValueError('silent shot cannot bind a voice reference')
        if asset['role'] in ('identity', 'wardrobe') and asset['owner'] not in shot['characters']:
            raise ValueError(f"{key}: {asset['role']} owner is outside the shot cast")
        if asset['role'] in ('location', 'background', 'ambience') and asset['owner'] != shot['location']:
            raise ValueError(f"{key}: {asset['role']} owner does not match shot location")
        if asset['role'] == 'prop' and asset['owner'] not in shot.get('props', []):
            raise ValueError(f'{key}: prop owner is not declared in the shot')
        if asset['kind'] != expected_kind or asset['selection']['kind'] != expected_kind:
            raise ValueError(f'{key}: unsupported role or selection kind')
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
    defs, retention, character_text, speakers = [], [], [], {}
    for number, cid in enumerate(shot['characters'], 1):
        character = characters[cid]
        label, _ = resolve('identity', cid)
        subject = f'<Subject {number}>'
        definition = {'text': f"{subject} is {character['name']}, whose facial identity is shown in {label}.", 'role': None, 'name': character['name']}
        defs.append(definition)
        retention.append({'label': subject, 'context': 'appears in [Shot 1]', 'marker': 'partially_preserved',
                          'note': f'Facial identity only from {label}; use the wardrobe, pose and gaze specified for this shot.'})
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
        definition['text'] += f' Clothing: {clothing}.'
        for key, asset in wardrobe_refs:
            if asset.get('instruction'):
                definition['text'] += f" For {labels[key]}: {asset['instruction']}"
        character_text.append(f"{subject} (S{number}): {character['appearance']}. Wears {clothing}.")
        speakers[cid] = f'S{number}'
    location, primary_asset = resolve('location', shot['location'])
    environment = f"<Subject {len(shot['characters']) + 1}>"
    location_doc = next(loc for loc in doc['locations'] if loc['id'] == shot['location'])
    backgrounds = [(k, a) for k, a in selected if a['role'] in ('background', 'ambience')]
    environment_sources = ', '.join([location] + [labels[k] for k, _ in backgrounds])
    env_desc = controls.get('environment_override') or location_doc['description']
    defs.append({'text': f"{environment} is the environment shown in {environment_sources}: {env_desc}."})
    retention_note = (
        'Preserve tabletop wood grain, paper fold geometry, close-up camera distance and lighting; ' + primary_asset.get('instruction', '')
        if controls.get('environment_override')
        else 'Preserve architecture, furniture and lighting; use the primary picture for camera layout. ' + ' '.join(a.get('instruction', '') for _, a in backgrounds)
    ).strip()
    if reference_layout == 'setting':
        retention_note = 'Use setting appearance only: materials, architecture and lighting. Follow the shot framing and camera instructions below; the reference does not fix the viewpoint or subject placement.'
        retention_note += ' ' + ' '.join(a.get('instruction', '') for _, a in backgrounds)
    elif reference_layout == 'first_frame':
        retention_note = 'Use the picture for the opening composition and visible object geometry; continue with the camera and action described for this shot.'
        retention_note += ' ' + ' '.join(a.get('instruction', '') for _, a in backgrounds)
    if reference_layout in ('setting', 'first_frame') or not controls.get('environment_override'):
        retention_note = ' '.join(filter(None, [retention_note.strip(), primary_asset.get('instruction', '')]))
    retention.append({'label': environment, 'context': 'appears in [Shot 1]', 'marker': 'partially_preserved',
                      'note': retention_note})
    if reference_layout == 'first_frame':
        defs.append({'text': f'{location} is the first frame of [Shot 1], providing the opening composition and visible object shapes.'})
        retention.append({'label': location, 'context': 'first frame of [Shot 1]', 'marker': 'fully_preserved',
                          'note': 'Match the opening image, then develop the specified shot without a cut.'})
    prop_text = []
    props = {p['id']: p for p in doc.get('props', [])}
    for key, asset in media:
        if asset['role'] == 'prop':
            prop = props[asset['owner']]
            subject = f'<Subject {len(shot["characters"]) + 2 + len(prop_text)}>'
            defs.append({'text': f"{subject} is {prop['description']}, with appearance from {labels[key]}."})
            retention.append({'label': subject, 'context': 'appears in [Shot 1]', 'marker': 'partially_preserved',
                              'note': asset.get('instruction', 'Preserve the object appearance; use the shot instructions for its placement.')})
            prop_text.append(f'Use prop reference {labels[key]} for {subject}.')
    if set(controls.get('props', [])) - set(shot.get('props', [])):
        raise ValueError('shot control props must be declared in the shot')
    dialogue = []
    for line in shot.get('dialogue', []):
        cid = line['character']
        voice, _ = resolve('voice', characters[cid]['voice'])
        voice_def = {'text': f"{voice} is a voice timbre reference for speaker ({speakers[cid]}). It is {characters[cid]['name']}'s voice.", 'role': None, 'name': ''}
        if voice_def not in defs:
            defs.append(voice_def)
            retention.append({'label': voice, 'context': '', 'marker': 'reference', 'note': 'Preserve voice timbre and accent; do not copy the reference words or background sound.'})
        delivery = line.get('delivery', 'naturally and clearly')
        channel = 'in off-screen voiceover, with lips closed' if mode == 'generated_voiceover' else 'on screen, with synchronized speech'
        dialogue.append(f"{characters[cid]['name']} ({speakers[cid]}) says once {channel}, {delivery}: <d>[{doc['project'].get('language', 'en')}] {line['line']}</d>")
    lighting = {**scene.get('lighting', doc['style_bible']['lighting_default']), **shot.get('lighting', {})}
    move = shot['camera_move']
    layout_description = {
        'composition': f'Environment: {environment}, primary camera layout from {location}.',
        'first_frame': f'Environment: {environment}. Opening composition from {location}; then follow the specified camera movement.',
        'setting': f'Environment: {environment}; follow this shot\'s explicit framing and movement rather than the reference viewpoint.',
    }[reference_layout]
    description = ' '.join([
        f"[Shot 1] One continuous {shot['shot_size']} shot, {shot['angle']}, {shot['lens']} lens.",
        'Camera: ' + ' '.join(filter(None, [move.get('speed'), move['type']])) + '. ' + move.get('note', ''),
        layout_description,
        *character_text, *prop_text, shot['action'], *dialogue,
        ('Keep visible in the same frame: ' + '; '.join(controls['must_show']) + '.') if controls.get('must_show') else '',
        *[f'{label}: {controls[key]}.' for key, label in [('gaze_target', 'Gaze target'), ('expression', 'Expression'), ('screen_position', 'Screen position')] if key in controls],
        binding.get('blocking', ''), ' '.join(doc['style_bible'].get('camera_rules', [])),
        ' '.join(filter(None, [doc['style_bible'].get('negative_prompt'), shot.get('negative_prompt')])),
    ]).strip()
    sound = {'room_tone': 'Quiet indoor room tone. No speech or music.', 'silent': 'No speech, music or sound effects.',
             'generated_voiceover': 'One clear off-screen voice over faint room tone. No other words or music.',
             'visible_dialogue': 'Only the specified dialogue over faint room tone. No music.'}[mode]
    state = {'version': 1, 'mode': 'REF', 'off': {}, 'duration': shot['duration_s'], 'p2Shot': 1, 'lastShot': 1,
             'imd': '', 'soundscape': '', 'music': 'N/A', 'ref': {
                 'subjectDefs': defs, 'summaryTypes': (['keyframe completion'] if reference_layout == 'first_frame' else []) + ['reference generation'] + (['audio reference'] if dialogue else []), 'summaryText': f"In {environment}, {shot['action']}",
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
    if recipe != DIAGNOSTIC:
        warnings.append('Recipe is a candidate; resource and visual qualification remain pending.')
    if sum(len(d['line'].split()) for d in shot.get('dialogue', [])) > shot['duration_s'] * 2.5:
        warnings.append('Dialogue may not fit the requested duration; text was preserved.')
    if frames != 56:
        warnings.append('Duration differs from the 56-frame baseline; resource and quality qualification required.')
    if mode == 'visible_dialogue':
        warnings.append('Visible dialogue has not been lip-sync qualified.')
    warnings.extend(binding.get('warnings', []))
    warnings.extend(prompt_timing_warnings(state, frames / recipe['fps']))
    result = {'schema_version': 1, 'shot_id': shot_id, 'source_sha256': digest(doc), 'shot': shot,
              'binding': binding, 'assets': dict(selected), 'recipe': recipe, 'labels': labels, 'subjects': {'environment': environment},
              'builder_state': state, 'prompt_text': render_prompt(state), 'frames': frames,
              'duration_actual_s': frames / recipe['fps'], 'seed': binding.get('seed', 0),
              'media_state': [a['selection'] for _, a in media], 'stack_state': {'picks': picks, 'budget': 0},
              'warnings': warnings, 'review_status': 'unreviewed'}
    result['fingerprint'] = digest(result)
    return result

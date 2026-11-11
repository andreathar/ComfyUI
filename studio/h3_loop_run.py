"""Validate bundle-driven live graph inputs; does not submit or qualify renders."""

import hashlib

import h3_loop


def check_graph(bundle, graph):
    payload = {key: value for key, value in bundle.items() if key != 'fingerprint'}
    if hashlib.sha256(h3_loop.canonical(payload).encode()).hexdigest() != bundle.get('fingerprint'):
        raise ValueError('bundle fingerprint mismatch')
    recipe = bundle['shots'][0]['recipe']
    expected = {
        '2': ('UNETLoader', {'unet_name': recipe['models']['diffusion_models']}),
        '3': ('MiniMaxH3SigmaShift', {'model': ['2', 0], 'shift_video': recipe['shift_video'], 'shift_audio': recipe['shift_audio']}),
        '4': ('CLIPLoader', {'clip_name': recipe['models']['text_encoders'], 'type': 'minimax'}),
        '5': ('VAELoader', {'vae_name': recipe['models']['video_vae']}),
        '7': ('MiniMaxH3RefModStack', {'stack_state': ['36', 1]}),
        '9': ('MiniMaxH3FantasticRefModTextEncode', {
            'clip': ['4', 0], 'vae': ['5', 0], 'mods': ['7', 0], 'references': ['21', 0],
            'prompt': ['35', 4], 'length': ['35', 6], 'width': ['35', 8], 'height': ['35', 9],
            **{key: recipe[key] for key in ('ref_image_size', 'reference_fps', 'max_total_tokens', 'voice_description_at_label', 'stack_pictures', 'stack_pictures_n')}}),
        '13': ('KSamplerSelect', {'sampler_name': recipe['sampler']}),
        '14': ('BasicScheduler', {'model': ['3', 0], 'scheduler': recipe['scheduler'], 'denoise': recipe['denoise'], 'steps': ['35', 7]}),
        '15': ('RandomNoise', {'noise_seed': ['35', 5]}),
        '21': ('MiniMaxH3MediaLoader', {'media_state': ['36', 2]}),
        '31': ('DynamicScriptNode', {'code': h3_loop.PLAN_CODE, 'input_0': ['30', 0], 'output_ports_count': 8, 'use_module_cache': False}),
        '32': ('MiniMaxH3GenerationProfile', {'scene_continuity': 'Independent scenes', 'audio_profile': 'No final audio'}),
        '33': ('MiniMaxH3ChainPlanModern', {'chain_policy': ['32', 0], 'plan_json_input': ['31', 1],
               'generation_fingerprint': ['31', 2], 'run_name': ['31', 3], 'width': ['31', 4], 'height': ['31', 5],
               'encode_mode': 'video', 'video_blend_frames': 0}),
        '36': ('DynamicScriptNode', {'code': h3_loop.SELECT_CODE, 'input_0': ['30', 0], 'input_1': ['35', 1], 'use_module_cache': False}),
        '37': ('MiniMaxH3LoopTrim', {'fps': ['31', 8], 'trim_frames': 0}),
        '38': ('MiniMaxH3ChainSegmentSave', {}),
        '40': ('MiniMaxH3ChainAssemble', {'audio_source': ['31', 6], 'output_subfolder': ['31', 7],
               'filename': 'draft', 'copy_to_output': True, 'delete_checkpoints_after_assembly': False}),
    }
    errors = []
    if recipe.get('delivery_audio') != 'none':
        errors.append('graph contract requires a silent delivery recipe')
    for node_id, (class_type, inputs) in expected.items():
        node = graph.get(node_id)
        if node is None or node.get('class_type') != class_type:
            errors.append(f'node {node_id}: expected {class_type}')
            continue
        for name, value in inputs.items():
            if node['inputs'].get(name) != value:
                errors.append(f'{node_id}.{name}: expected {value!r}')
    for node_id, name in [('9', 'audio_vae'), ('37', 'audio'), ('38', 'audio')]:
        if name in graph.get(node_id, {}).get('inputs', {}):
            errors.append(f'{node_id}.{name}: silent graph must disconnect audio')
    for node_id, node in graph.items():
        if node['class_type'] == 'VAEDecodeAudio':
            errors.append(f'node {node_id}: audio decode remains active')
    return errors

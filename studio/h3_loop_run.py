"""Track bundle-driven panel submissions without submitting or approving renders."""

from contextlib import contextmanager
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

import film
import h3_loop
import h3_preflight
import h3_recipe as h3


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
        if node['class_type'] == 'MiniMaxH3FantasticEditComposite':
            errors.append(f'node {node_id}: edit composite pass-through must be removed from silent generation')
        if node['class_type'] == 'WorkflowMonitorBrain':
            m_inputs = node.get('inputs', {})
            if m_inputs.get('enabled') is not True:
                errors.append(f'node {node_id}: WorkflowMonitorBrain must have enabled=True when present')
            if str(m_inputs.get('sample_interval', '2')) not in ('1', '2', '5'):
                errors.append(f'node {node_id}: unsupported WorkflowMonitorBrain sample_interval')
    return errors


def prepare(root, bundle, graph, models, workspace):
    errors = check_graph(bundle, graph)
    if errors:
        raise ValueError('\n'.join(errors))
    # Re-export also checks run paths, duplicate IDs and recipe consistency.
    if h3_loop.export(bundle['shots'], bundle['run_name'], bundle['output_subfolder']) != bundle:
        raise ValueError('unsupported production bundle')
    recipe = bundle['shots'][0]['recipe']
    state = {'schema_version': 1, 'bundle': bundle, 'graph': graph, 'models': models,
             'workspace': str(Path(workspace).resolve()), 'prompt_id': None, 'review': None,
             'shot_ids': [shot['shot_id'] for shot in bundle['shots']],
             'delivery': {'width': recipe['width'], 'height': recipe['height'], 'fps': recipe['fps'],
                          'frames': sum(shot['frames'] for shot in bundle['shots']), 'audio': 'none'}}
    state['identity_sha256'] = _identity(state)
    path = Path(root) / bundle['run_name']
    path.mkdir(parents=True, exist_ok=False)
    film.event(state, 'prepared')
    film.write_json(path / 'run.json', state)
    return path


def _identity(state):
    return h3.digest({key: state[key] for key in
                      ('bundle', 'graph', 'models', 'workspace', 'shot_ids', 'delivery')})


@contextmanager
def _locked_run(path):
    path = Path(path)
    with (path / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = film.read_json(path / 'run.json')
        if _identity(state) != state['identity_sha256']:
            raise ValueError('run identity changed; prepare a new run')
        yield state
        film.write_json(path / 'run.json', state)


def _preflight(state, resource_snapshot, registered_nodes):
    bundle, graph, workspace = state['bundle'], state['graph'], state['workspace']
    errors = check_graph(bundle, graph)
    routes = {
        '12': ('BasicGuider', {'model': ['3', 0], 'conditioning': ['9', 0]}),
        '16': ('SamplerCustomAdvanced', {'noise': ['15', 0], 'guider': ['12', 0], 'sampler': ['13', 0],
                                        'sigmas': ['14', 0], 'latent_image': ['9', 2]}),
        '17': ('VAEDecode', {'samples': ['16', 0], 'vae': ['5', 0]}),
        '34': ('MiniMaxH3ChainLoopStart', {'plan': ['33', 0], 'start_clip': 1, 'scene_range': '', 'verify_resume_history': True}),
        '35': ('MiniMaxH3ChainCurrent', {'state': ['34', 1], 'align_audio_reference': False}),
        '36': ('DynamicScriptNode', {'output_ports_count': 2}),
        '37': ('MiniMaxH3LoopTrim', {'images': ['17', 0], 'state': ['35', 0]}),
        '38': ('MiniMaxH3ChainSegmentSave', {'state': ['35', 0], 'images': ['37', 0], 'sampled_latent': ['16', 0]}),
        '39': ('MiniMaxH3ChainLoopEnd', {'execution_mode': 'recursive', 'flow': ['34', 0], 'state': ['35', 0],
                                      'images': ['37', 0], 'sampled_latent': ['16', 0], 'segment': ['38', 0]}),
        '40': ('MiniMaxH3ChainAssemble', {'manifest': ['39', 0], 'blend_schedule': 'plan',
                                       'boundary_tone_match': 'off', 'color_stabilization': 'off'}),
    }
    for node_id, (class_type, inputs) in routes.items():
        node = graph.get(node_id, {})
        if node.get('class_type') != class_type or any(node.get('inputs', {}).get(k) != v for k, v in inputs.items()):
            errors.append(f'node {node_id}: sampling/loop route does not match the full-run contract')
    if graph.get('39', {}).get('inputs', {}).get('between_scene_cleanup') not in ('unload_models', 'fresh_scene'):
        errors.append('node 39: between_scene_cleanup must be unload_models or fresh_scene for 6 GB VRAM safety')
    loader = graph.get('30', {})
    source = loader.get('inputs', {}).get('file_path')
    if loader.get('class_type') != 'DynamicLoadTextFileNode' or not isinstance(source, str):
        errors.append('bundle source: expected the production file loader at node 30')
    else:
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = Path(workspace) / source_path
        if not source_path.is_file() or film.read_json(source_path) != bundle:
            errors.append('bundle source changed or missing')
    files = h3_preflight.check(workspace, state['models'], {})
    errors.extend(files['errors'])
    checked_assets = set()
    for shot in bundle['shots']:
        for name, asset in shot['assets'].items():
            path = h3.asset_path(workspace, asset)
            key = (path.resolve(), asset['sha256'])
            if key not in checked_assets:
                if not path.is_file() or h3.file_hash(path) != asset['sha256']:
                    errors.append(f'{shot["shot_id"]}/{name}: asset missing or hash changed')
                checked_assets.add(key)
            if asset.get('input_use_authorized', asset.get('approved')) is not True:
                errors.append(f'{shot["shot_id"]}/{name}: input use is not authorized')
    if registered_nodes is None:
        errors.append('live node registration is required')
    else:
        needed = {node['class_type'] for node in graph.values()}
        errors.extend(f'node unavailable: {name}' for name in sorted(needed - set(registered_nodes)))
    resources = h3_preflight.resources(resource_snapshot)
    errors.extend(resources['errors'])
    if errors:
        raise ValueError('\n'.join(errors))
    return {'checked_at': time.time(), 'identity_sha256': state['identity_sha256'],
            'graph_sha256': h3.digest(graph), 'registered_nodes': sorted(registered_nodes),
            'resources': resources,
            'warnings': ['Model pins checked by file size and mtime; full hashes were pinned separately.',
                         'This is submission preflight, not peak-memory qualification or visual approval.']}


def preflight(path, resource_snapshot, registered_nodes):
    with _locked_run(path) as state:
        if state['status'] not in ('prepared', 'preflight_passed'):
            raise ValueError('preflight requires an unsubmitted run')
        state['preflight'] = _preflight(state, resource_snapshot, registered_nodes)
        film.event(state, 'preflight_passed')
        return state['preflight']


def mark_submitting(path, graph, resource_snapshot, registered_nodes):
    with _locked_run(path) as state:
        if state['status'] != 'preflight_passed':
            raise ValueError('run requires preflight; submitted or unknown runs cannot be retried')
        if not 0 <= time.time() - state['preflight']['checked_at'] <= 120:
            raise ValueError('preflight expired; check the unsubmitted run again')
        if graph != state['graph']:
            raise ValueError('live graph changed; prepare a new run')
        state['preflight'] = _preflight(state, resource_snapshot, registered_nodes)
        state['submitting_at'] = time.time()
        film.event(state, 'submitting')


def bind_prompt(path, prompt_id):
    if not isinstance(prompt_id, str) or not prompt_id.strip():
        raise ValueError('prompt_id is required')
    with _locked_run(path) as state:
        if state['prompt_id'] == prompt_id:
            return
        if state['prompt_id'] or state['status'] not in ('submitting', 'unknown'):
            raise ValueError('cannot replace prompt_id or bind an unsubmitted run')
        state['prompt_id'] = prompt_id
        film.event(state, 'queued', prompt_id=prompt_id)


def mark_unknown(path, reason):
    if not reason:
        raise ValueError('unknown submission requires a reason')
    with _locked_run(path) as state:
        if state['status'] not in ('submitting', 'unknown'):
            raise ValueError('only an unacknowledged submission can become unknown')
        film.event(state, 'unknown', reason=reason)


def recover_submission(path, history):
    """Bind one exact, recent history entry; never retry or infer completion."""
    with _locked_run(path) as state:
        if state['prompt_id']:
            return state
        if state['status'] not in ('submitting', 'unknown'):
            raise ValueError('no unacknowledged submission to recover')
        candidates = []
        for prompt_id, record in history.items():
            prompt = record.get('prompt', [])
            if len(prompt) < 3 or prompt[1] != prompt_id or prompt[2] != state['graph']:
                continue
            starts = [data.get('timestamp') for name, data in record.get('status', {}).get('messages', [])
                      if name == 'execution_start' and data.get('prompt_id') == prompt_id]
            if any(isinstance(stamp, (int, float)) and
                   state['submitting_at'] <= stamp / 1000 <= time.time() + 2 for stamp in starts):
                candidates.append(prompt_id)
        if len(candidates) == 1:
            state['prompt_id'] = candidates[0]
            state['submission_history'] = history[candidates[0]]
            film.event(state, 'queued', prompt_id=candidates[0], recovered_from_history=True)
        else:
            film.event(state, 'unknown', reason='history has no unique recent exact submission', candidates=candidates)
        return state


def _output_path(root, relative):
    root = Path(root).resolve()
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('artifact is outside the output directory')
    path = (root / path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('artifact is outside the output directory')
    return path


def _frame_hashes(path):
    result = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path),
                             '-map', '0:v:0', '-f', 'framehash', '-hash', 'sha256', '-'],
                            capture_output=True, text=True, check=True)
    return [line.rsplit(',', 1)[-1].strip() for line in result.stdout.splitlines()
            if line and not line.startswith('#')]


def _inspect_completion(state, record, output_root):
    items = [item for item in record.get('outputs', {}).get('40', {}).get('images', [])
             if item.get('type') == 'output' and item.get('filename', '').endswith('.mp4')]
    if len(items) != 1:
        raise ValueError('expected exactly one saved assembly from node 40')
    item = items[0]
    relative = Path(item.get('subfolder', '')) / item['filename']
    path = _output_path(output_root, relative)
    bundle = state['bundle']
    if relative.parent.as_posix() != bundle['output_subfolder']:
        raise ValueError('saved assembly is outside the run output folder')
    checksum = h3.file_hash(path)
    if state.get('output') and state['output']['sha256'] != checksum:
        raise ValueError('completed media changed; previous technical pass is invalid')
    probe = film.probe_video(path)
    raw = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-of', 'json', str(path)],
                         capture_output=True, text=True, check=True)
    tags = json.loads(raw.stdout).get('format', {}).get('tags', {})
    if 'h3_manifest' not in tags:
        raise ValueError('saved assembly has no embedded Context Loop manifest')
    manifest = json.loads(tags['h3_manifest'])
    partial = manifest.get('format') == 'h3_chain_partial_manifest_v3'
    if manifest.get('format') not in ('h3_chain_manifest_v3', 'h3_chain_partial_manifest_v3'):
        raise ValueError('unsupported Context Loop manifest')
    compatibility = manifest['compatibility']
    if manifest['run_name'] != bundle['run_name'] or compatibility.get('generation_fingerprint') != bundle['fingerprint']:
        raise ValueError('manifest belongs to a different production bundle')
    segments = manifest['segments']
    count = len(segments)
    if not 0 < count <= len(bundle['shots']) or manifest['clip_count'] != count:
        raise ValueError('manifest clip count mismatch')
    if not partial and count != len(bundle['shots']):
        raise ValueError('complete manifest is missing expected shots')
    shots = bundle['shots'][:count]
    expected_probe = {'width': state['delivery']['width'], 'height': state['delivery']['height'],
                      'fps': state['delivery']['fps'], 'frames': sum(s['frames'] for s in shots), 'audio': False}
    if probe != expected_probe or manifest['total_delivered_frames'] != expected_probe['frames']:
        raise ValueError('assembly dimensions, fps, decoded frames or audio do not match the bundle')
    if any(compatibility.get(key) != expected_probe[key] for key in ('width', 'height', 'fps')):
        raise ValueError('manifest dimensions or fps do not match the bundle')
    ordered_hashes = []
    receipts = []
    for index, (shot, segment) in enumerate(zip(shots, segments), 1):
        expected = {'index': index, 'id': shot['shot_id'], 'prompt': shot['prompt_text'],
                    'seed': shot['seed'], 'steps': shot['recipe']['steps'],
                    'raw_frames': shot['frames'], 'delivered_frames': shot['frames']}
        if any(segment.get(key) != value for key, value in expected.items()):
            raise ValueError(f'shot {index}: manifest identity, prompt or recipe mismatch')
        if not segment.get('revision'):
            raise ValueError(f'shot {index}: missing revision')
        for key in ('segment', 'checkpoint', 'prompt_file'):
            artifact = _output_path(output_root, segment[key])
            if h3.file_hash(artifact) != segment[key + '_sha256']:
                raise ValueError(f'shot {index}: {key} hash mismatch')
        prompt_path = _output_path(output_root, segment['prompt_file'])
        if prompt_path.read_text(encoding='utf-8') != shot['prompt_text']:
            raise ValueError(f'shot {index}: prompt sidecar mismatch')
        metadata_path = _output_path(output_root, segment['revision_metadata'])
        metadata = film.read_json(metadata_path)
        if (metadata.get('format') != 'h3_chain_segment_v3' or metadata.get('run_name') != bundle['run_name'] or
                metadata.get('plan_hash') != manifest.get('plan_hash') or
                metadata.get('compatibility', {}).get('generation_fingerprint') != bundle['fingerprint']):
            raise ValueError(f'shot {index}: revision metadata belongs to a different run')
        keys = (*expected, 'revision', 'segment', 'checkpoint', 'prompt_file',
                'segment_sha256', 'checkpoint_sha256', 'prompt_file_sha256')
        if any(metadata['segment'].get(key) != segment.get(key) for key in keys):
            raise ValueError(f'shot {index}: revision metadata mismatch')
        segment_path = _output_path(output_root, segment['segment'])
        if film.probe_video(segment_path) != {**expected_probe, 'frames': shot['frames']}:
            raise ValueError(f'shot {index}: segment media contract mismatch')
        ordered_hashes.extend(_frame_hashes(segment_path))
        receipts.append({'shot_id': shot['shot_id'], 'revision': segment['revision'],
                         'segment_sha256': segment['segment_sha256'], 'metadata_sha256': h3.file_hash(metadata_path)})
    if _frame_hashes(path) != ordered_hashes:
        raise ValueError('assembly decoded frame order differs from the saved shot segments')
    return {'path': str(path), 'sha256': checksum, 'probe': probe,
            'manifest': manifest, 'segments': receipts}, partial


def reconcile(path, history, output_root):
    """Verify the recorded recursive prompt's saved assembly; never approve it."""
    with _locked_run(path) as state:
        prompt_id = state['prompt_id']
        if not prompt_id or prompt_id not in history:
            raise ValueError('recorded prompt is absent from history; do not resubmit automatically')
        record = history[prompt_id]
        prompt = record.get('prompt', [])
        if len(prompt) < 3 or prompt[1] != prompt_id or prompt[2] != state['graph']:
            raise ValueError('history graph does not match the recorded submission')
        status = record.get('status', {})
        if status.get('status_str') == 'error':
            if state['status'] != 'failed':
                state['completion_history'] = record
                film.event(state, 'failed', history_status=status)
            return state
        if not status.get('completed') or status.get('status_str') != 'success':
            return state
        try:
            output, partial = _inspect_completion(state, record, output_root)
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            if state.get('output'):
                film.event(state, 'failed', reason=str(error))
                film.write_json(Path(path) / 'run.json', state)
            raise
        if state.get('output') == output:
            return state
        state.update(output=output, partial=partial, completion_history=record)
        film.event(state, 'rendered', partial=partial)
        if not partial:
            film.event(state, 'technical_pass')
            film.event(state, 'review_pending')
        return state


def _copy_atomic(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f'.{dst.name}.tmp')
    shutil.copyfile(src, tmp)
    tmp.replace(dst)


def publish_delivery(path, destination, output_root):
    """Publish friendly immutable shot and film copies plus index.json and README.md."""
    destination = Path(destination)
    if '..' in destination.parts or destination.is_symlink():
        raise ValueError('invalid delivery destination')
    destination = destination.resolve()
    with _locked_run(path) as state:
        if state['status'] not in ('review_pending', 'approved') or state.get('partial') is not False or not state.get('output'):
            raise ValueError('delivery publication requires a complete technical-pass run')
        bundle = state['bundle']
        output = state['output']
        final_src = Path(output['path'])
        if not final_src.is_file() or h3.file_hash(final_src) != output['sha256']:
            raise ValueError('completed assembly missing or hash changed before publication')
        manifest_segments = output['manifest']['segments']
        index_path = destination / 'index.json'
        film_name = f"{bundle['run_name']}.mp4"
        expected_shots = []
        for pos, (shot, seg) in enumerate(zip(bundle['shots'], manifest_segments), 1):
            seg_src = _output_path(output_root, seg['segment'])
            if not seg_src.is_file() or h3.file_hash(seg_src) != seg['segment_sha256']:
                raise ValueError(f'shot {pos}: verified segment missing or hash changed')
            slug = re.sub(r'[^a-z0-9]+', '_', shot['shot_id'].lower()).strip('_')
            rel_shot = f'shots/{pos:02d}_{slug}.mp4'
            expected_shots.append((seg_src, rel_shot, {
                'index': pos,
                'shot_id': shot['shot_id'],
                'friendly_file': rel_shot,
                'canonical_segment': seg['segment'],
                'canonical_checkpoint': seg['checkpoint'],
                'revision': seg['revision'],
                'sha256': seg['segment_sha256'],
                'seed': shot['seed'],
                'frames': shot['frames'],
                'duration_s': round(shot['frames'] / state['delivery']['fps'], 3),
                'assets': list(shot['assets']),
                'warnings': shot.get('warnings', []),
            }))
        creative_status = 'approved' if state['status'] == 'approved' and state.get('review') else 'review_pending'
        index_doc = {
            'schema_version': 1,
            'run_name': bundle['run_name'],
            'identity_sha256': state['identity_sha256'],
            'bundle_fingerprint': bundle['fingerprint'],
            'prompt_id': state['prompt_id'],
            'technical_status': 'passed',
            'creative_status': creative_status,
            'review': state.get('review'),
            'delivery': {
                **state['delivery'],
                'duration_s': round(state['delivery']['frames'] / state['delivery']['fps'], 3),
                'film_file': film_name,
                'film_sha256': output['sha256'],
                'canonical_draft': str(final_src),
            },
            'shots': [entry for _, _, entry in expected_shots],
        }
        if destination.exists():
            if not index_path.is_file():
                if any(destination.iterdir()):
                    raise ValueError('delivery destination already exists and has no matching index.json')
            else:
                existing = film.read_json(index_path)
                if (existing.get('identity_sha256') != state['identity_sha256'] or
                        existing.get('delivery', {}).get('film_sha256') != output['sha256']):
                    raise ValueError('delivery destination belongs to a different run or media hash')
                film_dst = destination / film_name
                if not film_dst.is_file() or h3.file_hash(film_dst) != output['sha256']:
                    raise ValueError('existing published film hash mismatch')
                for _, rel_shot, entry in expected_shots:
                    shot_dst = destination / rel_shot
                    if not shot_dst.is_file() or h3.file_hash(shot_dst) != entry['sha256']:
                        raise ValueError(f"existing published shot hash mismatch: {rel_shot}")
                return existing
        destination.mkdir(parents=True, exist_ok=True)
        _copy_atomic(final_src, destination / film_name)
        for seg_src, rel_shot, entry in expected_shots:
            shot_dst = destination / rel_shot
            _copy_atomic(seg_src, shot_dst)
            if h3.file_hash(shot_dst) != entry['sha256']:
                raise ValueError(f'published shot copy hash mismatch: {rel_shot}')
        if h3.file_hash(destination / film_name) != output['sha256']:
            raise ValueError('published film copy hash mismatch')
        _write_delivery_docs(destination, index_doc, expected_shots, bundle['run_name'], f'output/h3_chains/{bundle["run_name"]}/')
        state['published_delivery'] = {'destination': str(destination), 'film_sha256': output['sha256']}
        return index_doc


def _write_delivery_docs(destination, index_doc, expected_shots, title, source_note):
    delivery = index_doc['delivery']
    lines = [
        f'# {title}',
        '',
        f"- Technical verification: **passed** (`{delivery['width']}x{delivery['height']}`, `{delivery['fps']}` fps, `{delivery['frames']}` frames, audio `{delivery['audio']}`)",
        f"- Creative review: **{index_doc['creative_status']}** (technical pass is not creative approval)",
        f"- Assembled silent film: `{delivery['film_file']}` (`{delivery['film_sha256']}`)",
        f'- Canonical source: `{source_note}` (preserved untouched)',
        '',
        '## Shots',
        '',
    ]
    for _, _, entry in expected_shots:
        lines.append(
            f"- `{entry['friendly_file']}` — `{entry['shot_id']}` · {entry['frames']} frames ({entry['duration_s']}s) · seed `{entry['seed']}` · rev `{entry['revision']}` · sha256 `{entry['sha256'][:16]}…`"
        )
    readme_tmp = destination / '.README.md.tmp'
    readme_tmp.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    readme_tmp.replace(destination / 'README.md')
    film.write_json(destination / 'index.json', index_doc)


def assemble_replacement(base_run_path, patch_run_path, shot_id, run_name, destination, output_root):
    """Replace one verified shot in a completed run without mutating either source run."""
    destination = Path(destination)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_name) or '..' in destination.parts or destination.is_symlink():
        raise ValueError('invalid replacement run_name or destination')
    destination = destination.resolve()
    base_run_path, patch_run_path = Path(base_run_path).resolve(), Path(patch_run_path).resolve()
    if base_run_path == patch_run_path:
        raise ValueError('replacement requires different runs')
    first_path, second_path = sorted((base_run_path, patch_run_path))
    with _locked_run(first_path) as first_state, _locked_run(second_path) as second_state:
        base_state, patch_state = (first_state, second_state) if first_path == base_run_path else (second_state, first_state)
        for label, st in (('base', base_state), ('patch', patch_state)):
            if st['status'] not in ('review_pending', 'approved') or st.get('partial') is not False or not st.get('output'):
                raise ValueError(f'{label} run requires a complete technical-pass record')
        if base_state['delivery']['width'] != patch_state['delivery']['width'] or base_state['delivery']['height'] != patch_state['delivery']['height'] or base_state['delivery']['fps'] != patch_state['delivery']['fps']:
            raise ValueError('replacement shot dimensions or fps do not match base run')
        patch_shots = patch_state['bundle']['shots']
        if len(patch_shots) != 1 or patch_shots[0]['shot_id'] != shot_id:
            raise ValueError(f'patch run must contain only {shot_id}')
        target_pos = next((i for i, s in enumerate(base_state['bundle']['shots']) if s['shot_id'] == shot_id), None)
        if target_pos is None:
            raise ValueError(f'{shot_id} not in base run')
        merged_shots = []
        merged_segments = []
        expected_shots = []
        ordered_hashes = []
        for idx, (b_shot, b_seg) in enumerate(zip(base_state['bundle']['shots'], base_state['output']['manifest']['segments'])):
            pos = idx + 1
            if idx == target_pos:
                use_shot = patch_shots[0]
                use_seg = dict(patch_state['output']['manifest']['segments'][0], index=pos)
                source_run = patch_state['bundle']['run_name']
            else:
                use_shot = b_shot
                use_seg = b_seg
                source_run = base_state['bundle']['run_name']
            seg_src = _output_path(output_root, use_seg['segment'])
            if not seg_src.is_file() or h3.file_hash(seg_src) != use_seg['segment_sha256']:
                raise ValueError(f'shot {pos}: segment missing or hash changed')
            if film.probe_video(seg_src) != {'width': base_state['delivery']['width'], 'height': base_state['delivery']['height'], 'fps': base_state['delivery']['fps'], 'frames': use_shot['frames'], 'audio': False}:
                raise ValueError(f'shot {pos}: segment probe mismatch')
            ordered_hashes.extend(_frame_hashes(seg_src))
            slug = re.sub(r'[^a-z0-9]+', '_', use_shot['shot_id'].lower()).strip('_')
            rel_shot = f'shots/{pos:02d}_{slug}.mp4'
            merged_shots.append(use_shot)
            merged_segments.append(use_seg)
            expected_shots.append((seg_src, rel_shot, {
                'index': pos,
                'shot_id': use_shot['shot_id'],
                'source_run': source_run,
                'friendly_file': rel_shot,
                'canonical_segment': use_seg['segment'],
                'canonical_checkpoint': use_seg['checkpoint'],
                'revision': use_seg['revision'],
                'sha256': use_seg['segment_sha256'],
                'seed': use_shot['seed'],
                'frames': use_shot['frames'],
                'duration_s': round(use_shot['frames'] / base_state['delivery']['fps'], 3),
                'assets': list(use_shot['assets']),
                'warnings': use_shot.get('warnings', []),
            }))
        merged_bundle = h3_loop.export(merged_shots, run_name, f'The_Message/deliveries/{destination.name}')
        total_frames = sum(s['frames'] for s in merged_shots)
        film_name = f'{run_name}.mp4'
        index_path = destination / 'index.json'
        base_identity = {'run_name': base_state['bundle']['run_name'], 'prompt_id': base_state['prompt_id'], 'film_sha256': base_state['output']['sha256']}
        replacement_identity = {
            'shot_id': shot_id,
            'patch_run_name': patch_state['bundle']['run_name'],
            'patch_prompt_id': patch_state['prompt_id'],
            'previous_revision': base_state['output']['manifest']['segments'][target_pos]['revision'],
            'new_revision': patch_state['output']['manifest']['segments'][0]['revision'],
        }
        if destination.exists():
            if index_path.is_file():
                existing = film.read_json(index_path)
                if (existing.get('bundle_fingerprint') == merged_bundle['fingerprint'] and
                        existing.get('base_run') == base_identity and existing.get('replacement') == replacement_identity and
                        existing.get('shots') == [entry for _, _, entry in expected_shots]):
                    film_dst = destination / film_name
                    if film_dst.is_file() and h3.file_hash(film_dst) == existing['delivery']['film_sha256']:
                        for _, rel_shot, entry in expected_shots:
                            shot_dst = destination / rel_shot
                            if not shot_dst.is_file() or h3.file_hash(shot_dst) != entry['sha256']:
                                raise ValueError(f'existing published shot hash mismatch: {rel_shot}')
                        return existing
            if any(destination.iterdir()):
                raise ValueError('replacement destination already exists with different content')
        destination.mkdir(parents=True, exist_ok=True)
        for seg_src, rel_shot, entry in expected_shots:
            shot_dst = destination / rel_shot
            _copy_atomic(seg_src, shot_dst)
            if h3.file_hash(shot_dst) != entry['sha256']:
                raise ValueError(f'published shot copy hash mismatch: {rel_shot}')
        manifest_tag = {
            'format': 'h3_chain_editorial_replacement_v1',
            'run_name': run_name,
            'base_run_name': base_state['bundle']['run_name'],
            'base_prompt_id': base_state['prompt_id'],
            'patch_run_name': patch_state['bundle']['run_name'],
            'patch_prompt_id': patch_state['prompt_id'],
            'replaced_shot_id': shot_id,
            'replaced_base_revision': base_state['output']['manifest']['segments'][target_pos]['revision'],
            'replacement_revision': patch_state['output']['manifest']['segments'][0]['revision'],
            'bundle_fingerprint': merged_bundle['fingerprint'],
            'clip_count': len(merged_segments),
            'total_delivered_frames': total_frames,
            'segments': merged_segments,
        }
        concat_tmp = destination / '.concat.txt.tmp'
        concat_tmp.write_text(''.join(f"file '{rel}'\n" for _, rel, _ in expected_shots), encoding='utf-8')
        film_tmp = destination / f'.{film_name}.tmp.mp4'
        try:
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(concat_tmp), '-map', '0:v:0', '-c:v', 'copy', '-an',
                '-movflags', 'use_metadata_tags', '-metadata', 'h3_manifest=' + json.dumps(manifest_tag),
                str(film_tmp),
            ], check=True)
        finally:
            concat_tmp.unlink(missing_ok=True)
        expected_probe = {'width': base_state['delivery']['width'], 'height': base_state['delivery']['height'], 'fps': base_state['delivery']['fps'], 'frames': total_frames, 'audio': False}
        if film.probe_video(film_tmp) != expected_probe or _frame_hashes(film_tmp) != ordered_hashes:
            film_tmp.unlink(missing_ok=True)
            raise ValueError('replacement film probe or decoded frame order mismatch')
        film_dst = destination / film_name
        film_tmp.replace(film_dst)
        film_sha = h3.file_hash(film_dst)
        index_doc = {
            'schema_version': 1,
            'run_name': run_name,
            'bundle_fingerprint': merged_bundle['fingerprint'],
            'base_run': base_identity,
            'replacement': replacement_identity,
            'technical_status': 'passed',
            'creative_status': 'review_pending',
            'delivery': {
                **expected_probe,
                'audio': 'none',
                'duration_s': round(total_frames / expected_probe['fps'], 3),
                'film_file': film_name,
                'film_sha256': film_sha,
                'canonical_draft': str(film_dst),
            },
            'shots': [entry for _, _, entry in expected_shots],
        }
        _write_delivery_docs(destination, index_doc, expected_shots, run_name, f"base {base_state['bundle']['run_name']} + patch {patch_state['bundle']['run_name']} ({shot_id})")
        return index_doc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('prepare')
    for name in ('root', 'bundle', 'graph', 'models', 'workspace'):
        command.add_argument('--' + name, type=Path, required=True)
    for name in ('preflight', 'submitting'):
        command = commands.add_parser(name)
        command.add_argument('run', type=Path)
        command.add_argument('--resources', type=Path, required=True)
        command.add_argument('--nodes', type=Path, required=True)
        if name == 'submitting':
            command.add_argument('--graph', type=Path, required=True)
    for name, argument in (('bind', 'prompt_id'), ('unknown', 'reason'),
                           ('recover', 'history'), ('reconcile', 'history'),
                           ('publish', 'destination')):
        command = commands.add_parser(name)
        command.add_argument('run', type=Path)
        command.add_argument(argument)
        if name in ('reconcile', 'publish'):
            command.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        print(prepare(args.root, film.read_json(args.bundle), film.read_json(args.graph),
                      film.read_json(args.models), args.workspace))
    elif args.command == 'preflight':
        print(json.dumps(preflight(args.run, film.read_json(args.resources), film.read_json(args.nodes))))
    elif args.command == 'submitting':
        mark_submitting(args.run, film.read_json(args.graph), film.read_json(args.resources), film.read_json(args.nodes))
    elif args.command == 'bind':
        bind_prompt(args.run, args.prompt_id)
    elif args.command == 'unknown':
        mark_unknown(args.run, args.reason)
    elif args.command == 'recover':
        print(json.dumps(recover_submission(args.run, film.read_json(args.history))))
    elif args.command == 'reconcile':
        print(json.dumps(reconcile(args.run, film.read_json(args.history), args.output_root)))
    elif args.command == 'publish':
        print(json.dumps(publish_delivery(args.run, args.destination, args.output_root)))


if __name__ == '__main__':
    main()

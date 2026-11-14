#!/usr/bin/env python3
"""Prepare H3 shots and track panel-submitted takes. Never submits generation."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
from fractions import Fraction
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

import h3_recipe as h3
import h3_graph
import h3_preflight


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def safe_id(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError(f'invalid identifier: {value}')
    return value


def read_take(path):
    return read_json(Path(path) / 'take.json')


@contextmanager
def locked_take(path):
    path = Path(path)
    with (path / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = read_take(path)
        yield state
        write_json(path / 'take.json', state)


def event(state, status, **details):
    state['status'] = status
    state.setdefault('events', []).append({'at': datetime.now(timezone.utc).isoformat(), 'status': status, **details})


def prepare(root, compiled, attempt, output_namespace='The_Message'):
    safe_id(output_namespace)
    path = Path(root) / safe_id(compiled['shot_id']) / safe_id(attempt)
    path.mkdir(parents=True, exist_ok=False)
    for name in ('builder_state', 'stack_state', 'media_state'):
        write_json(path / f'{name}.json', compiled[name])
    (path / 'prompt.txt').write_text(compiled['prompt_text'])
    write_json(path / 'compiled.json', compiled)
    if 'shot' in compiled:
        prefix = f"{output_namespace}/shots/{compiled['shot_id']}/{attempt}/video"
        edits = [
            {'node_id': node, 'widget': widget, 'value': value}
            for node, widget, value in [
                (7, 'stack_state', h3.canonical(compiled['stack_state'])),
                (21, 'media_state', h3.canonical(compiled['media_state'])),
                (8, 'builder_state', h3.canonical(compiled['builder_state'])),
                (8, 'prompt_text', compiled['prompt_text']),
                (23, 'value', compiled['shot']['duration_s']),
                (15, 'noise_seed', compiled['seed']),
                (20, 'filename_prefix', prefix),
                (9, 'stack_pictures', compiled['recipe']['stack_pictures']),
                (9, 'stack_pictures_n', compiled['recipe']['stack_pictures_n']),
            ]]
        write_json(path / 'panel-edits.json', edits)
    state = {'schema_version': 1, 'shot_id': compiled['shot_id'], 'attempt': attempt,
             'fingerprint': compiled['fingerprint'], 'compiled_sha256': h3.file_hash(path / 'compiled.json'),
             'prompt_id': None, 'review': None, 'output_namespace': output_namespace}
    event(state, 'prepared')
    write_json(path / 'take.json', state)
    return path


def mark_submitting(path):
    with locked_take(path) as state:
        if state['status'] != 'prepared':
            raise ValueError('take already submitted or outcome unknown; reconcile before a new attempt')
        if h3.file_hash(Path(path) / 'compiled.json') != state['compiled_sha256']:
            raise ValueError('compiled recipe changed; prepare a new attempt')
        evidence = read_json(Path(path) / 'preflight.json')
        if evidence['compiled_sha256'] != state['compiled_sha256'] or not 0 <= time.time() - evidence['checked_at'] <= 120:
            raise ValueError('preflight expired or belongs to a different recipe')
        resource_check = h3_preflight.resources(evidence['resources']['snapshot'])
        if resource_check['errors']:
            raise ValueError('\n'.join(resource_check['errors']))
        checked = h3_preflight.check(evidence['workspace'], evidence['models'], read_json(Path(path) / 'compiled.json').get('assets', {}), evidence['registered_nodes'])
        if checked['errors']:
            raise ValueError('\n'.join(checked['errors']))
        event(state, 'submitting')


def bind_prompt(path, prompt_id):
    if not prompt_id:
        raise ValueError('prompt_id is required')
    with locked_take(path) as state:
        if state['prompt_id'] == prompt_id:
            return
        if state['prompt_id'] or state['status'] != 'submitting':
            raise ValueError('cannot replace prompt_id or bind an unsubmitted take')
        state['prompt_id'] = prompt_id
        event(state, 'queued', prompt_id=prompt_id)


def probe_video(path):
    raw = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(path)],
                         capture_output=True, text=True, check=True)
    data = json.loads(raw.stdout)
    videos = [s for s in data['streams'] if s['codec_type'] == 'video']
    if len(videos) != 1:
        raise ValueError('expected one video stream')
    video = videos[0]
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'], capture_output=True, check=True)
    return {'width': video['width'], 'height': video['height'], 'fps': float(Fraction(video['avg_frame_rate'])),
            'frames': int(video['nb_read_frames']), 'audio': any(s['codec_type'] == 'audio' for s in data['streams'])}


def reconcile(path, history, output_root):
    path = Path(path)
    with locked_take(path) as state:
        prompt_id = state['prompt_id']
        if not prompt_id or prompt_id not in history:
            raise ValueError('recorded prompt_id absent from history; do not resubmit automatically')
        record = history[prompt_id]
        status = record.get('status', {})
        if status.get('status_str') == 'error':
            event(state, 'failed', history_status=status)
            return state
        if not status.get('completed'):
            return state
        files = []
        for node_id, output in record.get('outputs', {}).items():
            for key in ('images', 'videos', 'gifs'):
                for item in output.get(key, []):
                    if item.get('type') == 'output' and Path(item.get('filename', '')).suffix.lower() in ('.mp4', '.webm', '.mov'):
                        files.append((node_id, item))
        if len(files) != 1:
            raise ValueError('expected exactly one saved video; preview/partial branch cannot finish a take')
        node_id, item = files[0]
        compiled = read_json(path / 'compiled.json')
        if h3.file_hash(path / 'compiled.json') != state['compiled_sha256']:
            raise ValueError('compiled recipe changed')
        prompt_record = record.get('prompt', [])
        graph = prompt_record[2] if len(prompt_record) > 2 else {}
        saved = graph.get(str(node_id), {})
        expected_prefix = f"{state.get('output_namespace', 'The_Message')}/shots/{state['shot_id']}/{state['attempt']}/video"
        if saved.get('class_type') != 'SaveVideo' or saved['inputs'].get('filename_prefix') != expected_prefix:
            raise ValueError('history output does not belong to this take prefix')
        builders = [n for n in graph.values() if n['class_type'] == 'MiniMaxH3PromptBuilder']
        if len(builders) != 1 or builders[0]['inputs'].get('prompt_text') != compiled['prompt_text']:
            raise ValueError('history prompt differs from the prepared shot')
        h3_graph.verify(graph, compiled, expected_prefix)
        root = Path(output_root).resolve()
        video = (root / item.get('subfolder', '') / item['filename']).resolve()
        if not video.is_relative_to(root):
            raise ValueError('history output escapes output root')
        info = probe_video(video)
        recipe = compiled['recipe']
        expected = {key: recipe[key] for key in ('width', 'height', 'fps')}
        expected.update(frames=compiled['frames'], audio=True)
        if info != expected:
            raise ValueError(f'technical video mismatch: {info}; expected {expected}')
        sha = h3.file_hash(video)
        if state['status'] in ('review_pending', 'approved', 'rejected'):
            if state['output']['sha256'] != sha:
                raise ValueError('previously recorded output changed')
            return state
        state['output'] = {'path': str(video), 'sha256': sha, **info}
        write_json(path / 'history.json', record)
        event(state, 'rendered')
        event(state, 'technical_pass')
        event(state, 'review_pending')
        return state


def review(path, approved, reviewer, note):
    if not reviewer.strip() or not note.strip():
        raise ValueError('reviewer and review note are required')
    with locked_take(path) as state:
        if state['status'] not in ('review_pending', 'approved', 'rejected'):
            raise ValueError('technical validation must pass before review')
        if h3.file_hash(state['output']['path']) != state['output']['sha256']:
            raise ValueError('output changed since technical validation')
        state['review'] = {'approved': approved, 'reviewer': reviewer, 'note': note, 'sha256': state['output']['sha256']}
        event(state, 'approved' if approved else 'rejected', review=state['review'])


def assembly_inputs(entries, draft=False):
    result = []
    for entry in entries:
        state = read_take(entry['take'])
        if draft:
            if state['status'] not in ('review_pending', 'approved'):
                raise ValueError(f"{entry['take']}: draft requires technical validation")
        elif state['status'] != 'approved' or not state['review'] or not state['review']['approved']:
            raise ValueError(f"{entry['take']}: take is not approved")
        output = state['output']
        if h3.file_hash(output['path']) != output['sha256'] or (not draft and state['review']['sha256'] != output['sha256']):
            raise ValueError('approved output hash changed')
        start, end = entry['in_frame'], entry['out_frame']
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= output['frames']:
            raise ValueError('invalid edit frame range')
        result.append({**output, 'in_frame': start, 'out_frame': end})
    if not result:
        raise ValueError('empty edit list')
    if len({(x['width'], x['height'], x['fps']) for x in result}) != 1:
        raise ValueError('assembly requires matching dimensions and fps')
    return result


def assemble(edit, destination, draft=False):
    clips = assembly_inputs(edit, draft=draft)
    if len({clip['audio'] for clip in clips}) != 1:
        raise ValueError('assembly requires a consistent audio policy')
    audio = clips[0]['audio']
    destination = Path(destination)
    if destination.exists() or destination.with_suffix('.receipt.json').exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        cmd = ['ffmpeg', '-v', 'error', '-nostdin']
        filters = []
        for i, clip in enumerate(clips):
            cmd += ['-i', clip['path']]
            start, end = clip['in_frame'], clip['out_frame']
            filters.append(f'[{i}:v]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS[v{i}]')
            if audio:
                filters.append(f"[{i}:a]atrim=start={start / clip['fps']}:end={end / clip['fps']},asetpts=PTS-STARTPTS[a{i}]")
        filters.append(''.join(f'[v{i}]' + (f'[a{i}]' if audio else '') for i in range(len(clips))) + f'concat=n={len(clips)}:v=1:a={int(audio)}[v]' + ('[a]' if audio else ''))
        candidate = Path(tmp) / 'cut.mp4'
        cmd += ['-filter_complex', ';'.join(filters), '-map', '[v]', '-c:v', 'libx264', '-threads', '1', '-crf', '18']
        cmd += ['-map', '[a]', '-c:a', 'aac'] if audio else ['-an']
        cmd.append(str(candidate))
        subprocess.run(cmd, capture_output=True, check=True)
        info = probe_video(candidate)
        if info['frames'] != sum(c['out_frame'] - c['in_frame'] for c in clips):
            raise ValueError('assembled frame count mismatch')
        os.link(candidate, destination)
        write_json(destination.with_suffix('.receipt.json'), {'inputs': clips, 'output_sha256': h3.file_hash(destination), 'technical': info, 'review': 'pending', 'purpose': 'draft' if draft else 'final'})
    return destination


def plan_run(takes, path, destination):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    rows = [{'take': str(Path(t).resolve()), 'compiled_sha256': read_take(t)['compiled_sha256']} for t in takes]
    if not rows or len({row['take'] for row in rows}) != len(rows):
        raise ValueError('run needs unique takes')
    data = {'version': 1, 'takes': rows, 'destination': str(Path(destination).resolve())}
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
    return path


def run_status(path):
    run = read_json(path)
    edit = []
    for row in run['takes']:
        take = Path(row['take'])
        state = read_take(take)
        if h3.file_hash(take / 'compiled.json') != row['compiled_sha256']:
            raise ValueError('run compiled input changed')
        action = {'prepared': 'render', 'submitting': 'reconcile_submission', 'queued': 'wait'}.get(state['status'])
        if action:
            return {'action': action, 'take': str(take), 'prompt_id': state['prompt_id']}
        if state['status'] not in ('review_pending', 'approved'):
            return {'action': 'blocked', 'take': str(take), 'status': state['status']}
        edit.append({'take': str(take), 'in_frame': 0, 'out_frame': state['output']['frames']})
    destination = Path(run['destination'])
    receipt_path = destination.with_suffix('.receipt.json')
    if destination.exists() or receipt_path.exists():
        if not destination.is_file() or not receipt_path.is_file():
            return {'action': 'blocked', 'reason': 'incomplete draft and receipt pair'}
        receipt = read_json(receipt_path)
        if h3.file_hash(destination) != receipt['output_sha256']:
            raise ValueError('draft hash changed')
        if receipt.get('purpose') != 'draft' or receipt['inputs'] != assembly_inputs(edit, draft=True):
            raise ValueError('draft receipt differs from run inputs')
        return {'action': 'draft_complete', 'destination': str(destination)}
    return {'action': 'assemble_draft', 'edit': edit, 'destination': str(destination)}


def compile_project(project, workspace, script='production.json', bindings_file='bindings.json', recipe_file='recipes/h3-ref-diagnostic-v1.json', shot_ids=None):
    project = Path(project)
    doc = read_json(project / script)
    assets = read_json(project / 'assets.json')
    bindings = read_json(project / bindings_file)
    recipe = read_json(project / recipe_file)
    known = {shot['id'] for shot in doc['shots']}
    if shot_ids is not None and set(shot_ids) - known:
        raise ValueError('unknown shot selection: ' + ', '.join(sorted(set(shot_ids) - known)))
    return [h3.compile_shot(doc, shot['id'], bindings[shot['id']], assets, recipe, workspace) for shot in doc['shots'] if shot_ids is None or shot['id'] in shot_ids]


def preflight_project(project, workspace):
    project = Path(project)
    result = h3_preflight.check(workspace, read_json(project / 'models.json'), read_json(project / 'assets.json'))
    if result['errors']:
        raise ValueError('\n'.join(result['errors']))
    return result


def preflight_take(path, graph, resource_snapshot, workspace, models, registered_nodes):
    path = Path(path)
    with locked_take(path) as state:
        if state['status'] != 'prepared':
            raise ValueError('preflight requires a prepared take')
        compiled = read_json(path / 'compiled.json')
        if h3.file_hash(path / 'compiled.json') != state['compiled_sha256']:
            raise ValueError('compiled recipe changed')
        prefix = f"{state.get('output_namespace', 'The_Message')}/shots/{state['shot_id']}/{state['attempt']}/video"
        graph_hash = h3_graph.verify(graph, compiled, prefix)
        files = h3_preflight.check(workspace, models, compiled.get('assets', {}), registered_nodes)
        resource_check = h3_preflight.resources(resource_snapshot)
        errors = files['errors'] + resource_check['errors']
        if errors:
            raise ValueError('\n'.join(errors))
        evidence = {'checked_at': time.time(), 'compiled_sha256': state['compiled_sha256'], 'graph_sha256': graph_hash,
                    'workspace': str(Path(workspace).resolve()), 'models': models, 'registered_nodes': sorted(registered_nodes),
                    'files': files, 'resources': resource_check}
        write_json(path / 'preflight.json', evidence)
        return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'prepare'):
        command = sub.add_parser(name)
        command.add_argument('project', type=Path)
        command.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parent.parent)
        if name == 'prepare':
            command.add_argument('--out', type=Path, required=True)
            command.add_argument('--attempt', required=True)
            command.add_argument('--output-namespace', default='The_Message')
    command = sub.add_parser('submitting')
    command.add_argument('take', type=Path)
    command = sub.add_parser('preflight')
    command.add_argument('take', type=Path)
    command.add_argument('--graph', type=Path, required=True)
    command.add_argument('--resources', type=Path, required=True)
    command.add_argument('--models', type=Path, required=True)
    command.add_argument('--nodes', type=Path, required=True)
    command.add_argument('--workspace', type=Path, required=True)
    command = sub.add_parser('bind')
    command.add_argument('take', type=Path)
    command.add_argument('prompt_id')
    command = sub.add_parser('reconcile')
    command.add_argument('take', type=Path)
    command.add_argument('history', type=Path)
    command.add_argument('--output-root', required=True, type=Path)
    command = sub.add_parser('review')
    command.add_argument('take', type=Path)
    command.add_argument('--decision', choices=['approve', 'reject'], required=True)
    command.add_argument('--reviewer', required=True)
    command.add_argument('--note', required=True)
    command = sub.add_parser('assemble')
    command.add_argument('edit', type=Path)
    command.add_argument('--out', type=Path, required=True)
    command.add_argument('--draft', action='store_true')
    command = sub.add_parser('plan-run')
    command.add_argument('run', type=Path)
    command.add_argument('--take', type=Path, action='append', required=True)
    command.add_argument('--draft-output', type=Path, required=True)
    command = sub.add_parser('run-status')
    command.add_argument('run', type=Path)
    command = sub.add_parser('assemble-run')
    command.add_argument('run', type=Path)
    args = parser.parse_args(argv)
    if args.command in ('check', 'prepare'):
        print(json.dumps({'preflight': preflight_project(args.project, args.workspace)}))
        shots = compile_project(args.project, args.workspace)
        if args.command == 'prepare':
            for shot in shots:
                path = args.out / safe_id(shot['shot_id']) / safe_id(args.attempt)
                if path.exists():
                    raise FileExistsError(path)
        for shot in shots:
            result = {'shot': shot['shot_id'], 'fingerprint': shot['fingerprint'], 'labels': shot['labels'], 'warnings': shot['warnings']}
            if args.command == 'prepare':
                result['take'] = str(prepare(args.out, shot, args.attempt, args.output_namespace))
            print(json.dumps(result))
    elif args.command == 'submitting':
        mark_submitting(args.take)
    elif args.command == 'preflight':
        print(json.dumps(preflight_take(args.take, read_json(args.graph), read_json(args.resources), args.workspace,
                                        read_json(args.models), read_json(args.nodes))))
    elif args.command == 'bind':
        bind_prompt(args.take, args.prompt_id)
    elif args.command == 'reconcile':
        print(json.dumps(reconcile(args.take, read_json(args.history), args.output_root)))
    elif args.command == 'review':
        review(args.take, args.decision == 'approve', args.reviewer, args.note)
    elif args.command == 'assemble':
        print(assemble(read_json(args.edit), args.out, draft=args.draft))
    elif args.command == 'plan-run':
        print(plan_run(args.take, args.run, args.draft_output))
    elif args.command == 'run-status':
        print(json.dumps(run_status(args.run)))
    elif args.command == 'assemble-run':
        status = run_status(args.run)
        if status['action'] == 'assemble_draft':
            print(assemble(status['edit'], status['destination'], draft=True))
        elif status['action'] != 'draft_complete':
            raise ValueError(f"run not ready to assemble: {status['action']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

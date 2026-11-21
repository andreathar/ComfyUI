"""Freeze and reconcile a Master Studio take; submission stays in the visible browser."""

import copy
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

from film import event, locked_take, probe_video, read_json, safe_id, write_json
from master_studio_package import package_review, resolve_shot_package


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def prompt_digest(value):
    # Suite sees execution's node-level cache markers; submitted inputs do not.
    value = {key: {field: val for field, val in node.items() if field != 'is_changed'}
             for key, node in value.items()}
    # JSON.stringify sends 1.0 as 1. Preserve booleans and all input values.
    def numbers(item):
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            return {key: numbers(val) for key, val in item.items()}
        if isinstance(item, list):
            return [numbers(val) for val in item]
        return item
    return digest(numbers(value))


def prepare(root, graph, workflow, package):
    shot = safe_id(package['shot_id'])
    project = safe_id(package.get('project', 'MSG'))
    output_project = safe_id(package.get('output_project', 'The_Message'))
    for node_id, kind in [('27', 'DynamicScriptNode'), ('22', 'MiniMaxH3PromptBuilder'),
                          ('61', 'H3ProjectSave'), ('64', 'SaveVideo'), ('44', 'WorkflowMonitorBrain')]:
        if graph.get(node_id, {}).get('class_type') != kind:
            raise ValueError(f'Master workflow requires active {kind} at {node_id}')
    for node_id, field, link in [('22', 'prompt_text', ['27', 1]), ('22', 'builder_state', ['27', 2]),
                                 ('21', 'media_state', ['27', 3]), ('23', 'stack_state', ['27', 4]),
                                 ('22', 'references', ['21', 0]), ('22', 'mods', ['23', 0])]:
        if graph.get(node_id, {}).get('inputs', {}).get(field) != link:
            raise ValueError(f'{node_id}.{field} bypasses the selected shot package')
    encoders = [(key, node) for key, node in graph.items()
                if node['class_type'] == 'MiniMaxH3FantasticRefModTextEncode']
    if len(encoders) != 1 or any(encoders[0][1]['inputs'].get(field) != link for field, link in
                               [('prompt', ['22', 0]), ('references', ['22', 19]), ('mods', ['22', 20])]):
        raise ValueError('The encoder must consume the selected prompt, media and RefMods')
    def ancestors(node_id, seen):
        if node_id in seen:
            return
        seen.add(node_id)
        for value in graph[node_id]['inputs'].values():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and value[0] in graph:
                ancestors(value[0], seen)
    media_inputs = [('61', 'latent'), ('64', 'video')]
    if 'images' in graph['61']['inputs']:
        media_inputs.append(('61', 'images'))
    for output, field in media_inputs:
        dependencies = set()
        source = graph[output]['inputs'][field]
        if isinstance(source, list) and len(source) == 2 and source[0] in graph:
            ancestors(source[0], dependencies)
        if encoders[0][0] not in dependencies:
            raise ValueError(f'Output {output}.{field} does not consume the selected encoder')
        samplers = [node_id for node_id in dependencies if graph[node_id]['class_type'] == 'SamplerCustomAdvanced']
        if not samplers:
            raise ValueError(f'Output {output}.{field} does not consume the Master sampler')
        for node_id in samplers:
            noise = graph[node_id]['inputs'].get('noise')
            if (not isinstance(noise, list) or len(noise) != 2 or noise[1] != 0
                    or not isinstance(noise[0], str) or graph.get(noise[0], {}).get('class_type') != 'RandomNoise'):
                raise ValueError(f'{node_id}.noise must consume RandomNoise output 0 for the frozen seed')
            seed = graph[noise[0]]['inputs'].get('noise_seed')
            if isinstance(seed, list) and len(seed) == 2 and isinstance(seed[0], str) and seed[1] == 0:
                source = graph.get(seed[0], {})
                if source.get('class_type') == 'FantasticSeeds':
                    seed = source['inputs'].get('seed')
            if seed != ['27', 5]:
                raise ValueError(f'{noise[0]}.noise_seed must consume the frozen resolver seed at output 5')
    directory = Path(root) / shot
    directory.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        path = directory / f'tk{number:03d}'
        try:
            path.mkdir()
            break
        except FileExistsError:
            number += 1
    revision = digest(package)
    write_json(path / 'package.json', package)
    review = package_review(package, revision)
    write_json(path / 'prompt-review.json', review)
    summary = dict(schema='workflow-monitor.runtime.v1', kind='prompt_review', values=review,
                   shot_id=shot, take_id=path.name, revision=revision,
                   snapshot=str((path / 'package.json').resolve()),
                   authority='Frozen selected shot library revision')
    frozen = copy.deepcopy(graph)
    # DynamicScript has a leading console output; data outputs start at slot 1.
    values = [package['prompt_text'], json.dumps(package['builder_state']),
              json.dumps(package['media_state']), json.dumps(package['stack_state']),
              package['seed'], package['transition'], json.dumps(summary)]
    frozen['27']['inputs']['code'] = (
        f'if str(inputs[0]).strip() != {shot!r}:\n    raise ValueError("Prepared shot changed")\n'
        f'outputs[:] = {values!r}\n')
    prefix = f'{output_project}/shots/{shot}/{path.name}/video'
    frozen['64']['inputs']['filename_prefix'] = prefix
    write_json(path / 'prompt.json', frozen)
    write_json(path / 'workflow.json', workflow)
    state = dict(schema_version=1, project=project, scene_id=shot.rsplit('_SH', 1)[0], shot_id=shot,
                 take_id=path.name, package_revision=revision, output_prefix=prefix,
                 prompt_sha256=file_hash(path / 'prompt.json'), prompt_id=None, review=None)
    event(state, 'prepared')
    write_json(path / 'take.json', state)
    return path


def verify_inputs(path, state):
    path = Path(path)
    if (file_hash(path / 'prompt.json') != state['prompt_sha256']
            or digest(read_json(path / 'package.json')) != state['package_revision']):
        raise ValueError('Prepared inputs changed; prepare a new take')


def mark_submitting(path):
    with locked_take(path) as state:
        if state['status'] != 'prepared':
            raise ValueError('Take already submitted or submission uncertain; inspect history')
        verify_inputs(path, state)
        event(state, 'submitting')


def bind(path, prompt_id):
    with locked_take(path) as state:
        if state['status'] != 'submitting' or state.get('prompt_id'):
            raise ValueError('Take cannot be rebound')
        verify_inputs(path, state)
        state['prompt_id'] = prompt_id
        event(state, 'submitted')


def reconcile(path, history, output_root, suite_project, brain_root):
    path, output_root = Path(path), Path(output_root).resolve()
    with locked_take(path) as state:
        verify_inputs(path, state)
        record = history.get(state['prompt_id'])
        if record and record.get('status', {}).get('status_str') == 'error':
            event(state, 'failed')
            return state
        if not record or not record.get('status', {}).get('completed'):
            raise ValueError('Submitted prompt has not completed')
        if record['status'].get('status_str') != 'success':
            event(state, 'failed')
            return state
        graph = read_json(path / 'prompt.json')
        if prompt_digest(record['prompt'][2]) != prompt_digest(graph):
            raise ValueError('History does not match frozen inputs')
        files = [item for key in ('images', 'videos', 'gifs')
                 for item in record['outputs'].get('64', {}).get(key, [])
                 if item.get('type') == 'output' and item.get('filename', '').endswith('.mp4')]
        if len(files) != 1:
            raise ValueError('Expected one review video from Master SaveVideo')
        item = files[0]
        video = (output_root / item.get('subfolder', '') / item['filename']).resolve()
        expected = output_root / Path(state['output_prefix']).parent
        if not video.is_relative_to(output_root) or video.parent != expected:
            raise ValueError('Output is outside this take')
        suite_root = output_root / 'h3_projects' / safe_id(suite_project) / 'clips'
        matches = []
        for sidecar in suite_root.glob('*.json'):
            data = read_json(sidecar)
            if data.get('prompt') and prompt_digest(data['prompt']) == prompt_digest(graph):
                matches.append((sidecar, data))
        if len(matches) != 1:
            raise ValueError('Cannot uniquely identify Suite clip from exact submitted inputs')
        sidecar, clip = matches[0]
        suite_video = sidecar.with_suffix('.mp4')
        suite_latent = sidecar.with_suffix('.safetensors')
        state['output'] = dict(path=str(video), sha256=file_hash(video), **probe_video(video))
        state['suite'] = dict(project=suite_project, clip=clip['clip'], index=clip['index'], take=clip['take'],
                              sidecar=str(sidecar), sidecar_sha256=file_hash(sidecar),
                              video=str(suite_video), video_sha256=file_hash(suite_video),
                              latent=str(suite_latent), latent_sha256=file_hash(suite_latent))
        run = Path(brain_root) / safe_id(state['prompt_id']) / 'run.json'
        if not run.is_file():
            raise ValueError('Brain run record missing')
        state['brain'] = {'run_id': state['prompt_id'], 'run_file': str(run.resolve())}
        write_json(path / 'history.json', record)
        review = state.get('review')
        changed_review = review and review['sha256'] != state['output']['sha256']
        if changed_review:
            state['review'] = None
        if changed_review or state['status'] not in ('review_pending', 'approved', 'rejected'):
            event(state, 'review_pending')
        return state


def review(path, verdicts, note, approved=False):
    with locked_take(path) as state:
        if state['status'] not in ('review_pending', 'approved', 'rejected'):
            raise ValueError('Verified output required before visual review')
        verify_inputs(path, state)
        if not note.strip() or not verdicts or any(v not in ('pass', 'fail', 'uncertain') for v in verdicts.values()):
            raise ValueError('Supply a review note and pass/fail/uncertain verdicts')
        if file_hash(state['output']['path']) != state['output']['sha256']:
            raise ValueError('Output changed since verification')
        state['review'] = dict(verdicts=verdicts, note=note, approved=approved,
                               sha256=state['output']['sha256'])
        event(state, 'approved' if approved else 'review_pending')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_cmd = commands.add_parser('prepare')
    prepare_cmd.add_argument('--shot', required=True)
    prepare_cmd.add_argument('--prompt', type=Path, required=True)
    prepare_cmd.add_argument('--workflow', type=Path, required=True)
    prepare_cmd.add_argument('--root', type=Path, default=Path('user/master_studio/takes'))
    for name in ('submitting', 'bind', 'collect', 'review'):
        command = commands.add_parser(name)
        command.add_argument('--take', type=Path, required=True)
        if name == 'bind':
            command.add_argument('--prompt-id', required=True)
        if name == 'collect':
            command.add_argument('--suite-project', required=True)
        if name == 'review':
            command.add_argument('--verdicts', type=Path, required=True)
            command.add_argument('--note', required=True)
            command.add_argument('--approve', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.root, read_json(args.prompt), read_json(args.workflow), resolve_shot_package(args.shot)))
    elif args.command == 'submitting':
        mark_submitting(args.take)
    elif args.command == 'bind':
        bind(args.take, args.prompt_id)
    elif args.command == 'collect':
        state = read_json(args.take / 'take.json')
        with urllib.request.urlopen('http://127.0.0.1:8188/history/' + safe_id(state['prompt_id']), timeout=15) as response:
            history = json.load(response)
        print(json.dumps(reconcile(args.take, history, 'output', args.suite_project,
                                   'user/workflow_monitor/runs'), indent=2))
    elif args.command == 'review':
        review(args.take, read_json(args.verdicts), args.note, args.approve)


if __name__ == '__main__':
    main()

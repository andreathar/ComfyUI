#!/usr/bin/env python3
"""Read-only preflight for the independent-shot Fantastic H3 encode recipe.

Consumes an API graph, not a canvas export. Does not import ComfyUI, load tensors,
write stages, compile browser macros, or submit prompts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

VERSION = 1
ENCODER = 'MiniMaxH3FantasticRefModTextEncode'
SUPPORTED = {
    ENCODER, 'MiniMaxH3PromptBuilder', 'MiniMaxH3MediaLoader', 'VAELoader',
    'CLIPLoader', 'PrimitiveInt', 'PrimitiveFloat', 'PrimitiveStringMultiline',
}
MODEL_INPUTS = {'VAELoader': 'vae_name', 'CLIPLoader': 'clip_name'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_digest(path):
    before = path.stat()
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(block)
    after = path.stat()
    if (before.st_mtime_ns, before.st_size, before.st_ino) != (after.st_mtime_ns, after.st_size, after.st_ino):
        raise ValueError(f'{path}: file changed during hashing')
    return sha.hexdigest()


def link(value):
    return isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and type(value[1]) is int


def ancestors(graph, roots):
    result, visiting = {}, set()

    def visit(node_id):
        if node_id in visiting:
            raise ValueError(f'{node_id}: cyclic API graph')
        if node_id in result:
            return
        if node_id not in graph:
            raise ValueError(f'{node_id}: missing upstream API node')
        node = graph[node_id]
        if not isinstance(node, dict) or not isinstance(node.get('inputs'), dict):
            raise ValueError(f'{node_id}: expected an API node with an inputs object')
        if node['class_type'] not in SUPPORTED:
            raise ValueError(f'{node_id}: unsupported encode dependency {node["class_type"]}; export/resolve it explicitly')
        visiting.add(node_id)
        for value in node['inputs'].values():
            if link(value):
                if value[1] < 0:
                    raise ValueError(f'{node_id}: negative output index')
                visit(value[0])
        visiting.remove(node_id)
        result[node_id] = {'class_type': node['class_type'], 'inputs': node['inputs']}

    for node_id in roots:
        visit(node_id)
    return result


def literal(graph, value):
    if not link(value):
        return value
    node = graph[value[0]]
    if value[1] != 0 or node['class_type'] not in {'PrimitiveInt', 'PrimitiveFloat', 'PrimitiveStringMultiline'}:
        raise ValueError(f'{value}: expected a literal or primitive output; cannot execute this node in a dry run')
    return node['inputs']['value']


def input_path(root, value):
    if not isinstance(value, str) or not value.endswith(' [input]'):
        raise ValueError(f'{value!r}: this recipe requires a saved [input] asset')
    relative = Path(value.removesuffix(' [input]'))
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError(f'{value!r}: unsafe media path')
    path = (root / 'input' / relative).resolve()
    if not path.is_relative_to((root / 'input').resolve()):
        raise ValueError(f'{value!r}: media escapes input directory')
    return path


def check(manifest, root):
    """Return a deterministic report; a matching receipt is evidence, not approval."""
    root = Path(root).resolve()
    if manifest['version'] != VERSION:
        raise ValueError('unsupported manifest version')
    if not isinstance(manifest['recipe'], str) or not manifest['recipe'].strip():
        raise ValueError('recipe must be a nonempty versioned name')
    graph = manifest['graph']
    save = graph[manifest['stage_save_node']]
    if save['class_type'] != 'AndreH3StageSave':
        raise ValueError('stage_save_node must identify AndreH3StageSave in an API graph')
    edges = {key: save['inputs'][key] for key in ('conditioning', 'latent')}
    if not all(link(v) for v in edges.values()):
        raise ValueError('stage save must link conditioning and latent')
    encoder_id = edges['conditioning'][0]
    if edges != {'conditioning': [encoder_id, 0], 'latent': [encoder_id, 2]}:
        raise ValueError('only direct Fantastic encoder conditioning/latent stages are supported')
    dependencies = ancestors(graph, [encoder_id])
    encoder = dependencies[encoder_id]
    if encoder['class_type'] != ENCODER:
        raise ValueError('stage must come directly from Fantastic RefMod Text Encode')
    inputs = encoder['inputs']
    builder_id = inputs['prompt'][0] if link(inputs['prompt']) else None
    if builder_id is None or graph[builder_id]['class_type'] != 'MiniMaxH3PromptBuilder':
        raise ValueError('encoder prompt must come from the committed Prompt Builder')
    if inputs['prompt'] != [builder_id, 0] or inputs['references'] != [builder_id, 19]:
        raise ValueError('prompt and references must come from the same Prompt Builder ports')
    builder_inputs = graph[builder_id]['inputs']
    allowed = {'prompt_text', 'builder_state', 'references', 'Edit prompt…', '+ Media loader', '+ RefMods'}
    if set(builder_inputs) - allowed:
        raise ValueError('Prompt Builder slot overrides/mods are outside this recipe')
    state = json.loads(literal(graph, builder_inputs.get('builder_state', '{}')))
    if not isinstance(state, dict) or state.get('mode', 'REF') != 'REF':
        raise ValueError('this recipe requires explicit REF-mode Prompt Builder state')
    media_link = builder_inputs['references']
    if not link(media_link) or media_link[1] != 0 or graph[media_link[0]]['class_type'] != 'MiniMaxH3MediaLoader':
        raise ValueError('Prompt Builder references must come directly from Media Loader port 0')
    for key, expected in (('clip', 'CLIPLoader'), ('vae', 'VAELoader'), ('audio_vae', 'VAELoader')):
        value = inputs[key]
        if not link(value) or value[1] != 0 or graph[value[0]]['class_type'] != expected:
            raise ValueError(f'{key}: expected {expected} port 0')
    controls = {key: literal(graph, inputs[key]) for key in
                ('width', 'height', 'length', 'reference_fps', 'ref_image_size',
                 'max_total_tokens', 'voice_description_at_label', 'stack_pictures', 'stack_pictures_n')}
    source = manifest['source']
    for field in ('delivery_frames', 'working_frames', 'width', 'height'):
        if type(source[field]) is not int or source[field] <= 0:
            raise ValueError(f'{field}: expected a positive integer')
    n = source['working_frames']
    if n < 5 or (n - 5) % 17 or n < source['delivery_frames']:
        raise ValueError('working_frames must cover delivery on the 5+17k grid')
    if (controls['width'], controls['height'], controls['length'], controls['reference_fps']) != (
            source['width'], source['height'], n, source['fps']):
        raise ValueError('requested encoder dimensions/frame count/FPS disagree with source contract')
    if source['fps'] != 24:
        raise ValueError('this independent-shot recipe currently supports conformed 24 fps only')
    if manifest['continuation'] is not False:
        raise ValueError('continuation is outside this independent-shot recipe')

    assets, media_order, prompts = {}, [], []

    def asset(binding, selected, path=None):
        entry = manifest['assets'][binding]
        if entry['selected'] != selected:
            raise ValueError(f'{binding}: selected asset differs from manifest')
        declared = Path(entry['path'])
        declared = (root / declared).resolve()
        if path is not None and declared != path:
            raise ValueError(f'{binding}: media path differs from loader resolution')
        actual = file_digest(declared)
        if actual != entry['sha256']:
            raise ValueError(f'{binding}: asset content hash mismatch')
        assets[binding] = {'selected': selected, 'path': str(declared), 'sha256': actual}

    videos = []
    for node_id, node in dependencies.items():
        inputs = node['inputs']
        kind = node['class_type']
        if kind in MODEL_INPUTS:
            key = MODEL_INPUTS[kind]
            selected = literal(graph, inputs[key])
            relative = Path(selected)
            declared = Path(manifest['assets'][f'{node_id}.{key}']['path'])
            if relative.is_absolute() or '..' in relative.parts or declared.parts[-len(relative.parts):] != relative.parts:
                raise ValueError(f'{node_id}.{key}: declared model path must end with the selected relative filename')
            asset(f'{node_id}.{key}', selected)
        elif kind == 'MiniMaxH3MediaLoader':
            items = json.loads(literal(graph, inputs['media_state']))
            if not isinstance(items, list):
                raise ValueError('media_state must contain a JSON array')
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    raise ValueError('each media_state entry must be an object')
                if item.get('enabled') is False:
                    continue
                if item['kind'] not in ('picture', 'video'):
                    raise ValueError('this recipe supports pictures plus one masked source video, not RefMods/audio')
                for key in ('file', 'mask'):
                    if key == 'file' or item.get(key):
                        asset(f'{node_id}.media.{i}.{key}', item[key], input_path(root, item[key]))
                media_order.append({'node': node_id, 'index': i, 'kind': item['kind'], 'file': item['file']})
                if item['kind'] == 'video':
                    if item.get('has_audio'):
                        raise ValueError('audio conditioning is outside this recipe')
                    videos.append(item)
        elif kind == 'MiniMaxH3PromptBuilder':
            text = literal(graph, inputs['prompt_text'])
            if not isinstance(text, str) or not text.strip():
                raise ValueError('committed prompt_text must be nonempty')
            if re.search(r'(?<!\w)![A-Za-z]|\$\{|\{\{', text):
                raise ValueError('prompt_text contains unresolved browser/template shorthand')
            prompts.append(text)
    if len(videos) != 1 or not videos[0].get('edit') or not videos[0].get('mask'):
        raise ValueError('expected exactly one masked edit video')
    picture_count = sum(m['kind'] == 'picture' for m in media_order)
    if not 1 <= picture_count <= 9:
        raise ValueError('this fixed-slot recipe supports 1–9 identity pictures')
    if len(prompts) != 1 or prompts[0] != manifest['prompt_text']:
        raise ValueError('committed prompt_text does not match the recipe')
    if set(assets) != set(manifest['assets']):
        raise ValueError('asset bindings must exactly cover the encode dependency assets')
    software = {}
    if not manifest['software']:
        raise ValueError('software source hashes are required')
    for name, entry in manifest['software'].items():
        actual = file_digest((root / entry['path']).resolve())
        if actual != entry['sha256']:
            raise ValueError(f'{name}: software content hash mismatch')
        software[name] = {'path': entry['path'], 'sha256': actual}
    key = digest({'version': VERSION, 'recipe': manifest['recipe'], 'dependencies': dependencies,
                  'edges': edges, 'source': source, 'assets': assets, 'software': software})
    stage = manifest.get('stage')
    stage_status = 'missing_receipt'
    if stage:
        try:
            actual = file_digest((root / stage['path']).resolve())
        except FileNotFoundError:
            stage_status = 'missing_artifact'
        else:
            stage_status = 'matching_receipt' if (stage['conditioning_key'] == key and stage['sha256'] == actual) else 'stale'
    return {'version': VERSION, 'conditioning_key': key, 'requested_controls': controls,
            'media_order': media_order, 'stage_status': stage_status,
            'model_resolution': 'unverified_explicit_bindings',
            'requires_encode': True,
            'reuse_authorized': False,
            'limitations': ['Does not probe/decode source, padding, guard or audio; counts are declared expectations.',
                            'Masked editing can override requested encoder dimensions/length; effective tensors are unverified.',
                            'Does not certify reference tags, likeness, performance or creative approval.',
                            'A receipt must be recorded by a trusted successful encode; this command cannot attest its origin.',
                            'Software inventory is explicit; unlisted runtime/backend changes are not detected.',
                            'Explicit model bindings are hashed, but ComfyUI search-path resolution is not verified; reuse is blocked.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        report = check(json.loads(args.manifest.read_text()), args.root)
    except (KeyError, TypeError, ValueError, OSError) as error:
        print(f'H3 preflight failed: {error}', file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

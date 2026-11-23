"""Resolve Master Movie Studio shot packages from studio records + preset folders."""

import json
import inspect
import uuid
from pathlib import Path

if __package__:
    from . import h3_recipe, production_store
    from .h3_recipe import render_prompt
    from .prompt_review import GUIDE, RULES_VERSION, review_digest, review_prompt
else:
    import h3_recipe
    from h3_recipe import render_prompt
    from prompt_review import GUIDE, RULES_VERSION, review_digest, review_prompt

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "studio/projects/the-message/silent-proof-v001"
PROMPTS = ROOT / "user/minimax_h3_prompts"
MEDIA = ROOT / "user/minimax_h3_presets"
REFMODS = ROOT / "user/minimax_h3_refmod_presets"
TRANSITIONS = ROOT / "studio/projects/the-message/silent-proof-v001/shot_transitions.json"
SNAPSHOTS = ROOT / "user/master_studio/packages"

# Prompt library filenames keyed by shot id (Silent Proof v004 category).
PROMPT_FILES = {
    "MSG_S001_SH01": "The Message _ 01 _ Cafe Wide Establishing.json",
    "MSG_S001_SH02": "The Message _ 02 _ Window Table Gaze.json",
    "MSG_S001_SH03": "The Message _ 03 _ Tabletop Note Insert.json",
    "MSG_S001_SH04": "The Message _ 04 _ Window Reaction.json",
    "MSG_S001_SH05": "The Message _ 05 _ Reverse Counter Gaze.json",
    "MSG_S001_SH06": "The Message _ 06 _ Closing Wide Master.json",
}


def default_transitions():
    return {shot_id: "cut" for shot_id in PROMPT_FILES}


def load_transitions():
    if TRANSITIONS.exists():
        data = json.loads(TRANSITIONS.read_text(encoding="utf-8"))
        out = default_transitions()
        out.update({k: str(v).lower() for k, v in data.items() if k in out})
        return out
    return default_transitions()


def resolve_shot_package(shot_id, *, project_root=None, workspace=None, recipe=None):
    shot_id = str(shot_id).strip()
    if project_root is not None:
        return resolve_project_shot_package(project_root, shot_id, workspace, recipe)
    if workspace is not None or recipe is not None:
        raise ValueError('Select a project before choosing its workspace or recipe')
    if shot_id not in PROMPT_FILES:
        raise ValueError(f"unknown shot package: {shot_id}")
    bindings = json.loads((PROJECT / "bindings.json").read_text(encoding="utf-8"))
    binding = bindings[shot_id]
    prompt = json.loads((PROMPTS / PROMPT_FILES[shot_id]).read_text(encoding="utf-8"))
    media_path = MEDIA / f"The Message _ {shot_id} Media.json"
    media = json.loads(media_path.read_text(encoding="utf-8"))
    refmod_path = REFMODS / f"The Message _ {shot_id} RefMods.json"
    if refmod_path.exists():
        refmod = json.loads(refmod_path.read_text(encoding="utf-8"))
        stack_state = {"picks": refmod.get("picks", []), "budget": refmod.get("budget", 0)}
    else:
        stack_state = {"picks": [], "budget": 0}
    transition = load_transitions().get(shot_id, "cut")
    return {
        "shot_id": shot_id,
        "prompt_text": prompt.get("prompt") or "",
        "builder_state": prompt.get("state") or {},
        "media_state": media.get("items", []),
        "stack_state": stack_state,
        "seed": int(binding.get("seed", 0)),
        "transition": transition,
        "prompt_name": prompt.get("name") or PROMPT_FILES[shot_id],
    }


def resolve_project_shot_package(project_root, shot_id, workspace, recipe):
    if __package__:
        store = production_store
    else:
        from studio import production_store as store
    if workspace is None or recipe is None:
        raise ValueError('Choose a workspace and H3 recipe for this project')
    state = store.read_project(project_root)
    return compile_project_shot_package(project_root, state, shot_id, workspace, recipe, state['bindings'].get(shot_id), state['assets'])


def compile_project_shot_package(project_root, state, shot_id, workspace, recipe, binding, assets, *, input_root=None):
    if __package__:
        store = production_store
    else:
        from studio import production_store as store
    if not any(shot['id'] == shot_id for shot in state['production']['shots']):
        raise ValueError(f'unknown project shot: {shot_id}')
    if not isinstance(binding, dict) or not isinstance(binding.get('assets'), list):
        raise ValueError(f'{shot_id}: select a shot binding and references first')
    if type(binding.get('seed')) is not int or not 0 <= binding['seed'] < 2**64:
        raise ValueError(f'{shot_id}: select an explicit seed')
    if state['transitions'].get(shot_id) not in ('cut', 'continue'):
        raise ValueError(f'{shot_id}: select a cut or continue transition')
    root = Path(workspace)
    for key in binding['assets']:
        asset = assets.get(key)
        if not isinstance(asset, dict):
            raise ValueError(f'{shot_id}: missing bound asset {key}')
        path = h3_recipe.asset_path(root, asset, input_root=input_root).resolve()
        roots = (h3_recipe.model_folders(root, 'refmods') if asset.get('kind') in ('video', 'audio')
                 else [Path(input_root) if input_root is not None else root / 'input'])
        if not any(path.is_relative_to(folder.resolve()) for folder in roots):
            raise ValueError(f'{key}: asset is outside the configured media roots')
    compiled = h3_recipe.compile_shot(state['production'], shot_id, binding, assets, recipe, root, input_root=input_root)
    if store.read_project(project_root)['revision'] != state['revision']:
        raise ValueError('The project changed while preparing this shot; reopen it')
    return {key: compiled[key] for key in ('shot_id', 'prompt_text', 'builder_state', 'media_state', 'stack_state', 'seed')} | {
        'transition': state['transitions'][shot_id], 'prompt_name': shot_id,
        'project': state['manifest']['slug'], 'project_code': state['manifest']['code'],
        'project_root': str(store.project_path(project_root)),
        'project_revision': state['revision'], 'prompt_status': 'draft_uncommitted',
        'width': compiled['recipe']['width'], 'height': compiled['recipe']['height'],
        'fps': compiled['recipe']['fps'], 'duration_s': compiled['shot']['duration_s']}


def package_table():
    return {shot_id: resolve_shot_package(shot_id) for shot_id in PROMPT_FILES}


def package_review(pkg, revision):
    state = pkg['builder_state'] if isinstance(pkg['builder_state'], dict) else {}
    ref = state.get('ref') if isinstance(state.get('ref'), dict) else {}
    supported = (state.get('mode') == 'REF' and all(k in ref for k in ('subjectDefs', 'summaryTypes', 'summaryText', 'retention', 'styleLine', 'detail', 'soundscape', 'music'))
                 and not any((state.get('off') or {}).values()) and '!' not in pkg['prompt_text']
                 and not any(d.get('voice') for d in ref.get('subjectDefs', [])))
    labels = None
    if not any(p.get('on', True) for p in pkg['stack_state'].get('picks', [])):
        counts = {'picture': 0, 'video': 0, 'audio': 0}
        for item in pkg['media_state']:
            if item.get('enabled') is False:
                continue
            kind = item.get('kind')
            if kind in counts:
                counts[kind] += 1
        labels = [f'<{kind.title()} {i}>' for kind, count in counts.items() for i in range(1, count + 1)]
        if counts['video'] or counts['picture'] > 9 or counts['audio'] > 3:
            labels = None  # Video audio routing and loader overflow need the evaluated map.
    return review_prompt(pkg['prompt_text'], pkg['builder_state'], expected_text=render_prompt(state) if supported else None,
                         reference_labels=labels, duration=state.get('duration'), package_revision=revision, seed=pkg['seed'])


def save_immutable(directory, key, payload):
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (key + '.json')
    if target.exists():
        if target.read_text(encoding='utf-8') != payload:
            raise ValueError('Saved snapshot changed: ' + key)
        return target
    pending = directory / ('.' + key + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with pending.open('x', encoding='utf-8') as stream:
            stream.write(payload)
        try:
            target.hardlink_to(pending)
        except FileExistsError:
            if target.read_text(encoding='utf-8') != payload:
                raise ValueError('Saved snapshot changed: ' + key)
    finally:
        pending.unlink(missing_ok=True)
    return target


def live_resolver_code():
    """Use the same resolver on the canvas without importing project modules."""
    constants = {"PROJECT": PROJECT, "PROMPTS": PROMPTS, "MEDIA": MEDIA, "REFMODS": REFMODS,
                 "TRANSITIONS": TRANSITIONS, "SNAPSHOTS": SNAPSHOTS}
    header = ["import json", "import hashlib", "import uuid", "import re", "from pathlib import Path"]
    header += [f"{key} = Path({str(path)!r})" for key, path in constants.items()]
    header += [f"PROMPT_FILES = {PROMPT_FILES!r}"]
    header += [f'GUIDE = {GUIDE!r}', f'RULES_VERSION = {RULES_VERSION!r}']
    header += [inspect.getsource(fn) for fn in (default_transitions, load_transitions, resolve_shot_package, render_prompt,
                                               review_digest, review_prompt, package_review, save_immutable)]
    return "\n".join(header) + '''
shot_id, = inputs
pkg = resolve_shot_package(shot_id)
payload = json.dumps(pkg, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
revision = hashlib.sha256(payload.encode('utf-8')).hexdigest()
snapshot = save_immutable(SNAPSHOTS, revision, payload)
review = package_review(pkg, revision)
review_path = save_immutable(SNAPSHOTS.parent / 'prompt_reviews', review['review_sha256'],
                             json.dumps(review, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
summary = dict(shot_id=pkg['shot_id'], prompt_name=pkg['prompt_name'], seed=pkg['seed'],
               transition=pkg['transition'], revision=revision, snapshot=str(snapshot),
               schema='workflow-monitor.runtime.v1', kind='prompt_review', values=review, review_file=str(review_path),
               authority='Committed prompt, media and RefMod libraries; linked widgets are previews')
outputs[:] = [pkg['prompt_text'], json.dumps(pkg['builder_state'], separators=(',', ':')),
              json.dumps(pkg['media_state'], separators=(',', ':')),
              json.dumps(pkg['stack_state'], separators=(',', ':')),
              int(pkg['seed']), str(pkg['transition']), json.dumps(summary, ensure_ascii=False, indent=2)]
'''

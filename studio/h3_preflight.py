"""Read-only asset/model checks and explicit dispatch resource evidence."""

from pathlib import Path
import time
import os

import yaml

import h3_graph
import h3_recipe as h3


def resolve_model(workspace, role):
    workspace = Path(workspace).resolve()
    category = 'vae' if role.endswith('_vae') else role
    folders = {'diffusion_models': ['unet', 'diffusion_models'], 'text_encoders': ['text_encoders', 'clip'], 'vae': ['vae']}
    paths = [workspace / 'models' / name for name in folders[category]]
    config = workspace / 'extra_model_paths.yaml'
    if config.is_file():
        for group in (yaml.safe_load(config.read_text()) or {}).values():
            if not group:
                continue
            base = group.get('base_path', str(workspace))
            base = Path(os.path.expandvars(os.path.expanduser(base)))
            if not base.is_absolute():
                base = workspace / base
            for key, value in group.items():
                mapped = {'unet': 'diffusion_models', 'clip': 'text_encoders'}.get(key, key)
                if mapped != category:
                    continue
                for folder in value.splitlines():
                    if not folder:
                        continue
                    path = Path(os.path.normpath(base / folder))
                    if path in paths:
                        if not group.get('is_default'):
                            continue
                        paths.remove(path)
                    if group.get('is_default'):
                        paths.insert(0, path)
                    else:
                        paths.append(path)
    filename = h3.DIAGNOSTIC['models'][role]
    return next((path / filename for path in paths if (path / filename).is_file()), paths[0] / filename)


def check(workspace, models, assets, registered_nodes=None, rehash=False):
    errors, warnings = [], []
    for role in h3.DIAGNOSTIC['models']:
        if role not in models:
            errors.append(f'{role}: model pin missing')
    for role, model in models.items():
        if role not in h3.DIAGNOSTIC['models']:
            errors.append(f'{role}: unknown model role')
            continue
        category = 'vae' if role.endswith('_vae') else role
        expected = f"models/{category}/{h3.DIAGNOSTIC['models'][role]}"
        if model['path'] != expected:
            errors.append(f'{role}: model pin does not match loader filename {expected}')
        config = Path(workspace) / 'extra_model_paths.yaml'
        config_hash = h3.file_hash(config) if config.is_file() else None
        if model.get('resolver_config_sha256') != config_hash:
            errors.append(f'{role}: model resolver configuration changed or unpinned')
        path = resolve_model(workspace, role)
        if not path.is_file():
            errors.append(f'{role}: weight missing: {path}')
            continue
        stat = path.stat()
        if stat.st_size != model['size_bytes'] or stat.st_mtime_ns != model['mtime_ns']:
            errors.append(f'{role}: model stamp changed; verify hash and explicitly repin')
        if rehash and h3.file_hash(path) != model['sha256']:
            errors.append(f'{role}: model hash mismatch')
    for key, asset in assets.items():
        path = h3.asset_path(workspace, asset)
        if not path.is_file() or h3.file_hash(path) != asset['sha256']:
            errors.append(f'{key}: asset missing or hash changed')
        if asset.get('approved') is not True:
            errors.append(f'{key}: asset approval required')
    if registered_nodes is None:
        warnings.append('Live node registration not checked; this is file preflight only.')
    else:
        needed = {n['class_type'] for n in h3_graph.BASE.values()}
        for node in sorted(needed - set(registered_nodes)):
            errors.append(f'node unavailable: {node}; distinguish disabled native node from absent pack before installing')
    if not rehash:
        warnings.append('Model SHA-256 values were pinned separately; this check compares file size and mtime, not full model bytes.')
    return {'ready': not errors, 'errors': errors, 'warnings': warnings}


def resources(snapshot):
    errors = []
    observed = snapshot.get('observed_at')
    if not isinstance(observed, (int, float)) or not 0 <= time.time() - observed <= 120:
        errors.append('resource observation missing or older than two minutes')
    if snapshot.get('running') != 0 or snapshot.get('pending') != 0:
        errors.append('ComfyUI queue is busy or unknown')
    if snapshot.get('conflicting_export') is not False:
        errors.append('Conflicting GPU export status is active or unknown')
    for field in ('free_ram_bytes', 'free_vram_bytes'):
        if not isinstance(snapshot.get(field), (int, float)) or snapshot[field] <= 0:
            errors.append(f'{field} is unknown or exhausted')
    return {'ready': not errors, 'errors': errors,
            'warnings': ['Free memory is a snapshot, not a measured peak-memory qualification or GPU reservation.'], 'snapshot': snapshot}

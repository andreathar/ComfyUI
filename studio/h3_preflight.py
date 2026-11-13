"""Read-only asset/model checks and explicit dispatch resource evidence."""

import argparse
import json
from pathlib import Path
import subprocess
import time
import os
import urllib.request

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


def resources(snapshot, min_free_ram_bytes=0, min_free_vram_bytes=0):
    errors = []
    warnings = ['Free memory is a snapshot, not a measured peak-memory qualification or GPU reservation.']
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
    min_ram = max(min_free_ram_bytes, snapshot.get('min_free_ram_bytes', 0) or 0)
    min_vram = max(min_free_vram_bytes, snapshot.get('min_free_vram_bytes', 0) or 0)
    if isinstance(snapshot.get('free_ram_bytes'), (int, float)) and snapshot['free_ram_bytes'] > 0 and snapshot['free_ram_bytes'] < min_ram:
        errors.append(f"free_ram_bytes ({snapshot['free_ram_bytes']}) is below required minimum ({min_ram})")
    usable_vram = snapshot.get('usable_comfy_vram_bytes', snapshot.get('free_vram_bytes'))
    if isinstance(usable_vram, (int, float)) and snapshot.get('free_vram_bytes', 0) > 0 and usable_vram < min_vram:
        errors.append(f'usable_comfy_vram_bytes ({usable_vram}) is below required minimum ({min_vram})')
    foreign = snapshot.get('foreign_gpu_processes')
    if foreign:
        errors.append('foreign GPU process holds VRAM: ' + ', '.join(str(item) for item in foreign))
    temp = snapshot.get('gpu_temp_c')
    if isinstance(temp, (int, float)):
        if temp >= 88:
            errors.append(f'GPU temperature too high to start render ({temp} C); let GPU cool first')
        elif temp >= 78:
            warnings.append(f'GPU temperature is {temp} C before dispatch; RTX 3060 throttles clocks near 89 C.')
    return {'ready': not errors, 'errors': errors, 'warnings': warnings, 'snapshot': snapshot}


def capture_snapshot(server='http://127.0.0.1:8188', min_free_ram_bytes=10 * 2**30, min_free_vram_bytes=4 * 2**30):
    with urllib.request.urlopen(server.rstrip('/') + '/queue', timeout=10) as response:
        queue = json.load(response)
    meminfo = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        if ':' in line:
            key, rest = line.split(':', 1)
            parts = rest.strip().split()
            if parts and parts[0].isdigit():
                meminfo[key] = int(parts[0]) * 1024
    gpu = subprocess.run(
        ['nvidia-smi', '--query-gpu=memory.free,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()[0]
    free_mib, total_mib, temp_c = [int(part.strip()) for part in gpu.split(',')]
    apps_out = subprocess.run(
        ['nvidia-smi', '--query-compute-apps=pid,process_name,used_gpu_memory', '--format=csv,noheader,nounits'],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    comfy_mib = 0
    foreign = []
    for line in apps_out.splitlines():
        if not line.strip():
            continue
        pid_text, name, used_text = [part.strip() for part in line.split(',', 2)]
        used_mib = int(used_text) if used_text.isdigit() else 0
        cmdline = Path(f'/proc/{pid_text}/cmdline').read_text(errors='ignore').replace('\x00', ' ') if Path(f'/proc/{pid_text}/cmdline').is_file() else ''
        if 'main.py' in cmdline and '8188' in cmdline:
            comfy_mib += used_mib
        elif used_mib > 0:
            foreign.append(f'{Path(name).name}(pid={pid_text},{used_mib}MiB)')
    free_vram_bytes = free_mib * 2**20
    return {
        'observed_at': time.time(),
        'running': len(queue.get('queue_running', [])),
        'pending': len(queue.get('queue_pending', [])),
        'conflicting_export': bool(foreign),
        'free_ram_bytes': meminfo.get('MemAvailable', meminfo.get('MemFree', 0)),
        'free_vram_bytes': free_vram_bytes,
        'usable_comfy_vram_bytes': (free_mib + comfy_mib) * 2**20,
        'total_vram_bytes': total_mib * 2**20,
        'gpu_temp_c': temp_c,
        'foreign_gpu_processes': foreign,
        'min_free_ram_bytes': min_free_ram_bytes,
        'min_free_vram_bytes': min_free_vram_bytes,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    snap = sub.add_parser('snapshot')
    snap.add_argument('--server', default='http://127.0.0.1:8188')
    snap.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    data = capture_snapshot(args.server)
    text = json.dumps(data, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()

"""Admission and process ownership for a separate native story-planning job."""

import asyncio
import ctypes
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import sys
import tempfile
import time
from uuid import UUID

import aiohttp

from .asset_vision import MODEL, MODEL_HOME, STUDIO_CACHE, launch_args, owns_listener
from .production_bootstrap import json_bytes
from .production_generate import DEFAULT_ENGINE
from . import production_outline, storyboard


NODE_TYPE = 'StudioStoryboardPlan'
ENGINE = DEFAULT_ENGINE
MODEL_FILE = MODEL_HOME / f'{MODEL}.gguf'
CACHE = STUDIO_CACHE
START_TIMEOUT = 120
REQUEST_TIMEOUT = 360


class PlanningCancelled(Exception):
    pass


def validate_inputs(inputs):
    if set(inputs) != {'story', 'title', 'project_code'} or any(not isinstance(value, str) or not value.strip() for value in inputs.values()):
        raise ValueError('Story, title and project code are required')
    if not re.fullmatch(r'[A-Z0-9]{2,8}', inputs['project_code']):
        raise ValueError('Project code must be 2–8 uppercase letters or digits')


def check_queue(queue, prompt_id, inputs):
    running = queue.get('queue_running')
    if not isinstance(running, list) or len(running) != 1 or not isinstance(queue.get('queue_pending'), list):
        raise ValueError('Story planning must own the only running native queue job')
    item = running[0]
    if not isinstance(item, (list, tuple)) or len(item) < 5 or item[1] != prompt_id or not isinstance(item[2], dict):
        raise ValueError('Story-planning queue ownership changed')
    planning = []
    for node in item[2].values():
        if not isinstance(node, dict):
            raise ValueError('Invalid story-planning prompt')
        if node.get('class_type') == NODE_TYPE:
            planning.append(node)
        elif node.get('class_type') != 'WorkflowMonitorBrain' or node.get('inputs', {}).get('enabled') is not True:
            raise ValueError('Run story planning separately from image or video generation')
    if len(planning) != 1 or planning[0].get('inputs') != inputs:
        raise ValueError('Story-planning inputs do not match the running job')


def check_capacity(stats):
    available = stats.get('system', {}).get('ram_free')
    devices = stats.get('devices')
    if type(available) not in (int, float) or not math.isfinite(available) or available < 15360 * 2**20:
        raise ValueError('Story planning needs at least 15 GiB available RAM; no model was loaded')
    if (not isinstance(devices, list) or len(devices) != 1 or devices[0].get('type') != 'cuda'
            or 'NVIDIA' not in devices[0].get('name', '')
            or type(devices[0].get('vram_free')) not in (int, float)
            or not math.isfinite(devices[0]['vram_free'])):
        raise ValueError('Cannot verify the NVIDIA memory budget for the selected story runtime')
    if devices[0]['vram_free'] < 5200 * 2**20:
        raise ValueError('Another local model is using the GPU; free it before story planning')


def publish(root, name, raw, *, replace=False):
    fd, temporary = tempfile.mkstemp(prefix='.writing-', dir=root)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, root / name)
        else:
            os.link(temporary, root / name)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def object_schema(properties, optional=()):
    return {'type': 'object', 'properties': properties, 'additionalProperties': False,
            'required': [key for key in properties if key not in optional]}


TEXT = {'type': 'string', 'minLength': 1}
INDEXES = {'type': 'array', 'items': {'type': 'integer', 'minimum': 0}}
OUTLINE_SCHEMA = {'anyOf': [object_schema({
    'place': object_schema({'name': TEXT, 'kind': {'enum': ['INT', 'EXT', 'INT/EXT']},
                            'time': {'enum': ['dawn', 'day', 'golden-hour', 'dusk', 'night']}, 'description': TEXT,
                            'light': TEXT, 'quality': {'enum': ['soft', 'hard', 'mixed']}}, optional=('light', 'quality')),
    'cast': {'type': 'array', 'maxItems': 8, 'items': object_schema({'name': TEXT, 'appearance': TEXT, 'wardrobe': TEXT})},
    'props': {'type': 'array', 'maxItems': 8, 'items': object_schema({'name': TEXT, 'description': TEXT})},
    'shots': {'type': 'array', 'minItems': 1, 'maxItems': 4, 'items': object_schema({
        'excerpt': TEXT, 'action': TEXT, 'cast': INDEXES, 'props': INDEXES,
        'size': {'enum': ['extreme-wide', 'wide', 'full', 'medium-wide', 'medium', 'medium-close', 'close-up', 'extreme-close-up']},
        'move': {'enum': ['static', 'pan', 'tilt', 'dolly-in', 'dolly-out', 'track', 'handheld', 'crane', 'orbit', 'zoom', 'whip-pan']},
        'seconds': {'type': 'number'}, 'lens': TEXT}, optional=('move', 'seconds', 'lens'))},
}), object_schema({'questions': {'type': 'array', 'minItems': 1, 'maxItems': 4,
                               'items': object_schema({'about': TEXT, 'ask': TEXT})}})]}


async def request(session, port, path, key, payload=None):
    async with session.request('GET' if payload is None else 'POST', f'http://127.0.0.1:{port}{path}',
                               headers={'Authorization': 'Bearer ' + key}, json=payload,
                               allow_redirects=False) as response:
        if 300 <= response.status < 400:
            raise ValueError('Local model redirects are not permitted')
        response.raise_for_status()
        raw = bytearray()
        async for chunk in response.content.iter_chunked(65536):
            raw.extend(chunk)
            if len(raw) > 1024 * 1024:
                raise ValueError('Local model response exceeds the limit')
        return json.loads(raw)


async def wait_owned(awaitable, process, guard):
    task = asyncio.ensure_future(awaitable)
    try:
        while not task.done():
            guard()
            if process.returncode is not None:
                raise RuntimeError('Owned story runtime exited; inspect runtime.log')
            await asyncio.wait({task}, timeout=.1)
        guard()
        return await task
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


async def stop_owned(process):
    if process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=15)
        except TimeoutError:
            process.kill()
            await process.wait()


async def identity(path, guard):
    path = path.resolve(strict=True)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            guard()
            digest.update(chunk)
            await asyncio.sleep(0)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('Runtime artifact changed while hashing')
    return {'path': str(path), 'bytes': after.st_size, 'mtime_ns': after.st_mtime_ns, 'sha256': digest.hexdigest()}


async def plan(inputs, prompt_id, jobs_root, queue_state, resources, cancelled, progress):
    if str(UUID(prompt_id)) != prompt_id:
        raise ValueError('Expected canonical native prompt UUID')
    validate_inputs(inputs)

    def guard():
        if cancelled():
            raise PlanningCancelled('Story planning cancelled')
        check_queue(queue_state(), prompt_id, inputs)

    guard()
    before = resources()
    check_capacity(before)
    jobs_root = Path(jobs_root)
    jobs_root.mkdir(parents=True, exist_ok=True)
    root = jobs_root / prompt_id
    root.mkdir()
    publish(root, 'source.txt', inputs['story'].encode())
    state = {'job_id': prompt_id, 'status': 'preparing', 'started': time.time(), 'resources_before': before,
             'source_sha256': hashlib.sha256(inputs['story'].encode()).hexdigest(),
             'title': inputs['title'], 'project_code': inputs['project_code'], 'render_ready': False}

    def save():
        publish(root, 'state.json', json_bytes(state), replace=True)

    save()
    process = None
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with (CACHE / 'asset-vision.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError('Another Studio model worker is active; no model was loaded') from error
            state['artifacts'] = {'engine': await identity(ENGINE, guard), 'model': await identity(MODEL_FILE, guard)}
            check_capacity(resources())
            await progress(1)
            with tempfile.TemporaryDirectory(prefix='story-', dir=CACHE) as work, (root / 'runtime.log').open('wb') as log:
                key = secrets.token_urlsafe(32)
                key_file = Path(work) / 'key'
                key_file.write_text(key + '\n')
                key_file.chmod(0o600)
                with socket.socket() as reserve:
                    reserve.bind(('127.0.0.1', 0))
                    port = reserve.getsockname()[1]
                args = launch_args(ENGINE, MODEL_FILE, None, port, key_file)
                # Pin the installed engine's existing default desktop margin explicitly.
                args += ['--fit-target', '1024']
                environment = {name: value for name, value in os.environ.items()
                               if name in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'LD_LIBRARY_PATH', 'CUDA_VISIBLE_DEVICES')}
                guard()
                process = await asyncio.create_subprocess_exec(sys.executable, '-m', 'studio.production_runtime',
                    'exec', str(os.getpid()), *args, env=environment, stdin=asyncio.subprocess.DEVNULL, stdout=log, stderr=log)
                try:
                    state.update(status='loading', runtime_pid=process.pid, runtime_port=port)
                    save()
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT), trust_env=False) as session:
                        deadline = time.monotonic() + START_TIMEOUT
                        while True:
                            guard()
                            if process.returncode is not None:
                                raise RuntimeError('Owned story runtime failed to start; inspect runtime.log')
                            if time.monotonic() >= deadline:
                                raise TimeoutError('Story runtime startup timed out')
                            try:
                                if owns_listener(process.pid, port):
                                    health = await wait_owned(asyncio.wait_for(request(session, port, '/health', key), 2), process, guard)
                                    if health.get('status') == 'ok':
                                        break
                            except (aiohttp.ClientConnectorError, TimeoutError):
                                pass
                            except aiohttp.ClientResponseError as error:
                                if error.status != 503:
                                    raise
                            await asyncio.sleep(.1)
                        inventory = await wait_owned(request(session, port, '/v1/models', key), process, guard)
                        props = await wait_owned(request(session, port, '/props', key), process, guard)
                        if ([item.get('id') for item in inventory.get('data', [])] != [MODEL]
                                or Path(props.get('model_path', '')).resolve() != MODEL_FILE.resolve()):
                            raise ValueError('Owned runtime loaded an unexpected story model')
                        state.update(status='analyzing', runtime_properties=props)
                        save()
                        await progress(2)
                        messages = [{'role': 'system', 'content': production_outline.SYSTEM},
                                    {'role': 'user', 'content': json.dumps({'story': inputs['story']}, ensure_ascii=False)}]
                        for attempt in range(2):
                            guard()
                            if not owns_listener(process.pid, port):
                                raise ValueError('Story runtime no longer owns its listener')
                            payload = {'model': MODEL, 'messages': messages, 'temperature': 0, 'max_tokens': 768,
                                       'chat_template_kwargs': {'enable_thinking': False},
                                       'response_format': {'type': 'json_schema', 'json_schema': {
                                           'name': 'story_outline', 'strict': True, 'schema': OUTLINE_SCHEMA}}}
                            reply = await wait_owned(request(session, port, '/v1/chat/completions', key, payload), process, guard)
                            publish(root, f'reply-{attempt + 1}.json', json_bytes(reply))
                            if reply.get('model') != MODEL:
                                raise ValueError('Unexpected local story model; no retry submitted')
                            choice = reply.get('choices', [{}])[0]
                            if choice.get('finish_reason') != 'stop':
                                raise ValueError('Incomplete story reply; no automatic retry submitted')
                            content = choice.get('message', {}).get('content')
                            try:
                                result = production_outline.expand(json.loads(content), inputs['story'], inputs['project_code'], inputs['title'])
                                if result.get('problems'):
                                    raise ValueError('\n'.join(result['problems']))
                                break
                            except (ValueError, TypeError) as error:
                                if attempt:
                                    raise ValueError('Story outline is invalid after one bounded repair') from error
                                messages += [{'role': 'assistant', 'content': content}, {'role': 'user', 'content':
                                    'Fix only these validation errors; keep the original story unchanged: ' + str(error)[:2000]}]
                        if 'document' in result:
                            result['document'] = storyboard.upgrade(result['document'])
                        await progress(3)
                finally:
                    try:
                        state['status'] = 'stopping'
                        save()
                    finally:
                        cleanup = asyncio.create_task(stop_owned(process))
                        interrupted = False
                        while not cleanup.done():
                            try:
                                await asyncio.shield(cleanup)
                            except asyncio.CancelledError:
                                interrupted = True
                        await cleanup
                        if interrupted:
                            raise asyncio.CancelledError
            guard()
            result.update(runtime_pid=process.pid, runtime_port=port, release={'process_exited': True, 'resources_after': resources()},
                          render_ready=False, job_id=prompt_id)
            publish(root, 'proposal.json', json_bytes(result))
            state.update(status='needs_review', result_file='proposal.json', release=result['release'])
            await progress(4)
            return result
    except BaseException as error:
        state.update(status='cancelled' if isinstance(error, (PlanningCancelled, asyncio.CancelledError)) else 'failed', error=str(error)[:500])
        raise
    finally:
        state.setdefault('release', {}).update(process_exited=process is None or process.returncode is not None)
        state['ended'] = time.time()
        save()


def exec_owned(parent_pid, command):
    if sys.platform != 'linux':
        raise RuntimeError('Owned story runtime currently requires Linux parent-death signaling')
    if os.getppid() != parent_pid:
        raise RuntimeError('Runtime parent changed before startup')
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'Cannot bind story runtime lifetime')
    if os.getppid() != parent_pid:
        raise RuntimeError('Runtime parent exited during startup')
    os.execv(command[0], command)


if __name__ == '__main__':
    if len(sys.argv) < 4 or sys.argv[1] != 'exec':
        raise SystemExit('Internal owned-runtime launcher: exec PARENT_PID COMMAND [ARGS]')
    exec_owned(int(sys.argv[2]), sys.argv[3:])

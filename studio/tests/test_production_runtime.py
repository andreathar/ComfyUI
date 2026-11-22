import asyncio
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from studio import production_runtime as runtime


INPUTS = {'story': 'INT. ROOM - DAY. Ada opens a letter.', 'title': 'A letter', 'project_code': 'LET'}


def queue():
    return {'queue_running': [[1, 'job-a', {
        '1': {'class_type': runtime.NODE_TYPE, 'inputs': INPUTS},
        '2': {'class_type': 'WorkflowMonitorBrain', 'inputs': {'enabled': True}},
    }, {}, ['1', '2']]], 'queue_pending': []}


def stats():
    return {'system': {'ram_free': 16 * 2**30}, 'devices': [
        {'type': 'cuda', 'name': 'NVIDIA test', 'vram_free': 5500 * 2**20}]}


@pytest.mark.parametrize('code', ['a', 'has spaces', 'TOOLONG123', '../LET'])
def test_invalid_project_code_cannot_start_a_model_or_write_a_job(tmp_path, fake_runtime, monkeypatch, code):
    async def forbidden(*args, **kwargs):
        pytest.fail('Invalid project code must be rejected before model launch')
    monkeypatch.setattr(runtime.asyncio, 'create_subprocess_exec', forbidden)
    inputs = dict(INPUTS, project_code=code)
    prompt_id = '00000000-0000-4000-8000-000000000005'
    snapshot = queue()
    snapshot['queue_running'][0][1] = prompt_id
    snapshot['queue_running'][0][2]['1']['inputs'] = inputs
    async def progress(value):
        pass
    with pytest.raises(ValueError, match='Project code must be 2'):
        asyncio.run(runtime.plan(inputs, prompt_id, tmp_path / 'jobs', lambda: snapshot,
                                 stats, lambda: False, progress))
    assert not (tmp_path / 'jobs').exists()


def test_admission_recognizes_its_own_prompt_and_does_not_wait_for_pending_jobs():
    snapshot = queue()
    snapshot['queue_pending'] = [[2, 'next-render', {}, {}, []]]
    runtime.check_queue(snapshot, 'job-a', INPUTS)
    runtime.check_capacity(stats())


@pytest.mark.parametrize('mutation', ['wrong-job', 'wrong-story', 'extra-render', 'missing-running', 'malformed', 'wrong-monitor'])
def test_admission_rejects_wrong_or_mixed_execution_ownership(mutation):
    snapshot = copy.deepcopy(queue())
    if mutation == 'wrong-job':
        snapshot['queue_running'][0][1] = 'other-job'
    elif mutation == 'wrong-story':
        snapshot['queue_running'][0][2]['1']['inputs'] = dict(INPUTS, story='Changed story')
    elif mutation == 'extra-render':
        snapshot['queue_running'][0][2]['3'] = {'class_type': 'KSampler', 'inputs': {}}
    elif mutation == 'missing-running':
        snapshot['queue_running'] = []
    elif mutation == 'wrong-monitor':
        snapshot['queue_running'][0][2]['2']['inputs']['enabled'] = False
    else:
        snapshot['queue_pending'] = None
    with pytest.raises(ValueError):
        runtime.check_queue(snapshot, 'job-a', INPUTS)


@pytest.mark.parametrize('mutation', ['low-ram', 'external-gpu', 'unknown-gpu', 'missing-ram'])
def test_resource_pressure_prevents_model_loading(mutation):
    snapshot = stats()
    if mutation == 'low-ram':
        snapshot['system']['ram_free'] = 14 * 2**30
    elif mutation == 'external-gpu':
        snapshot['devices'][0]['vram_free'] = 2 * 2**30
    elif mutation == 'unknown-gpu':
        snapshot['devices'] = []
    else:
        del snapshot['system']['ram_free']
    with pytest.raises(ValueError):
        runtime.check_capacity(snapshot)


def test_parent_death_guard_stops_only_its_owned_exec_child(tmp_path):
    if sys.platform != 'linux':
        pytest.skip('Linux parent-death protocol')
    pid_file = tmp_path / 'pid'
    script = "import os,time,pathlib;pathlib.Path(%r).write_text(str(os.getpid()));time.sleep(60)" % str(pid_file)
    launcher = "import os,subprocess,sys,time;subprocess.Popen([sys.executable,'-m','studio.production_runtime','exec',str(os.getpid()),sys.executable,'-c',%r]);time.sleep(60)" % script
    parent = subprocess.Popen([sys.executable, '-c', launcher])
    sibling = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'])
    child = None
    try:
        deadline = time.monotonic() + 5
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        assert pid_file.exists(), 'Owned exec child never started'
        child = int(pid_file.read_text())
        parent.terminate()
        parent.wait(timeout=5)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            path = runtime.Path('/proc') / str(child) / 'stat'
            try:
                zombie = path.read_text().split()[2] == 'Z'
            except (FileNotFoundError, ProcessLookupError):
                break
            if zombie:
                break
            time.sleep(.02)
        else:
            pytest.fail('Owned child survived its parent')
        assert sibling.poll() is None
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait()
        sibling.terminate()
        sibling.wait(timeout=5)
        if child:
            try:
                os.kill(child, 9)
            except ProcessLookupError:
                pass


@pytest.fixture
def fake_runtime(tmp_path, monkeypatch):
    source = json.loads((runtime.Path(__file__).parent / 'fixtures/storyboard/cases.json').read_text())['cases'][0]
    inputs = {'story': source['source_text'], 'title': 'A letter', 'project_code': 'LET'}
    model = tmp_path / 'model.json'
    model.write_text(json.dumps({'outline': source['compact_outline']}))
    engine = tmp_path / 'fake-engine'
    engine.write_text('#!' + sys.executable + '\n' + '''
import argparse,http.server,json,time
p=argparse.ArgumentParser();p.add_argument('--port',type=int);p.add_argument('--model');p.add_argument('--alias');p.add_argument('--api-key-file');a,_=p.parse_known_args()
key=open(a.api_key_file).read().strip(); data=json.load(open(a.model))
class Handler(http.server.BaseHTTPRequestHandler):
 calls=0
 def log_message(self,*args): pass
 def answer(self,value):
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(value).encode())
 def do_GET(self):
  if self.headers.get('Authorization') != 'Bearer '+key: self.send_error(403);return
  if self.path == '/health': self.answer({'status':'ok'})
  elif self.path == '/props': self.answer({'model_path':a.model,'build_info':'dummy-test-build'})
  else: self.answer({'data':[{'id':data.get('inventory',a.alias)}]})
 def do_POST(self):
  if self.headers.get('Authorization') != 'Bearer '+key: self.send_error(403);return
  request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  open(a.model+'.request','w').write(json.dumps(request))
  Handler.calls+=1;open(a.model+'.calls','w').write(str(Handler.calls))
  if data.get('status'): self.send_error(data['status']);return
  time.sleep(data.get('delay',0))
  outlines=data.get('outlines',[data['outline']]);outline=outlines[min(Handler.calls-1,len(outlines)-1)]
  self.answer({'model':data.get('model',a.alias),'choices':[{'finish_reason':data.get('finish','stop'),'message':{'content':json.dumps(outline)}}]})
http.server.HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
''')
    engine.chmod(0o700)
    monkeypatch.setattr(runtime, 'ENGINE', engine)
    monkeypatch.setattr(runtime, 'MODEL_FILE', model)
    monkeypatch.setattr(runtime, 'CACHE', tmp_path / 'cache')
    snapshot = queue()
    snapshot['queue_running'][0][2]['1']['inputs'] = inputs
    return inputs, model, lambda: snapshot


def test_owned_local_roundtrip_preserves_source_and_exits_before_return(tmp_path, fake_runtime):
    inputs, model, queue_state = fake_runtime
    stages = []
    async def progress(value):
        stages.append(value)
    result = asyncio.run(runtime.plan(inputs, '00000000-0000-4000-8000-000000000001', tmp_path / 'jobs',
                                      lambda: dict(queue_state(), queue_running=[[
                                          1, '00000000-0000-4000-8000-000000000001', queue_state()['queue_running'][0][2], {}, ['1', '2']]]),
                                      stats, lambda: False, progress))
    assert result['document']['project']['source_text'] == inputs['story']
    assert result['document']['schema_version'] == 2
    assert result['release']['process_exited'] is True
    assert not runtime.owns_listener(result['runtime_pid'], result['runtime_port'])
    request = json.loads(model.with_suffix('.json.request').read_text())
    assert request['response_format']['type'] == 'json_schema'
    assert request['messages'][1]['content'] == json.dumps({'story': inputs['story']}, ensure_ascii=False)
    assert stages[-1] == 4


@pytest.mark.parametrize('failure', ['cancel', 'wrong-model', 'incomplete'])
def test_failed_or_cancelled_inference_releases_owned_server_and_keeps_story(tmp_path, fake_runtime, failure):
    inputs, model, queue_state = fake_runtime
    data = json.loads(model.read_text())
    if failure == 'cancel':
        data['delay'] = 60
    elif failure == 'wrong-model':
        data['model'] = 'wrong-model'
    else:
        data['finish'] = 'length'
    model.write_text(json.dumps(data))
    started = time.monotonic()
    async def progress(value):
        pass
    prompt_id = '00000000-0000-4000-8000-000000000002'
    def owned():
        snapshot = queue_state()
        snapshot['queue_running'][0][1] = prompt_id
        return snapshot
    with pytest.raises((runtime.PlanningCancelled, ValueError)):
        asyncio.run(runtime.plan(inputs, prompt_id, tmp_path / 'jobs', owned, stats,
                                  lambda: failure == 'cancel' and time.monotonic() - started > .6, progress))
    root = tmp_path / 'jobs' / prompt_id
    state = json.loads((root / 'state.json').read_text())
    assert state['release']['process_exited'] is True
    assert not runtime.owns_listener(state['runtime_pid'], state['runtime_port'])
    assert (root / 'source.txt').read_bytes() == inputs['story'].encode()
    assert not (root / 'proposal.json').exists()
    assert time.monotonic() - started < 5


@pytest.mark.parametrize('failed_stage', ['loading', 'stopping'])
def test_state_write_failure_cannot_leave_an_owned_model_running(tmp_path, fake_runtime, monkeypatch, failed_stage):
    inputs, _, queue_state = fake_runtime
    original_publish = runtime.publish
    original_spawn = runtime.asyncio.create_subprocess_exec
    children = []
    async def spawn(*args, **kwargs):
        child = await original_spawn(*args, **kwargs)
        children.append(child)
        return child
    def publish(root, name, raw, **kwargs):
        if name == 'state.json' and json.loads(raw)['status'] == failed_stage:
            raise OSError('state disk full')
        return original_publish(root, name, raw, **kwargs)
    monkeypatch.setattr(runtime, 'publish', publish)
    monkeypatch.setattr(runtime.asyncio, 'create_subprocess_exec', spawn)
    prompt_id = '00000000-0000-4000-8000-000000000003'
    snapshot = queue_state()
    snapshot['queue_running'][0][1] = prompt_id
    async def scenario():
        async def progress(value):
            pass
        try:
            with pytest.raises(OSError, match='state disk full'):
                await runtime.plan(inputs, prompt_id, tmp_path / 'jobs', lambda: snapshot, stats, lambda: False, progress)
            assert children and children[0].returncode is not None, 'Disk failure leaked the owned model'
        finally:
            for child in children:
                if child.returncode is None:
                    child.kill()
                    await child.wait()
    asyncio.run(scenario())


@pytest.mark.parametrize('failure', ['timeout', 'wrong-listener', 'transport', 'wrong-inventory'])
def test_protocol_failures_do_not_retry_or_contact_an_unowned_listener(tmp_path, fake_runtime, monkeypatch, failure):
    inputs, model, queue_state = fake_runtime
    data = json.loads(model.read_text())
    if failure == 'timeout':
        data['delay'] = 60
        monkeypatch.setattr(runtime, 'REQUEST_TIMEOUT', .2)
    elif failure == 'wrong-listener':
        monkeypatch.setattr(runtime, 'START_TIMEOUT', .2)
        monkeypatch.setattr(runtime, 'owns_listener', lambda *_: False)
    elif failure == 'transport':
        data['status'] = 503
    else:
        data['inventory'] = 'unrelated-model'
    model.write_text(json.dumps(data))
    prompt_id = '00000000-0000-4000-8000-000000000005'
    snapshot = queue_state()
    snapshot['queue_running'][0][1] = prompt_id
    async def progress(value):
        pass
    with pytest.raises((ValueError, TimeoutError, runtime.aiohttp.ClientError)):
        asyncio.run(runtime.plan(inputs, prompt_id, tmp_path / 'jobs', lambda: snapshot, stats, lambda: False, progress))
    state = json.loads((tmp_path / 'jobs' / prompt_id / 'state.json').read_text())
    assert state['status'] == 'failed' and state['release']['process_exited']
    calls = Path(str(model) + '.calls')
    assert (int(calls.read_text()) if calls.exists() else 0) == (1 if failure in ('timeout', 'transport') else 0)


def test_one_semantic_repair_is_bounded_and_preserves_original_source(tmp_path, fake_runtime):
    inputs, model, queue_state = fake_runtime
    data = json.loads(model.read_text())
    broken = copy.deepcopy(data['outline'])
    broken['shots'][0]['excerpt'] = 'An invented action not in the story.'
    data['outlines'] = [broken, data['outline']]
    model.write_text(json.dumps(data))
    prompt_id = '00000000-0000-4000-8000-000000000006'
    snapshot = queue_state()
    snapshot['queue_running'][0][1] = prompt_id
    async def progress(value):
        pass
    result = asyncio.run(runtime.plan(inputs, prompt_id, tmp_path / 'jobs', lambda: snapshot, stats, lambda: False, progress))
    assert int(Path(str(model) + '.calls').read_text()) == 2
    assert result['document']['project']['source_text'] == inputs['story']

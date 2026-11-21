import http.server
import json
import os
from threading import Thread
from unittest.mock import MagicMock

import pytest

from studio import asset_vision as vision


@pytest.fixture
def endpoint():
    assets = []
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            assets.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.end_headers()
            record = {'role_candidate': 'prop', 'visible_evidence': 'Red mug', 'needs_review': False}
            self.wfile.write(json.dumps({'model': vision.MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(record)}}]}).encode())
    with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            yield server.server_port, assets
        finally:
            server.shutdown()
            thread.join()


def test_startup_retries_health_read_timeout(tmp_path, monkeypatch):
    process = MagicMock(pid=42)
    process.__enter__.return_value = process
    process.poll.return_value = None
    health = MagicMock(side_effect=[TimeoutError, {'status': 'ok'}])
    monkeypatch.setattr(vision, 'STUDIO_CACHE', tmp_path)
    monkeypatch.setattr(vision, 'check_capacity', lambda: None)
    monkeypatch.setattr(vision.subprocess, 'Popen', lambda *a, **kw: process)
    monkeypatch.setattr(vision, 'owns_listener', lambda pid, port: True)
    monkeypatch.setattr(vision, 'http', health)
    monkeypatch.setattr(vision.time, 'sleep', lambda _: None)
    with vision.local_server('llama-server', 'model.gguf', None, None) as (_, _, pid):
        assert pid == 42
    assert health.call_count == 2
    process.terminate.assert_called_once()


def test_listener_ownership_rejects_an_unrelated_process(endpoint):
    port, _ = endpoint
    assert vision.owns_listener(os.getpid(), port)
    assert not vision.owns_listener(os.getppid(), port)


def test_vision_sends_bytes_and_not_source_names(endpoint):
    port, requests = endpoint
    reply = vision.classify(port, 'fixture-key', 'opaque', b'test-pixels')
    assert reply == {'id': 'opaque', 'role_candidate': 'prop', 'visible_evidence': 'Red mug', 'needs_review': False}
    parts = requests[0]['messages'][1]['content']
    assert parts[-1]['image_url']['url'] == 'data:image/png;base64,dGVzdC1waXhlbHM='
    assert 'source' not in requests[0]['messages'][1]['content'][0]['text']


@pytest.mark.parametrize('document', [
    {'role_candidate': 'prop', 'visible_evidence': 'Mug', 'needs_review': False, 'path': '/tmp/evil'},
    {'role_candidate': 'unknown', 'visible_evidence': 'Unclear', 'needs_review': False},
    {'role_candidate': 'prop', 'visible_evidence': 'Mug', 'needs_review': 0},
])
def test_vision_rejects_untrusted_output(document):
    with pytest.raises(ValueError):
        vision.observation('opaque', document)


def test_isolated_command_pins_context_without_tensor_override(tmp_path):
    cmd = vision.launch_args(tmp_path/'llama-server', tmp_path/'model.gguf', tmp_path/'mmproj.gguf', 9919, tmp_path/'key')
    assert cmd[cmd.index('--host')+1] == '127.0.0.1'
    assert cmd[cmd.index('--ctx-size')+1] == '16384'
    assert '--override-tensor' not in cmd
    assert '--models-preset' not in cmd

import unittest
from unittest.mock import patch

from brain_local_model import ModelResponseError, endpoint, generate, validate_interpretation

PACKET = {'runs': [{'run_id': 'a', 'report': {'phase_seconds': {'Sampling': 2}}, 'resources': {}}]}
VALID = {'summary': 'Insufficient matched trials.', 'observations': [{'text': 'Sampling took 2 seconds.',
         'citations': [{'run_id': 'a', 'field': '/report/phase_seconds/Sampling'}]}],
         'proposed_tests': ['Repeat matched trials'], 'limitations': ['No causal inference']}


class LocalModelTests(unittest.TestCase):
    def test_only_literal_loopback_without_redirect_targets(self):
        for url in ('https://example.com', 'http://127.0.0.1.evil:1234', 'http://user@localhost:1234',
                    'http://localhost:1234/v1', 'http://localhost:1234?x=1'):
            with self.assertRaises(ValueError):
                endpoint(url)
        self.assertEqual(endpoint('http://127.0.0.1:1234/'), 'http://127.0.0.1:1234')

    def test_citations_must_exist_in_evidence(self):
        validate_interpretation(VALID, PACKET)
        bad = {**VALID, 'observations': [{'text': 'Fabricated', 'citations': [{'run_id': 'a', 'field': '/report/fake'}]}]}
        with self.assertRaises(ValueError):
            validate_interpretation(bad, PACKET)

    def test_busy_queue_blocks_inference(self):
        with patch('brain_local_model.request_json', return_value={'queue_running': [[1]], 'queue_pending': []}) as request:
            with self.assertRaisesRegex(ValueError, 'queue'):
                generate(PACKET, 'http://127.0.0.1:1234', 'test')
            self.assertEqual(request.call_count, 1)

    def test_unloaded_model_is_not_implicitly_loaded(self):
        responses = [{'queue_running': [], 'queue_pending': []}, {'data': [{'id': 'test', 'type': 'llm', 'state': 'not-loaded'}]}]
        with patch('brain_local_model.request_json', side_effect=responses) as request:
            with self.assertRaisesRegex(ValueError, 'not loaded'):
                generate(PACKET, 'http://127.0.0.1:1234', 'test')
            self.assertEqual(request.call_count, 2)
    def test_reasoning_exhaustion_is_rejected_with_diagnostics(self):
        responses = [{'queue_running': [], 'queue_pending': []},
                     {'data': [{'id': 'test', 'type': 'llm', 'state': 'loaded'}]},
                     {'queue_running': [], 'queue_pending': []},
                     {'model': 'test', 'usage': {'completion_tokens': 1024}, 'choices': [
                         {'finish_reason': 'length', 'message': {'content': '', 'reasoning_content': 'unfinished'}}]}]
        with patch('brain_local_model.request_json', side_effect=responses):
            with self.assertRaises(ModelResponseError) as caught:
                generate(PACKET, 'http://127.0.0.1:1234', 'test')
        self.assertEqual(caught.exception.details['content_characters'], [0])
        self.assertEqual(caught.exception.details['finish_reasons'], ['length'])


class LocalHTTPTests(unittest.TestCase):
    def test_actual_http_roundtrip_and_redirect_rejection(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from brain_local_model import request_json
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                calls.append(self.path)
                if self.path == '/redirect':
                    self.send_response(302)
                    self.send_header('Location', 'http://example.com/')
                    self.end_headers()
                    return
                payload = {'queue_running': [], 'queue_pending': []} if self.path == '/queue' else {
                    'data': [{'id': 'test', 'type': 'llm', 'state': 'loaded'}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append((self.path, body))
                payload = {'model': 'test', 'usage': {'total_tokens': 100}, 'choices': [{
                    'finish_reason': 'stop', 'message': {'content': json.dumps(VALID)}}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = 'http://127.0.0.1:' + str(server.server_port)
        try:
            result = generate(PACKET, origin, 'test', comfy_origin=origin)
            self.assertEqual(result['interpretation'], VALID)
            self.assertEqual(calls[:3], ['/queue', '/api/v0/models', '/queue'])
            self.assertEqual(calls[3][1]['max_tokens'], 1024)
            self.assertNotIn('tools', calls[3][1])
            with self.assertRaisesRegex(ValueError, 'redirects'):
                request_json(origin, '/redirect')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()

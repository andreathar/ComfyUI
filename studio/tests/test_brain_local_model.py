import unittest
import contextlib
import io
from unittest.mock import patch

from brain_index import encoded, decode
from brain_local_model import ModelResponseError, endpoint, generate, validate_interpretation

PACKET = {'runs': [{'run_id': 'a', 'report': {'phase_seconds': {'Sampling': 2}}, 'resources': {}}]}
VALID = {'summary': 'Insufficient matched trials.', 'observations': [{'text': 'Sampling took 2 seconds.',
         'citations': [{'run_id': 'a', 'field': '/report/phase_seconds/Sampling'}]}],
         'proposed_tests': ['Repeat matched trials'], 'limitations': ['No causal inference']}


class LocalModelTests(unittest.TestCase):
    def test_advice_must_cite_supplied_production_findings_for_each_reviewed_run(self):
        review = {'reviewer': 'assistant', 'findings': {'action': 'Head turn order correct.'}}
        packet = {'runs': [{'run_id': 'a', 'resources': {}, 'report': {
            'phase_seconds': {'Sampling': 2}, 'visual_reviews': {'f' * 64: review}}}]}
        with self.assertRaisesRegex(ValueError, 'production findings'):
            validate_interpretation(VALID, packet)
        field = '/report/visual_reviews/' + 'f' * 64 + '/findings/action'
        cited = {**VALID, 'observations': [{'text': 'Assistant reports correct turn order.',
                 'citations': [{'run_id': 'a', 'field': field}]}]}
        validate_interpretation(cited, packet)
        packet['runs'].append({**packet['runs'][0], 'run_id': 'b'})
        with self.assertRaisesRegex(ValueError, 'production findings'):
            validate_interpretation(cited, packet)


    def test_output_bound_visual_findings_reach_model_and_are_citable(self):
        review = {'reviewer': 'assistant', 'findings': {'temporal': 'Envelope lifts without contact.'},
                  'basis': 'submitted assessment; not production acceptance'}
        packet = {'runs': [{'run_id': 'a', 'resources': {}, 'report': {
            'phase_seconds': {'Sampling': 2}, 'visual_reviews': {'a' * 64: review}}}]}
        field = '/report/visual_reviews/' + 'a' * 64 + '/findings/temporal'
        interpretation = {**VALID, 'observations': [{'text': 'Reviewer observed prop instability.',
                          'citations': [{'run_id': 'a', 'field': field}]}]}
        responses = [{'queue_running': [], 'queue_pending': []}, {'status': 'ok'},
                     {'data': [{'id': 'test', 'object': 'model'}]},
                     {'queue_running': [], 'queue_pending': []},
                     {'model': 'test', 'choices': [{'finish_reason': 'stop',
                         'message': {'content': encoded(interpretation)}}]}]
        with patch('brain_local_model.request_json', side_effect=responses) as request:
            result = generate(packet, 'http://127.0.0.1:9931', 'test', runtime='llama.cpp')
        sent = decode(request.call_args_list[-1].args[2]['messages'][1]['content'])
        self.assertEqual(sent['runs'][0]['report']['visual_reviews']['a' * 64], review)
        self.assertNotIn('visual_reviews', sent['omitted_from_model_view'])
        self.assertEqual(result['interpretation'], interpretation)

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

    def test_llamacpp_uses_loaded_inventory_and_disables_thinking(self):
        from brain_index import encoded
        responses = [{'queue_running': [], 'queue_pending': []}, {'status': 'ok'},
                     {'data': [{'id': 'brain-qwen35-9b', 'object': 'model'}]},
                     {'queue_running': [], 'queue_pending': []},
                     {'model': 'brain-qwen35-9b', 'choices': [{'finish_reason': 'stop',
                         'message': {'content': encoded(VALID)}}]}]
        packet = {'runs': [*PACKET['runs'], {'run_id': 'b', 'report': {'other': 3}, 'resources': {}}]}
        with patch('brain_local_model.request_json', side_effect=responses) as request:
            result = generate(packet, 'http://127.0.0.1:9931', 'brain-qwen35-9b', runtime='llama.cpp')
        self.assertEqual(result['runtime'], 'llama.cpp')
        self.assertEqual(result['interpretation'], VALID)
        self.assertEqual([c.args[1] for c in request.call_args_list],
                         ['/queue', '/health', '/v1/models', '/queue', '/v1/chat/completions'])
        call = request.call_args_list[-1]
        self.assertEqual(call.args[2]['chat_template_kwargs'], {'enable_thinking': False})
        citations = call.args[2]['response_format']['json_schema']['schema']['properties']['observations']['items']['properties']['citations']['items']
        branch = citations['anyOf'][0]['properties']
        self.assertEqual(branch['run_id']['enum'], ['a'])
        self.assertIn('/report/phase_seconds/Sampling', branch['field']['enum'])
        self.assertNotIn('/report/other', branch['field']['enum'])
        other = citations['anyOf'][1]['properties']
        self.assertEqual(other['run_id']['enum'], ['b'])
        self.assertIn('/report/other', other['field']['enum'])
        self.assertEqual(call.kwargs['timeout'], 600)
        self.assertNotIn('tools', call.args[2])

    def test_llamacpp_rejects_wrong_loaded_model_before_inference(self):
        responses = [{'queue_running': [], 'queue_pending': []}, {'status': 'ok'},
                     {'data': [{'id': 'other'}]}]
        with patch('brain_local_model.request_json', side_effect=responses) as request:
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                generate(PACKET, 'http://127.0.0.1:9931', 'brain-qwen35-9b', runtime='llama.cpp')
        self.assertEqual(request.call_count, 3)

    def test_llamacpp_loading_health_blocks_inference(self):
        responses = [{'queue_running': [], 'queue_pending': []}, {'status': 'loading model'}]
        with patch('brain_local_model.request_json', side_effect=responses) as request:
            with self.assertRaisesRegex(ValueError, 'ready'):
                generate(PACKET, 'http://127.0.0.1:9931', 'brain-qwen35-9b', runtime='llama.cpp')
        self.assertEqual(request.call_count, 2)

    def test_cli_rejects_credentials_without_recording_or_echoing_them(self):
        from brain_analysis import main
        output = io.StringIO()
        argv = ['brain_analysis', 'report', 'unused', '--model', 'test', '--endpoint', 'http://user:private@localhost:1234']
        with patch('sys.argv', argv), contextlib.redirect_stderr(output), patch('brain_analysis.AnalysisIndex') as index:
            with self.assertRaises(SystemExit):
                main()
        self.assertNotIn('private', output.getvalue())
        index.assert_not_called()


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
                if self.path == '/queue':
                    payload = {'queue_running': [], 'queue_pending': []}
                elif self.path == '/health':
                    payload = {'status': 'ok'}
                else:
                    payload = {'data': [{'id': 'test', 'type': 'llm', 'state': 'loaded'}]}
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
            for runtime, paths in (('LM Studio', ['/queue', '/api/v0/models', '/queue']),
                                   ('llama.cpp', ['/queue', '/health', '/v1/models', '/queue'])):
                with self.subTest(runtime=runtime):
                    calls.clear()
                    result = generate(PACKET, origin, 'test', comfy_origin=origin, runtime=runtime)
                    self.assertEqual(result['interpretation'], VALID)
                    self.assertEqual(calls[:-1], paths)
                    self.assertEqual(calls[-1][1]['max_tokens'], 2048 if runtime == 'llama.cpp' else 1024)
                    self.assertNotIn('tools', calls[-1][1])
            with self.assertRaisesRegex(ValueError, 'redirects'):
                request_json(origin, '/redirect')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()

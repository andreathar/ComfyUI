import json
import unittest

from brain_comparison import comparison, chart, execution_evidence
from brain_index import history_fingerprint


class ComparisonTests(unittest.TestCase):
    def history(self, rid='a'):
        graph = {'1': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'private prompt text'}}}
        return {rid: {'prompt': [0, rid, graph, {}, ['1']], 'status': {
            'completed': True, 'status_str': 'success', 'messages': [
                ['execution_start', {'prompt_id': rid, 'timestamp': 1000}],
                ['execution_success', {'prompt_id': rid, 'timestamp': 11000}]]}}}

    def report(self, history):
        return {'status': 'succeeded', 'generation_fingerprint': history_fingerprint(*history['a']['prompt'][2:]),
                'admitted_wall_seconds': 100, 'phase_seconds': {'Sampling': None}}

    def test_native_timing_requires_matching_generation_and_terminal_pair(self):
        history = self.history()
        report = self.report(history)
        record = history['a']
        evidence = execution_evidence(record, 'a', report)
        assert evidence is not None
        self.assertEqual(evidence['succeeded_ms'], 11000)
        self.assertIsNone(execution_evidence(record, 'a', {**report, 'status': 'failed'}))
        record['prompt'][2]['1']['inputs']['text'] = 'different generation'
        self.assertIsNone(execution_evidence(record, 'a', report))
        record = self.history()['a']
        record['status']['messages'].append(record['status']['messages'][0])
        self.assertIsNone(execution_evidence(record, 'a', report))

    def test_comparison_retains_only_selected_timestamps_and_reports_missing(self):
        history = {**self.history(), **self.history('unselected')}
        packet = {'runs': [{'run_id': r, 'resources': {}, 'report': self.report(history)} for r in ['a', 'b']], 'differences': []}
        data = comparison(packet, 'Reduce draft time', history)
        self.assertEqual(data['rows'][0]['execution_seconds'], 10)
        self.assertEqual(set(data['native_timing']), {'a'})
        self.assertNotIn('private prompt text', json.dumps(data))
        self.assertNotIn('unselected', json.dumps(data))
        self.assertIsNone(data['rows'][1]['execution_difference_percent'])
        self.assertIsNone(data['rows'][0]['sampling_seconds'])
        self.assertIn('Unavailable', chart(data))
        with self.assertRaises(ValueError):
            comparison(packet, ' ', {})

    def test_recorded_outcome_stays_visible_when_native_success_is_unverified(self):
        history = self.history()
        succeeded = self.report(history)
        failed = {**succeeded, 'status': 'failed', 'peaks': {'cuda:0.nvml_used': 2**30}}
        packet = {'runs': [
            {'run_id': 'a', 'resources': {}, 'report': succeeded},
            {'run_id': 'b', 'resources': {}, 'report': failed},
            {'run_id': 'c', 'resources': {}, 'report': {**succeeded, 'status': 'unknown'}},
        ], 'differences': []}
        data = comparison(packet, 'Compare resource use', history)
        rows = data['rows']
        self.assertEqual([row['brain_status'] for row in rows], ['succeeded', 'failed', 'unknown'])
        self.assertEqual(rows[1]['vram_peak_gib'], 1)
        self.assertIsNone(rows[1]['execution_seconds'])
        self.assertIsNone(rows[2]['execution_seconds'])
        self.assertIn('(failed)', chart(data))

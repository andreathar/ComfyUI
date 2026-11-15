import json
import unittest
from unittest.mock import patch

import test_brain_analysis
from brain_index import AnalysisIndex, build_index
from brain_reports import evidence_packet, save_report, create_experiment, record_decision


class ReportTests(unittest.TestCase):
    def test_incomplete_phase_stays_null_through_sqlite_and_packet(self):
        path = self.source / self.rid / 'run.json'
        run = json.loads(path.read_text())
        run.update(phase_seconds={'Sampling': .6472}, intervals=[
            {'phase': 'Sampling', 'node': 's', 'display_node': 's', 'session': 'a',
             'start': 1, 'end': None, 'incomplete': True},
            {'phase': 'Sampling', 'node': 's', 'display_node': 's', 'session': 'a',
             'start': 10, 'end': 10.6472, 'incomplete': False}])
        path.write_text(json.dumps(run))
        before = path.read_bytes()
        build_index(self.source, self.analysis)
        with AnalysisIndex(self.analysis) as index:
            packet = evidence_packet(index, [self.rid])
        report = packet['runs'][0]['report']
        self.assertIsNone(report['phase_seconds']['Sampling'])
        self.assertEqual(report['phase_timing_coverage']['Sampling'], 'incomplete')
        self.assertEqual(path.read_bytes(), before)


    setUp = test_brain_analysis.IndexTests.setUp
    add_run = test_brain_analysis.IndexTests.add_run

    def test_packet_reports_differences_without_ranking(self):
        candidate = self.add_run()
        path = self.source / candidate / 'run.json'
        run = json.loads(path.read_text())
        run['captured']['resolved_inputs']['1']['seed'] = 7
        path.write_text(json.dumps(run))
        build_index(self.source, self.analysis)
        with AnalysisIndex(self.analysis) as index:
            packet = evidence_packet(index, [self.rid, candidate])
        self.assertFalse(packet['benchmark_qualified'])
        difference = next(d for d in packet['differences'] if d['field'].endswith('/seed'))
        self.assertEqual(difference['baseline'], '18446744073709551615')
        self.assertEqual(difference['candidate'], 7)
        report = save_report(self.analysis, packet)
        self.assertTrue((report / 'report.md').is_file())
        experiment = create_experiment(self.analysis, packet, 'Test seed', [difference['field']], {'cache': 'unknown'})
        decision = record_decision(self.analysis, experiment.name, 'test_further', 'athar', 'Need matched repeated trials')
        saved = json.loads(decision.read_text())
        self.assertEqual(saved['experiment_id'], experiment.name)
        self.assertEqual(saved['decision'], 'test_further')
        self.assertEqual(len(list(experiment.glob('decision-*.json'))), 1)

    def test_packet_is_bounded(self):
        build_index(self.source, self.analysis)
        with AnalysisIndex(self.analysis) as index:
            with patch('brain_reports.MAX_PACKET_BYTES', 100):
                with self.assertRaisesRegex(ValueError, 'packet exceeds'):
                    evidence_packet(index, [self.rid])

    def test_unknown_decision_cannot_be_recorded(self):
        with self.assertRaises(ValueError):
            record_decision(self.analysis, '../bad', 'adopt', 'athar', 'test')


if __name__ == '__main__':
    unittest.main()

class PublicationTests(unittest.TestCase):
    setUp = ReportTests.setUp
    add_run = ReportTests.add_run
    def test_irrelevant_skipped_runs_do_not_overflow_selected_packet(self):
        build_index(self.source, self.analysis)
        with AnalysisIndex(self.analysis) as index:
            index.metadata['skipped'] = [{'run_id': str(i), 'reason': 'x' * 300} for i in range(1000)]
            packet = evidence_packet(index, [self.rid])
        self.assertEqual(packet['generation']['skipped_count'], 1000)
        self.assertNotIn('skipped', packet['generation'])

    def test_failed_decision_write_leaves_no_published_file(self):
        from brain_reports import save_bundle
        from brain_index import sha
        packet = {'runs': [], 'test': True}
        folder = save_bundle(self.analysis, 'experiments', {
            'experiment.json': {'packet_sha256': sha(packet)}, 'packet.json': packet})
        def partial(path, value):
            path.write_text('{partial')
            raise OSError('disk full')
        with patch('brain_reports.write_json', side_effect=partial):
            with self.assertRaises(OSError):
                record_decision(self.analysis, folder.name, 'inconclusive', 'athar', 'test')
        self.assertEqual(list(folder.glob('decision-*.json')), [])
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['experiment.json', 'packet.json'])

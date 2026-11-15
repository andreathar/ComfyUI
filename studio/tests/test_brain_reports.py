import json
import unittest
from unittest.mock import patch

import test_brain_analysis
from brain_index import AnalysisIndex, build_index
from brain_reports import evidence_packet, save_report, create_experiment, record_decision


class ReportTests(unittest.TestCase):
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

import json
import fcntl
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from brain_index import AnalysisIndex, build_index


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'runs'
        self.source.mkdir()
        self.analysis = self.root / 'analysis'
        self.rid = self.add_run()

    def add_run(self, status='succeeded'):
        rid = str(uuid4())
        folder = self.source / rid
        folder.mkdir()
        (folder / 'run.json').write_text(json.dumps({
            'prompt_id': rid, 'status': status, 'created': 1, 'ended': 4,
            'captured': {'resolved_inputs': {'1': {'seed': 18446744073709551615}}},
            'sample_count': 1,
        }))
        (folder / 'events.jsonl').write_text('{"type":"execution_start","session":"a"}\n')
        (folder / 'samples.jsonl').write_text('{"received":2,"devices":[{"type":"cuda","index":0,"temperature":61}]}\n')
        return rid

    def test_snapshot_exact_seed_nulls_and_readonly(self):
        build_index(self.source, self.analysis)
        with AnalysisIndex(self.analysis) as index:
            row = index.list_runs()[0]
            self.assertEqual(row['run_id'], self.rid)
            report = index.evidence([self.rid])[0]['report']
            self.assertEqual(report['resolved_primitive_inputs']['1']['seed'], '18446744073709551615')
            self.assertEqual(index.resources(self.rid)['gpu_temperature_max_c'], 61)
            self.assertIsNone(index.resources(self.rid)['process_rss_max_bytes'])
            with self.assertRaises(sqlite3.OperationalError):
                index.connection.execute('DELETE FROM runs')

    def test_active_and_malformed_are_visible_diagnostics(self):
        active = self.add_run('running')
        bad = self.add_run()
        (self.source / bad / 'samples.jsonl').write_text('{broken\n')
        result = build_index(self.source, self.analysis)
        self.assertEqual(result['run_count'], 1)
        self.assertEqual({d['run_id'] for d in result['skipped']}, {active, bad})

    def test_stale_record_cannot_supply_fresh_packet(self):
        build_index(self.source, self.analysis)
        (self.source / self.rid / 'samples.jsonl').write_text('')
        with AnalysisIndex(self.analysis) as index:
            with self.assertRaisesRegex(ValueError, 'changed'):
                index.evidence([self.rid])

    def test_failed_build_preserves_pointer_and_reader_generation(self):
        first = build_index(self.source, self.analysis)
        with AnalysisIndex(self.analysis) as reader:
            second = build_index(self.source, self.analysis)
            self.assertNotEqual(first['generation'], second['generation'])
            self.assertEqual(reader.metadata['generation'], first['generation'])
            original = (self.analysis / 'current.json').read_bytes()
            with patch('brain_index.import_run', side_effect=RuntimeError('failure')):
                with self.assertRaises(RuntimeError):
                    build_index(self.source, self.analysis)
            self.assertEqual((self.analysis / 'current.json').read_bytes(), original)

    def test_symlink_and_bad_ids_rejected(self):
        (self.source / str(uuid4())).symlink_to(self.source / self.rid)
        result = build_index(self.source, self.analysis)
        self.assertEqual(len(result['skipped']), 1)
        with AnalysisIndex(self.analysis) as index:
            with self.assertRaises(ValueError):
                index.evidence(['../outside'])
            with self.assertRaises(ValueError):
                index.list_runs(limit=1000)

    def test_mutation_before_publication_keeps_previous_generation(self):
        build_index(self.source, self.analysis)
        original = (self.analysis / 'current.json').read_bytes()
        from brain_index import import_run
        def mutate(*args):
            result = import_run(*args)
            (self.source / self.rid / 'events.jsonl').write_text('')
            return result
        with patch('brain_index.import_run', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed'):
                build_index(self.source, self.analysis)
        self.assertEqual((self.analysis / 'current.json').read_bytes(), original)

    def test_second_writer_cannot_publish(self):
        build_index(self.source, self.analysis)
        original = (self.analysis / 'current.json').read_bytes()
        with (self.analysis / 'build.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                build_index(self.source, self.analysis)
        self.assertEqual((self.analysis / 'current.json').read_bytes(), original)

    def test_analyzer_change_requires_rebuild(self):
        build_index(self.source, self.analysis)
        with AnalysisIndex(self.analysis) as index:
            with patch('brain_index.analyzer_identity', return_value={'changed': 'code'}):
                with self.assertRaisesRegex(ValueError, 'Analyzer changed'):
                    index.evidence([self.rid])


if __name__ == '__main__':
    unittest.main()

class MalformedScalarTests(unittest.TestCase):
    setUp = IndexTests.setUp
    add_run = IndexTests.add_run
    def test_malformed_label_skips_only_its_run(self):
        bad = self.add_run()
        path = self.source / bad / 'run.json'
        value = json.loads(path.read_text())
        value['label'] = {'invalid': 'scalar'}
        path.write_text(json.dumps(value))
        result = build_index(self.source, self.analysis)
        self.assertEqual(result['run_count'], 1)
        self.assertEqual(result['skipped'][0]['run_id'], bad)

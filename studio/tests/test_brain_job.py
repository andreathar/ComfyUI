import json
import unittest
from uuid import uuid4
from unittest.mock import patch

import brain_local_model
import test_brain_analysis


class QueueOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.job, self.run = str(uuid4()), str(uuid4())
        self.queue = {'queue_running': [[0, self.job, {
            '1': {'class_type': 'WorkflowBrainAnalysis', 'inputs': {'source_run_id': self.run}}
        }, {}, ['1']]], 'queue_pending': [[1, str(uuid4()), {}, {}, []]]}

    def check(self):
        brain_local_model.check_queue(self.queue, (self.job, self.run))

    def test_owned_single_node_job_allows_pending_render(self):
        self.check()

    def test_mixed_graph_wrong_job_and_wrong_run_rejected(self):
        for key in ('mixed', 'job', 'run'):
            with self.subTest(key=key):
                original = json.loads(json.dumps(self.queue))
                if key == 'mixed':
                    self.queue['queue_running'][0][2]['2'] = {'class_type': 'KSampler', 'inputs': {}}
                elif key == 'job':
                    self.queue['queue_running'][0][1] = str(uuid4())
                else:
                    self.queue['queue_running'][0][2]['1']['inputs']['source_run_id'] = str(uuid4())
                with self.assertRaises(ValueError):
                    self.check()
                self.queue = original

    def test_manual_call_still_requires_empty_queue(self):
        with self.assertRaises(ValueError):
            brain_local_model.check_queue(self.queue)

class JobTests(unittest.TestCase):
    setUp = test_brain_analysis.IndexTests.setUp
    add_run = test_brain_analysis.IndexTests.add_run
    def test_cached_run_gets_deterministic_report_without_model(self):
        import brain_job
        with patch('brain_job.generate', side_effect=AssertionError('No inference for cached runs')):
            result = brain_job.analyze(self.rid, str(uuid4()), self.source, self.analysis)
        report = json.loads((self.analysis / 'reports' / result['report_id'] / 'report.json').read_text())
        self.assertIsNone(report['model'])

    def test_unsettled_run_cannot_be_analyzed(self):
        import brain_job
        path = self.source / self.rid / 'run.json'
        run = json.loads(path.read_text())
        run['evidence_status'] = 'collecting'
        path.write_text(json.dumps(run))
        with self.assertRaisesRegex(ValueError, 'settled'):
            brain_job.analyze(self.rid, str(uuid4()), self.source, self.analysis)

class ParentLifetimeTests(unittest.TestCase):
    def test_worker_rejects_changed_parent_before_work(self):
        import brain_job
        with self.assertRaisesRegex(RuntimeError, 'parent'):
            brain_job.bind_parent(0)

    def test_owned_worker_stops_when_parent_exits(self):
        import os
        from pathlib import Path
        import subprocess
        import sys
        import time
        worker = 'import os,time; from brain_job import bind_parent; bind_parent(int(os.environ["BRAIN_PARENT"])); print("ready",flush=True); time.sleep(30)'
        parent = ('import os,subprocess,sys,time; '
                  'env=dict(os.environ,BRAIN_PARENT=str(os.getpid())); '
                  f'p=subprocess.Popen([sys.executable,"-c",{worker!r}],env=env,stdout=subprocess.PIPE,text=True); '
                  'assert p.stdout.readline().strip()=="ready"; print(p.pid,flush=True); time.sleep(30)')
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        p = subprocess.Popen([sys.executable, '-c', parent], env=env, stdout=subprocess.PIPE, text=True)
        child_id = int(p.stdout.readline())
        try:
            p.terminate()
            p.wait(timeout=5)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                status = Path(f'/proc/{child_id}/stat')
                if not status.exists() or status.read_text().split()[2] == 'Z':
                    break
                time.sleep(.05)
            else:
                self.fail('Owned worker survived parent exit')
        finally:
            p.stdout.close()
            if p.poll() is None:
                p.kill()
                p.wait()

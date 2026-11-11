import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film
import h3_graph


class TakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.compiled = {'shot_id': 'MSG_S001_SH01', 'fingerprint': 'f' * 64, 'prompt_text': 'Hello',
                         'builder_state': {}, 'stack_state': {}, 'media_state': [], 'recipe': dict(film.h3.DIAGNOSTIC), 'frames': 56, 'shot': {'duration_s': 2}, 'seed': 0}
        self.take = film.prepare(self.root, self.compiled, 'tk001')
        self.models = {}
        for role, name in film.h3.DIAGNOSTIC['models'].items():
            relative = 'models/' + ('vae' if role.endswith('_vae') else role) + '/' + name
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture weight')
            stat = path.stat()
            self.models[role] = {'path': relative, 'size_bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'sha256': film.h3.file_hash(path)}
        self.graph = h3_graph.compile_graph(self.compiled, 'The_Message/shots/MSG_S001_SH01/tk001/video')
        film.preflight_take(self.take, self.graph,
                            {'running': 0, 'pending': 0, 'free_ram_bytes': 20 * 2**30, 'free_vram_bytes': 2 * 2**30,
                             'conflicting_export': False, 'observed_at': time.time()},
                            self.root, self.models, {n['class_type'] for n in self.graph.values()})

    def test_prepare_does_not_overwrite_or_auto_approve(self):
        with self.assertRaises(FileExistsError):
            film.prepare(self.root, self.compiled, 'tk001')
        self.assertEqual(film.read_take(self.take)['status'], 'prepared')
        self.assertEqual((self.take / 'prompt.txt').read_text(), 'Hello')

    def test_ambiguous_submission_cannot_queue_again(self):
        film.mark_submitting(self.take)
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            film.mark_submitting(self.take)
        film.bind_prompt(self.take, 'prompt-1')
        film.bind_prompt(self.take, 'prompt-1')
        with self.assertRaises(ValueError):
            film.bind_prompt(self.take, 'prompt-2')

    def test_partial_history_does_not_finish_take(self):
        film.mark_submitting(self.take)
        film.bind_prompt(self.take, 'prompt-1')
        history = {'prompt-1': {'status': {'completed': True, 'status_str': 'success'}, 'outputs': {'preview': {'images': [{'filename': 'preview.png', 'type': 'temp'}]}}, 'prompt': []}}
        with self.assertRaisesRegex(ValueError, 'saved video'):
            film.reconcile(self.take, history, self.root)
        self.assertEqual(film.read_take(self.take)['status'], 'queued')

    def test_approval_requires_technical_pass(self):
        with self.assertRaisesRegex(ValueError, 'technical'):
            film.review(self.take, True, 'user', 'looks good')

    def test_expired_preflight_blocks_submission(self):
        evidence = film.read_json(self.take / 'preflight.json')
        evidence['checked_at'] -= 121
        film.write_json(self.take / 'preflight.json', evidence)
        with self.assertRaisesRegex(ValueError, 'expired'):
            film.mark_submitting(self.take)

    def test_changed_model_after_preflight_blocks_submission(self):
        model = next(iter(self.models.values()))
        (self.root / model['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'stamp changed'):
            film.mark_submitting(self.take)

    def test_old_resource_observation_blocks_submission(self):
        evidence = film.read_json(self.take / 'preflight.json')
        evidence['resources']['snapshot']['observed_at'] -= 121
        film.write_json(self.take / 'preflight.json', evidence)
        with self.assertRaisesRegex(ValueError, 'resource observation'):
            film.mark_submitting(self.take)

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            film.prepare(self.root, self.compiled, '../escape')

    def test_another_movie_uses_its_own_output_namespace(self):
        take = film.prepare(self.root, self.compiled, 'tk002', output_namespace='Second_Film')
        edits = film.read_json(take / 'panel-edits.json')
        prefix = next(e['value'] for e in edits if e['widget'] == 'filename_prefix')
        self.assertEqual(prefix, 'Second_Film/shots/MSG_S001_SH01/tk002/video')
        graph = h3_graph.compile_graph(self.compiled, prefix)
        evidence = film.preflight_take(take, graph,
            {'running': 0, 'pending': 0, 'free_ram_bytes': 20 * 2**30, 'free_vram_bytes': 2 * 2**30,
             'conflicting_export': False, 'observed_at': time.time()},
            self.root, self.models, {n['class_type'] for n in graph.values()})
        self.assertTrue(evidence['files']['ready'])
        with self.assertRaises(ValueError):
            film.prepare(self.root, self.compiled, 'tk003', output_namespace='../escape')
        self.assertFalse((self.root / self.compiled['shot_id'] / 'tk003').exists())

    def test_unreviewed_take_excluded_from_assembly(self):
        with self.assertRaisesRegex(ValueError, 'approved'):
            film.assembly_inputs([{'take': str(self.take), 'in_frame': 0, 'out_frame': 56}])

    def test_changed_execution_seed_is_rejected(self):
        graph = h3_graph.compile_graph(self.compiled, 'test/video')
        graph['15']['inputs']['noise_seed'] = 999
        with self.assertRaisesRegex(ValueError, 'nodes: 15'):
            h3_graph.verify(graph, self.compiled, 'test/video')

    def test_real_decode_recovery_review_and_trimmed_assembly(self):
        self.take = film.prepare(self.root, self.compiled, 'tk002', output_namespace='Second_Film')
        prefix = 'Second_Film/shots/MSG_S001_SH01/tk002/video'
        graph = h3_graph.compile_graph(self.compiled, prefix)
        film.preflight_take(self.take, graph,
            {'running': 0, 'pending': 0, 'free_ram_bytes': 20 * 2**30, 'free_vram_bytes': 2 * 2**30,
             'conflicting_export': False, 'observed_at': time.time()},
            self.root, self.models, {n['class_type'] for n in graph.values()})
        video = self.root / (prefix + '_00001_.mp4')
        video.parent.mkdir(parents=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'color=c=red:s=608x352:r=24',
                        '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-frames:v', '56', '-t', str(56/24),
                        '-c:v', 'libx264', '-threads', '1', '-c:a', 'aac', str(video)], check=True)
        history = {'prompt-1': {'prompt': [0, 'prompt-1', graph], 'status': {'completed': True, 'status_str': 'success'},
                               'outputs': {'20': {'images': [{'type': 'output', 'subfolder': str(video.parent.relative_to(self.root)), 'filename': video.name}]}}}}
        film.mark_submitting(self.take)
        film.bind_prompt(self.take, 'prompt-1')
        result = film.reconcile(self.take, history, self.root)
        self.assertEqual(result['status'], 'review_pending')
        with self.assertRaisesRegex(ValueError, 'approved'):
            film.assembly_inputs([{'take': str(self.take), 'in_frame': 0, 'out_frame': 28}])
        draft_edit = [{'take': str(self.take), 'in_frame': 0, 'out_frame': 56}]
        run = film.plan_run([self.take], self.root / 'run.json', self.root / 'draft.mp4')
        self.assertEqual(film.run_status(run)['action'], 'assemble_draft')
        draft = film.assemble(draft_edit, self.root / 'draft.mp4', draft=True)
        self.assertEqual(film.probe_video(draft)['frames'], 56)
        self.assertEqual(film.read_take(self.take)['status'], 'review_pending')
        self.assertEqual(film.read_json(draft.with_suffix('.receipt.json'))['purpose'], 'draft')
        self.assertEqual(film.run_status(run)['action'], 'draft_complete')
        stamp = draft.stat().st_mtime_ns
        self.assertEqual(film.main(['assemble-run', str(run)]), 0)
        self.assertEqual(draft.stat().st_mtime_ns, stamp)
        receipt_path = draft.with_suffix('.receipt.json')
        receipt = film.read_json(receipt_path)
        changed = {**receipt, 'inputs': []}
        film.write_json(receipt_path, changed)
        with self.assertRaisesRegex(ValueError, 'draft receipt'):
            film.run_status(run)
        receipt_path.unlink()
        self.assertEqual(film.run_status(run)['action'], 'blocked')
        film.write_json(receipt_path, receipt)
        original = draft.read_bytes()
        draft.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'draft hash'):
            film.run_status(run)
        draft.write_bytes(original)
        film.review(self.take, True, 'test reviewer', 'synthetic fixture only')
        film.reconcile(self.take, history, self.root)
        self.assertEqual(film.read_take(self.take)['status'], 'approved')
        edit = [{'take': str(self.take), 'in_frame': 0, 'out_frame': 28}, {'take': str(self.take), 'in_frame': 28, 'out_frame': 56}]
        output = film.assemble(edit, self.root / 'cut.mp4')
        self.assertEqual(film.probe_video(output)['frames'], 56)
        with self.assertRaises(FileExistsError):
            film.assemble(edit, output)
        video.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash changed'):
            film.assembly_inputs(edit)

    def test_run_resumes_without_resubmitting_uncertain_job(self):
        run = film.plan_run([self.take], self.root / 'run.json', self.root / 'draft.mp4')
        self.assertEqual(film.run_status(run)['action'], 'render')
        film.mark_submitting(self.take)
        self.assertEqual(film.run_status(run)['action'], 'reconcile_submission')
        film.bind_prompt(self.take, 'job-1')
        status = film.run_status(run)
        self.assertEqual(status['action'], 'wait')
        self.assertEqual(status['prompt_id'], 'job-1')
        with self.assertRaises(FileExistsError):
            film.plan_run([self.take], self.root / 'run.json', self.root / 'draft.mp4')


if __name__ == '__main__':
    unittest.main()

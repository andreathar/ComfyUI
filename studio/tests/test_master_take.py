import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import master_take as takes
from master_studio_package import resolve_shot_package


def graph_fixture():
    return {
        '27': {'class_type': 'DynamicScriptNode', 'inputs': {'code': 'old'}},
        '21': {'class_type': 'MiniMaxH3MediaLoader', 'inputs': {'media_state': ['27', 3]}},
        '23': {'class_type': 'MiniMaxH3RefModStack', 'inputs': {'stack_state': ['27', 4]}},
        '22': {'class_type': 'MiniMaxH3PromptBuilder', 'inputs': {'prompt_text': ['27', 1], 'builder_state': ['27', 2], 'references': ['21', 0], 'mods': ['23', 0]}},
        'encoder': {'class_type': 'MiniMaxH3FantasticRefModTextEncode', 'inputs': {'prompt': ['22', 0], 'references': ['22', 19], 'mods': ['22', 20]}},
        'seed': {'class_type': 'FantasticSeeds', 'inputs': {'seed': ['27', 5], 'mode': 'fixed'}},
        'noise': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': ['seed', 0]}},
        'sampler': {'class_type': 'SamplerCustomAdvanced', 'inputs': {'noise': ['noise', 0], 'guider': ['encoder', 0]}},
        '61': {'class_type': 'H3ProjectSave', 'inputs': {'latent': ['sampler', 0]}},
        '64': {'class_type': 'SaveVideo', 'inputs': {'filename_prefix': ['62', 0], 'video': ['sampler', 0]}},
        '44': {'class_type': 'WorkflowMonitorBrain', 'inputs': {}},
    }

class MasterTakeTests(unittest.TestCase):
    def test_seed_bypass_is_rejected_before_allocating_a_take(self):
        package = resolve_shot_package('MSG_S001_SH05')
        package['seed'] = 11005
        for seed in (123, 11005, ['27', 4], ['other_seed', 0]):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as tmp:
                graph = graph_fixture()
                graph['noise']['inputs']['noise_seed'] = seed
                graph['other_seed'] = {'class_type': 'PrimitiveInt', 'inputs': {'value': 123}}
                # A correctly connected but unused noise node proves nothing.
                graph['unused_noise'] = {'class_type': 'RandomNoise', 'inputs': {'noise_seed': ['27', 5]}}
                with self.assertRaisesRegex(ValueError, 'seed'):
                    takes.prepare(tmp, graph, {}, package)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_generation_must_consume_the_verified_noise_output(self):
        package = resolve_shot_package('MSG_S001_SH05')
        for link in (['noise', 1], ['other_noise', 0]):
            with self.subTest(link=link), tempfile.TemporaryDirectory() as tmp:
                graph = graph_fixture()
                graph['sampler']['inputs']['noise'] = link
                graph['other_noise'] = {'class_type': 'DisableNoise', 'inputs': {}}
                with self.assertRaisesRegex(ValueError, 'noise'):
                    takes.prepare(tmp, graph, {}, package)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_seed_wrapper_cannot_substitute_a_different_value(self):
        package = resolve_shot_package('MSG_S001_SH05')
        with tempfile.TemporaryDirectory() as tmp:
            graph = graph_fixture()
            graph['seed']['inputs']['seed'] = 123
            with self.assertRaisesRegex(ValueError, 'seed'):
                takes.prepare(tmp, graph, {}, package)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_direct_resolver_seed_is_valid_and_unused_noise_is_irrelevant(self):
        package = resolve_shot_package('MSG_S001_SH05')
        with tempfile.TemporaryDirectory() as tmp:
            graph = graph_fixture()
            graph['noise']['inputs']['noise_seed'] = ['27', 5]
            graph['unused_noise'] = {'class_type': 'RandomNoise', 'inputs': {'noise_seed': 123}}
            take = takes.prepare(tmp, graph, {}, package)
            self.assertEqual(takes.read_json(take / 'prompt.json')['noise']['inputs']['noise_seed'], ['27', 5])

    def test_output_without_generation_cannot_pass_via_encoder_dependency(self):
        package = resolve_shot_package('MSG_S001_SH05')
        for node, field in [('61', 'latent'), ('61', 'images'), ('64', 'video')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                graph = graph_fixture()
                graph[node]['inputs'][field] = ['encoder', 0]
                with self.assertRaisesRegex(ValueError, 'sampler'):
                    takes.prepare(tmp, graph, {}, package)
                self.assertEqual(list(Path(tmp).iterdir()), [])


    def test_filename_dependency_cannot_substitute_for_generated_video(self):
        package = resolve_shot_package('MSG_S001_SH05')
        graph = graph_fixture()
        graph['62'] = {'class_type': 'PreviewAny', 'inputs': {'source': ['encoder', 0]}}
        graph['other_video'] = {'class_type': 'VideoFromFile', 'inputs': {'file': 'unrelated.mp4'}}
        graph['64']['inputs']['video'] = ['other_video', 0]
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, '64.video'):
            takes.prepare(tmp, graph, {}, package)

    def test_explicit_project_keeps_take_and_output_outside_the_message(self):
        package = resolve_shot_package('MSG_S001_SH05')
        package.update(shot_id='FARM_S001_SH01', project='FARM', output_project='Farm_Reference_Lab')
        with tempfile.TemporaryDirectory() as tmp:
            take = takes.prepare(tmp, graph_fixture(), {}, package)
            state = takes.read_json(take / 'take.json')
            self.assertEqual(state['project'], 'FARM')
            self.assertEqual(state['scene_id'], 'FARM_S001')
            self.assertEqual(state['output_prefix'], 'Farm_Reference_Lab/shots/FARM_S001_SH01/tk001/video')
            for field in ('project', 'output_project'):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    takes.prepare(tmp, graph_fixture(), {}, {**package, field: '../escape'})

    def test_preparation_freezes_package_and_allocates_distinct_take_without_mutating_canvas(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = graph_fixture()
            pkg = {'shot_id': 'MSG_S001_SH05', 'seed': 11005, 'transition': 'cut', 'prompt_name': 'Shot',
                   'prompt_text': 'Turn toward counter', 'builder_state': {}, 'media_state': [], 'stack_state': {'picks': []}}
            a = takes.prepare(root, graph, {}, pkg)
            b = takes.prepare(root, graph, {}, pkg)
            self.assertNotEqual(a.name, b.name)
            frozen = json.loads((a/'prompt.json').read_text())
            env = {'inputs': ['MSG_S001_SH05'], 'outputs': [None]*7}
            exec(frozen['27']['inputs']['code'], env)
            self.assertEqual(env['outputs'][0], 'Turn toward counter')
            self.assertEqual(json.loads(env['outputs'][6])['take_id'], a.name)
            env['inputs'] = ['MSG_S001_SH04']
            with self.assertRaises(ValueError):
                exec(frozen['27']['inputs']['code'], env)
            self.assertEqual(graph['64']['inputs']['filename_prefix'], ['62', 0])
            self.assertIn(a.name, frozen['64']['inputs']['filename_prefix'])
            self.assertTrue((a/'package.json').exists())

    def test_submission_is_single_use_and_modified_inputs_cannot_be_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Prepared record minimal fixture, hashes are independently computed.
            prompt = b'{}'
            (root/'prompt.json').write_bytes(prompt)
            (root/'take.json').write_text(json.dumps({'status': 'prepared', 'prompt_sha256': hashlib.sha256(prompt).hexdigest()}))
            takes.mark_submitting(root)
            with self.assertRaises(ValueError): takes.mark_submitting(root)
            takes.bind(root, 'uuid-1')
            with self.assertRaises(ValueError): takes.bind(root, 'uuid-2')
            self.assertEqual(json.loads((root/'take.json').read_text())['prompt_id'], 'uuid-1')

    def test_review_does_not_approve_without_verified_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'take.json').write_text('{"status":"submitted"}')
            with self.assertRaises(ValueError): takes.review(root, {'action': 'pass'}, 'Looks good', True)

    def test_review_rejects_changed_frozen_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'prompt.json').write_text('{}')
            video = root/'video.mp4'
            video.write_bytes(b'verified video')
            takes.write_json(root/'take.json', {'status': 'review_pending',
                'prompt_sha256': takes.file_hash(root/'prompt.json'),
                'output': {'path': str(video), 'sha256': takes.file_hash(video)}})
            (root/'prompt.json').write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'inputs changed'):
                takes.review(root, {'action': 'pass'}, 'Human selected this take', True)
            self.assertEqual(takes.read_json(root/'take.json')['status'], 'review_pending')

    def test_reconcile_requires_exact_prompt_and_records_suite_and_brain_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            take = root/'take'
            take.mkdir()
            graph = {'27': {'inputs': {'code': 'frozen'}}, '64': {'class_type': 'SaveVideo'}}
            takes.write_json(take/'prompt.json', graph)
            output = root/'output'
            video = output/'The_Message/shots/S1/tk001/video_00001_.mp4'
            video.parent.mkdir(parents=True)
            video.write_bytes(b'review video')
            suite = output/'h3_projects/Film/clips'
            suite.mkdir(parents=True)
            side = suite/'clip_001_take2.json'
            takes.write_json(side, {'prompt': graph, 'clip': 'clip_001_take2', 'index': 1, 'take': 2})
            side.with_suffix('.mp4').write_bytes(b'suite video')
            side.with_suffix('.safetensors').write_bytes(b'latent')
            brain = root/'brain/run-1'
            brain.mkdir(parents=True)
            (brain/'run.json').write_text('{}')
            takes.write_json(take/'take.json', {'status': 'submitted', 'prompt_id': 'run-1',
                'prompt_sha256': takes.file_hash(take/'prompt.json'), 'output_prefix': 'The_Message/shots/S1/tk001/video'})
            record = {'status': {'completed': True, 'status_str': 'success'}, 'prompt': [0, 'run-1', graph],
                      'outputs': {'64': {'images': [{'type': 'output', 'subfolder': 'The_Message/shots/S1/tk001', 'filename': video.name}]}}}
            record['prompt'][2] = {'wrong': {}}
            with self.assertRaisesRegex(ValueError, 'History'):
                takes.reconcile(take, {'run-1': record}, output, 'Film', root/'brain')
            record['prompt'][2] = graph
            with patch.object(takes, 'probe_video', return_value={'width': 832, 'height': 480, 'frames': 73, 'fps': 24, 'audio': False}):
                state = takes.reconcile(take, {'run-1': record}, output, 'Film', root/'brain')
            self.assertEqual(state['status'], 'review_pending')
            self.assertEqual(state['suite']['take'], 2)
            self.assertEqual(state['brain']['run_id'], 'run-1')
            self.assertNotIn('review', state)
            takes.review(take, {'action': 'uncertain'}, 'Needs playback', False)
            self.assertFalse(takes.read_json(take/'take.json')['review']['approved'])
            takes.review(take, {'action': 'pass'}, 'Human selected this take', True)
            with patch.object(takes, 'probe_video', return_value={'width': 832, 'height': 480, 'frames': 73, 'fps': 24, 'audio': False}):
                repeated = takes.reconcile(take, {'run-1': record}, output, 'Film', root/'brain')
            self.assertEqual(repeated['status'], 'approved')
            self.assertTrue(repeated['review']['approved'])
            video.write_bytes(b'replaced')
            with self.assertRaisesRegex(ValueError, 'changed'):
                takes.review(take, {'action': 'pass'}, 'Cannot approve changed video', True)
            with patch.object(takes, 'probe_video', return_value={'width': 832, 'height': 480, 'frames': 73, 'fps': 24, 'audio': False}):
                replaced = takes.reconcile(take, {'run-1': record}, output, 'Film', root/'brain')
            self.assertEqual(replaced['status'], 'review_pending')
            self.assertIsNone(replaced['review'])

    def test_failed_native_history_with_completed_false_marks_take_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            take = Path(tmp)
            takes.write_json(take/'prompt.json', {})
            takes.write_json(take/'take.json', {'status': 'submitted', 'prompt_id': 'run-1',
                'prompt_sha256': takes.file_hash(take/'prompt.json')})
            history = {'run-1': {'status': {'completed': False, 'status_str': 'error'}}}
            state = takes.reconcile(take, history, take/'output', 'Film', take/'brain')
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(takes.read_json(take/'take.json')['status'], 'failed')

    def test_preparation_rejects_builder_state_or_encoder_bypassing_selected_package(self):
        graph = graph_fixture()
        package = resolve_shot_package('MSG_S001_SH05')
        with tempfile.TemporaryDirectory() as tmp:
            graph['22']['inputs']['builder_state'] = '{}'
            with self.assertRaisesRegex(ValueError, 'builder_state'):
                takes.prepare(tmp, graph, {}, package)
            graph['22']['inputs']['builder_state'] = ['27', 2]
            encoder = next(n for n in graph.values() if n['class_type']=='MiniMaxH3FantasticRefModTextEncode')
            encoder['inputs']['prompt'] = 'Old unrelated instruction'
            with self.assertRaisesRegex(ValueError, 'encoder'):
                takes.prepare(tmp, graph, {}, package)

    def test_prepared_prompt_edit_is_rejected_before_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'prompt.json').write_text('{}')
            takes.write_json(root/'take.json', {'status':'prepared', 'prompt_sha256':takes.file_hash(root/'prompt.json')})
            (root/'prompt.json').write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'inputs changed'):
                takes.mark_submitting(root)
            self.assertEqual(takes.read_json(root/'take.json')['status'],'prepared')

    def test_prompt_identity_allows_json_integer_float_roundtrip_but_not_value_changes(self):
        a={'n':{'inputs':{'weight':1.0,'steps':20,'on':True}}}
        b={'n':{'inputs':{'weight':1,'steps':20.0,'on':True}}}
        self.assertEqual(takes.prompt_digest(a), takes.prompt_digest(b))
        b['n']['inputs']['on']=1
        self.assertNotEqual(takes.prompt_digest(a), takes.prompt_digest(b))
        b['n']['inputs']['on']=True
        b['n']['inputs']['weight']=1.01
        self.assertNotEqual(takes.prompt_digest(a), takes.prompt_digest(b))

    def test_suite_execution_cache_markers_do_not_change_prompt_identity(self):
        source={'n':{'class_type':'DynamicScriptNode','inputs':{'code':'original'}}}
        sidecar={'n':{**source['n'],'is_changed':[float('nan')]}}
        self.assertEqual(takes.prompt_digest(source),takes.prompt_digest(sidecar))
        sidecar['n']['inputs']={'code':'different'}
        self.assertNotEqual(takes.prompt_digest(source),takes.prompt_digest(sidecar))
        sidecar['n']['inputs']={'is_changed':float('nan')}
        with self.assertRaises(ValueError):takes.prompt_digest(sidecar)

import copy
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3_loop
import h3_recipe
import h3_loop_run


class LoopContractTests(unittest.TestCase):
    def setUp(self):
        recipe = copy.deepcopy(h3_recipe.SILENT_MEDIUM)
        shot = dict(shot_id='MSG_S001_SH01', recipe=recipe, frames=73, seed=1,
                    prompt_text='Empty cafe', assets={}, media_state=[], stack_state={'picks': []})
        self.bundle = h3_loop.export([shot], 'silent_test')
        self.graph = {
            '2': {'class_type': 'UNETLoader', 'inputs': {'unet_name': recipe['models']['diffusion_models']}},
            '3': {'class_type': 'MiniMaxH3SigmaShift', 'inputs': {'model': ['2', 0], 'shift_video': 12, 'shift_audio': 3}},
            '4': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': recipe['models']['text_encoders'], 'type': 'minimax'}},
            '5': {'class_type': 'VAELoader', 'inputs': {'vae_name': recipe['models']['video_vae']}},
            '7': {'class_type': 'MiniMaxH3RefModStack', 'inputs': {'stack_state': ['36', 1]}},
            '9': {'class_type': 'MiniMaxH3FantasticRefModTextEncode', 'inputs': {
                'clip': ['4', 0], 'vae': ['5', 0], 'mods': ['7', 0], 'references': ['21', 0],
                'prompt': ['35', 4], 'length': ['35', 6], 'width': ['35', 8], 'height': ['35', 9],
                **{k: recipe[k] for k in ('ref_image_size', 'reference_fps', 'max_total_tokens',
                   'voice_description_at_label', 'stack_pictures', 'stack_pictures_n')}}},
            '13': {'class_type': 'KSamplerSelect', 'inputs': {'sampler_name': recipe['sampler']}},
            '14': {'class_type': 'BasicScheduler', 'inputs': {'model': ['3', 0], 'scheduler': recipe['scheduler'], 'denoise': 1, 'steps': ['35', 7]}},
            '15': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': ['35', 5]}},
            '21': {'class_type': 'MiniMaxH3MediaLoader', 'inputs': {'media_state': ['36', 2]}},
            '31': {'class_type': 'DynamicScriptNode', 'inputs': {'code': h3_loop.PLAN_CODE, 'input_0': ['30', 0], 'output_ports_count': 8, 'use_module_cache': False}},
            '32': {'class_type': 'MiniMaxH3GenerationProfile', 'inputs': {'scene_continuity': 'Independent scenes', 'audio_profile': 'No final audio'}},
            '33': {'class_type': 'MiniMaxH3ChainPlanModern', 'inputs': {'chain_policy': ['32', 0], 'plan_json_input': ['31', 1], 'generation_fingerprint': ['31', 2], 'run_name': ['31', 3], 'width': ['31', 4], 'height': ['31', 5], 'encode_mode': 'video', 'video_blend_frames': 0}},
            '36': {'class_type': 'DynamicScriptNode', 'inputs': {'code': h3_loop.SELECT_CODE, 'input_0': ['30', 0], 'input_1': ['35', 1], 'use_module_cache': False}},
            '37': {'class_type': 'MiniMaxH3LoopTrim', 'inputs': {'fps': ['31', 8], 'trim_frames': 0}},
            '38': {'class_type': 'MiniMaxH3ChainSegmentSave', 'inputs': {}},
            '40': {'class_type': 'MiniMaxH3ChainAssemble', 'inputs': {'audio_source': ['31', 6], 'output_subfolder': ['31', 7], 'filename': 'draft', 'copy_to_output': True, 'delete_checkpoints_after_assembly': False}},
        }

    def test_bundle_driven_silent_contract(self):
        self.assertEqual(h3_loop_run.check_graph(self.bundle, self.graph), [])

    def test_replacement_rejects_same_run_before_acquiring_locks(self):
        with patch.object(h3_loop_run, '_locked_run', side_effect=AssertionError('must reject before locking')):
            with self.assertRaisesRegex(ValueError, 'different runs'):
                h3_loop_run.assemble_replacement('/tmp/run', '/tmp/run/.', 'shot', 'replacement', '/tmp/delivery', '/tmp/output')

    def test_replacement_lock_order_does_not_depend_on_argument_order(self):
        for base, replacement in [('/tmp/run-a', '/tmp/run-b'), ('/tmp/run-b', '/tmp/run-a')]:
            with patch.object(h3_loop_run, '_locked_run') as lock:
                lock.return_value.__enter__.return_value = {'status': 'prepared'}
                with self.assertRaisesRegex(ValueError, 'technical-pass'):
                    h3_loop_run.assemble_replacement(base, replacement, 'shot', 'replacement', '/tmp/delivery', '/tmp/output')
                self.assertEqual([call.args[0] for call in lock.call_args_list], [Path('/tmp/run-a'), Path('/tmp/run-b')])

    def test_stale_dimensions_and_wrong_script_fail(self):
        self.graph['33']['inputs']['width'] = 608
        self.graph['31']['inputs']['code'] = 'old script'
        errors = h3_loop_run.check_graph(self.bundle, self.graph)
        self.assertTrue(any('33.width' in e for e in errors))
        self.assertTrue(any('31.code' in e for e in errors))

    def test_audio_routes_cannot_survive_silent_contract(self):
        self.graph['38']['inputs']['audio'] = ['18', 0]
        self.graph['32']['inputs']['audio_profile'] = 'Generate audio'
        errors = h3_loop_run.check_graph(self.bundle, self.graph)
        self.assertTrue(any('38.audio' in e for e in errors))
        self.assertTrue(any('32.audio_profile' in e for e in errors))

    def test_changed_bundle_is_rejected_before_graph_check(self):
        self.bundle['shots'][0]['seed'] = 9
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            h3_loop_run.check_graph(self.bundle, self.graph)

    def test_missing_required_node_is_an_actionable_failure(self):
        del self.graph['9']
        errors = h3_loop_run.check_graph(self.bundle, self.graph)
        self.assertTrue(any('node 9' in e for e in errors))

    def test_edit_composite_passthrough_is_rejected_in_silent_generation(self):
        self.graph['25'] = {'class_type': 'MiniMaxH3FantasticEditComposite', 'inputs': {'images': ['17', 0], 'references': ['21', 0]}}
        errors = h3_loop_run.check_graph(self.bundle, self.graph)
        self.assertTrue(any('edit composite' in e for e in errors))

    def test_workflow_monitor_brain_passes_when_enabled_and_rejects_disabled(self):
        self.graph['46'] = {
            'class_type': 'WorkflowMonitorBrain',
            'inputs': {'enabled': True, 'run_label': 'Shot 05 monitor', 'sample_interval': '2', 'phase_overrides': '{}'},
        }
        self.assertEqual(h3_loop_run.check_graph(self.bundle, self.graph), [])
        self.graph['46']['inputs']['enabled'] = False
        errors = h3_loop_run.check_graph(self.bundle, self.graph)
        self.assertTrue(any('WorkflowMonitorBrain' in e for e in errors))


class RunRecordFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture = LoopContractTests()
        fixture.setUp()
        self.bundle, self.graph = fixture.bundle, fixture.graph
        self.source = self.root / 'bundle.json'
        self.source.write_text(json.dumps(self.bundle))
        self.graph['30'] = {'class_type': 'DynamicLoadTextFileNode', 'inputs': {
            'file_path': str(self.source), 'encoding': 'utf_8'}}
        self.graph.update({
            '12': {'class_type': 'BasicGuider', 'inputs': {'model': ['3', 0], 'conditioning': ['9', 0]}},
            '16': {'class_type': 'SamplerCustomAdvanced', 'inputs': {'noise': ['15', 0], 'guider': ['12', 0],
                  'sampler': ['13', 0], 'sigmas': ['14', 0], 'latent_image': ['9', 2]}},
            '17': {'class_type': 'VAEDecode', 'inputs': {'samples': ['16', 0], 'vae': ['5', 0]}},
            '34': {'class_type': 'MiniMaxH3ChainLoopStart', 'inputs': {
                'plan': ['33', 0], 'start_clip': 1, 'scene_range': '', 'verify_resume_history': True}},
            '35': {'class_type': 'MiniMaxH3ChainCurrent', 'inputs': {'state': ['34', 1], 'align_audio_reference': False}},
            '39': {'class_type': 'MiniMaxH3ChainLoopEnd', 'inputs': {
                'execution_mode': 'recursive', 'between_scene_cleanup': 'unload_models', 'flow': ['34', 0],
                'state': ['35', 0], 'images': ['37', 0], 'sampled_latent': ['16', 0], 'segment': ['38', 0]}},
        })
        self.graph['36']['inputs']['output_ports_count'] = 2
        self.graph['37']['inputs'].update(images=['17', 0], state=['35', 0])
        self.graph['38']['inputs'].update(state=['35', 0], images=['37', 0], sampled_latent=['16', 0])
        self.graph['40']['inputs'].update(manifest=['39', 0], blend_schedule='plan',
                                         boundary_tone_match='off', color_stabilization='off')
        self.models = {}
        for role, filename in self.bundle['shots'][0]['recipe']['models'].items():
            category = 'vae' if role.endswith('_vae') else role
            relative = f'models/{category}/{filename}'
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'test weights')
            stat = path.stat()
            self.models[role] = dict(path=relative, size_bytes=stat.st_size,
                                     mtime_ns=stat.st_mtime_ns, sha256=h3_recipe.file_hash(path))
        self.nodes = {node['class_type'] for node in self.graph.values()}
        self.resources = dict(observed_at=time.time(), running=0, pending=0,
                              conflicting_export=False, free_ram_bytes=1000, free_vram_bytes=1000)

    def prepare(self):
        return h3_loop_run.prepare(self.root / 'runs', self.bundle, self.graph, self.models, self.root)

    def read(self, path):
        return json.loads((path / 'run.json').read_text())

    def submitting(self):
        path = self.prepare()
        h3_loop_run.preflight(path, self.resources, self.nodes)
        h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)
        return path

    def history(self, path, prompt_id='prompt-one'):
        return {prompt_id: {'prompt': [0, prompt_id, self.graph, {}, ['40']],
                           'status': {'messages': [['execution_start', {
                               'prompt_id': prompt_id,
                               'timestamp': int((self.read(path)['submitting_at'] + 1) * 1000)}]]}}}


class RunRecordTests(RunRecordFixture, unittest.TestCase):
    def test_wrong_sampling_route_blocks_preflight(self):
        self.graph['16']['inputs']['latent_image'] = ['9', 1]
        path = self.prepare()
        with self.assertRaisesRegex(ValueError, 'node 16'):
            h3_loop_run.preflight(path, self.resources, self.nodes)

    def test_disabled_between_scene_cleanup_blocks_preflight(self):
        self.graph['39']['inputs']['between_scene_cleanup'] = 'off'
        path = self.prepare()
        with self.assertRaisesRegex(ValueError, 'between_scene_cleanup'):
            h3_loop_run.preflight(path, self.resources, self.nodes)

    def test_cli_prepares_record_without_submitting(self):
        graph = self.root / 'graph.json'
        graph.write_text(json.dumps(self.graph))
        models = self.root / 'models.json'
        models.write_text(json.dumps(self.models))
        result = subprocess.run([sys.executable, h3_loop_run.__file__, 'prepare', '--root', str(self.root / 'runs'),
                                 '--bundle', str(self.source), '--graph', str(graph), '--models', str(models),
                                 '--workspace', str(self.root)], capture_output=True, text=True, check=True)
        self.assertEqual(self.read(Path(result.stdout.strip()))['status'], 'prepared')
    def test_records_identity_before_submission_and_refuses_collision(self):
        path = self.prepare()
        state = self.read(path)
        self.assertEqual(state['status'], 'prepared')
        self.assertEqual(state['shot_ids'], ['MSG_S001_SH01'])
        self.assertEqual(state['delivery'], dict(width=832, height=480, fps=24, frames=73, audio='none'))
        self.assertEqual(state['bundle']['fingerprint'], self.bundle['fingerprint'])
        self.assertIsNone(state['review'])
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_submit_requires_preflight_and_binds_prompt_only_once(self):
        path = self.prepare()
        with self.assertRaisesRegex(ValueError, 'preflight'):
            h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)
        h3_loop_run.preflight(path, self.resources, self.nodes)
        h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)
        h3_loop_run.bind_prompt(path, 'prompt-one')
        before = self.read(path)
        h3_loop_run.bind_prompt(path, 'prompt-one')
        self.assertEqual(self.read(path), before)
        self.assertEqual([e['status'] for e in before['events']],
                         ['prepared', 'preflight_passed', 'submitting', 'queued'])
        with self.assertRaises(ValueError):
            h3_loop_run.bind_prompt(path, 'prompt-two')
        with self.assertRaises(ValueError):
            h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)

    def test_changed_bundle_file_blocks_dispatch(self):
        path = self.prepare()
        h3_loop_run.preflight(path, self.resources, self.nodes)
        self.bundle['shots'][0]['seed'] = 22
        self.source.write_text(json.dumps(self.bundle))
        with self.assertRaisesRegex(ValueError, 'bundle source'):
            h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)
        self.assertEqual(self.read(path)['status'], 'preflight_passed')

    def test_changed_graph_blocks_dispatch(self):
        path = self.prepare()
        h3_loop_run.preflight(path, self.resources, self.nodes)
        self.graph['32']['inputs']['audio_profile'] = 'Generate audio'
        with self.assertRaisesRegex(ValueError, 'graph changed'):
            h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)

    def test_changed_model_blocks_dispatch(self):
        path = self.prepare()
        h3_loop_run.preflight(path, self.resources, self.nodes)
        (self.root / self.models['video_vae']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'model stamp changed'):
            h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)

    def test_input_authorization_does_not_mark_visual_approval(self):
        asset_path = self.root / 'input/reference.png'
        asset_path.parent.mkdir()
        asset_path.write_bytes(b'fixture')
        asset = dict(path='input/reference.png', sha256=h3_recipe.file_hash(asset_path),
                     input_use_authorized=True, approved=False)
        self.bundle['shots'][0]['assets'] = {'reference': asset}
        self.bundle = h3_loop.export(self.bundle['shots'], 'silent_test')
        self.source.write_text(json.dumps(self.bundle))
        path = self.prepare()
        h3_loop_run.preflight(path, self.resources, self.nodes)
        self.assertIsNone(self.read(path)['review'])
        asset_path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'asset missing or hash changed'):
            h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)

    def test_stale_resources_and_missing_nodes_block_preflight(self):
        path = self.prepare()
        self.resources['observed_at'] -= 121
        with self.assertRaisesRegex(ValueError, 'two minutes'):
            h3_loop_run.preflight(path, self.resources, self.nodes)
        self.resources['observed_at'] = time.time()
        with self.assertRaisesRegex(ValueError, 'node unavailable'):
            h3_loop_run.preflight(path, self.resources, [])
        self.assertEqual(self.read(path)['status'], 'prepared')

    def test_unknown_submission_cannot_be_retried(self):
        path = self.submitting()
        h3_loop_run.mark_unknown(path, 'queue acknowledgement lost')
        with self.assertRaises(ValueError):
            h3_loop_run.mark_submitting(path, self.graph, self.resources, self.nodes)
        h3_loop_run.recover_submission(path, {})
        self.assertEqual(self.read(path)['status'], 'unknown')

    def test_recovery_requires_unique_recent_exact_graph(self):
        path = self.submitting()
        history = self.history(path)
        history['unrelated'] = copy.deepcopy(history['prompt-one'])
        history['unrelated']['prompt'][1] = 'unrelated'
        history['unrelated']['prompt'][2]['32']['inputs']['audio_profile'] = 'wrong'
        h3_loop_run.recover_submission(path, history)
        self.assertEqual(self.read(path)['prompt_id'], 'prompt-one')
        before = self.read(path)
        h3_loop_run.recover_submission(path, history)
        self.assertEqual(self.read(path), before)

    def test_old_or_ambiguous_history_stays_unknown(self):
        path = self.submitting()
        old = self.history(path)
        old['prompt-one']['status']['messages'][0][1]['timestamp'] = 0
        h3_loop_run.recover_submission(path, old)
        self.assertEqual(self.read(path)['status'], 'unknown')
        history = {**self.history(path), **self.history(path, 'prompt-two')}
        h3_loop_run.recover_submission(path, history)
        self.assertEqual(self.read(path)['status'], 'unknown')
        self.assertIsNone(self.read(path)['prompt_id'])

    def test_record_identity_edit_cannot_bypass_file_checks(self):
        path = self.prepare()
        state = self.read(path)
        state['models']['video_vae']['sha256'] = 'changed'
        (path / 'run.json').write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, 'run identity changed'):
            h3_loop_run.preflight(path, self.resources, self.nodes)


class CompletionTests(RunRecordFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        first = self.bundle['shots'][0]
        first['recipe'].update(width=32, height=32)
        first['frames'] = 3
        second = copy.deepcopy(first)
        second.update(shot_id='MSG_S001_SH02', prompt_text='Second angle', seed=2)
        self.bundle = h3_loop.export([first, second], 'silent_test')
        self.source.write_text(json.dumps(self.bundle))
        self.path = self.submitting()
        h3_loop_run.bind_prompt(self.path, 'prompt-one')
        self.output = self.root / 'output'
        self.output.mkdir()
        self.manifest = dict(format='h3_chain_manifest_v3', run_name='silent_test', plan_hash='native-plan',
                             compatibility=dict(width=32, height=32, fps=24,
                                                generation_fingerprint=self.bundle['fingerprint']),
                             clip_count=2, total_delivered_frames=6, segments=[])
        for index, shot in enumerate(self.bundle['shots'], 1):
            segment_path = self.output / f'{index}.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            f'color={"red" if index == 1 else "blue"}:s=32x32:r=24',
                            '-frames:v', '3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(segment_path)], check=True)
            (self.output / f'{index}.checkpoint').write_bytes(b'checkpoint fixture')
            (self.output / f'{index}.txt').write_text(shot['prompt_text'])
            segment = dict(index=index, id=shot['shot_id'], revision=f'revision-{index}',
                           segment=segment_path.name, checkpoint=f'{index}.checkpoint', prompt_file=f'{index}.txt',
                           revision_metadata=f'{index}.json', prompt=shot['prompt_text'],
                           seed=shot['seed'], steps=20, raw_frames=3, delivered_frames=3)
            for key in ('segment', 'checkpoint', 'prompt_file'):
                segment[key + '_sha256'] = h3_recipe.file_hash(self.output / segment[key])
            (self.output / f'{index}.json').write_text(json.dumps(dict(
                format='h3_chain_segment_v3', run_name='silent_test', plan_hash='native-plan',
                compatibility=self.manifest['compatibility'], segment=segment)))
            self.manifest['segments'].append(segment)
        self.final = self.output / self.bundle['output_subfolder'] / 'draft.mp4'
        self.final.parent.mkdir(parents=True)
        self.render_final()
        self.completed = self.history(self.path)
        self.completed['prompt-one']['status'].update(completed=True, status_str='success')
        self.completed['prompt-one']['outputs'] = {'40': {'images': [dict(
            filename='draft.mp4', subfolder=self.bundle['output_subfolder'], type='output')]}}

    def render_final(self, reverse=False):
        concat = self.output / 'concat.txt'
        order = [s['index'] for s in self.manifest['segments']]
        if reverse:
            order.reverse()
        concat.write_text(''.join(f"file '{self.output / f'{index}.mp4'}'\n" for index in order))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat),
                        '-c', 'copy', '-movflags', 'use_metadata_tags', '-metadata',
                        'h3_manifest=' + json.dumps(self.manifest), str(self.final)], check=True)

    def test_complete_receipt_is_idempotent_and_requires_visual_review(self):
        result = h3_loop_run.reconcile(self.path, self.completed, self.output)
        self.assertEqual(result['status'], 'review_pending')
        self.assertIsNone(result['review'])
        self.assertEqual(result['output']['probe']['frames'], 6)
        self.assertFalse(result['output']['probe']['audio'])
        self.assertEqual(h3_loop_run.reconcile(self.path, self.completed, self.output), result)

    def test_unrelated_history_cannot_complete_run(self):
        with self.assertRaisesRegex(ValueError, 'recorded prompt'):
            h3_loop_run.reconcile(self.path, {'other': self.completed['prompt-one']}, self.output)
        self.assertEqual(self.read(self.path)['status'], 'queued')

    def test_temporary_preview_cannot_be_a_delivery(self):
        self.completed['prompt-one']['outputs']['40']['images'][0]['type'] = 'temp'
        with self.assertRaisesRegex(ValueError, 'saved assembly'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)

    def test_changed_checkpoint_is_rejected(self):
        (self.output / '1.checkpoint').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checkpoint hash'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)

    def test_partial_manifest_never_becomes_technical_pass(self):
        self.manifest.update(format='h3_chain_partial_manifest_v3', clip_count=1,
                             total_delivered_frames=3, planned_clip_count=2)
        self.manifest['segments'] = self.manifest['segments'][:1]
        self.render_final()
        result = h3_loop_run.reconcile(self.path, self.completed, self.output)
        self.assertEqual(result['status'], 'rendered')
        self.assertTrue(result['partial'])
        self.assertNotIn('technical_pass', [e['status'] for e in result['events']])

    def test_changed_completed_media_does_not_keep_old_pass(self):
        h3_loop_run.reconcile(self.path, self.completed, self.output)
        with self.final.open('ab') as stream:
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'completed media changed'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)
        self.assertEqual(self.read(self.path)['status'], 'failed')

    def test_audio_stream_blocks_silent_delivery(self):
        audio = self.final.with_name('with-audio.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.final), '-f', 'lavfi',
                        '-i', 'anullsrc=r=48000:cl=stereo', '-map', '0:v:0', '-map', '1:a:0',
                        '-c:v', 'copy', '-c:a', 'aac', '-shortest', '-movflags', 'use_metadata_tags',
                        str(audio)], check=True)
        audio.replace(self.final)
        with self.assertRaisesRegex(ValueError, 'audio'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)

    def test_manifest_from_another_bundle_is_rejected(self):
        self.manifest['compatibility']['generation_fingerprint'] = 'wrong bundle'
        self.render_final()
        with self.assertRaisesRegex(ValueError, 'different production bundle'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)

    def test_symlinked_artifact_cannot_escape_output(self):
        checkpoint = self.output / '1.checkpoint'
        outside = self.root / 'outside.checkpoint'
        checkpoint.replace(outside)
        checkpoint.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'outside'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)

    def test_revision_metadata_mismatch_is_rejected(self):
        path = self.output / '1.json'
        metadata = json.loads(path.read_text())
        metadata['segment']['revision'] = 'other revision'
        path.write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, 'revision metadata mismatch'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)

    def test_reversed_frames_are_not_accepted_despite_matching_counts(self):
        self.render_final(reverse=True)
        with self.assertRaisesRegex(ValueError, 'frame order'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)

    def test_history_path_cannot_escape_output(self):
        self.completed['prompt-one']['outputs']['40']['images'][0]['subfolder'] = '../outside'
        with self.assertRaisesRegex(ValueError, 'outside'):
            h3_loop_run.reconcile(self.path, self.completed, self.output)

    def test_authoritative_error_is_recorded_as_failed(self):
        self.completed['prompt-one']['status'].update(completed=False, status_str='error')
        result = h3_loop_run.reconcile(self.path, self.completed, self.output)
        self.assertEqual(result['status'], 'failed')

    def test_publish_delivery_is_idempotent_and_refuses_conflict(self):
        h3_loop_run.reconcile(self.path, self.completed, self.output)
        dest = self.root / 'delivery'
        first = h3_loop_run.publish_delivery(self.path, dest, self.output)
        self.assertEqual(first['technical_status'], 'passed')
        self.assertEqual(first['creative_status'], 'review_pending')
        self.assertTrue((dest / 'silent_test.mp4').is_file())
        self.assertTrue((dest / 'shots/01_msg_s001_sh01.mp4').is_file())
        self.assertTrue((dest / 'shots/02_msg_s001_sh02.mp4').is_file())
        self.assertTrue((dest / 'README.md').is_file())
        second = h3_loop_run.publish_delivery(self.path, dest, self.output)
        self.assertEqual(first, second)
        conflict = self.root / 'conflict'
        conflict.mkdir()
        (conflict / 'other.txt').write_text('existing')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            h3_loop_run.publish_delivery(self.path, conflict, self.output)

    def test_controlled_single_shot_replacement_preserves_other_segments_and_base_run(self):
        base_before = h3_loop_run.reconcile(self.path, self.completed, self.output)
        patch_shot = copy.deepcopy(self.bundle['shots'][1])
        patch_shot['prompt_text'] = 'Tabletop only close-up'
        patch_bundle = h3_loop.export([patch_shot], 'patch_sh02')
        patch_source = self.root / 'patch_bundle.json'
        patch_source.write_text(json.dumps(patch_bundle))
        patch_graph = copy.deepcopy(self.graph)
        patch_graph['30']['inputs']['file_path'] = str(patch_source)
        patch_dir = h3_loop_run.prepare(self.root / 'runs', patch_bundle, patch_graph, self.models, self.root)
        h3_loop_run.preflight(patch_dir, self.resources, self.nodes)
        h3_loop_run.mark_submitting(patch_dir, patch_graph, self.resources, self.nodes)
        h3_loop_run.bind_prompt(patch_dir, 'prompt-patch')
        patch_seg_path = self.output / 'patch2.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=green:s=32x32:r=24',
                        '-frames:v', '3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(patch_seg_path)], check=True)
        (self.output / 'patch2.checkpoint').write_bytes(b'patch checkpoint')
        (self.output / 'patch2.txt').write_text(patch_shot['prompt_text'])
        compat = dict(width=32, height=32, fps=24, generation_fingerprint=patch_bundle['fingerprint'])
        seg = dict(index=1, id='MSG_S001_SH02', revision='rev-patch-2', segment='patch2.mp4',
                   checkpoint='patch2.checkpoint', prompt_file='patch2.txt', revision_metadata='patch2.json',
                   prompt=patch_shot['prompt_text'], seed=patch_shot['seed'], steps=20, raw_frames=3, delivered_frames=3)
        for k in ('segment', 'checkpoint', 'prompt_file'):
            seg[k + '_sha256'] = h3_recipe.file_hash(self.output / seg[k])
        (self.output / 'patch2.json').write_text(json.dumps(dict(
            format='h3_chain_segment_v3', run_name='patch_sh02', plan_hash='patch-plan', compatibility=compat, segment=seg)))
        p_manifest = dict(format='h3_chain_manifest_v3', run_name='patch_sh02', plan_hash='patch-plan',
                          compatibility=compat, clip_count=1, total_delivered_frames=3, segments=[seg])
        patch_final = self.output / patch_bundle['output_subfolder'] / 'draft.mp4'
        patch_final.parent.mkdir(parents=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(patch_seg_path), '-c', 'copy',
                        '-movflags', 'use_metadata_tags', '-metadata', 'h3_manifest=' + json.dumps(p_manifest), str(patch_final)], check=True)
        p_hist = {'prompt-patch': {'prompt': [0, 'prompt-patch', patch_graph, {}, ['40']],
                                   'status': {'completed': True, 'status_str': 'success', 'messages': []},
                                   'outputs': {'40': {'images': [dict(filename='draft.mp4', subfolder=patch_bundle['output_subfolder'], type='output')]}}}}
        h3_loop_run.reconcile(patch_dir, p_hist, self.output)
        rep_dest = self.root / "director's projects" / 'delivery_v2'
        doc = h3_loop_run.assemble_replacement(self.path, patch_dir, 'MSG_S001_SH02', 'silent_test_v2', rep_dest, self.output)
        self.assertEqual(doc['shots'][0]['sha256'], base_before['output']['segments'][0]['segment_sha256'])
        self.assertEqual(doc['shots'][1]['sha256'], seg['segment_sha256'])
        self.assertEqual(self.read(self.path)['output']['sha256'], base_before['output']['sha256'])
        self.assertEqual(h3_loop_run.assemble_replacement(self.path, patch_dir, 'MSG_S001_SH02', 'silent_test_v2', rep_dest, self.output), doc)
        new_patch = self.root / 'new_patch_revision'
        new_patch.mkdir()
        state = self.read(patch_dir)
        state['prompt_id'] = 'new-prompt'
        state['output']['manifest']['segments'][0]['revision'] = 'new-revision'
        (new_patch / 'run.json').write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, 'different content'):
            h3_loop_run.assemble_replacement(self.path, new_patch, 'MSG_S001_SH02', 'silent_test_v2', rep_dest, self.output)
        (rep_dest / doc['shots'][0]['friendly_file']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'published shot hash mismatch'):
            h3_loop_run.assemble_replacement(self.path, patch_dir, 'MSG_S001_SH02', 'silent_test_v2', rep_dest, self.output)

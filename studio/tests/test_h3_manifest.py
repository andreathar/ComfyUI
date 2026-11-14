import copy
import json
import sys
from pathlib import Path
import tempfile
import unittest

from h3_manifest import check, file_digest, main


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'input').mkdir()
        for name in ('portrait.png', 'source.mkv', 'mask.safetensors'):
            (self.root / 'input' / name).write_bytes(name.encode())
        for name in ('video.safetensors', 'audio.safetensors', 'clip.safetensors', 'encoder.py'):
            (self.root / name).write_bytes(name.encode())
        items = [{'kind': 'picture', 'file': 'portrait.png [input]', 'enabled': True},
                 {'kind': 'video', 'file': 'source.mkv [input]', 'mask': 'mask.safetensors [input]',
                  'edit': True, 'resize': 512, 'mask_grow': 0}]
        graph = {
            '1': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'video.safetensors'}},
            '2': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'audio.safetensors'}},
            '3': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'clip.safetensors', 'type': 'minimax'}},
            '4': {'class_type': 'MiniMaxH3MediaLoader', 'inputs': {'media_state': json.dumps(items)}},
            '5': {'class_type': 'PrimitiveStringMultiline', 'inputs': {'value': 'Replace identity from <Picture 1>.'}},
            '6': {'class_type': 'MiniMaxH3PromptBuilder', 'inputs': {'prompt_text': ['5', 0], 'references': ['4', 0]}},
            '7': {'class_type': 'MiniMaxH3FantasticRefModTextEncode', 'inputs': {
                'prompt': ['6', 0], 'references': ['6', 19], 'clip': ['3', 0], 'vae': ['1', 0], 'audio_vae': ['2', 0],
                'width': 512, 'height': 288, 'length': 73, 'reference_fps': 24,
                'ref_image_size': 'match', 'max_total_tokens': 0, 'voice_description_at_label': False,
                'stack_pictures': 'every 4th', 'stack_pictures_n': 8}},
            '8': {'class_type': 'AndreH3StageSave', 'inputs': {'conditioning': ['7', 0], 'latent': ['7', 2], 'name': 'pilot'}},
            '99': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': 42}},
        }
        assets = {}
        for binding, selected, path in [
            ('1.vae_name', 'video.safetensors', 'video.safetensors'),
            ('2.vae_name', 'audio.safetensors', 'audio.safetensors'),
            ('3.clip_name', 'clip.safetensors', 'clip.safetensors'),
            ('4.media.0.file', 'portrait.png [input]', 'input/portrait.png'),
            ('4.media.1.file', 'source.mkv [input]', 'input/source.mkv'),
            ('4.media.1.mask', 'mask.safetensors [input]', 'input/mask.safetensors'),
        ]:
            assets[binding] = {'selected': selected, 'path': path, 'sha256': file_digest(self.root / path)}
        self.manifest = {'version': 1, 'recipe': 'head_source_lock_control_v1', 'graph': graph,
                         'stage_save_node': '8', 'continuation': False, 'prompt_text': graph['5']['inputs']['value'],
                         'source': {'delivery_frames': 67, 'working_frames': 73, 'fps': 24, 'width': 512, 'height': 288},
                         'assets': assets, 'software': {'encoder': {'path': 'encoder.py', 'sha256': file_digest(self.root / 'encoder.py')}}}

    def run_check(self):
        return check(self.manifest, self.root)

    def media_change(self, key, value):
        node = self.manifest['graph']['4']['inputs']
        items = json.loads(node['media_state'])
        items[1][key] = value
        node['media_state'] = json.dumps(items)

    def test_deterministic_and_missing_receipt_requires_encode(self):
        self.assertEqual(self.run_check(), check(copy.deepcopy(self.manifest), self.root))
        self.assertTrue(self.run_check()['requires_encode'])

    def test_unrelated_sampler_does_not_invalidate_encode(self):
        key = self.run_check()['conditioning_key']
        self.manifest['graph']['99']['inputs']['noise_seed'] = 1337
        self.assertEqual(key, self.run_check()['conditioning_key'])

    def test_edit_settings_change_key(self):
        key = self.run_check()['conditioning_key']
        self.media_change('resize', 1024)
        self.assertNotEqual(key, self.run_check()['conditioning_key'])
        key = self.run_check()['conditioning_key']
        self.media_change('mask_grow', 32)
        self.assertNotEqual(key, self.run_check()['conditioning_key'])

    def test_same_filename_changed_bytes_rejected(self):
        (self.root / 'input/portrait.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'content hash mismatch'):
            self.run_check()

    def test_asset_path_must_match_loader(self):
        self.manifest['assets']['4.media.0.file']['path'] = 'input/source.mkv'
        with self.assertRaisesRegex(ValueError, 'path differs'):
            self.run_check()

    def test_traversal_and_symlink_escape_rejected(self):
        for value in ('../outside.mkv [input]', '/etc/passwd [input]', 'source.mkv [output]'):
            self.media_change('file', value)
            with self.assertRaises(ValueError):
                self.run_check()
        (self.root / 'input/escape').symlink_to(self.root / 'video.safetensors')
        self.media_change('file', 'escape [input]')
        with self.assertRaisesRegex(ValueError, 'escapes input'):
            self.run_check()

    def test_stale_and_matching_receipts(self):
        key = self.run_check()['conditioning_key']
        path = self.root / 'stage.pt'
        path.write_bytes(b'not loaded as a tensor')
        self.manifest['stage'] = {'path': 'stage.pt', 'sha256': file_digest(path), 'conditioning_key': key}
        self.assertEqual(self.run_check()['stage_status'], 'matching_receipt')
        self.assertTrue(self.run_check()['requires_encode'])
        self.assertFalse(self.run_check()['reuse_authorized'])
        self.media_change('mask_grow', 3)
        self.assertEqual(self.run_check()['stage_status'], 'stale')
        self.manifest['stage']['conditioning_key'] = self.run_check()['conditioning_key']
        path.write_bytes(b'overwritten')
        self.assertEqual(self.run_check()['stage_status'], 'stale')

    def test_deleted_stage_requires_encode(self):
        self.manifest['stage'] = {'path': 'deleted.pt', 'sha256': 'old', 'conditioning_key': 'old'}
        report = self.run_check()
        self.assertEqual(report['stage_status'], 'missing_artifact')
        self.assertTrue(report['requires_encode'])

    def test_falsy_enabled_values_are_not_disabled(self):
        for enabled in (0, None, ''):
            self.media_change('enabled', enabled)
            self.assertEqual(len(self.run_check()['media_order']), 2)

    def test_empty_required_media_files_rejected(self):
        inputs = self.manifest['graph']['4']['inputs']
        for value in ('', None):
            items = json.loads(inputs['media_state'])
            items[0]['file'] = value
            inputs['media_state'] = json.dumps(items)
            self.manifest['assets'].pop('4.media.0.file', None)
            with self.assertRaisesRegex(ValueError, 'saved \\[input\\] asset'):
                self.run_check()

    def test_disabled_source_is_not_a_valid_recipe(self):
        self.media_change('enabled', False)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.run_check()

    def test_mode_and_slot_overrides_rejected(self):
        builder = self.manifest['graph']['6']['inputs']
        builder['builder_state'] = '{"mode":"T2VA"}'
        with self.assertRaisesRegex(ValueError, 'REF-mode'):
            self.run_check()
        builder['builder_state'] = '{}'
        builder['picture_1'] = ['4', 99]
        with self.assertRaisesRegex(ValueError, 'slot overrides'):
            self.run_check()

    def test_mismatched_encoder_reference_ports_rejected(self):
        self.manifest['graph']['7']['inputs']['references'] = ['6', 18]
        with self.assertRaisesRegex(ValueError, 'same Prompt Builder ports'):
            self.run_check()

    def test_malformed_media_has_clean_cli_failure(self):
        for item in (None, 42, 'picture'):
            self.manifest['graph']['4']['inputs']['media_state'] = json.dumps([item])
            path = self.root / 'bad-media.json'
            path.write_text(json.dumps(self.manifest))
            self.assertEqual(main([str(path), '--root', str(self.root)]), 1)

    def test_duplicate_basename_cannot_authorize_model_reuse(self):
        duplicate = self.root / 'another/video.safetensors'
        duplicate.parent.mkdir()
        duplicate.write_bytes(b'an unrelated same-named checkpoint')
        entry = self.manifest['assets']['1.vae_name']
        entry.update(path=str(duplicate), sha256=file_digest(duplicate))
        report = self.run_check()
        self.assertEqual(report['model_resolution'], 'unverified_explicit_bindings')
        self.assertFalse(report['reuse_authorized'])
        self.assertTrue(report['requires_encode'])

    def test_media_order_and_encoder_options_change_key(self):
        key = self.run_check()['conditioning_key']
        self.manifest['graph']['7']['inputs']['stack_pictures_n'] = 4
        self.assertNotEqual(key, self.run_check()['conditioning_key'])
        key = self.run_check()['conditioning_key']
        inputs = self.manifest['graph']['4']['inputs']
        items = json.loads(inputs['media_state'])
        items.reverse()
        inputs['media_state'] = json.dumps(items)
        bindings = self.manifest['assets']
        bindings['4.media.1.file'], bindings['4.media.0.file'] = bindings['4.media.0.file'], bindings['4.media.1.file']
        bindings['4.media.0.mask'] = bindings.pop('4.media.1.mask')
        self.assertNotEqual(key, self.run_check()['conditioning_key'])

    def test_invalid_grid_and_delivery_rejected(self):
        for count in (67, 4, 56):
            self.manifest['source']['working_frames'] = count
            with self.assertRaisesRegex(ValueError, '5\\+17k grid'):
                self.run_check()

    def test_encoder_dimensions_must_match_contract(self):
        self.manifest['graph']['7']['inputs']['width'] = 1024
        with self.assertRaisesRegex(ValueError, 'disagree'):
            self.run_check()

    def test_unexpanded_prompt_rejected(self):
        self.manifest['graph']['5']['inputs']['value'] = 'Replace with !Andre'
        with self.assertRaisesRegex(ValueError, 'shorthand'):
            self.run_check()

    def test_prompt_mismatch_rejected(self):
        self.manifest['prompt_text'] = 'Other prompt'
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.run_check()

    def test_kj_get_and_unknown_dependencies_fail_closed(self):
        self.manifest['graph']['5']['class_type'] = 'GetNode'
        with self.assertRaisesRegex(ValueError, 'unsupported encode dependency'):
            self.run_check()

    def test_missing_node_and_cycle_rejected(self):
        self.manifest['graph']['6']['inputs']['prompt_text'] = ['absent', 0]
        with self.assertRaisesRegex(ValueError, 'missing upstream'):
            self.run_check()
        self.manifest['graph']['6']['inputs']['prompt_text'] = ['6', 0]
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            self.run_check()

    def test_missing_and_extra_assets_rejected(self):
        self.manifest['assets']['unused'] = self.manifest['assets']['1.vae_name']
        with self.assertRaisesRegex(ValueError, 'exactly cover'):
            self.run_check()
        del self.manifest['assets']['unused']
        del self.manifest['assets']['1.vae_name']
        with self.assertRaises(KeyError):
            self.run_check()

    def test_continuation_rejected(self):
        self.manifest['continuation'] = True
        with self.assertRaisesRegex(ValueError, 'continuation'):
            self.run_check()

    def test_software_changed_rejected(self):
        (self.root / 'encoder.py').write_bytes(b'changed code')
        with self.assertRaisesRegex(ValueError, 'software content hash mismatch'):
            self.run_check()

    def test_stage_name_and_titles_do_not_change_conditioning(self):
        key = self.run_check()['conditioning_key']
        self.manifest['graph']['8']['inputs']['name'] = 'other-name'
        self.manifest['graph']['7']['_meta'] = {'title': 'New title'}
        self.assertEqual(key, self.run_check()['conditioning_key'])

    def test_preflight_does_not_write_or_import_execution_code(self):
        before = {str(p.relative_to(self.root)): p.stat().st_mtime_ns for p in self.root.rglob('*')}
        imported = set(sys.modules)
        self.run_check()
        self.assertEqual(before, {str(p.relative_to(self.root)): p.stat().st_mtime_ns for p in self.root.rglob('*')})
        self.assertFalse(any(name == 'torch' or name.startswith(('torch.', 'comfy.', 'server.'))
                             for name in set(sys.modules) - imported))

    def test_invalid_api_inputs_object_has_clean_failure(self):
        self.manifest['graph']['4']['inputs'] = []
        with self.assertRaisesRegex(ValueError, 'inputs object'):
            self.run_check()

    def test_cli_reports_bad_manifest_without_traceback(self):
        path = self.root / 'bad.json'
        path.write_text('{}')
        self.assertEqual(main([str(path), '--root', str(self.root)]), 1)


if __name__ == '__main__':
    unittest.main()

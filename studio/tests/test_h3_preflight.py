from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import io
import types
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3_preflight as preflight
import h3_recipe as h3


class PreflightTests(unittest.TestCase):
    def test_snapshot_uses_listener_pid_and_keeps_unknown_queue_state(self):
        def command(args, **kwargs):
            if args[0] == 'ss':
                self.assertEqual(args[-1], 'sport = :8190')
                output = 'LISTEN 0 128 127.0.0.1:8190 0.0.0.0:* users:(("python",pid=123,fd=5))'
            elif '--query-gpu=memory.free,memory.total,temperature.gpu' in args:
                output = '4000, 6000, 40'
            else:
                output = '123, python, 1000\n456, python, 500'
            return types.SimpleNamespace(stdout=output)

        with patch.object(preflight.urllib.request, 'urlopen', return_value=io.BytesIO(b'{}')), patch.object(preflight.subprocess, 'run', side_effect=command):
            result = preflight.capture_snapshot('http://127.0.0.1:8190')
        self.assertEqual(result['foreign_gpu_processes'], ['python(pid=456,500MiB)'])
        self.assertEqual(result['usable_comfy_vram_bytes'], 5000 * 2**20)
        self.assertIsNone(result['running'])
        self.assertIsNone(result['pending'])

    def test_missing_weights_and_nodes_are_distinct(self):
        with tempfile.TemporaryDirectory() as root:
            result = preflight.check(Path(root), {'diffusion_models': {'path': 'missing', 'size_bytes': 1, 'mtime_ns': 0, 'sha256': 'x'}}, {}, {'UNETLoader'})
            self.assertTrue(any('weight missing' in e for e in result['errors']))
            self.assertTrue(any('node unavailable' in e for e in result['errors']))

    def test_input_authorization_takes_precedence_over_creative_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'asset.png'
            source.write_bytes(b'fixture')
            asset = {'path': source.name, 'sha256': h3.file_hash(source)}
            for flags, blocked in (({'approved': False, 'input_use_authorized': True}, False),
                                   ({'approved': True, 'input_use_authorized': False}, True),
                                   ({'approved': True}, False)):
                with self.subTest(flags=flags):
                    result = preflight.check(root, {}, {'ref': {**asset, **flags}})
                    self.assertEqual(any('approval required' in e for e in result['errors']), blocked)

    def test_changed_model_stamp_requires_rehash(self):
        with tempfile.TemporaryDirectory() as root:
            relative = 'models/diffusion_models/' + h3.DIAGNOSTIC['models']['diffusion_models']
            path = Path(root) / relative
            path.parent.mkdir(parents=True)
            path.write_bytes(b'weight')
            record = {'path': relative, 'size_bytes': 6, 'mtime_ns': 0, 'sha256': h3.file_hash(path)}
            result = preflight.check(Path(root), {'diffusion_models': record}, {}, None)
            self.assertTrue(any('model stamp changed' in e for e in result['errors']))

    def test_busy_gpu_job_blocks_dispatch(self):
        result = preflight.resources({'running': 1, 'pending': 0, 'free_ram_bytes': 20 * 2**30, 'free_vram_bytes': 2 * 2**30, 'conflicting_export': False, 'observed_at': time.time()})
        self.assertFalse(result['ready'])
        self.assertEqual(result['errors'], ['ComfyUI queue is busy or unknown'])

    def test_unknown_export_status_is_not_qualified(self):
        result = preflight.resources({'running': 0, 'pending': 0, 'free_ram_bytes': 20 * 2**30, 'free_vram_bytes': 2 * 2**30, 'observed_at': time.time()})
        self.assertFalse(result['ready'])
        self.assertEqual(result['errors'], ['Conflicting GPU export status is active or unknown'])

    def test_invalid_memory_observations_cannot_qualify_dispatch(self):
        for field in ('free_ram_bytes', 'free_vram_bytes', 'usable_comfy_vram_bytes'):
            for value in (None, float('nan'), float('inf'), 'unknown'):
                with self.subTest(field=field, value=value):
                    snapshot = {'running': 0, 'pending': 0, 'conflicting_export': False,
                                'observed_at': time.time(), 'free_ram_bytes': 20 * 2**30,
                                'free_vram_bytes': 4 * 2**30, 'usable_comfy_vram_bytes': 4 * 2**30}
                    snapshot[field] = value
                    result = preflight.resources(snapshot)
                    self.assertFalse(result['ready'])
                    self.assertTrue(any(field in error for error in result['errors']))

    def test_foreign_gpu_process_and_thermal_ceiling_block_dispatch(self):
        result = preflight.resources({
            'running': 0, 'pending': 0, 'free_ram_bytes': 20 * 2**30, 'free_vram_bytes': 1 * 2**30,
            'usable_comfy_vram_bytes': 1 * 2**30, 'min_free_vram_bytes': 4 * 2**30,
            'conflicting_export': False, 'foreign_gpu_processes': ['llama-server(pid=99,4800MiB)'],
            'gpu_temp_c': 89, 'observed_at': time.time(),
        })
        self.assertFalse(result['ready'])
        self.assertTrue(any('usable_comfy_vram_bytes' in e for e in result['errors']))
        self.assertTrue(any('foreign GPU process' in e for e in result['errors']))
        self.assertTrue(any('temperature too high' in e for e in result['errors']))

    def test_model_role_cannot_pin_an_unrelated_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'unrelated'
            path.write_bytes(b'wrong weights')
            stat = path.stat()
            record = {'path': 'unrelated', 'size_bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'sha256': h3.file_hash(path)}
            result = preflight.check(root, {role: record for role in h3.DIAGNOSTIC['models']}, {}, None, rehash=True)
            self.assertFalse(result['ready'])

    def test_preferred_external_copy_is_checked(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            name = h3.DIAGNOSTIC['models']['diffusion_models']
            relative = 'models/diffusion_models/' + name
            original = root / relative
            original.parent.mkdir(parents=True)
            original.write_bytes(b'original')
            hot = root / 'hot/diffusion_models' / name
            hot.parent.mkdir(parents=True)
            hot.write_bytes(b'different')
            config = root / 'extra_model_paths.yaml'
            config.write_text('hot:\n  base_path: hot\n  is_default: true\n  diffusion_models: diffusion_models\n')
            stat = original.stat()
            record = {'path': relative, 'size_bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'sha256': h3.file_hash(original), 'resolver_config_sha256': h3.file_hash(config)}
            result = preflight.check(root, {'diffusion_models': record}, {}, None, rehash=True)
            self.assertTrue(any('model hash mismatch' in e for e in result['errors']))

    def test_resolve_model_uses_model_folders(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            name = h3.DIAGNOSTIC['models']['diffusion_models']
            hot = root / 'hot/diffusion_models ' / name
            hot.parent.mkdir(parents=True)
            hot.write_bytes(b'external')
            wrong = hot.parent.with_name('diffusion_models') / name
            wrong.parent.mkdir()
            wrong.write_bytes(b'wrong normalized copy')
            config = root / 'extra_model_paths.yaml'
            config.write_text('hot:\n  base_path: hot\n  is_default: true\n  unet: "diffusion_models "\n')
            folders = h3.model_folders(root, 'diffusion_models')
            self.assertIn(hot.parent, folders)
            resolved = preflight.resolve_model(root, 'diffusion_models')
            self.assertEqual(resolved, hot)


if __name__ == '__main__':
    unittest.main()

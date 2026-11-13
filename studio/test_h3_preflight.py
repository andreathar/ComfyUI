from pathlib import Path
import sys
import tempfile
import unittest
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3_preflight as preflight
import h3_recipe as h3


class PreflightTests(unittest.TestCase):
    def test_missing_weights_and_nodes_are_distinct(self):
        with tempfile.TemporaryDirectory() as root:
            result = preflight.check(Path(root), {'diffusion_models': {'path': 'missing', 'size_bytes': 1, 'mtime_ns': 0, 'sha256': 'x'}}, {}, {'UNETLoader'})
            self.assertTrue(any('weight missing' in e for e in result['errors']))
            self.assertTrue(any('node unavailable' in e for e in result['errors']))

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


if __name__ == '__main__':
    unittest.main()

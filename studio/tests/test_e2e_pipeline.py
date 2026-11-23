"""End-to-end integration test spanning compile → graph → preflight → prepare."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3_recipe as h3
import h3_graph
import h3_preflight as preflight
import production_validate as pv
import film


class E2EPipelineTest(unittest.TestCase):
    """Spans the full pipeline: compile_shot → compile_graph → preflight.check → film.prepare."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # Build a minimal production document
        self.doc = json.loads((pv.SPEC / 'example.production.json').read_text())
        self.doc['shots'][0].pop('target', None)
        self.doc['shots'][0]['duration_s'] = 2
        self.doc['characters'][0]['voice'] = 'DEMO-VOX-MAIN'
        self.doc['voices'] = [{'id': 'DEMO-VOX-MAIN', 'name': 'Main voice', 'description': 'Test voice reference'}]
        self.doc['shots'][0]['dialogue'] = [{'character': 'DEMO-CHR-MAIN', 'line': 'Not again.'}]
        # Create asset files
        self.assets = {}
        for key, kind, role, owner in [('actor', 'video', 'identity', 'DEMO-CHR-MAIN'),
                                        ('room', 'picture', 'location', 'DEMO-LOC-STREET'),
                                        ('voice', 'audio', 'voice', 'DEMO-VOX-MAIN')]:
            relative = f'input/{key}.png' if kind == 'picture' else f'models/refmods/{key}.safetensors'
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(key.encode())
            if kind == 'picture':
                sel_file = f'{key}.png [input]'
            else:
                sel_file = key
            self.assets[key] = dict(path=relative, sha256=h3.file_hash(path), approved=True,
                                    role=role, owner=owner, version=1, kind=kind, source='test fixture',
                                    selection={'file': sel_file, 'kind': kind})
        self.binding = {'assets': ['room', 'actor', 'voice'], 'audio_mode': 'generated_voiceover', 'seed': 0}
        self.recipe = copy.deepcopy(h3.DIAGNOSTIC)
        # Create model files for preflight
        self._create_models()

    def _create_models(self):
        """Create all four model files and pin them for preflight."""
        self.model_records = {}
        config_path = self.root / 'extra_model_paths.yaml'
        config_hash = h3.file_hash(config_path) if config_path.is_file() else None
        for role, filename in self.recipe['models'].items():
            category = 'vae' if role.endswith('_vae') else role
            path = self.root / f'models/{category}/{filename}'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(role.encode())
            stat = path.stat()
            self.model_records[role] = {
                'path': f'models/{category}/{filename}',
                'size_bytes': stat.st_size,
                'mtime_ns': stat.st_mtime_ns,
                'sha256': h3.file_hash(path),
                'resolver_config_sha256': config_hash,
            }

    def _compile(self):
        shot_id = self.doc['shots'][0]['id']
        return h3.compile_shot(self.doc, shot_id, self.binding, self.assets, self.recipe, self.root)

    def test_full_pipeline_compile_graph_preflight_prepare(self):
        """Span compile → graph → preflight → prepare and verify consistency."""
        # Step 1: Compile shot
        compiled = self._compile()
        self.assertIn('builder_state', compiled)
        self.assertIn('prompt_text', compiled)
        self.assertIn('fingerprint', compiled)
        self.assertEqual(compiled['frames'], 56)  # 2s at 24fps: max(5,48) + (5-48%17)%17 = 56

        # Step 2: Build graph from compiled shot
        graph = h3_graph.compile_graph(compiled, 'test/video')
        self.assertEqual(graph['20']['inputs']['filename_prefix'], 'test/video')
        self.assertEqual(graph['15']['inputs']['noise_seed'], compiled['seed'])
        self.assertEqual(graph['23']['inputs']['value'], compiled['shot']['duration_s'])

        # Step 3: Preflight check models and assets
        check_result = preflight.check(self.root, self.model_records, compiled.get('assets', {}), None)
        self.assertTrue(check_result['ready'], f"preflight errors: {check_result['errors']}")

        # Step 4: Prepare take directory
        takes_root = self.root / 'takes'
        take_path = film.prepare(takes_root, compiled, 'take001')
        self.assertTrue((take_path / 'compiled.json').is_file())
        self.assertTrue((take_path / 'prompt.txt').is_file())
        self.assertTrue((take_path / 'panel-edits.json').is_file())
        self.assertTrue((take_path / 'take.json').is_file())

        # Verify consistency: take.json matches compiled fingerprint
        take_state = film.read_json(take_path / 'take.json')
        self.assertEqual(take_state['fingerprint'], compiled['fingerprint'])
        self.assertEqual(take_state['status'], 'prepared')
        self.assertEqual(take_state['compiled_sha256'], h3.file_hash(take_path / 'compiled.json'))

        # Verify graph matches compiled recipe via verify()
        graph_digest = h3_graph.verify(graph, compiled, 'test/video')
        self.assertEqual(len(graph_digest), 64)  # SHA-256 hex digest

    def test_preflight_catches_changed_model(self):
        """Verify preflight detects when a model file changes after pinning."""
        compiled = self._compile()
        # Tamper with a model file
        model_path = self.root / 'models/diffusion_models' / self.recipe['models']['diffusion_models']
        model_path.write_bytes(b'tampered')
        # Preflight should detect the stamp change
        check_result = preflight.check(self.root, self.model_records, compiled.get('assets', {}), None)
        self.assertFalse(check_result['ready'])
        self.assertTrue(any('model stamp changed' in e for e in check_result['errors']))

    def test_graph_verify_catches_modified_canvas(self):
        """Verify graph.verify() detects when the canvas diverges from the recipe."""
        compiled = self._compile()
        graph = h3_graph.compile_graph(compiled, 'test/video')
        # Tamper with the graph
        graph['15']['inputs']['noise_seed'] = 999999
        with self.assertRaisesRegex(ValueError, 'differs from prepared recipe'):
            h3_graph.verify(graph, compiled, 'test/video')

    def test_prompt_media_and_refmods_reach_their_h3_consumers(self):
        compiled = self._compile()
        graph = h3_graph.compile_graph(compiled, 'test/video')
        builder = graph['8']['inputs']
        encoder = graph['9']['inputs']
        self.assertEqual(builder['prompt_text'], compiled['prompt_text'])
        self.assertEqual(json.loads(builder['builder_state']), compiled['builder_state'])
        self.assertEqual(json.loads(graph['21']['inputs']['media_state']), compiled['media_state'])
        self.assertEqual(json.loads(graph['7']['inputs']['stack_state']), compiled['stack_state'])
        self.assertEqual((builder['references'], builder['mods']), (['21', 0], ['7', 0]))
        self.assertEqual((encoder['prompt'], encoder['references'], encoder['mods']),
                         (['8', 0], ['8', 19], ['8', 20]))
        take = film.prepare(self.root / 'contract-takes', compiled, 'take001')
        edits = {(row['node_id'], row['widget']): row['value']
                 for row in json.loads((take / 'panel-edits.json').read_text())}
        self.assertEqual(json.loads(edits[(8, 'builder_state')]), compiled['builder_state'])
        self.assertEqual(json.loads(edits[(21, 'media_state')]), compiled['media_state'])
        self.assertEqual(json.loads(edits[(7, 'stack_state')]), compiled['stack_state'])
        self.assertEqual(edits[(15, 'noise_seed')], compiled['seed'])

        for node, field, value in [('8', 'prompt_text', 'other shot'),
                                   ('21', 'media_state', '[]'),
                                   ('7', 'stack_state', '{"picks": [], "budget": 0}'),
                                   ('9', 'references', ['21', 0])]:
            with self.subTest(node=node, field=field):
                changed = copy.deepcopy(graph)
                changed[node]['inputs'][field] = value
                with self.assertRaisesRegex(ValueError, 'differs from prepared recipe'):
                    h3_graph.verify(changed, compiled, 'test/video')

    def test_prepare_rejects_duplicate_attempt(self):
        """Verify film.prepare() fails when the take directory already exists."""
        compiled = self._compile()
        takes_root = self.root / 'takes'
        film.prepare(takes_root, compiled, 'take001')
        with self.assertRaises(FileExistsError):
            film.prepare(takes_root, compiled, 'take001')


if __name__ == '__main__':
    unittest.main()

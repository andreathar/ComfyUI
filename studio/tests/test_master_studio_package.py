#!/usr/bin/env python3
from pathlib import Path
import sys
import unittest
import json
import tempfile
import copy
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from master_studio_package import resolve_shot_package
import master_studio_package as packages
import h3_recipe as h3
import h3_graph
from studio import production_bootstrap
from studio.production_validate import SPEC


class MasterStudioPackageTests(unittest.TestCase):
    def test_project_package_is_importable_from_comfyui_root(self):
        result = subprocess.run([sys.executable, '-c', 'import studio.master_studio_package'],
                                cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_resolver_imports_with_only_studio_directory_on_path(self):
        source = str(Path(__file__).resolve().parents[1])
        result = subprocess.run([sys.executable, '-I', '-c',
                                 f'import sys; sys.path.insert(0, {source!r}); import master_studio_package'],
                                cwd='/tmp', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def _project(self, root, tag, seed):
        doc = json.loads((SPEC / 'example.production.json').read_text())
        shot = doc['shots'][0]
        shot.pop('target', None)
        shot['dialogue'] = []
        shot['duration_s'] = 3
        shot['action'] = f'{tag} opens the door.'
        parent = root / tag
        parent.mkdir()
        proposal = production_bootstrap.preview(doc, 'movie')
        production_bootstrap.create(parent, proposal, proposal['digest'])
        project = parent / 'movie'
        assets = {}
        for name, role, owner in [('room', 'location', shot['location']),
                                  ('actor', 'identity', shot['characters'][0])]:
            file = root / 'input' / tag / f'{name}.png'
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(f'{tag}-{name}'.encode())
            assets[name] = {'path': file.relative_to(root).as_posix(), 'sha256': h3.file_hash(file),
                            'input_use_authorized': True, 'role': role, 'owner': owner,
                            'kind': 'picture', 'selection': {'kind': 'picture', 'file': f'{tag}/{name}.png [input]'}}
        binding = {'assets': ['room', 'actor'], 'audio_mode': 'silent', 'seed': seed}
        (project / 'assets.json').write_text(json.dumps(assets))
        (project / 'bindings.json').write_text(json.dumps({shot['id']: binding}))
        return project, doc, binding, assets

    def test_explicit_projects_resolve_native_h3_state_without_cross_talk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, doc_a, bind_a, assets_a = self._project(root, 'alpha', 123)
            b, doc_b, bind_b, assets_b = self._project(root, 'beta', 456)
            shot = doc_a['shots'][0]['id']
            recipe = copy.deepcopy(h3.DIAGNOSTIC)
            one = packages.resolve_shot_package(shot, project_root=a, workspace=root, recipe=recipe)
            two = packages.resolve_shot_package(shot, project_root=b, workspace=root, recipe=recipe)
            for result, doc, binding, assets, tag, project in [(one, doc_a, bind_a, assets_a, 'alpha', a),
                                                                (two, doc_b, bind_b, assets_b, 'beta', b)]:
                expected = h3.compile_shot(doc, shot, binding, assets, recipe, root)
                for key in ('prompt_text', 'builder_state', 'media_state', 'stack_state', 'seed'):
                    self.assertEqual(result[key], expected[key])
                self.assertIn(tag, result['prompt_text'])
                self.assertEqual(len(result['project_revision']), 64)
                self.assertEqual(result['prompt_status'], 'draft_uncommitted')
                self.assertEqual(result['project_root'], str(project))
                self.assertEqual((result['width'], result['height'], result['fps'], result['duration_s']),
                                 (recipe['width'], recipe['height'], recipe['fps'], doc['shots'][0]['duration_s']))
                self.assertTrue(all(item['file'].startswith(tag + '/') for item in result['media_state']))
                graph = h3_graph.compile_graph(expected, f'{tag}/shot')
                self.assertEqual(graph['8']['inputs']['prompt_text'], result['prompt_text'])
                self.assertEqual(json.loads(graph['8']['inputs']['builder_state']), result['builder_state'])
                self.assertEqual(json.loads(graph['21']['inputs']['media_state']), result['media_state'])
                self.assertEqual(json.loads(graph['7']['inputs']['stack_state']), result['stack_state'])
                self.assertEqual(graph['15']['inputs']['noise_seed'], result['seed'])
                self.assertEqual(graph['16']['inputs']['noise'], ['15', 0])
            self.assertNotEqual(one['project_revision'], two['project_revision'])
            self.assertNotEqual(one['seed'], two['seed'])

    def test_explicit_project_without_shot_binding_never_uses_legacy_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, doc, _, _ = self._project(root, 'alpha', 123)
            (project / 'bindings.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'binding'):
                packages.resolve_shot_package(doc['shots'][0]['id'], project_root=project, workspace=root,
                                              recipe=copy.deepcopy(h3.SILENT_MEDIUM))

    def test_partial_project_arguments_never_fall_back_to_the_message(self):
        with self.assertRaisesRegex(ValueError, 'project'):
            packages.resolve_shot_package('MSG_S001_SH05', workspace=Path('/tmp'))

    def test_changed_project_during_compile_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, doc, _, _ = self._project(root, 'alpha', 123)
            compile_shot = h3.compile_shot
            def changed(*args, **kwargs):
                compiled = compile_shot(*args, **kwargs)
                (project / 'shot_transitions.json').write_text(json.dumps({doc['shots'][0]['id']: 'continue'}))
                return compiled
            with patch.object(packages.h3_recipe, 'compile_shot', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'project changed'):
                    packages.resolve_shot_package(doc['shots'][0]['id'], project_root=project, workspace=root,
                                                  recipe=copy.deepcopy(h3.SILENT_MEDIUM))

    def test_reference_symlink_outside_native_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, doc, _, assets = self._project(root, 'alpha', 123)
            outside = root / 'external.png'
            outside.write_bytes(b'external')
            actor = root / assets['actor']['path']
            actor.unlink()
            actor.symlink_to(outside)
            assets['actor']['sha256'] = h3.file_hash(outside)
            (project / 'assets.json').write_text(json.dumps(assets))
            with self.assertRaisesRegex(ValueError, 'outside'):
                packages.resolve_shot_package(doc['shots'][0]['id'], project_root=project, workspace=root,
                                              recipe=copy.deepcopy(h3.SILENT_MEDIUM))

    def test_native_refmod_uses_configured_external_root_and_rechecks_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, doc, _, assets = self._project(root, 'alpha', 123)
            external = root / 'external' / 'refmods'
            external.mkdir(parents=True)
            refmod = external / 'actor.safetensors'
            refmod.write_bytes(b'identity refmod')
            (root / 'extra_model_paths.yaml').write_text('external:\n  base_path: external\n  refmods: refmods\n  is_default: true\n')
            assets['actor'].update(path='models/refmods/actor.safetensors', sha256=h3.file_hash(refmod),
                                   kind='video', selection={'kind': 'video', 'file': 'actor'})
            (project / 'assets.json').write_text(json.dumps(assets))
            shot = doc['shots'][0]['id']
            result = packages.resolve_shot_package(shot, project_root=project, workspace=root,
                                                   recipe=copy.deepcopy(h3.SILENT_MEDIUM))
            self.assertEqual(result['stack_state']['picks'][0]['visual']['file'], 'actor')
            self.assertEqual(result['media_state'][0]['file'], 'alpha/room.png [input]')
            refmod.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash'):
                packages.resolve_shot_package(shot, project_root=project, workspace=root,
                                              recipe=copy.deepcopy(h3.SILENT_MEDIUM))

    def test_unknown_transition_does_not_silently_become_a_cut(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project, doc, _, _ = self._project(root, 'alpha', 123)
            (project / 'shot_transitions.json').write_text(json.dumps({doc['shots'][0]['id']: 'dissolve'}))
            with self.assertRaisesRegex(ValueError, 'transition'):
                packages.resolve_shot_package(doc['shots'][0]['id'], project_root=project, workspace=root,
                                              recipe=copy.deepcopy(h3.SILENT_MEDIUM))
    def test_sh03_tabletop_package(self):
        pkg = resolve_shot_package("MSG_S001_SH03")
        self.assertEqual(pkg["shot_id"], "MSG_S001_SH03")
        self.assertEqual(pkg["seed"], 11003)
        self.assertEqual(pkg["transition"], "cut")
        self.assertEqual(pkg["stack_state"]["picks"], [])
        self.assertTrue(pkg["media_state"])
        self.assertIn("tabletop", pkg["prompt_text"].lower() + pkg["prompt_name"].lower())

    def test_sh05_has_andre_refmod(self):
        pkg = resolve_shot_package("MSG_S001_SH05")
        self.assertEqual(pkg["seed"], 11005)
        self.assertTrue(pkg["stack_state"]["picks"])
        self.assertIn("Andre", pkg["prompt_text"])

    def test_unknown_shot_rejected(self):
        with self.assertRaises(ValueError):
            resolve_shot_package("MSG_S999_SH99")

    def test_live_resolver_reads_committed_edits_and_keeps_old_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["prompts", "media", "refmods", "project"]:
                (root / name).mkdir()
            prompt = root / "prompts" / "shot.json"
            prompt.write_text(json.dumps({"name": "Shot", "prompt": "First text", "state": {"version": 1, "mode": "REF"}}))
            (root / "project/bindings.json").write_text(json.dumps({"S1": {"seed": 42}}))
            (root / "media/The Message _ S1 Media.json").write_text('{"items": []}')
            with patch.multiple(packages, PROJECT=root / "project", PROMPTS=root / "prompts", MEDIA=root / "media",
                                REFMODS=root / "refmods", TRANSITIONS=root / "transitions.json", PROMPT_FILES={"S1": "shot.json"},
                                SNAPSHOTS=root / "snapshots"):
                code = packages.live_resolver_code()
                env = {"inputs": ["S1"], "outputs": [None] * 7}
                exec(code, env)
                first = json.loads(env["outputs"][6])
                old_snapshot = Path(first["snapshot"])
                self.assertEqual(json.loads(old_snapshot.read_text())["prompt_text"], "First text")
                prompt.write_text(json.dumps({"name": "Shot", "prompt": "Saved edit", "state": {"version": 2, "mode": "REF"}}))
                exec(code, env)
                second = json.loads(env["outputs"][6])
                self.assertEqual(env["outputs"][0], "Saved edit")
                self.assertEqual(json.loads(env["outputs"][1])["version"], 2)
                self.assertNotEqual(first["revision"], second["revision"])
                self.assertEqual(json.loads(old_snapshot.read_text())["prompt_text"], "First text")
                Path(second["snapshot"]).unlink()
                def resolve_once(_):
                    env = {"inputs": ["S1"], "outputs": [None] * 7}
                    exec(code, env)
                    return json.loads(env["outputs"][6])["revision"]
                with ThreadPoolExecutor(max_workers=4) as pool:
                    revisions = list(pool.map(resolve_once, range(16)))
                self.assertEqual(set(revisions), {second["revision"]})
                self.assertEqual(len(list((root / "snapshots").iterdir())), 2)
                Path(second["snapshot"]).unlink()
                real_open = Path.open
                @contextmanager
                def interrupted_open(path, mode="r", *args, **kwargs):
                    with real_open(path, mode, *args, **kwargs) as stream:
                        if mode == "x":
                            def write_partial(text):
                                stream.write(text[:10])
                                raise OSError("Simulated interrupted write")
                            yield SimpleNamespace(write=write_partial)
                        else:
                            yield stream
                with patch.object(Path, "open", interrupted_open), self.assertRaises(OSError):
                    exec(code, env)
                self.assertFalse(Path(second["snapshot"]).exists())
                prompt.unlink()
                with self.assertRaises(FileNotFoundError):
                    exec(code, env)


if __name__ == "__main__":
    unittest.main()

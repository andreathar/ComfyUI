#!/usr/bin/env python3
from pathlib import Path
import sys
import unittest
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from master_studio_package import resolve_shot_package
import master_studio_package as packages


class MasterStudioPackageTests(unittest.TestCase):
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

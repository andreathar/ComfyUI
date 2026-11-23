import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot


PRESETS = json.loads((shot.STUDIO / "presets.json").read_text())


class Response(io.BytesIO):
    def __init__(self, data):
        super().__init__(json.dumps(data).encode())


class ShotTests(unittest.TestCase):
    def spec(self, **extra):
        return {"project": "argon-demo", "scene": "s01", "shot": "010", "subject": "a lone courier", **extra}

    def test_prompt_and_output_follow_patterns(self):
        job = shot.resolve(self.spec(look="noir", aspect="2.39x1"), PRESETS, Path("/unused"))
        self.assertEqual(job["template"], "z-image-t2i")
        self.assertEqual((job["width"], job["height"]), (1536, 640))
        self.assertNotIn(", ,", job["prompt"])
        self.assertIn("a lone courier", job["prompt"])
        self.assertIn(PRESETS["looks"]["noir"], job["prompt"])
        self.assertEqual(shot.output_prefix(job, PRESETS, 44), "refs/argon-demo/s01/010/s01-010_z-image-turbo_2.39x1_s44")

    def test_spec_overrides_model_settings(self):
        job = shot.resolve(self.spec(model="sd15", steps=30), PRESETS, Path("/unused"))
        self.assertEqual((job["steps"], job["cfg"], job["width"]), (30, 7, 768))

    def test_names_must_be_slugs(self):
        for key, value in (("project", "../escape"), ("shot", "Shot 1"), ("scene", "")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                shot.resolve(self.spec(**{key: value}), PRESETS, Path("/unused"))

    def test_reference_switches_to_image_to_image_inside_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = Path(tmp)
            (inputs / "refs/argon-demo").mkdir(parents=True)
            (inputs / "refs/argon-demo/plate.png").write_bytes(b"png")
            job = shot.resolve(self.spec(reference="refs/argon-demo/plate.png"), PRESETS, inputs)
            self.assertEqual((job["template"], job["denoise"]), ("z-image-i2i", 0.6))
            for bad in ("../outside.png", "refs/argon-demo/missing.png"):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    shot.resolve(self.spec(reference=bad), PRESETS, inputs)

    def test_fill_keeps_types_and_rejects_unknown_variables(self):
        graph = shot.fill({"1": {"inputs": {"seed": "{{seed}}", "link": ["2", 0]}}}, {"seed": 7})
        self.assertEqual(graph, {"1": {"inputs": {"seed": 7, "link": ["2", 0]}}})
        with self.assertRaises(ValueError):
            shot.fill({"1": {"inputs": {"text": "{{missing}}"}}}, {})

    def test_every_template_fills_from_its_model_preset(self):
        for name, model in PRESETS["models"].items():
            for reference in (None, "refs/x.png"):
                if model["family"] == "flux2" and reference:
                    continue  # references are chained in by worker.add_references
                job = {**model, "prompt": "p", "width": 64, "height": 64, "reference": reference}
                template = f"{model['family']}-{'i2i' if reference else 't2i'}"
                with self.subTest(template=template):
                    shot.fill(shot.load_template(template), {**job, "seed": 1, "output": "o"})

    def test_sheet_expands_shared_fields(self):
        sheet = {"project": "argon-demo", "scene": "s01", "look": "noir", "shots": [{"shot": "010", "subject": "a"}, {"shot": "020", "subject": "b", "look": "natural"}]}
        self.assertEqual([(s["shot"], s["look"]) for s in shot.expand(sheet)], [("010", "noir"), ("020", "natural")])

    def test_render_writes_tagged_sidecar_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = Path(tmp)
            image = outputs / "refs/argon-demo/s01/010/s01-010_z-image-turbo_16x9_s44_00001_.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"png")
            history = {"pid": {"status": {"status_str": "success"}, "outputs": {"10": {"images": [
                {"filename": image.name, "subfolder": "refs/argon-demo/s01/010", "type": "output"}]}}}}
            job = shot.resolve(self.spec(tags=["night"]), PRESETS, Path("/unused"))
            with patch.object(shot.urllib.request, "urlopen", side_effect=[Response({"prompt_id": "pid"}), Response(history)]):
                images = shot.render(job, PRESETS, 44, "http://127.0.0.1:8188", outputs)
            self.assertEqual(images, [image])
            sidecar = json.loads(image.with_suffix(".json").read_text())
            self.assertEqual((sidecar["seed"], sidecar["tags"], sidecar["prompt_id"]), (44, ["night"], "pid"))
            self.assertEqual(sidecar["model_files"]["z-image-vae"]["sha256"][:8], "afc8e282")
            index = (outputs / "refs/argon-demo/index.jsonl").read_text().splitlines()
            self.assertEqual(json.loads(index[0])["image"], "refs/argon-demo/s01/010/" + image.name)

    def test_monitored_reference_links_native_brain_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / 'output'
            image = outputs / 'refs/argon-demo/s01/010/still.png'
            image.parent.mkdir(parents=True)
            image.write_bytes(b'png')
            brain = root / 'user/workflow_monitor/runs/pid/run.json'
            brain.parent.mkdir(parents=True)
            brain.write_text(json.dumps({'prompt_id': 'pid', 'status': 'succeeded', 'coverage': 'resources-only'}))
            history = {'pid': {'status': {'status_str': 'success'}, 'outputs': {'10': {'images': [
                {'filename': image.name, 'subfolder': 'refs/argon-demo/s01/010', 'type': 'output'}]}}}}
            job = shot.resolve(self.spec(), PRESETS, Path('/unused'))
            with (patch.object(shot, 'PROJECT', root), patch.object(shot, 'post', side_effect=[
                    {'queue_running': [], 'queue_pending': []}, {'prompt_id': 'pid'}, history]) as post):
                shot.render(job, PRESETS, 44, 'http://127.0.0.1:8188', outputs, brain=True)
            graph = post.call_args_list[1].args[2]['prompt']
            monitor, = [node for node in graph.values() if node['class_type'] == 'WorkflowMonitorBrain']
            self.assertFalse(monitor['inputs']['analyze_when_finished'])
            self.assertEqual(json.loads(image.with_suffix('.json').read_text())['brain_run'],
                             'user/workflow_monitor/runs/pid/run.json')


if __name__ == "__main__":
    unittest.main()

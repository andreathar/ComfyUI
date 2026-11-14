import http.server
import json
import os
from pathlib import Path
import pathlib
import sys
import tempfile
import threading
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot
import worker

PRESETS = json.loads((shot.STUDIO / "presets.json").read_text())


class PresetTests(unittest.TestCase):
    def test_aspect_3x4_present(self):
        self.assertEqual(PRESETS["aspects"]["3x4"], {"z-image": [864, 1152], "sd15": [384, 512], "flux2": [864, 1152]})

    def test_refine_template_fills(self):
        model = PRESETS["models"]["z-image-turbo"]
        values = {**model, "prompt": "p", "width": 64, "height": 64, "reference": "r.png", "seed": 1, "output": "o"}
        graph = shot.fill(shot.load_template("z-image-refine"), values)
        classes = {node["class_type"] for node in graph.values()}
        self.assertLessEqual({"VAEEncodeTiled", "VAEDecodeTiled"}, classes)
        self.assertNotIn("{{", json.dumps(graph))


def make_job(project, **extra):
    job = {"version": 1, "id": "cf-20261030-091200-ab12", "kind": "keyframe", "target": "comfy-zimage",
           "shot": "S1", "entity": None, "prompt": "a courier", "refs": [], "source": None, "aspect": "16x9",
           "seeds": [44, 45], "denoise": None, "outputs": ["shots/S001/a.png", "shots/S001/b.png"], **extra}
    folder = worker.jobs_dir(project)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{job['id']}.json").write_text(json.dumps(job))
    return job, folder / f"{job['id']}.json"


def make_models(root):
    for folder, name in (("unet", "z_image_turbo_bf16.safetensors"), ("clip", "qwen_3_4b.safetensors"),
                         ("vae", "ae.safetensors"), ("diffusion_models", "flux-2-klein-4b-Q4_K_M.gguf"),
                         ("vae", "flux2-vae.safetensors"), ("checkpoints", "v1-5-pruned-emaonly-fp16.safetensors")):
        (root / folder).mkdir(parents=True, exist_ok=True)
        (root / folder / name).write_bytes(b"x")


class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        graph = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["prompt"]
        self.server.graphs.append(graph)
        save = next(n for n in graph.values() if n["class_type"] == "SaveImage")["inputs"]["filename_prefix"]
        path = self.server.root / "output" / f"{save}_00001_.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 48)).save(path)
        self.server.history = {"p1": {"status": {"status_str": "success"}, "outputs": {"10": {"images": [
            {"filename": path.name, "subfolder": str(path.parent.relative_to(self.server.root / "output")), "type": "output"}]}}}}
        self.reply({"prompt_id": "p1"})

    def do_GET(self):
        self.reply(self.server.history)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.project, self.comfy, self.models = self.root / "proj", self.root / "comfy", self.root / "models"
        self.project.mkdir()
        make_models(self.models)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        self.server.graphs, self.server.root, self.server.history = [], self.comfy, {}
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def run_it(self, path, url=None):
        worker.run_job(path, self.project, url or self.url, self.comfy, self.models)
        return worker.read_status(self.project, path.stem)

    def invalid(self, **extra):
        job, _ = make_job(self.project, **extra)
        with self.assertRaises(worker.JobError) as caught:
            worker.validate_job(job, self.project, self.models)
        return str(caught.exception)

    def test_valid_job_passes(self):
        job, _ = make_job(self.project)
        worker.validate_job(job, self.project, self.models, job["id"])

    def test_validation_rejections(self):
        self.assertIn("version", self.invalid(version=2))
        self.assertIn("does not match", self.invalid(kind="refine"))
        self.assertIn("same length", self.invalid(seeds=[1]))
        self.assertIn("denoise", self.invalid(kind="refine", target="comfy-refine", denoise=1.5, source="a.png"))
        self.assertIn("outside", self.invalid(outputs=["../x.png", "b.png"]))

    def test_source_symlink_escape_and_missing(self):
        outside = self.root / "secret.png"
        Image.new("RGB", (16, 16)).save(outside)
        (self.project / "link.png").symlink_to(outside)
        refine = dict(kind="refine", target="comfy-refine", denoise=0.3, seeds=[1], outputs=["o.png"])
        self.assertIn("outside", self.invalid(source="link.png", **refine))
        self.assertIn("not found", self.invalid(source="none.png", **refine))

    def test_existing_output_and_missing_model(self):
        (self.project / "shots/S001").mkdir(parents=True)
        (self.project / "shots/S001/a.png").write_bytes(b"old")
        self.assertEqual(self.invalid(), "output exists")
        (self.project / "shots/S001/a.png").unlink()
        (self.models / "unet/z_image_turbo_bf16.safetensors").unlink()
        self.assertEqual(self.invalid(), "missing models/unet/z_image_turbo_bf16.safetensors")

    def test_refine_size(self):
        self.assertEqual(worker.refine_size(864, 1152), (1296, 1728))
        self.assertEqual(worker.refine_size(1344, 768), (2016, 1152))
        w, h = worker.refine_size(1536, 1024)
        self.assertEqual(max(w, h), 2048)
        self.assertEqual((w % 16, h % 16), (0, 0))
        self.assertAlmostEqual(w / h, 1.5, delta=0.03)
        self.assertEqual(worker.refine_size(10, 10), (16, 16))

    def test_build_graph_targets(self):
        job = {"id": "j", "project_code": "p", "kind": "keyframe", "target": "comfy-zimage", "prompt": "hi", "aspect": "3x4"}
        graph = worker.build_graph(job, 7, 0, None, None, PRESETS)
        self.assertIn("864", json.dumps(graph))
        self.assertIn(7, [n["inputs"].get("seed") for n in graph.values()])
        sd = worker.build_graph({**job, "target": "comfy-sd15"}, 7, 0, None, None, PRESETS)
        self.assertIn("watermark", json.dumps(sd))
        refine = worker.build_graph({**job, "kind": "refine", "target": "comfy-refine", "denoise": 0.35}, 7, 0, "openreel/j/s.png", (1296, 1728), PRESETS)
        self.assertEqual(refine["12"]["inputs"]["width"], 1296)
        self.assertEqual(refine["8"]["inputs"]["denoise"], 0.35)

    def test_klein_build_graph_chains_refs(self):
        job = {"id": "j", "project_code": "p", "kind": "keyframe", "target": "comfy-klein", "prompt": "hi", "aspect": "3x4"}
        graph = worker.build_graph(job, 7, 0, None, None, PRESETS, ["openreel/j/ref0_a.png", "openreel/j/ref1_b.png"])
        self.assertNotIn("{{", json.dumps(graph))
        guider = graph["60"]["inputs"]
        self.assertEqual(guider["positive"], ["23", 0])
        self.assertEqual(guider["negative"], ["24", 0])
        self.assertEqual(graph["23"]["inputs"]["conditioning"], ["13", 0])
        self.assertEqual(graph["13"]["inputs"]["conditioning"], ["4", 0])
        self.assertEqual(graph["10"]["inputs"]["image"], "openreel/j/ref0_a.png")

    def test_klein_rejects_too_many_refs(self):
        with tempfile.TemporaryDirectory() as d:
            project, models = pathlib.Path(d) / "p", pathlib.Path(d) / "m"
            make_models(models)
            (project / "refs").mkdir(parents=True)
            for i in range(4):
                (project / "refs" / f"{i}.png").write_bytes(b"x")
            job = {"version": 1, "id": "j", "kind": "keyframe", "target": "comfy-klein", "shot": "S", "entity": "E",
                   "prompt": "p", "refs": [f"refs/{i}.png" for i in range(4)], "source": None, "aspect": "3x4",
                   "seeds": [1], "denoise": None, "outputs": ["shots/a.png"]}
            with self.assertRaises(worker.JobError):
                worker.validate_job(job, project, models, job_id="j")

    def test_status_and_discovery(self):
        _, first = make_job(self.project)
        second = first.with_name("cf-20261030-091300-cd34.json")
        second.write_text(first.read_text().replace("ab12", "cd34"))
        os.utime(first, (2000, 2000))
        os.utime(second, (1000, 1000))
        self.assertEqual(worker.pending_jobs(self.project), [second, first])
        worker.write_status(self.project, {"id": second.stem, "state": "running"})
        worker.write_status(self.project, {"id": first.stem, "state": "done"})
        self.assertEqual(worker.pending_jobs(self.project), [])
        worker.recover_interrupted(self.project)
        self.assertEqual(worker.read_status(self.project, second.stem)["error"], "interrupted")
        self.assertEqual(worker.read_status(self.project, first.stem)["state"], "done")
        self.assertEqual([p.name for p in worker.jobs_dir(self.project).glob(".*")], [])

    def test_run_keyframe_job(self):
        job, path = make_job(self.project)
        status = self.run_it(path)
        self.assertEqual(status["state"], "done", status)
        self.assertEqual(status["outputs"], job["outputs"])
        for name in job["outputs"]:
            self.assertTrue((self.project / name).is_file())
        self.assertEqual(status["records"][0]["seed"], 44)
        self.assertEqual(status["records"][0]["width"], 32)
        self.assertEqual(list(self.project.rglob(".cf-*")), [])
        backups = list((self.comfy / "output/openreel/proj" / job["id"]).glob("*.json"))
        self.assertEqual(len(backups), 2)
        self.assertEqual(json.loads(backups[0].read_text())["job"], job["id"])

    def test_run_refine_job_copies_source(self):
        Image.new("RGB", (864, 1152)).save(self.project / "src.png")
        job, path = make_job(self.project, kind="refine", target="comfy-refine", denoise=0.3,
                             source="src.png", seeds=[3], outputs=["up.png"])
        status = self.run_it(path)
        self.assertEqual(status["state"], "done", status)
        graph = self.server.graphs[0]
        self.assertEqual(graph["11"]["inputs"]["image"], f"openreel/{job['id']}/src.png")
        self.assertEqual((graph["12"]["inputs"]["width"], graph["12"]["inputs"]["height"]), (1296, 1728))
        self.assertFalse((self.comfy / "input/openreel" / job["id"]).exists())

    def test_unreachable_and_invalid_send_nothing(self):
        _, path = make_job(self.project)
        status = self.run_it(path, "http://127.0.0.1:9")
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["error"], "ComfyUI unreachable at 127.0.0.1:9")
        _, bad = make_job(self.project, version=3)
        bad.rename(bad.with_name("cf-20261030-091200-ff00.json"))
        self.assertEqual(self.server.graphs, [])

    def test_partial_failure_keeps_first_output(self):
        (self.project / "shots/S001").mkdir(parents=True)
        job, path = make_job(self.project)
        original = worker.render_one
        def second_appears(*args):
            result = original(*args)
            (self.project / job["outputs"][1]).write_bytes(b"late")
            return result
        worker.render_one = second_appears
        self.addCleanup(setattr, worker, "render_one", original)
        status = self.run_it(path)
        self.assertEqual((status["state"], status["error"], status["outputs"]), ("failed", "output exists", [job["outputs"][0]]))
        self.assertEqual((self.project / job["outputs"][1]).read_bytes(), b"late")

    def test_main_once(self):
        job, path = make_job(self.project)
        old = worker.run_job
        worker.run_job = lambda p, proj, server: old(p, proj, server, self.comfy, self.models)
        self.addCleanup(setattr, worker, "run_job", old)
        self.assertEqual(worker.main(["--project", str(self.project), "--once", "--server", self.url]), 0)
        self.assertEqual(worker.read_status(self.project, job["id"])["state"], "done")


if __name__ == "__main__":
    unittest.main()

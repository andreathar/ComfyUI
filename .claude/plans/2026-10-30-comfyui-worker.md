# ComfyUI Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `studio/worker.py`, a polling process that runs openreel ComfyUI job files and writes status files and images back into the project folder.

**Architecture:** One module with small pure functions (validate, build graph, status IO) and one `run_job` that talks to ComfyUI over HTTP. It reuses `studio/shot.py` helpers (`load_template`, `fill`, `post`) and the presets, but writes its own sidecar because `shot.render` hardcodes `refs/<project>/index.jsonl`.

**Tech Stack:** Python stdlib (`urllib`, `json`, `unittest`), PIL 12.3.0 (image size), existing `studio/templates/*.json`.

**Spec:** `.claude/specs/2026-10-30-comfyui-worker-design.md`; job contract: `/mnt/data/Projects_SSD/openreel-video/docs/superpowers/specs/2026-10-30-comfyui-jobs-design.md` (it wins on any disagreement).

## Global Constraints

- Run Python as `.venv/bin/python`; tests are unittest (no pytest in the venv): `.venv/bin/python -m unittest discover -s studio -p test_worker.py`
- Only new files under `studio/` plus additive edits to `studio/presets.json` and `studio/README.md`; no upstream file is touched.
- Never edit `production.json`, never retry a job, never overwrite an existing output, never download models.
- Job files `<project>/jobs/comfy/*.json` (not `*.status.json`); status `<id>.status.json` written via temp file + `os.replace`.
- Output temp files are `<dir>/.cf-<jobid>-<n>.part`, renamed to the exact `outputs[n]`.
- Source images are copied (not symlinked) into `input/openreel/<job id>/`: `folder_paths.is_within_directory` uses realpath and rejects links leaving `input/`.
- Model files: `models/unet/`, `models/clip/`, `models/vae/`, `models/checkpoints/`.
- Refine size: source × 1.5, each side rounded to a multiple of 16, long side capped at 2048.
- Failure messages exactly: `ComfyUI unreachable at <host:port>`, `missing models/<dir>/<file>`, `interrupted`, `output exists`.
- Do not commit `api_server/utils/file_operations.py`; do not push.
- Before the manual run: check port 8188, RAM and VRAM (6 GiB GPU shared with Argon).

## Review Focus

- Source path is a symlink pointing outside the project: job fails validation, nothing copied.
- `outputs[n]` already exists (partial earlier run): fail `output exists`, earlier outputs stay listed.
- Worker killed mid-job: next start marks the `running` status `failed: interrupted`, never re-runs it.
- Source image smaller than 16 px or already above the 2048 cap: refine size stays valid (min 16, cap respected).
- ComfyUI down at start or mid-job: `failed: ComfyUI unreachable at ...`, no traceback, loop keeps polling.

---

### Task 1: Aspect `3x4` and refine template

**Files:**
- Modify: `studio/presets.json` (aspects)
- Create: `studio/templates/z-image-refine.json` (copy of `z-image-i2i.json`; node 7 `VAEEncode` → `VAEEncodeTiled`, node 9 `VAEDecode` → `VAEDecodeTiled`, tile_size 512, overlap 64, temporal_size 64, temporal_overlap 8; keep node 12 `ImageScale` with `{{width}}`/`{{height}}`)
- Test: `studio/test_worker.py`

**Interfaces:**
- Produces: aspect key `3x4` = z-image `[864,1152]`, sd15 `[384,512]` in the same shape as existing aspects; template name `z-image-refine` with variables `reference, width, height, denoise, output, prompt, seed` plus the model fields of `z-image-i2i`.

- [ ] **Step 1: Write failing tests** in `studio/test_worker.py`: `test_aspect_3x4_present` asserts the two sizes above from `presets.json`; `test_refine_template_fills` fills `z-image-refine` the same way `test_every_template_fills_from_its_model_preset` does (copy its filler approach) and asserts node classes include `VAEEncodeTiled` and `VAEDecodeTiled` and no `{{` remains.
- [ ] **Step 2:** Run `.venv/bin/python -m unittest discover -s studio -p test_worker.py`. Expected: FAIL (aspect missing, template file missing).
- [ ] **Step 3:** Add the aspect and the template (check `nodes.py:348/399` for the tiled nodes' required inputs).
- [ ] **Step 4:** Re-run. Expected: PASS; also run `test_shot.py` to confirm nothing regressed.
- [ ] **Step 5:** Commit `studio/presets.json studio/templates/z-image-refine.json studio/test_worker.py` — "Add 3x4 aspect and z-image-refine template".

### Task 2: `validate_job`

**Files:** Create `studio/worker.py`; Test `studio/test_worker.py`

**Interfaces:**
- Produces: `class JobError(Exception)`; `validate_job(job: dict, project: Path, models_root: Path) -> None` raising `JobError(<message>)`.

- [ ] **Step 1: Write failing tests**, each using a temp project dir: valid keyframe job passes; `version: 2` fails; `kind: refine` with `target: comfy-zimage` fails (and the reverse); `len(seeds) != len(outputs)` fails; refine `denoise` 1.5 fails; output path `../x.png` fails; `source` symlink escaping the project fails; missing `source` fails; existing output fails with message `output exists`; missing unet file fails with `missing models/unet/z_image_turbo_bf16.safetensors` (models_root is a temp dir).
- [ ] **Step 2:** Run; Expected: FAIL (module missing).
- [ ] **Step 3:** Implement `validate_job` and `JobError` in `studio/worker.py`. Containment check: `Path.resolve()` of every path in `refs`/`source`/`outputs` must be inside `project.resolve()`. Model-file check maps target → preset (`comfy-zimage`/`comfy-refine` → `z-image-turbo`, `comfy-sd15` → `sd15`) and the dir table in Global Constraints.
- [ ] **Step 4:** Run; Expected: PASS.
- [ ] **Step 5:** Commit "Add worker job validation".

### Task 3: `refine_size` and `build_graph`

**Files:** Modify `studio/worker.py`; Test `studio/test_worker.py`

**Interfaces:**
- Consumes: `shot.load_template(name)`, `shot.fill(node, values)`, presets from `studio/presets.json`.
- Produces: `refine_size(width: int, height: int) -> tuple[int, int]`; `build_graph(job: dict, seed: int, n: int, source_name: str | None, size: tuple[int, int] | None, presets: dict) -> dict` (filled ComfyUI API graph; `output` prefix is `openreel/<job id>/<n>`).

- [ ] **Step 1: Write failing tests**: `refine_size(864,1152)` == `(1296,1728)`; `refine_size(1344,768)` == `(2016,1152)` (under the cap); `refine_size(1536,1024)` has `max(w,h) == 2048`, both sides multiples of 16, aspect ratio within 2%; `refine_size(10,10)` == `(16,16)`; `build_graph` for `comfy-zimage` uses the `3x4` aspect size and the given seed; for `comfy-sd15` carries the sd15 negative prompt; for `comfy-refine` contains `VAEEncodeTiled` and the job `denoise`.
- [ ] **Step 2:** Run; Expected: FAIL.
- [ ] **Step 3:** Implement both. `refine_size`: scale by 1.5, shrink to cap if needed, round each side to nearest multiple of 16 with floor 16. `build_graph`: pick template by target (`z-image-t2i`, `sd15-t2i`, `z-image-refine`), fill from the preset model fields plus aspect size.
- [ ] **Step 4:** Run; Expected: PASS.
- [ ] **Step 5:** Commit "Add worker graph building".

### Task 4: Status IO, discovery, startup recovery

**Files:** Modify `studio/worker.py`; Test `studio/test_worker.py`

**Interfaces:**
- Produces: `write_status(project: Path, status: dict) -> None` (temp file + `os.replace`, sets `updatedAt`); `read_status(project: Path, job_id: str) -> dict | None`; `pending_jobs(project: Path) -> list[Path]` (oldest mtime first, excludes `*.status.json`, excludes jobs whose status is `running`/`done`/`failed`); `recover_interrupted(project: Path) -> None` (every `running` status → `failed`, `error: "interrupted"`).

- [ ] **Step 1: Write failing tests**: write/read round trip leaves no `.tmp` file; `pending_jobs` ordering with two jobs of different mtime; done job and `*.status.json` files excluded; `recover_interrupted` turns `running` into `failed: interrupted` and leaves `done` alone.
- [ ] **Step 2:** Run; Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run; Expected: PASS.
- [ ] **Step 5:** Commit "Add worker status handling".

### Task 5: `run_job` against a fake ComfyUI

**Files:** Modify `studio/worker.py`; Test `studio/test_worker.py` (add `FakeComfy`: `http.server` on port 0 in a thread; `POST /prompt` returns `{"prompt_id": "p1"}` and records the graph; `GET /history/p1` returns an output entry for a `SaveImage` file; `GET /view` serves a small PNG made with PIL)

**Interfaces:**
- Consumes: Tasks 2–4 functions; `shot.post(server, path, data)` for `/prompt`.
- Produces: `run_job(job_path: Path, project: Path, server: str, comfy_root: Path, repo_root: Path, models_root: Path) -> None` (never raises for job-level failures; writes status).

- [ ] **Step 1: Write failing tests**: keyframe with 2 seeds → status `done`, two outputs exist at exact paths, `records` has seed/model/width/height/promptId, backup copies exist under `output/openreel/<project code>/<job id>/` with sidecar; refine → source copied to `input/openreel/<id>/` during the run and removed after; no `.cf-*.part` left behind; server closed → status `failed` with `ComfyUI unreachable at 127.0.0.1:<port>`; second output pre-existing → `failed: output exists`, first output kept and listed; invalid job → `failed` with validation message and no request sent to the fake.
- [ ] **Step 2:** Run; Expected: FAIL.
- [ ] **Step 3:** Implement: validate → status `running` → for each output build graph, submit with `client_id`, poll `/history/<id>` (1 s interval, 30 min cap), fetch image via `/view`, write `.part` then `os.replace` to the output, copy to backup dir plus sidecar JSON line, append record; map `URLError`/`OSError` to the unreachable message and `ValueError` from `shot.post` to its own message; `finally` removes the copied source dir; final status `done` with `seconds`.
- [ ] **Step 4:** Run; Expected: PASS.
- [ ] **Step 5:** Commit "Add worker run_job".

### Task 6: CLI, docs, manual run

**Files:** Modify `studio/worker.py` (`main`), `studio/README.md`

**Interfaces:**
- Produces: `main(argv: list[str] | None = None) -> int` with `--project` (required), `--once`, `--server` (default `http://127.0.0.1:8188`); loop sleeps 3 s between scans; `--once` processes everything pending and exits 0.

- [ ] **Step 1: Write failing test** `test_main_once_processes_pending_job` using `FakeComfy` and a temp project; asserts exit code 0 and the status file `done`.
- [ ] **Step 2:** Run; Expected: FAIL.
- [ ] **Step 3:** Implement `main` (call `recover_interrupted` once at start; Ctrl-C exits cleanly). Document usage and the job/status contract in `studio/README.md`.
- [ ] **Step 4:** Run the full suite (`discover -s studio -p "test_*.py"`). Expected: PASS.
- [ ] **Step 5:** Commit "Add worker CLI and docs".
- [ ] **Step 6 (manual, ask first):** Check port 8188, RAM, VRAM; launch `.codex/launch.sh`; run the worker with `--once` on a throwaway project containing one `comfy-zimage` and one `comfy-refine` job; record peak VRAM/RAM for the refine in `studio/README.md`. This needs the models already present; do not download any.

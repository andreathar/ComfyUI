# ComfyUI worker for openreel jobs

The job contract (files, fields, names, status, failures) is owned by
openreel: `/mnt/data/Projects_SSD/openreel-video/docs/superpowers/specs/2026-10-30-comfyui-jobs-design.md`.
This spec covers only the worker that executes those jobs here. If the
two disagree, the openreel spec wins and this one is fixed.

## 1. Scope

- New `studio/worker.py` and `studio/test_worker.py`.
- Reuses `studio/shot.py` helpers (`load_template`, `fill`, `post`) and
  `studio/presets.json` models and aspects.
- No changes to ComfyUI core, `comfy/`, nodes or the server. The worker
  is a client of the local HTTP API, like `shot.py`.
- `shot.py` keeps working for sheet-based renders. Its prompt pattern and
  looks stay available as a prompt helper but are not used by the worker:
  job prompts are final.

## 2. Running

```
python studio/worker.py --project /path/to/openreel-project [--once] [--server http://127.0.0.1:8188]
```

- Polls `<project>/jobs/comfy/*.json` (not `*.status.json`) every 3 s and
  picks jobs with no status file, oldest file first.
- Runs one job at a time: 6 GiB VRAM cannot hold two Z-Image renders.
- `--once`: process the jobs that are waiting, then exit (tests, CLI).
- On start, any job whose status is `running` is set to
  `failed: interrupted`.
- Logs one line per job state change to stdout.

## 3. Per job

1. **Validate** before anything is rendered or written:
   - `version == 1`, known `kind` and `target`, `kind`/`target` pairing
     (`refine` ⇔ `comfy-refine`);
   - `len(seeds) == len(outputs)`; `denoise` in 0–1 for refine;
   - every path in `refs`, `source` and `outputs` resolves (following
     symlinks) inside the project folder; `source` exists; no output
     exists yet;
   - model files for the target exist under `models/`.
   Any failure writes `failed` with the reason.
2. **Status** `running`.
3. **Build the graph** per output, filling the existing templates:

   | target | template | size |
   |---|---|---|
   | `comfy-zimage` | `z-image-t2i` | `presets.aspects[aspect]["z-image"]` |
   | `comfy-sd15` | `sd15-t2i` | `presets.aspects[aspect]["sd15"]` |
   | `comfy-refine` | new `z-image-refine` | source size × 1.5, rounded to 16, long side capped at 2048 |

   `presets.json` gains aspect `3x4`: z-image 864×1152, sd15 384×512.
   `z-image-refine` is `z-image-i2i` with `ImageScaleBy` before encoding
   and tiled VAE encode/decode, so the larger image fits in 6 GiB.
   Peak VRAM and time are measured before the size cap is final.
4. **Inputs**: `source` is symlinked into `input/openreel/<job id>/`
   (removed after the job) so ComfyUI reads it in place without a copy.
   `refs` are not used by the graph in v1.
5. **Submit** to `/prompt` with a `client_id` (keeps the upstream
   headless deploy-to-cloud marker off), then poll `/history/<id>`.
   ComfyUI's error message is stored on failure.
6. **Write outputs**: ComfyUI saves into `output/openreel/<project
   code>/<job id>/` as the backup copy, with the same sidecar record
   format `shot.py` writes. The worker copies each image to
   `<project>/<dir>/.cf-<job id>-<n>.part` and renames it to the exact
   `outputs[n]` path. Nothing else is written into `shots/` or `refs/`.
   After each output, the status `outputs` list is updated.
7. **Status** `done` with `seconds` and `records`.

Status files are written to a temporary file in `jobs/comfy/` and
renamed, so openreel never reads a partial status.

## 4. Never

- Edit `production.json`.
- Retry a job, or render a job that already has a status file.
- Overwrite an existing file in the project.
- Download models.

## 5. Testing

`studio/test_worker.py` (pytest, no GPU, fake ComfyUI server in-process):

- validation: each rejection reason in §3.1, including `../` and symlink
  escapes;
- graph building: each target and aspect produces the expected sizes,
  seeds and prompt in the filled template;
- refine size rounding and the 2048 cap;
- outputs renamed atomically; no `.part` left behind on success or
  failure; existing output not overwritten;
- startup turns `running` into `failed: interrupted`;
- a job with a status file is skipped.

Manual end to end on this machine: the run described in the openreel
spec §6, with peak VRAM and RAM recorded in this spec.

## 6. Decisions (2026-10-30)

1. The worker stays outside ComfyUI core: a local API client under
   `studio/`, so upstream merges are unaffected.
2. No sidecars in the project folder; metadata goes into the status file
   and the backup copy in `output/`.
3. Refine uses Z-Image img2img after a 1.5× scale, with no new upscale
   model in v1. An ESRGAN-type upscaler is a later, approved download.

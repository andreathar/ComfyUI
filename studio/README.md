# Studio

Shot specs in, categorized and tagged reference stills out, rendered by the
local ComfyUI server. Local to this fork; upstream has no `studio/` folder.

## Where things live

| What | Where |
| --- | --- |
| Reference images (plates, character refs) | `input/refs/<project>/...` |
| Shot specs and sheets | `studio/shots/<project>-<scene>.json` |
| Model settings, aspects, looks, naming patterns | `studio/presets.json` |
| API graphs with `{{variables}}` | `studio/templates/<family>-{t2i,i2i}.json` |
| Renders | `output/refs/<project>/<scene>/<shot>/<scene>-<shot>_<model>_<aspect>_s<seed>_00001_.png` |
| Per-image tags and provenance | same path, `.json` sidecar |
| Project index (one line per image) | `output/refs/<project>/index.jsonl` |

## Start here

- [Film preparation and take tracking](docs/FILM_AUTOMATION.md) and [Context Loop run records](docs/H3_LOOP_RUN.md) cover the two execution paths.
- [Master Movie Studio](docs/MASTER_MOVIE_STUDIO_GUIDE.md) covers the current visible production canvas.
- [Review agent instructions](docs/STUDIO_REVIEW_AGENT.md) define the pre-tuning review scope and verification gates.
- [Workflow review](workflow-review/START_HERE.md) is a dated qualification/evidence collection, not an active project or training corpus.

## Local reference intake

Use [Local reference intake with Hermes and Qwen](docs/LOCAL_ASSET_WORKER.md)
for read-only inventory, optional local image classification, and reviewed copies
into `input/refs/<project>/`. It does not rename existing workflow inputs.

## Workflow health

After saving or changing a workflow, refresh the local report with ComfyUI running:

```sh
python studio/workflow_health.py
```

This scans saved workflows, the default graph, and Studio templates into
`user/workflow-health.json`. It checks installed nodes, choices, and link
endpoints without queuing work, downloading models, or calling external APIs.
It runs on demand, not as a background monitor.

`preflight_pass` is not a render test; `needs_inputs` marks unresolved templates.
Runtime receipts from local history match exact graph settings and survive later
report refreshes. UI receipts require a matching API graph; unsupported subgraphs
or bypasses retain related-run evidence without claiming a verified UI mapping.
`success` means every output was targeted without an execution or explicit node
error; `partial_success` means only some outputs were targeted.
Receipts do not certify image quality, unchanged model weights, or current
credentials. Exit status is nonzero for preflight failures or matched runtime
errors; unverified workflows remain explicitly unverified.

## Shot sheet

Top-level fields are shared; each entry in `shots` overrides them.

```json
{
  "project": "argon-demo", "scene": "s01", "look": "neon-night", "tags": ["night"],
  "location": "rain-soaked neon alley",
  "shots": [
    {"shot": "010", "shot_size": "wide", "subject": "a lone courier", "aspect": "2.39x1"},
    {"shot": "020", "shot_size": "close-up", "subject": "a lone courier", "seeds": [44, 45],
     "reference": "refs/argon-demo/plate.png", "denoise": 0.5}
  ]
}
```

- Required: `project`, `scene`, `shot` (lowercase slugs) and `subject`.
- Prompt fields: `shot_size`, `camera`, `subject`, `action`, `location`,
  `lighting`, `look` (preset name or free text), `lens`. Empty fields are
  dropped from `prompt_pattern`.
- `model`, `aspect`, `seeds`, `tags` default from `presets.json`. Any model
  setting (`steps`, `cfg`, `sampler`, `scheduler`, `shift`, `denoise`) can be
  overridden per shot.
- `reference` (path under `input/`) switches the shot to the image-to-image
  template.

## Run

Start the server with `.codex/launch.sh`, then:

```bash
.venv/bin/python studio/shot.py studio/shots/argon-demo-s01.json --dry-run
.venv/bin/python studio/shot.py studio/shots/argon-demo-s01.json --only 020
PYTHONPATH=studio .venv/bin/python -m unittest discover -s studio/tests -p test_shot.py
```

The PNG keeps ComfyUI's native `prompt` metadata for Argon; the sidecar adds
the model files' SHA-256 and license from `.codex/models.json`. Import into
Argon stays manual.

## H3 encode preflight

`studio/h3_manifest.py` checks an explicit version-1 manifest containing an API
`graph`, `stage_save_node`, versioned `recipe`, committed `prompt_text`,
`continuation: false`, source frame/dimension expectations, and hashed `assets`
and `software` files. Asset bindings use `node.input` or
`node.media.index.file` / `node.media.index.mask`, each with `selected`, `path`
and `sha256`. Paths resolve relative to `--root`; model paths may be explicitly
absolute. Use only trusted local manifests: the checker reads their declared files.

```bash
.venv/bin/python studio/h3_manifest.py <manifest.json> [--root /path/to/ComfyUI]
PYTHONPATH=studio .venv/bin/python -m unittest discover -s studio/tests -p test_h3_manifest.py
```

This supports the direct Fantastic REF-mode, picture-plus-masked-video encode
recipe only. It hashes the encode dependency closure, not sampler branches, and
prints JSON without queuing work or writing files. A successful check validates
configuration/content identities, not decoded media or effective tensor shapes.
Stage receipts are compared but **reuse remains blocked** until actual ComfyUI
model search-path resolution and trusted encode provenance are integrated.
An exit code of zero does not mean an existing stage can be sampled safely.

### Decoded H3 media validation

`studio/h3_media_validate.py` independently verifies prepared source pixels,
repeat-last video padding, frame counts/timestamps, guard video/NPY agreement,
audio samples and optional final lossless protected-pixel/audio equality.
It uses the compositor's PyAV resize path and native RGB16, not lossy MP4/RGB8.

```bash
.venv/bin/python studio/h3_media_validate.py <contract.json> [--root /path/to/ComfyUI]
PYTHONPATH=studio .venv/bin/python -m unittest discover -s studio/tests -p test_h3_media_validate.py
```

The version-1 contract contains `source` expectations (`delivery_frames`,
`working_frames`, `width`, `height`, `fps`, `sample_rate`, `channels`),
`guard_padding_policy` (`repeat_last` or explicitly `tracked`), and `assets`.
Each asset has `path` and `sha256`; roles are `original` (prepared source clip,
not the full film), `working`, `guard`, `guard_array`, `audio`, and optional
`final`. Paths are trusted local declarations, relative to `--root` or absolute.
Tracked padding drift is reported, never silently treated as repeated masks.
The checker prints JSON, writes nothing, and does not approve segmentation,
original-film alignment, likeness or performance. Neither checker is wired into
live nodes or the batch driver.

## Worker (openreel jobs)

`studio/worker.py` runs the job files openreel writes to
`<project>/jobs/comfy/*.json`. The contract is owned by openreel
(`docs/superpowers/specs/2026-10-30-comfyui-jobs-design.md`); the worker
design is `.claude/specs/2026-10-30-comfyui-worker-design.md`.

```bash
.venv/bin/python studio/worker.py --project /path/to/openreel-project [--once] [--server http://127.0.0.1:8188]
PYTHONPATH=studio .venv/bin/python -m unittest discover -s studio/tests -p test_worker.py
```

- One job at a time, oldest first; a job with a status file is never re-run.
- Status goes to `jobs/comfy/<id>.status.json`; a `running` status found at
  start becomes `failed: interrupted`.
- Refine copies its source to `input/openreel/<id>/` for the run (a symlink
  would be rejected by ComfyUI) and renders at 1.5x, rounded to 16, long side
  capped at 2048, with tiled VAE.
- Backup copies and metadata sidecars go to `output/openreel/<project folder name>/<id>/`.
- Measured 2026-10-30 on the RTX 3060 6 GiB with the server already warm: keyframe 864x1152 35 s, peak 5.2 GiB VRAM (whole GPU); refine to 1296x1728 76 s, peak 5.1 GiB VRAM, 1.7 GiB system RAM free at the lowest.

### Targets and reference conditioning

| Target | Model | Notes |
|---|---|---|
| `comfy-zimage` | Z-Image Turbo | text only; refs are recorded, not used |
| `comfy-sd15` | SD 1.5 | draft quality |
| `comfy-refine` | Z-Image + tiled VAE | upscale and detail pass on `source` |
| `comfy-klein` | FLUX.2 klein 4B GGUF Q4_K_M | up to 3 `refs` condition the image (identity follows the refs); 864x1152 in ~40 s, ~3.5 GiB VRAM |

Use one ref for close-ups and three for profile or wide shots. References fix identity, not
expression or wardrobe, so describe those in the prompt. Models come from catalogue profile
`flux2-klein-4b` (`.codex/models.json`).

## Offline regression checks

Run the full studio suite from the ComfyUI root:

```bash
.venv/bin/python -m pytest studio/tests -q
```

Production validation and prompt generation use the versioned files in
`studio/specs/production/`. Keep those runtime resources with the studio code.

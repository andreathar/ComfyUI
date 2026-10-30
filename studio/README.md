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
.venv/bin/python -m unittest discover -s studio -p test_shot.py
```

The PNG keeps ComfyUI's native `prompt` metadata for Argon; the sidecar adds
the model files' SHA-256 and license from `.codex/models.json`. Import into
Argon stays manual.

## Worker (openreel jobs)

`studio/worker.py` runs the job files openreel writes to
`<project>/jobs/comfy/*.json`. The contract is owned by openreel
(`docs/superpowers/specs/2026-10-30-comfyui-jobs-design.md`); the worker
design is `.claude/specs/2026-10-30-comfyui-worker-design.md`.

```bash
.venv/bin/python studio/worker.py --project /path/to/openreel-project [--once] [--server http://127.0.0.1:8188]
.venv/bin/python -m unittest discover -s studio -p test_worker.py
```

- One job at a time, oldest first; a job with a status file is never re-run.
- Status goes to `jobs/comfy/<id>.status.json`; a `running` status found at
  start becomes `failed: interrupted`.
- Refine copies its source to `input/openreel/<id>/` for the run (a symlink
  would be rejected by ComfyUI) and renders at 1.5x, rounded to 16, long side
  capped at 2048, with tiled VAE.
- Backup copies and metadata sidecars go to `output/openreel/<project folder name>/<id>/`.
- Measured 2026-10-30 on the RTX 3060 6 GiB with the server already warm: keyframe 864x1152 35 s, peak 5.2 GiB VRAM (whole GPU); refine to 1296x1728 76 s, peak 5.1 GiB VRAM, 1.7 GiB system RAM free at the lowest.

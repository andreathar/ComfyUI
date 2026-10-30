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

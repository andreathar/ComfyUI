# H3 tools: useful paths and current limits

This pass continues the ComfyUI-only workspace plan. Slow local workflows remain candidates (**Patient** preference); swap-quality work stays paused.

## What to use now

| Tool | Purpose | Qualification |
| --- | --- | --- |
| **03 → Project Hub - Browse Existing (no generation)** | Open the existing H3 clip-project panel | Previously browser-verified. Current project-list/state endpoints respond. Keep this as the project entry point. |
| **02 → H3 three-view comparison** | Preserve the existing experiment and its settings | All node types and the seven checked loader selections are advertised by the running backend. This is dependency availability, not proof of generation quality or resource safety. Not a daily preset. |
| **02 → Stage 1 Encode / Stage 2 Sample** | Preserve the split encode/sample experiment | Checked loader selections are available. Both retain two unregistered Claude nodes, but those nodes are muted (`mode=2`) with no output links. Do not install a paid provider merely to remove their warnings. |
| **02 → video_minimax_h3_i2v** | Candidate for new motion rather than swapping | Its embedded subgraph resolves to registered nodes. The selected `minimax_h3_fl2va_pruned_int8_convrot.safetensors` is **not advertised** by the running UNET loader. Keep experimental until the exact model path is qualified. Do not substitute the ref2va model merely because it is available. |
| **03 → H3 Project Suite - Prompt Builder AIO** | Reference for future chain wiring | Still has unregistered rgthree switch/bypasser types. Do not promote or reinstall packs just to make this large example open cleanly. |
| **03 → Andre shot-review graphs** | Existing preparation/review entry points | **Not passive review.** `AndreShotSwapPrepare.execute` starts background H3 import for unprocessed shots. Keep review-required; do not queue merely to inspect footage. |

Missing-backend-node checks exclude frontend-only notes, reroutes, Set/Get and embedded subgraph identifiers. A UUID-shaped subgraph type is not itself a missing extension.

## Project and control ownership

The live project API returned **12 existing projects**, all with `auto_approve=false` and `chain_active=false`. Four have one recorded clip each; the other eight have none. No project was created, approved, rejected, imported, exported or modified.

Use the existing Hub/project panel for clip review and chain state, not a second production database. Its controls are not all passive: approve/reopen/branch/import/export/cleanup change project state or produce files. In particular, a pending clip is not an approved continuation context.

For an eventual useful generation canvas:

- Preserve an existing project's dimensions. The Hub already owns width/height outputs and rejects contradictory dimensions.
- Keep native loaders as the source of model objects. KJ Set/Get only distribute graph-local values; they do not offload weights.
- Keep manual review on. Do not approve a pending clip to make continuation appear ready.
- Wire optional video/audio VAEs only when enabling a deliberately tested import path. A browse-only Hub does not need them.
- Do not add H3 Controls / Models groups to an unqualified graph solely for visual consistency.

## Checks performed in this pass

- Read-only GETs against the running server: `/object_info`, `/queue`, `/h3_suite/projects`, and each project's `/h3_suite/project/state`.
- Examined all eight video/project graphs, expanding the native i2v embedded subgraph for type checks.
- Compared 22 standard loader selections in the four video graphs against the running loader's choices: 21 advertised, one absent. This does not hash model files or test loading them.
- Ran the extension's standalone `tests/project_probe.py`: **all 18 numbered project-lifecycle checks passed**, using its temporary fixture directory rather than the user's projects. This is a fixture contract test, not an end-to-end render test.
- The queue was empty when observed. No graph was submitted; no model loaded, download, install, paid request, restart or manual unload was requested.
- `pytest` is not installed in the project venv. Nothing was installed to obtain it; the existing standalone probe runs without it.

Receipts: `.codex/artifacts/h3-tools-qualification-20261110/live-readonly.json`, `model-selections.json`, and `project-probe.log`.

## Import/continuation blockers verified in source

These are static findings, not reproduced live imports:

- `custom_nodes/ComfyUI-H3-Project-Suite/import_source.py:475-481` saves `"audio": audio_lat if audio_lat is not None else video_lat`. A silent import can therefore label a video tensor as audio. `custom_nodes/ComfyUI-H3-Project-Suite/nodes.py:261-274` expects an audio stream with shape `[B,C,2,T]` and rejects other ranks. Do not treat a successfully written silent-import file as qualified AV continuation context.
- `custom_nodes/comfyui-andre-shot-swap/__init__.py:44-56` invokes `service().start(job["id"], "continue_in_h3")` after preparation. `custom_nodes/comfyui-andre-shot-swap/andre_swap/service.py:333-386` selects every unprocessed shot when no index is supplied and submits work to an executor. The saved review graph is not a harmless metadata preview.
- The handoff uses `with_audio=False, width=0, height=0` in `custom_nodes/comfyui-andre-shot-swap/andre_swap/h3_handoff.py:85-111`: it is neither a sound-preserving import nor a guaranteed small-resolution path.

No extension code was changed during this organization pass. These paths should be corrected and fixture-tested before any automatic import/continuation qualification, rather than worked around in a canvas.

## Next bounded work

1. Keep the small Hub as the useful project surface.
2. **Done in the following pass:** [bounded local clip review](LOCAL_CLIP_REVIEW_2026-11-10.md) is available under **05 - Video Review**. It now uses native `VHS_LoadVideoFFmpeg` upload/selection controls with no VAE or typed path; the embedded player is hidden/paused, with its lifecycle fixed to avoid hidden preview requests. Browser roundtrip and a 24-frame, 512×288 decode passed. No such minimal graph existed at the initial qualification.
3. Resolve and fixture-test the silent-import AV contract before import → manual approval → continuation. Do not approve existing clips just to enable a chain.
4. Separately qualify the native new-motion example's exact model selection before adding H3 generation controls.

Do not delete active providers or shared weights based on this availability check. No additional model or extension is approved for download by this report.

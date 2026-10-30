# Convergent production strategy: Kling, Higgsfield, ComfyUI, Openreel

Status: DRAFT for user review. Nothing here has been implemented in openreel-video.
Sources: four read-only agent reports (kling.md, higgsfield.md, comfy.md, openreel.md in the session
scratchpad). Their claims are unverified against code unless marked; verify before building on them.

## 1. Flow

1. Script plus movie settings (style bible, aspect, genre) -> `planProduction` builds the manifest.
2. Openreel builds the timeline (placeholder clips, one undoable edit) and a **task list**: every predicted
   production task, each tagged with one responsible platform.
3. Tasks run in dependency order: voices and character sheets -> location images -> start/end frames ->
   video takes -> audio/lipsync -> edit.
4. Every output is registered back by its task id and a fixed file name. Paid generations need explicit approval.

## 2. Routing table (task type -> platform)

| Task | Platform | Tool / model | Notes |
|---|---|---|---|
| Character sheet, identity | Higgsfield | soul_2 / soul_cinematic + Soul ID (CLI training, 5-20 photos) | Soul ID works only with Soul image models |
| Character sheet, local draft | ComfyUI | comfy-klein (refs, free) | faces weaker than Soul; use for drafts and non-face consistency |
| Location / prop images | ComfyUI first, Higgsfield if quality needed | klein / Z-Image | free local first |
| Start and end frames | Higgsfield Soul (characters), ComfyUI (cheap drafts) | | |
| Keyframe variations, refine | ComfyUI | comfy-zimage, comfy-klein, refine | exists |
| Hero video, best quality | Kling | omni_ref_video v4 (3-30 s, 720/1080p, native audio) | most credits; draft at 720p |
| Video, cheap preview | Higgsfield Seedance 2.5 draft (480p) or Kling v3 turbo | | |
| Complex motion from phone clip | Higgsfield Genjutsu (hf_mult_motion_control) or Kling motion_control | needs one driving video | pick by test; limits unverified |
| Voice reference / clone | Higgsfield create_voice (Kling element can carry voice .mp3) | | per-character VOX entity |
| Dialogue TTS, dubbing, lipsync | Higgsfield (seed_audio, qwen_audio_tts, dubbing, sync_so) | | Kling has no lipsync tool |
| Pose / depth / cutout / interpolate / extract-frames | ComfyUI | core SDPose, Depth-Anything-3, RemoveBackground, FrameInterpolate | |
| Script, prompts, task planning | Claude / Codex subscription | via openreel agent skills | no API key |

## 3. Shared naming grammar (extends openreel naming.ts)

- Project code `<PROJ>` (<= 8 chars). Entity `<PROJ>-<KIND>-<SLUG>`, <= 32 chars total (Higgsfield limit; elements
  cannot be renamed or deleted, so names must be right at creation). Kinds: CHR, LOC, PRP, VOX, new MOT (motion ref).
- Shot `<PROJ>_S###_SH##`. Take `<shot>_<modeltag>_T##.<ext>` (unchanged, parser regex untouched).
- Refs `refs/<KIND>/<CODE>/<CODE>_NN.<ext>` plus variants `_sheet`, `_angle1`, `_voice`.
- Task id `<shot-or-entity>~TASKTYPE~platform`, e.g. `TH_S001_SH03~MOTION~hf`. Platform codes kl, hf, cf, cl (Claude/Codex).
  Task ids live only in the manifest and job files, never in media file names.
- ComfyUI saved workflows `<TARGETS key>__<kind>__vN.json`; template node titles prefixed `IN:`, `MODEL:`, `OUT:`;
  variables snake_case `{{...}}`.
- Existing platform elements (Higgsfield 7, Kling 6) use ad-hoc names; leave them, map them via the manifest.

## 4. Job contract

Generalize the existing Comfy contract to `jobs/<platform>/<id>.json` plus `<id>.status.json`
(status values queued/running/done/failed, plus `needs-approval` for paid platforms). `studio/worker.py` already
implements the `comfy` version. Paid platforms keep manual or agent-driven submission through `prod.mjs`, gated by a
credit estimate and an approval flag.

## 5. Shot-spec fields to add (union of platform needs)

target/model, tool, mode, duration, aspect, resolution, audio flag, dialogue/SFX, draft flag, imageCount,
start/end frame, keyframes, image/video/audio refs, element ids, soulId, voice id, motion source + direction,
timed beats, credit estimate, approved flag, generation/job id.

## 6. Openreel changes (spec only; not started)

1. Task object plus router and a task-list panel with per-task buttons (generate, approve, register output).
2. New targets: kling-motion-control, kling-v3 i2v/turbo, hf-seedance-2-5, hf-soul-cinematic, hf-motion-control.
3. MOT entity kind plus phone-clip registration; routing rule for complex moves.
4. Voice field on entities, voice-clone task, dialogue -> audio tracks, lipsync target.
5. Style-bible input for script generation.
6. `createComfyJob`, `registerRefFile`, `applyComfyStatus` (specified, unbuilt).
7. Credit estimate and approval gate before every paid task.

## 7. ComfyUI side

- Add job kinds beyond keyframe/variations/refine: character-sheet, location-sheet, face-detail, pose-extract,
  depth-extract, cutout, inpaint/outpaint, interpolate, extract-frames, caption.
- Extension hygiene (APPLIED 2026-10-30, measured). Method: each package loaded alone with
  `--disable-all-custom-nodes --whitelist-custom-nodes <pkg>` on a throwaway CPU instance (port 8199).
  All 38 packages together add only ~2.3 GB RSS; startup-time deltas were noise (cold-cache baseline).
  Heaviest: fill-nodes 368 MB, llm_party 368, qwen3-tts 208, reactor 184, Apt_Preset 177, Distorch 172,
  gguf-loader 138, qwen3-tts-comfyui 138, aiia 119, easy-use 110, QwenVL 109.
  No saved workflow or studio template uses any disabled package (only core + comfyui-gguf-loader).
  Moved 23 packages to `custom_nodes/.disabled/` (list in `.codex/disabled-extensions.txt`; undo = move back):
  API-key or paid-API packages (anthropic-claude, promptmodels, prompt-assistant, higgsfield-direct,
  sequencer, secrets, deno-custom-nodes, llm_party, fill-nodes), redundant (ComfyUI-GGUF shadowed by
  gguf-loader, both TTS packs because Higgsfield owns voice, both model managers because `--enable-manager`
  exists), and clutter or broken (WAS, Apt_Preset, arkennemasis, aiia, Element_easy, itools, lmstudio, d2-nodes,
  reactor). Kept 19: impact-pack, VHS, kjnodes, basic_data_handling, easy-use, rgthree, cg-use-everywhere,
  frame-interpolation, QwenVL, qwenmultiangle, z-image-power-nodes, nvidia_rtx_nodes, Distorch,
  memory_cleanup, gguf-loader, agent-panel, openbio-comfy-mcp.
  Verified: reduced profile boots with zero errors; node classes 4218 -> 2246; every class the studio templates
  need is present. Takes effect on the running server only after restart.
- Earlier "server RSS ~16 GiB" was wrong; it is 3.3 GB.

## 8. Open questions for the user

1. Approve this routing table and naming grammar as the standard?
2. Extension cull: test-then-disable in a copy, or leave as is?
3. Which openreel change first (suggest 1 + 6: task list and Comfy job registration)?
4. Genjutsu vs Kling motion control: run one cheap comparison on your phone clip?

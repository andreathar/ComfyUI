# Andre shot-by-shot character swap

Status: proposed design; not implemented or authorized for paid batch execution.

Read-only builder review completed: no additional material design questions.
User selected local vision. Existing Qwen3.5-4B Q4_K_M is validated for reviewed
draft descriptions; see `andre-local-vision-validation.md`. Implementation is
not started; no downloads or paid jobs were authorized by this validation.

## Intent

From a user-selected source video, detect and export its shots, describe each shot,
identify the intended male character, create an editable Kling edit prompt, replace
that character with Andre Athar Element `323525046658711`, and assemble the results
in their original order. Operate through ComfyUI without the sidebar agent.

Preserve source action, timing, pose, facial expression, head orientation, camera,
lighting and original audio. Carry forward the user's previous wardrobe choice:
Andre's reference outfit, with an explicit source-clothes alternative. This is an
assumption to show in the UI, not an interpretation of the ambiguous word
"flawless". Generative output cannot guarantee exact expressions or lighting;
result review remains separate from successful execution.

## Verified context

- The live preparation workflow has ten nodes, no shot detector or paid execution
  node. Its result and source are intact; preserve that tab and create a new one.
- This session's successful test used the official pinned Kling CLI 0.2.1,
  `omni_ref_video` / `kling-video-v3_0_omni`, with an image Element, 1080p,
  original sound, and one output. Evidence is under
  `.codex/artifacts/kling-dance-andre-20261107/`.
- Live native `KlingOmniProEditVideoNode` exposes reference images but no Element
  ID input, and uses Comfy auth. It is not the existing subscription/Element route.
- PySceneDetect, OpenCV and PyAV are installed in the project interpreter.
- `custom_nodes/anthropic-claude/anthropic_claude_node.py` accepts batched images,
  editable instructions, prompt templates and cached responses. Authentication
  and actual analysis performance have not been tested in this task.
- QwenVL source is installed, but no ready local analysis model was verified.
  Connected stats: 5.4 GiB free VRAM and 13.1 GiB free RAM at inspection; volatile.
- `studio/shot.py` owns reference-still jobs. This feature does not change it,
  Argon shot approval, core inference, global config, PATH, or shared providers.

## Approaches

1. Native partner nodes: less code, but a different billing/auth route and no
   exposed reusable Element ID. Does not preserve this task's established route.
2. Separate V3 custom node pack and narrow CLI worker: proposed. Retains the
   existing Kling connection and Element, with durable per-shot recovery.
3. Prompt presets only: simplest and avoids analysis inference, but does not
   satisfy the user's requested automatic shot descriptions.

The user chose video-aware automation and local analysis. Reuse the existing
Qwen3.5-4B Q4_K_M plus BF16 vision projector through LM Studio's loopback API.
No cloud analyzer fallback or implicit download. The model is suitable for
reviewed draft descriptions; sampled frames do not establish exact motion,
facial expression, identity, or gender. Saved runtime overrides must be surfaced.

## User flow

1. Select a source video, target Element, wardrobe policy, source-audio policy,
   and output resolution. Show existing connected account and model availability.
2. Prepare shots: probe media, detect cuts, show a numbered contact sheet and
   editable boundaries. Export non-destructive shot files with exact source ranges.
3. Analyze: explicitly run the chosen analyzer over timestamped samples from each
   shot. Return structured descriptions, visible action/expression, lighting,
   framing, target candidates, uncertainty, and draft prompts. Cache by media and
   settings hashes. Analysis may itself incur API cost and is labeled separately.
4. Review: select the intended male target per shot when ambiguous; choose
   replace, keep original, or exclude. Shots with no intended target retain the
   original. Exclusion is explicit because it changes total running time.
5. Generate reviewed shots: show immutable shot inputs/prompts/Element/model,
   number of submissions and available billing information. One explicit batch
   authorization covers that fixed list; no chat confirmation per unchanged shot.
6. Run serially, retrieve completed videos, and expose before/after playback.
   Reassemble in source order, using originals for explicitly kept shots and the
   original soundtrack. Save final video, individual shots, manifest and history.

Selecting a video, reopening results, changing layout, or pressing ordinary
preview/run must never implicitly approve spending. Explicit actions distinguish
Prepare, Analyze, Generate reviewed shots, Resume status, Reopen result, and Retry.

## Shot preparation and target ownership

Use PySceneDetect AdaptiveDetector for candidate hard cuts; threshold-based fade
detection is a separately surfaced aid. Flash frames, dissolves and rapid pans
may be ambiguous. Boundaries are editable; do not claim all transitions are found.
Retain frame indices and PTS/timebase, original fps, dimensions and source SHA256.
Decode/re-encode exact ranges for trims; do not rely on keyframe-only stream copy.
For VFR inputs retain a source-to-prepared timestamp map and disclose any required
CFR conversion. Never discard short shots solely to meet a detector minimum.

Sample opening, middle, ending and additional action frames per shot. The vision
model describes candidates and visible attributes; it is not an authoritative
identity or gender detector. It must not replace every man in group scenes or
assume the same actor across cuts. Ambiguous target selection stops that shot for
review. Preserve non-target people. A target is bound to reviewed shot-specific
descriptors and reference thumbnails, not only the words "the male character".

## Prompt contract

Each prompt binds the existing Element marker AND structured Element metadata.
Specify target location/appearance, identity and wardrobe role, source expression
and performance, camera/framing, lighting direction/color/shadows, background and
other people to preserve, and original-audio intent. Do not invent dialogue,
emotions, lighting sources or actions not supported by sampled evidence. Keep the
source as the base edit video. Reference syntax and flags come from live CLI
capabilities, not native-node syntax. Store the approved prompt unchanged.

## Duration, assembly and incomplete results

The previously verified base-video path declares 3–10 second inputs; rediscover
at use. Short shots need disclosed edge-frame padding and inverse trimming.
Long shots need a reviewed subdivision plan, with overlap/context where supported;
each extra generation and possible seam is visible before approval. Do not merge
unrelated shots or silently crop the user's scene to fit. Gradual transitions
require manual boundary review and are not promised seamless in version one.

Check returned fps, frames and duration against planned source ranges. Only
explicitly declared boundary trimming/padding is automatic; larger mismatches go
to review rather than speeding action or stretching dialogue. Preserve original
audio at assembly from the source timeline; do not concatenate independent lossy
audio chunks when the source track can be remuxed. Excluded ranges require an
explicit audio edit map. Keep output color metadata where supported; do not
automatically grade over a provider lighting mismatch.

Failed, ambiguous or missing shots remain visible. Do not export a file labeled
complete while silently replacing failed swaps with originals. An incomplete
review export must label its gaps and requires explicit user selection.

## Ownership, persistence and paid execution

Proposed new pack: `custom_nodes/comfyui-andre-shot-swap/`, with V3 node boundaries
for preparation, analysis/review, paid batch execution/recovery, and assembly.
Reuse native video/media contracts and existing preview/save components where
they fit; do not add pass-through ports or modify core ComfyUI. All provider
network work stays in the optional integration layer/official CLI; no new core
outbound request path. Analysis uses the existing local LM Studio service, with
no cloud fallback, automatic model download, or shared service launch/restart.
Validate the selected loaded model and actual resource settings. Use per-request
reasoning off; parse the complete response and validate its schema before review.
One surrounding JSON code fence may be removed; malformed or truncated JSON is
an error. No duplicated credential storage or changes to shared model defaults.

Keep a durable job manifest under ComfyUI's resolved user directory and output
files under its resolved output directory. A new attempt ID binds source/shot
hashes, exact prompt, Element, model, flags and approval. Write submitting state
before invoking the CLI; persist generation ID immediately after acceptance.
Repeated queue execution, restart or status resume must not issue a second paid
submission. An ambiguous submission without an ID requires user resolution;
the CLI does not expose account-history lookup. A trace ID is not idempotency.

One active paid submission per batch, bounded retry policy of zero automatic
retries, per-shot cancellation, serialized work, and real timeout/error states.
Cancellation stops future submissions; a remote task may still finish and incur
cost. Refresh balance immediately before each paid call. Do not promise a hard
credit cap if the provider offers no enforceable quote; expose unknown prices and
require explicit acceptance of that billing scope. A changed input invalidates
only its dependent approval/results; completed files remain recoverable.

Use argv arrays, validated server-resolved paths, no shell interpolation, no
credentials in workflow JSON, and sanitized receipts. Do not dynamically install
or upgrade the CLI during execution. Resolve the approved pinned CLI at setup.
No launch agents, shared service restarts, global hooks or model changes.

## Validation gates

- Synthetic 3-shot clip: exact boundaries/range coverage, original preserved,
  no dropped/duplicated frames, soundtrack alignment; include VFR and short shots.
- One-person, multiple-person and no-target fixtures: candidate review, no
  unrequested replacement of bystanders, editable wardrobe/lighting prompts.
- Analyzer response schema, cache invalidation, malformed output, missing auth,
  and paid-analysis action cannot run via preview alone.
- Fake CLI tests: one approved batch, duplicate Run, partial success, rejection,
  timeout before/after acceptance, restart/resume, cancellation and no auto retry.
- Reopen completed local media after deleting its preview node; no provider call.
- Assembly range, fps, audio, missing-shot and color-metadata checks.
- Real UI smoke for preparation/review/recovery on a NEW workflow tab.
- Any cloud analysis or Kling smoke is a separately authorized bounded paid run;
  source tests and UI success do not prove provider or creative acceptance.

## Local analysis selection

Selected existing Qwen3.5-4B Q4_K_M through the current LM Studio installation.
Three source frames produced schema-valid descriptions in 11.24 seconds with
reasoning off. This is one clip test, not a general quality benchmark. The model
still added an unsupported activity label, so draft review remains required.
Face details too small to resolve must stay unknown; ambiguity blocks automatic
target selection. Multi-person/no-target and full batch integration tests remain
implementation gates. See the linked validation report for evidence and settings.
No Kling batch, new weight download, shared-setting change or service restart is
authorized by this validation.

## References

- Live panel graph and native Kling node schema inspected in this conversation.
- `custom_nodes/anthropic-claude/anthropic_claude_node.py` schema and image batching.
- `custom_nodes/ComfyUI-QwenVL/README.md` capabilities (not runtime proof).
- https://github.com/breakthrough/pyscenedetect/blob/main/docs/api/detectors.rst
- https://github.com/comfy-org/docs/blob/main/custom-nodes/v3_migration.mdx
- Installed Kling skill 1.1.2 and pinned CLI 0.2.1 contracts, read this session.

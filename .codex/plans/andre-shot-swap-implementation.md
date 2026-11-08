# Andre Shot Swap Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task by task.

**Goal:** A local ComfyUI preparation/review workflow with persistent shot jobs,
local Qwen descriptions, explicitly approved Kling batches and recoverable videos.

**Architecture:** One optional V3 custom-node pack. Python owns media, job state,
local analysis and the pinned CLI adapter. A native web review screen operates
through same-origin routes; ordinary queue execution only prepares shots.

**Tech Stack:** Existing Python 3.13 venv, FFmpeg/ffprobe, PySceneDetect, aiohttp,
jsonschema, LM Studio loopback API, pinned Kling CLI 0.2.1, plain HTML/JS/CSS.

**Spec:** `.codex/plans/andre-shot-swap-design.md` and
`.codex/plans/andre-local-vision-validation.md`.

## Global Constraints

- Andre Element `323525046658711`; Andre reference clothes by default.
- No downloads, paid smoke tests, shared settings changes or service restarts.
- Preserve current workflow and results. Add a new tab after activation.
- No core ComfyUI changes; all code in `custom_nodes/comfyui-andre-shot-swap/`.
- Use existing venv by absolute path in the isolated worktree. No new dependencies.
- Local analysis only; reasoning off, complete schema validation, explicit review.
- No automatic paid retry. Unknown submission state requires explicit resolution.
- Use immutable source/media hashes and reviewed batch snapshots.
- Implementation runs inline under the user's proceed instruction; no additional
  planning approval loop. Activation approval remains separate if restart needed.

## Review Focus

1. Double clicks, duplicate queue runs and process interruption cannot resubmit.
2. Changing a prompt, source bytes or cuts invalidates the reviewed batch.
3. Short/VFR/long clips preserve an explicit source-time mapping and audio.
4. Missing results and remote failure cannot masquerade as completed assembly.
5. Traversal, forged origins and model-generated strings cannot cause arbitrary
   filesystem reads, script injection or unintended paid actions.

## Task 1: Media preparation and durable jobs

Files: `andre_swap/media.py`, `andre_swap/jobs.py`, `tests/test_media.py`,
`tests/test_jobs.py` within the new pack.
Interfaces: `probe(path)->dict`, `prepare(source,directory,boundaries)->dict`,
`prepare_part(source,start,end,destination,fps)->dict`,
`assemble(job,output_directory)->Path`; `Store(root,output,input_root)` with
`create(source,settings)->dict`, `read(id)->dict`, `edit(id,revision,updates)->dict`.

- [ ] Write tests for cut coverage, short-shot padding, VFR time map, exact-frame
  trims, source hash changes, revision conflicts and path containment; observe RED.
- [ ] Implement source snapshot, editable boundaries, frame samples and atomic
  manifests with process locks. Use frame-accurate encoded media, no source writes.
- [ ] Run pack tests using the project venv; expect PASS. Commit only pack files.

## Task 2: Local analysis and prompt review

Files: `andre_swap/providers.py`, `tests/test_analysis.py`.
Interfaces: `LocalVision.describe(frames)->dict`, `draft_prompt(analysis,target,
wardrobe,element)->str`; `Service.analyze(id)`, `Service.review(id,revision,rows)`.

- [ ] Test malformed/truncated/fenced JSON, frame counts, no-target/multiple-target
  review, loopback-only endpoint and no cloud fallback; observe RED.
- [ ] Reuse validated LM Studio request. Require existing loaded vision model;
  return actionable error otherwise. Retain descriptions separate from prompts.
- [ ] Draft conservative edit prompts with Element marker and source performance;
  require target descriptor plus explicit review before paid planning.
- [ ] Run tests; expect PASS. Commit only pack files.

## Task 3: Explicit paid batch, recovery and assembly

Files: `andre_swap/service.py`, `andre_swap/providers.py`, `tests/test_batch.py`.
Interfaces: `Kling.capabilities()->dict`, `balance()->number`,
`submit(part,prompt,settings,trace)->dict`, `status(task_id)->dict`;
`Service.plan(id)`, `generate(id,plan_hash,accept_unknown_cost)`, `resume(id)`,
`cancel(id)`, `retry(id,attempt_id,accept_duplicate_risk)`, `assemble(id)`.

- [ ] Fake provider tests for explicit approval, changed source, repeated Run,
  one nonterminal task, unknown submit, partial completion, cancel and resume.
- [ ] Persist submission intent before CLI; persist task ID immediately; poll
  only accepted IDs. Refresh live capability and balance before each paid call.
- [ ] Save results locally, verify media duration and retain every attempt. Retry
  creates a new reviewed plan, never replays an unknown task automatically.
- [ ] Validate assembly/frame coverage/audio for success and missing results.
- [ ] Run tests; expect PASS. Commit only pack files.

## Task 4: V3 node and independent review UI

Files: `__init__.py`, `andre_swap/web.py`, `js/extension.js`,
`web/index.html`, `web/app.js`, `web/style.css`, `tests/test_web.py`, `README.md`.
Interfaces: `AndreShotSwapPrepare` V3 node outputs job ID and UI job metadata;
same-origin `/andre_swap` routes expose existing jobs, media and explicit actions.

- [ ] Write route tests for forbidden origins, invalid paths, explicit paid ack,
  stale revisions and safe media access; observe RED.
- [ ] Build compact review screen: upload/select source, cut boundaries, local
  analyze, editable targets/prompts, keep/exclude, quote/approval, stop/resume,
  per-shot retry, original/result playback and complete assembly.
- [ ] Reopen jobs without model/provider calls; persist in-progress edits without
  background polling overwriting them. Render text with textContent.
- [ ] Test real review UI with isolated temporary data and fake provider; no paid
  action or restart of the user's service. Verify V3 schema import separately.
- [ ] Run complete pack suite and JS syntax checks; expect PASS. Commit pack.

## Task 5: Review and activation handoff

- [ ] Fresh read-only whole-pack review; fix material findings with regression tests.
- [ ] Copy only verified pack files into the connected checkout after confirming
  the destination is still absent; preserve unrelated work.
- [ ] If restart is required, present tested artifact and request activation only.
  After approved restart: verify registration, create new live tab via panel tools,
  add/configure preparation node and run local-only smoke on selected source.
- [ ] State observed runtime/UI gates separately from untested paid generation.

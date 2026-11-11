# The Message automatic draft implementation plan

Goal: one visible local workflow consumes compiled shot data, iterates two scenes,
checkpoints each and assembles a draft without per-shot widget editing.
Architecture: existing Fantastic encoder/sampler, installed Context Loop for
iteration/checkpoints/assembly, Comfy Dynamic file loading and pure JSON selectors.
Spec: user requests reusable script-driven local movie production; existing
studio/projects/the-message/REUSABLE_WORKFLOW.md and NODE_AUTOMATION_AUDIT.md.
Execution: inline, preserve dirty work, no service restart or new dependencies.

- [x] Add studio/h3_loop.py export and pure node scripts; test invalid/changed data,
  one-based scene selection, prompt/reference ordering and deterministic fingerprint.
- [x] Save-As Automated Draft; wire loader/selectors, Plan/Profile/Start/Current,
  existing encoder/sampler, Trim/Segment/End/Assemble. Mute old outputs.
- [x] Run CPU-only selector/reference map validation before model work.
- [x] Validate two short 56-frame scenes through one recursive prompt, inspect
  both saved clips and assembled draft; keep creative status review_pending.
- [x] Verify resume contract with checkpoint metadata and bounded recovery test;
  document exact run controls, failures and limits.

Review focus: missing JSON must stop, bad scene index cannot select stale state,
changed asset/recipe data changes generation fingerprint, recursive references
follow scene index, resume never silently rerolls already completed scenes.
Ruling: independent scenes and fresh room-tone audio; preserve current 608x352,
20-step recipe. Do not migrate to Tagged Ref2VA or enable any paid optimizer.

Completed bounded two-shot qualification. Recovery scope: manifest load and explicit scene-2 selection only; no crash injection or resumed sampling. Creative review remains pending. See auto-draft-v001/recovery-validation.json and studio/projects/the-message/AUTOMATED_DRAFT.md.

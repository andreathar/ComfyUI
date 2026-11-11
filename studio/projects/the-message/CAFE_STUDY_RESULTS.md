# Cafe reference study results

All three local videos decoded at 608x352, 56 frames, 24 fps. All are candidates
awaiting human creative review. Audio exists but was not auditioned. Original
references, earlier takes and workflow copies are preserved.

| Shot / take | Runtime | Observed result | Open quality gate |
| --- | --- | --- | --- |
| MSG_S003_SH01 / tk002 | 151.31 s | Empty cafe; stable counter/window-table layout | Fine motion and sound |
| MSG_S003_SH02 / tk002 | 605.48 s | Andre lowers gaze to note; stable clothing/background | Likeness, prop design, sound |
| MSG_S003_SH03 / tk003 | 1078.58 s | Andre and paper stable; both RefMods reached execution | Counter/plants absent, gaze near camera, paper looks like pad; intended coverage fails |

These are per-run timings, not a speed benchmark: prompts, references and cache
conditions differ. Technical success does not qualify automatic assembly.

## Current reference handling

- One primary location picture guides composition.
- Andre is Video 1, once at strength 1. Two stored near-frontal encoder frames
  do not establish broad multi-angle facial coverage.
- German_Cofee is Video 2, ambience owned by MSG-LOC-CAFE. Up-to-4 includes all
  three stored views; 3096 tokens, or 10320 combined with Andre before other inputs.
- Wardrobe stays a separate 182x107 guide, not a high-detail master.
- Room-tone shots omit voice conditioning. This does not isolate voice as the
  cause of earlier mouth motion.
- Asset hashes, prompts, editor state, manual stack, graph receipt, prompt ID
  and output hashes are retained per take. Ambience support passed 30 relevant
  recipe/tracker/preflight tests.

## Next qualification sequence

1. Resolve composition before another animation. The tight 85mm character shot
   competes with showing the counter. Prepare a medium layout explicitly keeping
   Andre, window table and espresso counter in frame; approve a concrete keyframe
   before longer video.
2. Compare that same composition, seed and identity with ambience off/on. Change
   only ambience conditioning. Retain current files and failed candidate.
3. Establish a note reference and a stable seat/screen-direction plan. These
   three generated cafe views are not a verified floor plan.
4. Obtain human likeness selection, keep that identity version across shots,
   and qualify voice separately with playback and speech-channel tests.
5. Increase resolution/duration only after composition, likeness and sound pass.
   The 608x352 pilots are not high-resolution masters.

## Automation readiness

Script-to-shot preparation, role mapping, versioned takes, panel edits, preflight
and technical reconciliation are implemented and exercised locally. Creative
selection, cross-shot geometry, final audio and unattended batch generation
remain unqualified. Assembly requires approved takes; failed compositions are
not automatically selected to make a batch appear complete.

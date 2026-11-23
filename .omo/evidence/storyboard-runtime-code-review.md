# Storyboard runtime code review

codeQualityStatus: WATCH
recommendation: APPROVE
blockers: []

Reviewed 2026-11-21. Approval covers the implemented code slice, not activation, live GPU safety, full P2 completion, or creative acceptance.

## Scope

Parent `/mnt/data/Projects_SSD/ComfyUI`, branch `studio/stabilization-20261113`, HEAD `34ec01d6c20a5663b438e2ce3ffbdec67e67761d`; pack HEAD `a4c07bac5173b8d27b463dc2082e9cba98c09fcb`.

Read full new `studio/production_runtime.py`, `studio/tests/test_production_runtime.py`, pack `production_node.py` and `tests/test_production_node.py`; reviewed only Path import and Studio mapping addition in pack `__init__.py`. Other dirty work excluded and preserved. Inspected dependency contracts in asset_vision, production_outline, model_management and native nodes loader.

Goal: separate queued V3 planning node owning authenticated loopback engine, preserving existing 27B fit settings and 1024 MiB reserve, single planning job admission, shared Studio lock, source/evidence preservation, bounded repair, and process exit before return.

Plan: `studio/plans/best-storyboard-creator-assistant.md`, P2. Rulings/notepad: `.codex/artifacts/storyboard-implementation/progress.md`. Native lifetime plus flock/parent-death replaces expiring lease; global external-app contention remains unqualified.

`omo-agent-toolkit ulw-loop status --json` failed: installed runtime target missing. No repair/install attempted. Used assigned fallback report path.

## Findings by severity

### CRITICAL
None.

### HIGH
None.

### MEDIUM
M1 — Reject invalid project identity before expensive inference. `studio/production_runtime.py:177` accepts any nonblank project_code; `studio/production_outline.py:52` requires 2–8 uppercase letters/digits. A code such as `my-film` passes admission, hashes artifacts and launches the model, then fails at `production_runtime.py:277` after inference. Lines 281–285 spend the repair attempt on immutable caller input that model output cannot fix; the final error incorrectly describes an invalid outline. Validate the existing identity contract before hashing/spawning (and before node model unloading). Keep semantic repair for model-output errors. Bounded resource/UX waste, not demonstrated safety or data loss: nonblocking. Parent acknowledged and intends a separate fix pass; that later change is outside these reviewed hashes.

### LOW
None.

## Independent verification and evidence

- `.venv/bin/python -m pytest -q studio/tests/test_production_runtime.py`: **23 passed in 4.27s**.
- `.venv/bin/python -m pytest -q custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests/test_production_node.py --rootdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --confcutdir=custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/tests --import-mode=importlib`: **3 passed in 3.72s**, existing pytest-asyncio loop-scope deprecation warning.
- Scoped parent and pack git diff --check exited zero. New untracked files additionally read in full; diff --check alone does not cover them.
- Tests inspected directly: authenticated dummy loopback subprocess, parent death/unrelated sibling survival, source-byte preservation, state-write failures, admission rejection, timeout/wrong listener/model/truncated response, bounded repair, native V3 interface and adapter behavior.
- Native loader `nodes.py:2305` prefers mappings; installed V3 schema methods passed node tests. Pack import/live activation remains untested.
- Cleanup awaits owned process exit within flock before successful proposal publication. State-write failure after spawn cannot skip cleanup. Loopback HTTP disables redirects and environment proxies. No cloud fallback, unrelated-process kill, core model change or host-setting mutation introduced.

## Skill perspectives and graph coverage

Searched `/home/athar/.agents` and `/home/athar/.codex` for remove-ai-slops/SKILL.md and programming/SKILL.md; neither is installed. Applied both documented review perspectives from the prompt. No deletion-only, removal-verification, tautological, brittle prompt-string, or solely implementation-constant tests found. Schema test checks native interface behavior. Production validation/parsing serves ownership, persistence or untrusted model-response boundaries. No needless extraction, untyped escape hatch or speculative abstraction found. M1 concerns validation placement, not justification for generic defensive parsing. No other violation of either skill perspective identified.

Graph discovery and architectures consulted for both owners before source investigation; runtime symbols present but pack production_node search returned zero symbols. Pack graph coverage is missing; direct source inspection used. Targeted AKB recall returned nothing. Registry quick memory search provided no relevant task-specific evidence relied upon.

## Limits

No weights loaded. Dummy tests prove no GPU-release claim. No live Qwen, native browser/queue integration, actual GPU release, external Hermes reload contention, real OOM recovery or activation tested. Predicate cancellation is exercised; repeated asyncio task cancellation during shutdown was inspected in shielding code, not independently tested. Real installed-engine schema/model/property compatibility must pass bounded live qualification. Parent-death dummy test does not prove a stalled engine exits. Full root/pack reruns reported by others are not claimed as independently verified here.

## Frozen reviewed SHA-256

- studio/production_runtime.py: `7ca59af98f1994f786194d1f2eb73de554a250df64ac2a7b046769262ca47853`
- studio/tests/test_production_runtime.py: `f4294b7fed577d8360983b452cbed957805f67b4744136a1971676829004f263`
- pack production_node.py: `e520b32b3a9df9338440244c28d692598eeb8430da0bccd7cfc2d3fc0135a98d`
- pack tests/test_production_node.py: `e227e52e5822b2d8193d559aa41b1381c43534ae48ee05fd60af66b3246d2c60`
- pack __init__.py: `a5237407cf0b5df87ce57bc6b76cefc252469eb507264326bd8fe6614282c214`

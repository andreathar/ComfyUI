# Final re-review — supersedes the historical review below

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

## Current findings

CRITICAL: none. HIGH: none. MEDIUM: none. LOW: none.

H1 resolved: model role pins now require canonical loader filenames; resolution honors default model folders and default extra_model_paths.yaml precedence, including preferred external copies and legacy category aliases. Configuration hash is pinned. Independently compared the new resolver against native folder_paths.get_full_path after native utils.extra_config.load_extra_path_config in a fresh CPU-only process: all four roles matched the actual hot NVMe paths. Inspected refreshed models.json and /mnt/data/Projects_SSD/ComfyUI/.codex/artifacts/the-message-model-verification.json. That artifact records separately streamed SHA-256 hashes of preferred files matching originals; reviewer did not independently repeat these large full-file reads.

M1 resolved: mark_submitting revalidates the original resource snapshot, including observed_at. New regression covers expired observation with recent preflight.

M2 resolved: queue/export tests now use fresh timestamps and exact relevant diagnostics, so unrelated freshness errors cannot satisfy them.

## Independently executed checks

From the isolated worktree, with /mnt/data/Projects_SSD/ComfyUI/.venv/bin/python:

- unittest discovery test_h3_preflight.py: 6 passed.
- unittest discovery test_film.py: 11 passed, including real CPU FFmpeg roundtrip.
- unittest discovery test_h3_recipe.py: 9 passed.
- film.py check studio/projects/the-message --workspace /mnt/data/Projects_SSD/ComfyUI: model stat/config checks and asset hashes passed; both shots compiled with expected label maps.
- Native/new model resolver comparison: all four roles matched.

FILM_AUTOMATION.md now states the fixed The_Message namespace, default-local-launch model resolution scope, and unsupported additional CLI overrides. Approval applies to this reviewed offline code and documented scope. It does not qualify generation, peak GPU/RAM usage, cache lineage, likeness, audio performance or creative acceptance. Parent reports visible save/reopen smoke blocked by a panel state error; reviewer did not independently inspect the panel. Keep this acceptance gate explicitly separate from code approval.

## Skill-perspective check

remove-ai-slops and programming perspectives ran using supplied reviewer criteria because their skill files were unavailable, as detailed in the historical review. Revised tests exercise actual failure boundaries. Model resolution is necessary boundary validation for a reproduced provenance failure. No remaining skill-perspective violations found.

---

# Historical initial review — all findings below resolved above

# The Message code review

codeQualityStatus: BLOCK
recommendation: REQUEST_CHANGES

Reviewed isolated checkout `/mnt/data/Projects_SSD/ComfyUI/.codex/artifacts/film-automation-worktree` against base `561cf1e4d56ea8b53b8772be6913bbe2ede3b179`. The seven implementation/test files and project fixture directory are new untracked files, so their complete contents constitute the diff. Read the implementation plan and `.codex/artifacts/film-automation-ledger.md` in the main checkout. No executor test logs or notepad beyond that ledger were supplied. No live panel, GPU generation, provider calls or original-media writes were performed.

`omo-agent-toolkit ulw-loop status --json` fails because its installed runtime target is missing. This report therefore uses the specified fallback path.

## CRITICAL

None.

## HIGH

### H1: Model preflight certifies files that need not be the executed model files

`studio/h3_preflight.py:12-24`, `studio/film.py:274`, `studio/projects/the-message/models.json:3`.

The checker requires four role keys but checks whichever path each record supplies. It never binds those paths to the fixed loader selections in `h3_graph.BASE` or the backend's model-folder search precedence. This is a practical issue in this workspace: main checkout `extra_model_paths.yaml` registers `/home/athar/ComfyUI-models-hot` with `is_default: true`, whereas the shipped pins point at `models/...`. Checking the original copies does not establish which bytes the running loader will use.

Reproduction, independently executed: create one temporary file `unrelated` containing `not a model`; record its real size, mtime and SHA-256; use that same record for every key in `h3_recipe.DIAGNOSTIC['models']`; call `h3_preflight.check(root, pins, {}, rehash=True)`. Actual: `ready=True`, `errors=[]`. The graph still selects its four named model files, none of which exist in that temporary root. Thus even full rehash can report readiness for an impossible/different execution.

Required fix: explicitly bind each graph loader selection to evidence of its actual backend-resolved path and pin those bytes, accounting for configured folder precedence. Reject role/name/path mismatch and preserve the resolution evidence in the take. Add a regression using mismatched pins and a shadowed model name. An offline file-only check may remain clearly limited, but it must not satisfy submission preflight without this binding.

## MEDIUM

### M1: Submission freshness ignores the original resource observation time

`studio/film.py:98-103`, `studio/film.py:275-281`.

Preflight validates snapshot freshness against `observed_at`, then stamps a new `checked_at`. Submission validates only that newer stamp and reruns file checks, not resource checks. An observation almost two minutes old gets another two-minute validity window.

Reproduction, independently executed using `test_film.TakeTests.setUp()` fixtures: run `preflight_take` with an otherwise valid snapshot whose `observed_at=time.time()-119`; advance mocked time by three seconds; `h3_preflight.resources(snapshot)['ready']` is False but `film.mark_submitting(take)` succeeds and records `submitting`.

Required fix: validate `evidence['resources']['snapshot']` again at the submitting transition, preserving the original observation timestamp. Add a test where preflight itself is recent but its resource observation has expired.

### M2: Resource tests do not isolate the behavior they claim to test

`studio/test_h3_preflight.py:27-34`.

Both busy-job and unknown-export tests omit `observed_at`; therefore both pass merely because every snapshot without a timestamp is rejected. Removing the queue or export checks would leave these tests green. Supply a fresh otherwise-valid snapshot and assert the relevant diagnostic, with a valid-snapshot control. This is a test-relevance issue, not a demonstrated extra production failure.

## LOW

None.

## Skill-perspective check

Ran the requested remove-ai-slops and programming perspectives using the criteria supplied in the reviewer instructions. Neither skill is in the available catalog, and targeted searches under `/home/athar/.agents/skills`, `/home/athar/.codex/skills`, and the installed plugin cache found no matching SKILL.md. No deletion-only tests, unnecessary abstraction, untyped escape hatches, or needless production normalization were found. JSON normalization in graph comparison is necessary to compare equivalent editor-state serialization. M2 violates the meaningful-test perspective: its tests can pass for an unrelated reason. The exact graph contract is scoped to the supported canvas and is not itself gratuitous constant mirroring; the changed-seed check tests a meaningful safety contract.

## Verification and limits

Executed with `/mnt/data/Projects_SSD/ComfyUI/.venv/bin/python` from the isolated checkout:

- `-m unittest discover -s studio -p test_h3_recipe.py`: 9 passed.
- `-m unittest discover -s studio -p test_h3_preflight.py`: 4 passed.
- `-m unittest discover -s studio -p test_film.py`: 10 passed, including real CPU FFmpeg generation, decode, recovery, human-review gate, and trimmed assembly.
- Independently reproduced H1 and M1 as described above.

The graph comparator checks all node IDs, classes, and inputs while ignoring frontend metadata and JSON object key order. Reconciliation binds the saved-output node, prefix, prompt text, graph, decoded video dimensions/fps/frame count/audio presence, and file hash. Reconciliation retains approved/rejected status when repeated with the same output. Assembly checks selected take approval and hashes, uses temporary output and an exclusive hard link, and rejects an existing destination. Original source clips are read, not rewritten.

These tests do not qualify real H3 generation, actual model residency, measured RAM/VRAM peaks, cache lineage, visual likeness, audio content/synchronization, or creative approval. Those are acknowledged deferred phase-5/product qualification limits, not reasons to claim the offline implementation has rendered a film. The free-memory check intentionally only proves positive reported availability; it is not a capacity guarantee. An assembly receipt-write failure after output publication can leave a final file without a receipt; originals remain intact, but recovery requires operator handling.

## Blockers

- H1: Bind model preflight to actual resolved loader files before treating the preflight as submission readiness.
- M1: Recheck resource observation expiry at submission.

M2 should be corrected alongside the resource regression coverage.

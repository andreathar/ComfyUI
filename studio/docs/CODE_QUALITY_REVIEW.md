# Studio Code Quality Review

**Date:** 2026-11-21
**Scope:** `studio/` — 30 Python modules, ~4,500 lines, 28 test files, 400 tests

## Pre-tuning follow-up

Three independent read-only reviews covered Studio production contracts, catalogue and project organization, and intake/Brain evidence. CodeRabbit CLI authentication was checked; no remote review ran against this mixed worktree. Use [Studio review agent instructions](STUDIO_REVIEW_AGENT.md) for future reviews or a separately scoped CodeRabbit diff.

- Script revisions preserve the existing full source unless `--revised-script` supplies an explicit replacement. Undeclared dialogue speakers now return validation problems instead of crashing.
- H3 preflight and compilation honor the same input-use authorization, and the shared H3 resolver preserves folder names as the native parser does. Master take transitions verify the frozen package as well as the prompt.
- Brain comparison binds native timestamps to a successful indexed generation; it retains matching timestamps and a history digest, not unrelated native histories. Intake distinguishes an unverified publication from a blocked copy. Local vision checks that its child owns the loopback listener before transmitting pixels and records source digests and runtime file stamps.
- Operator manuals now live in `docs/`. Workflow qualification output is a dated snapshot; benchmark, pilot, and production records are retained. The only files removed outright were ignored generated caches.

Verified: **405 Studio tests and 96 subtests passed**. No production render or live GPU validation was part of this review. The code is suitable for building a reviewed evaluation set; benchmark receipts, draft prompts, and rejection evidence are not automatically eligible training data. Real-image role calibration and native library binding remain separate gates.

## Earlier Studio quality pass

The studio production pipeline implements a complete movie production workflow:
script generation → shot compilation → workflow graph building → preflight →
submission → reconciliation → review → local-model analysis.

The codebase is well-architected with clear layering, strong integrity guarantees,
and excellent test coverage.

## Architecture

```
Production Document (production_generate.py, production_validate.py)
  ↓
Shot Compilation (h3_recipe.py) — binds assets, renders prompts, computes frames
  ↓
Graph Compilation (h3_graph.py, h3_loop.py) — builds ComfyUI workflow graphs
  ↓
Preflight (h3_preflight.py) — resource checks, model verification
  ↓
Take Lifecycle (film.py, master_take.py, h3_loop_run.py) — prepare, submit, reconcile, review
  ↓
Analysis (brain_*.py) — local-model interpretation of workflow runs
  ↓
Master Studio (master_studio_*.py) — project-specific resolver, compiler, package
```

## Strengths

- **Strong integrity:** SHA-256 fingerprints at every boundary, file-hash verification,
  immutable snapshots with hardlinks, file-locking for concurrent access.
- **Clear separation:** Each module owns one domain (recipe, graph, preflight, lifecycle, analysis).
- **Excellent tests:** 400 tests with real fixtures, temp directories, real file hashes,
  and edge cases (silent recipes, empty casts, prop binding, wardrobe mismatch).
- **Deterministic:** Canonical JSON serialization, explicit frame alignment math,
  versioned recipe constants.

## Issues Found and Resolved

### 1. Duplicated model path resolution (Resolved)

**Problem:** Three modules implemented nearly identical `extra_model_paths.yaml`
parsing: `h3_recipe.model_folders()`, `h3_preflight.resolve_model()`, and
`qualify_workflows.model_roots()`. Each handled `base_path`, `is_default`, alias
mapping (`unet`→`diffusion_models`, `clip`→`text_encoders`), and path normalization.

**Fix:** Refactored `h3_preflight.resolve_model()` to call `h3_recipe.model_folders()`
instead of duplicating ~30 lines of YAML parsing logic. Removed unused `yaml` and `os`
imports from `h3_preflight.py`. Added cross-module test
`test_resolve_model_uses_model_folders` to verify consistency.

**Files changed:**
- `studio/h3_preflight.py` — `resolve_model()` reduced from 32 to 6 lines
- `studio/tests/test_h3_preflight.py` — added cross-module test

### 2. No end-to-end integration test (Resolved)

**Problem:** Each module was tested in isolation. No test spanned the full pipeline
(compile → graph → preflight → prepare), leaving cross-layer contract mismatches
undetectable by the test suite.

**Fix:** Created `studio/tests/test_e2e_pipeline.py` with 4 integration tests:
- `test_full_pipeline_compile_graph_preflight_prepare` — spans all four layers,
  verifying fingerprint consistency, graph topology, and preflight readiness.
- `test_preflight_catches_changed_model` — verifies preflight detects tampered models.
- `test_graph_verify_catches_modified_canvas` — verifies graph.verify() detects
  canvas divergence from recipe.
- `test_prepare_rejects_duplicate_attempt` — verifies take directory uniqueness.

**Files created:**
- `studio/tests/test_e2e_pipeline.py`

## Remaining Observations

### Redundant preflight snapshots (Deferred)

`h3_preflight.capture_snapshot()` spawns 4 subprocess calls and runs twice per
submission. A TTL cache or pass-through pattern would eliminate the duplicate.
Low priority: the 120-second expiry window already limits staleness.

### Monolithic `compile_shot()` (Deferred)

At 205 lines, `h3_recipe.compile_shot()` orchestrates ~15 steps. The function
already uses local helpers like `resolve()`. Named sub-functions would improve
error context but the current structure is functional.

## Performance Characteristics

- **Frame computation:** O(1) modular arithmetic.
- **Hash operations:** ~42 file hashes per preflight for a 6-shot production,
  ~50ms total on SSD.
- **Graph verification:** Deep-copy + normalize + diff on 26 nodes, <1ms.
- **VRAM safety:** Correctly enforces `between_scene_cleanup` for 6 GB VRAM systems.

## Test Results

| Metric | Before | After |
|--------|--------|-------|
| Tests | 396 | 400 |
| Subtests | 93 | 93 |
| Status | All passing | All passing |

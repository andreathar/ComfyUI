---
sessionId: session-261121-035702-apm8
---

# Analysis

# Studio Code Quality Analysis

## Overview
30 Python modules, 28 test files, 395 tests all passing. Well-architected pipeline with clear layering.

## Key Findings

### Strengths
- Strong integrity: SHA-256 at every boundary, file hashing, immutable snapshots, file locking
- Clear separation: recipe, graph, preflight, lifecycle, analysis each own their domain
- Excellent tests: real fixtures, edge cases covered
- Deterministic: canonical JSON, explicit frame math, versioned recipes

### Issues

1. **Duplicated model path resolution** (Medium) - Three modules duplicate `extra_model_paths.yaml` parsing: `h3_recipe.model_folders()`, `h3_preflight.resolve_model()`, `qualify_workflows.model_roots()`. Consolidate into one helper.

2. **Redundant preflight snapshots** (Medium) - `capture_snapshot()` spawns 4 subprocess calls and runs twice per submission. Cache or pass-through.

3. **Monolithic compile_shot()** (Low-Medium) - 205 lines doing 15 steps. Consider named sub-functions for better error context.

4. **No end-to-end integration test** (Gap) - Each module tested in isolation. Add a test spanning compile → graph → preflight → prepare.

### Performance
- Frame computation: O(1), efficient
- Hash operations: ~42 per preflight, ~50ms on SSD
- Graph verification: <1ms for 26 nodes
- VRAM safety: correctly enforced

### Recommendation
No broad refactoring needed. Two concrete improvements: deduplicate model path resolution and add an integration test.

# Delivery Steps

### ✓ Step 1: Deduplicate model path resolution
Consolidate duplicated extra_model_paths.yaml parsing into h3_recipe.model_folders() and update h3_preflight.resolve_model() to use it. Add a cross-module test.

### ✓ Step 2: Add integration test and document findings
Create studio/tests/test_e2e_pipeline.py spanning compile → graph → preflight → prepare. Document analysis in studio/docs/CODE_QUALITY_REVIEW.md.
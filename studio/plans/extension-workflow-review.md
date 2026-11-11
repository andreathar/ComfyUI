# ComfyUI extension workflow review and PC qualification

Prepared: 2026-11-09. Status: proposed plan; discovery only, no new generation tests or installs.

## Goal

Map every locally available extension workflow, connect it to its nodes and required models, and establish which exact configurations run reliably and practically on this PC. Every discovered workflow gets an explicit outcome; missing dependencies and oversized models stay visible rather than disappearing from the report.

“Every workflow” means installed extensions’ shipped examples, embedded workflow metadata, locally registered templates, and saved workflows using those extensions. It does not mean every possible graph or every example published online. Extensions without examples get a coverage-gap entry and, where feasible, a clearly labelled newly constructed minimal test. A single test does not certify an entire extension.

## Verified starting point

- GPU: NVIDIA RTX 3060 Laptop, 6,144 MiB physical VRAM. The running server reports about 5.67 GiB usable CUDA memory; actual free memory varies.
- CPU: Intel i7-11800H, 16 logical CPUs. RAM: about 31 GiB usable; only about 8 GiB currently available. Swap: about 83 GiB, with 6.8 GiB already used. Swap is not a substitute for a practical RAM budget.
- Live local server: ComfyUI 0.44.2, frontend 1.57.6, PyTorch 2.14.1+cu130. Queue was empty at inspection; this does not reserve it for testing.
- Source checkout: branch `master`, commit `561cf1e4`; existing dirty files must be preserved.
- Current launch policy includes `--reserve-vram 1.0 --disable-pinned-memory`. Preserve it for the baseline; confirm effective runtime settings before tests.
- Model roots include `/mnt/data/ComfyUI-models` and `/home/athar/ComfyUI-models-hot`, configured through `extra_model_paths.yaml`. The former is on SATA storage, the latter NVMe. Approximately 276 GiB and 94 GiB respectively were free at inspection.
- Local artifacts include SD1.5, FLUX.2 Klein Q4/Q8, Z-Image BF16/Q4, Qwen Image, MiniMax H3 components, SAM3.1, and RealESRGAN. Presence does not establish a complete compatible model stack or hardware support.
- The pinned downloader catalogue lists only four profiles: SD1.5, Z-Image Turbo, FLUX.2 Klein, DA3. It is not a complete disk inventory.
- `.codex/PC_WORKFLOW_GUIDE.md` records earlier successful SD1.5, FLUX.2 Klein Q8, Z-Image BF16, and LC123 tests. Treat these as historical evidence, not fresh certification; they lack measured peak memory and do not cover all extensions.

## Initial discovery scale

Read-only discovery found **28 extension directories in the enabled location and 16 disabled**, plus a standalone Python loader candidate. Placement is not proof of loading: the recorded startup lists 27 extension directories without an import-failed marker, while Manager is blocked by policy.

| Source | UI JSON occurrences | API JSON occurrences |
|---|---:|---:|
| Enabled-location extension examples | 282 | 7 |
| Disabled extension examples | 48 | 8 |
| Saved user workflows | 39 | 1 |
| Studio templates | 0 | 6 |

These are not unique executable workflow counts. There are also 25 H3 builder recipes, eight extension PNGs containing ten workflow/prompt payloads, 20 saved metadata sidecars to exclude, and historical backups. Z-Image alone contributes 155 JSON graphs, including many style variants and documentation figures. Twelve enabled-location extensions have no discovered JSON/PNG graph.

For broader coverage, separately catalogue 116 core blueprints and 664 installed template-package UI graphs; do not mix these into extension coverage totals. JPEG/WebP metadata, archives and documentation snippets remain discovery gaps to inspect or explicitly exclude. Frontend panel snapshots can contain paired UI/API representations of the same workflow.

## Phase 1 — Freeze the baseline and inventory everything

1. Record core/frontend/Python/Torch versions, launch arguments, extension revisions and enablement, import errors, available node schemas, model search paths, and resource availability. Use read-only inspection; do not import extension modules just to enumerate nodes.
2. Inventory every extension, including disabled ones and frontend-only plugins. Distinguish installed folders, successfully loaded backend nodes, and frontend functionality.
3. Discover workflow JSONs by graph structure, not filename alone. Include UI graphs, API prompts, nested subgraphs, extension examples/templates, saved user workflows, and workflow metadata in supported media. Record unreadable, unsupported, and malformed candidates separately.
4. Exclude configuration JSONs and metadata sidecars from executable workflow counts. Deduplicate identical graphs while preserving every original path and meaningful variant. Snapshot hashes so later edits cannot silently change the scope.
5. Review existing `studio/workflow_health.py` and its tests before reusing it. Its current discovery covers saved/default/studio graphs, not extension examples; the existing report is dated 2026-11-07 with only 19 rows. Verify sidecar filtering, virtual Set/Get nodes, and subgraph handling; these must not produce false missing-node failures. Preserve explicit uncertainty where exact UI/API/subgraph execution correspondence is unavailable.

**Deliverables:** `extensions.csv`, `workflows.json`, and a readable coverage table in a dedicated audit directory. Counts must reconcile to unique workflows, duplicate aliases, excluded non-workflows, parse errors, and uninspected candidates.

## Phase 2 — Build the extension → workflow → model map

For each workflow, record:

- Stable ID, source path/hash, extension owner/revision, title, purpose, family, and whether it is a complete runnable graph, node catalogue, or partial example.
- All node types and providers, cross-extension dependencies, frontend-only/virtual nodes, custom subgraphs, missing or renamed node types, and disconnected output branches.
- Exact required diffusion/checkpoint, text encoder, VAE, LoRA, adapter, segmentation, upscaler, and other model artifacts; resolve their actual paths and loader compatibility. Account for dynamically selected filenames and mark unresolved requirements explicitly.
- Input media, dimensions, frame/sample counts, output type, external programs, local services such as LM Studio, and any network/cloud requirement.
- Model availability, quantization/compute/backend requirements, and an initial hardware feasibility estimate with its confidence.

Separate complete generation workflows from prompt builders, image/video utilities, segmentation, face tools, converters, UI integrations, and remote API nodes. Utilities may need no diffusion model. Cloud workflows do not demonstrate local model capability.

**Deliverable:** a filterable matrix: extension | workflow | task | models | blockers | original/adapted | test status | evidence.

## Phase 3 — Make a safe, hardware-aware test matrix

First inspect each candidate for auto-downloads, remote requests, arbitrary code/shell execution, destructive outputs, and persistent configuration changes. Do not blindly batch-run extension examples.

| Lane | Initial test | Next step if successful |
|---|---|---|
| Prompt/data/image utilities | Small fixed local fixtures; no model unless needed | Cover each distinct operation and output |
| SD1.5 image generation | 512×512, batch 1, normal quality settings | One larger supported size, only with memory headroom |
| FLUX.2 Klein | Existing Q4/Q8 compatible stacks, 512×512, batch 1 | Compare quality/time/RAM under identical conditions |
| Z-Image | Existing Q4 or BF16 stack when compatible | Compare encoder placement and quality; no assumed winner |
| Qwen Image | Resolve complete encoder/VAE/loader stack first | Pilot only if memory/backend estimate is credible |
| Upscale/segmentation/face tools | Small local fixture; tiled mode if supported | Representative input with visual inspection |
| Video/audio/H3 | Architecture-supported shortest duration and smallest useful size | One representative clip only after the pilot passes |
| 3D/rigging utilities | Inspect TripoSG/Trellis2/Pixal3D/UniRig dependencies; tiny compatible fixture | Validate generated geometry/rig, not just successful history |
| Frontend-only extensions | Load/select/edit/save/reopen and inspect relevant controls | Verify behavior in the actual browser |
| Cloud/API/local-service integrations | Map dependency and inspect configuration | Run only with explicit authorization/service readiness |

Quantized weights are not automatically executable: verify the loader, architecture, GPU generation, compute dtype, text encoder and VAE together. In particular, do not assume NVFP4 support from a filename on an RTX 3060.

Preserve originals. Create test copies with a documented diff. Use an architecture-compatible lighter variant only where supported, and report it as **adapted**, never as a successful run of the unmodified original. Arbitrarily swapping SD1.5 into an H3 or Qwen graph is not a valid test.

## Phase 4 — Execute progressively, one job at a time

1. Agree on a quiet test window and check the live queue before submitting work. Do not interrupt existing jobs, stop shared services, close apps, change launch settings, or clear another session’s caches without permission.
2. Refresh available RAM/VRAM, disk space, GPU load and temperature immediately before each test. As an initial conservative guard, defer heavy tests below 10 GiB available RAM; revise the per-model requirement after measurement. Do not start workloads whose estimated host peak leaves less than about 4 GiB available.
3. Validate node availability, connections, required inputs and files without generation. Structural success is not runtime success.
4. Run one pilot per family, beginning with utilities and SD1.5, then compatible quantized image stacks. Use batch 1, fixed seed and fixed local media. Keep quality-relevant steps appropriate for that model rather than lowering everything to meaningless values.
5. Expand to every runnable unique workflow/meaningful branch. Duplicate graphs may share a run only when the graph, effective settings and dependencies genuinely match; record that relationship.
6. Separate fresh model-load timing from warm execution; record executed and cached nodes. Do not claim cached output as fresh model validation. Reuse existing instrumentation where possible; otherwise record sampled system memory peaks as sampled, not exact per-process CUDA allocator peaks.
7. Record prompt/run ID, graph/settings hash, models and actual paths, total/model-load time where available, sampled peak GPU usage, host RAM, swap activity, temperature, errors, output files, and visual/audio observations.
8. Stop escalating on OOM, sustained swap thrashing, thermal trouble, or a run exceeding its agreed time budget. Never automatically interrupt a shared queue: use a job-specific cancellation mechanism if available; otherwise obtain exclusive ownership before a global interrupt or report that safe cancellation is unavailable. Retry once only with a documented supported change.
9. For recommended everyday configurations, complete two fresh executions plus one save/reopen/browser run. Inspect actual output dimensions, non-empty image/video/audio, prompt/input correspondence, obvious artifacts, and playable media. Ask the person to judge creative quality where it is subjective.

## Phase 5 — Report capabilities and gaps honestly

Track structural readiness, runtime outcome, adaptation, and practical usability separately. Use outcomes such as:

- **Mapped / not run** — inventory complete, execution unverified.
- **Passed locally** — this exact original configuration produced verified output.
- **Passed with adaptation** — a documented compatible test copy passed.
- **Slow but feasible** — finished correctly, exceeds the chosen everyday time budget.
- **Blocked: missing model/input/node/service** — exact missing requirement listed.
- **Failed** — observed error, timeout, OOM or invalid output with evidence.
- **Hardware/backend unsuitable** — observed incompatibility or clearly labelled estimate; not an invented runtime failure.
- **Remote-only / authorization needed** — mapped, not represented as local capability.
- **No shipped workflow / frontend-only** — use a labelled constructed test or browser checklist.

Deliver a shortlist of ready-to-open PC-safe workflows with exact models/settings, outputs and measured costs; a full extension/workflow coverage ledger; and a prioritized repair/download list. No candidate vanishes simply because it cannot run.

## Completion criteria

- Every installed extension has an ownership/coverage row, including those with no shipped examples.
- Every discovered workflow has a source, dependency map and explicit disposition; scan exclusions and errors are accounted for.
- Every locally runnable unique workflow in scope is exercised or has a precise reason it was not tested.
- Every recommended workflow has reproducible evidence and opens correctly in the frontend.
- Model recommendations distinguish proven practical, slow-but-feasible, blocked, and estimated unsuitable configurations.

## Approval boundaries and order of work

This document proposes implementation and testing; it does not authorize downloads, extension updates, shared runtime restarts, paid/cloud calls, or executing arbitrary-code examples. Model downloads need a per-profile plan showing exact artifacts, sizes and license followed by explicit approval, using `.codex/model_download.py`.

Recommended order: inventory → dependency map → review blockers → small pilot suite → exhaustive eligible workflow tests → final PC-safe catalogue. Finish inventory before estimating total test hours. The practical turnaround threshold is awaiting the person’s choice in the Inbox; mapping can proceed independently.

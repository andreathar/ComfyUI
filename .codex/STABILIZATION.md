# Studio stabilization — 2026-11-13

The maintained integration branch is `studio/stabilization-20261113`.

## Verified state

- All 15 active custom-node Git roots match `.codex/custom_nodes.lock.json`; no dirty roots or missing origins remain.
- All 498 installed Python distributions pass `uv pip check`. The snapshot resolves successfully; its only proposed reinstalls replace two obsolete temporary wheel origins with recoverable sources of the same builds.
- The original torch 2.14.1+cu130, torchaudio 2.11.0+cu130, torchvision 0.29.1+cu130, comfy-kitchen 0.2.41 and comfy-aimdo 0.6.0 were retained. CUDA tensor execution passed.
- Normal custom-node initialization through `.codex/launch.sh --quick-test-for-ci` completed without import failures. The live canonical launcher serves 127.0.0.1:8188, with 1,435 registered node types and frontend HTML available.
- The retained SD15 baseline performed fresh inference (empty execution cache), completed in 9.70 seconds, and saved a decoded 512x512 RGB image with workflow/prompt metadata. Visual inspection found a complete cabin/forest/lake image. This is technical smoke evidence, not a performance improvement or creative approval.
- The missing saved Balanced SD15 workflow was recovered from `.codex/artifacts/history-44.json`. No weights were downloaded or replaced. The smoke model was unloaded and the queue was empty afterward. Workflow Monitor recorded the prompt as succeeded with output evidence collected; API submission does not attest browser phase timing.

## Repository ownership

Original plugin sources remain as `upstream` remotes. Maintained revisions are published under `andreathar`. Agent Panel exactly matched v0.15.184 before restoring Git ownership. Fantastic LoRAs differs from its v2.3.0 source only in reviewed import ordering. Spark retains the upstream comfyui-v0.2.0 history and the actual installed registry distribution in `studio-package/`; that distribution is not represented as byte-identical to the source root. Native Audio Lock has its own private repository and focused regression tests.

LC Vision disappeared between inventory and final verification. Its previously clean pinned revision was restored from upstream; the checker again reports all 15 roots reproducible. No server restart was needed.

The two Swarm install links now point into `.codex/worktrees/swarm-nodes`, a clean detached worktree at the original pinned commit. The separate dirty Swarm application checkout was not edited or committed. The original links and copied package directories are preserved under the follow-up artifacts.

| Git root | Published revision |
| --- | --- |
| `.codex/repos/agent-panel` | `cbadda173d3d` |
| `.codex/repos/fantastic-loras` | `c0acd42f597a` |
| `.codex/repos/spark-h3` | `ad528128d474` |
| `.codex/worktrees/swarm-nodes` | `d347f3061ce9` |
| `.codex/worktrees/workflow-monitor-brain` | `8693d17273f1` |
| `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder` | `a4c07bac5173` |
| `custom_nodes/ComfyUI-H3-NativeAudioLock` | `6dbf2dd11ebf` |
| `custom_nodes/ComfyUI-H3-Project-Suite` | `e8584fd0dcbe` |
| `custom_nodes/ComfyUI_LC123_nodes` | `4358590c88bf` |
| `custom_nodes/ComfyUI_LC_Vision_nodes` | `4b1de5a9048d` |
| `custom_nodes/comfyui-manager` | `78db9bb75968` |
| `custom_nodes/comfyui-minimaxh3-contex-loop` | `9b63462dc5af` |
| `custom_nodes/comfyui-websocket-reconnect-fix` | `12b5fdf38e8b` |
| `custom_nodes/comfyui_dynamic` | `21802e54f436` |
| `custom_nodes/hermes-nodes` | `950306092d7f` |

## Fixes and dependency decisions

Shot replacement now rejects identical source runs, acquires distinct run locks in a consistent order, and uses relative FFmpeg concat paths so apostrophes in parent directories do not break assembly. Resource preflight rejects missing/non-finite memory readings instead of crashing or qualifying unknown capacity. Regression tests reproduced each defect before correction.

Existing production documents now declare their referenced voices explicitly; technical revision requests retain the full script and its reference offsets. All saved production documents passed validation.

The stack checker now reports unversioned copied node packs instead of silently excluding them. Two failing-then-passing regression tests cover missing Git ownership and dirty parent-owned packs.

Native Audio Lock now copies cropped latents so a short result cannot keep an entire long encoded audio tensor alive. Its unused model-option flag was removed; native audio denoise masks already own clean-audio conditioning. Node interfaces remain unchanged.

The dependency repair updates Transformers, Hub, sentence-transformers, Gradio and related metadata coherently, and selects compatible NumPy, OmegaConf and fsspec versions. It retains Pillow 13 instead of downgrading into known vulnerabilities. MoviePy, Qwen-TTS, Decord and NuVu were unused by active pack imports and incompatible with the shared environment; they were archived and removed. CPU ONNX Runtime replaces the overlapping development GPU distribution. Stale Realtime metadata pointed to a missing source directory; unused vulnerable PyPDF2 had no active reverse dependency. Both were archived and removed.

The package snapshot also records pre-existing changes since the older snapshot; not every diff line represents an installation performed in this pass. `packages.before.tar` preserves files of all changed/removed distributions for recovery; `requirements.before.txt` records initial versions. These artifacts are not a full environment backup.

The llama.cpp dependency now names the original publisher release URL and matching SHA-256. Spark's release archive and wheel hashes were checked, and its wheel package files exactly match the installed files. `restore_runtime_wheel.py` restores that software wheel explicitly; it does not download models or run automatically from ComfyUI.

## Validation

| Scope | Result |
| --- | --- |
| Studio | 319 tests, 75 subtests passed |
| Workflow Monitor Brain | 76 tests passed |
| Focused core | 49 tests passed |
| Stack checker, including copied-pack regression | 11 tests passed |
| Manager | 218 tests, 223 subtests passed; 98 skipped |
| Dynamic | 8 tests passed |
| PromptBuilder cache | 2 tests passed |
| Project Suite scene metadata | 3 tests passed |
| Native Audio Lock | 2 tests passed |
| Wheel recovery | 3 tests passed |
| Project Suite | Node smoke, route contracts and project lifecycle passed |
| Context Loop | Five Python probes and JavaScript plan editor passed |

A combined pytest invocation across independent hyphenated plugin packages produced collection errors from package-relative imports. Their supported independent unittest invocations passed; this is not represented as a passing combined suite. Manager skips and the asyncio configuration warning remain visible in the logs.

## Remaining limits

Interactive browser validation could not run: the browser access host is unavailable. Frontend HTTP, live APIs and generation succeeded, but those do not establish UI interaction coverage or full H3 video acceptance.

All critical/high advisories reported against the old default-branch dependency snapshot are addressed in this installed candidate. Two medium advisories have no published fixed version in the retrieved GitHub records: DiskCache unsafe pickle deserialization and Accelerate sharded-checkpoint path traversal. Their dependencies remain required; do not load untrusted cache databases or external checkpoint index files. This report does not claim a vulnerability-free environment, and GitHub default-branch alerts will not reflect an unmerged candidate branch.

CodeRabbit completed the follow-up source review with 19 findings. All were addressed, including two already corrected before its snapshot: replacement provenance and published-shot hashes, 16-bit source precision, selected-port and unknown-queue handling, model CSV fields, voice-bank references, script-revision preservation, catalogue special-file and recursion handling, test discovery, and stale operational instructions. Only three oversized generated JSON reports were skipped (qualification.json, static-preflight.json and workflows.json); PNG files were excluded. The bounded correction review completed across 21 files and found one additional major issue: matching command-line names and ports could count an unrelated GPU process as reclaimable. Preflight now requires the unique local listening-socket PID before counting its VRAM. Its failing-then-passing regression and a live snapshot passed. This final socket correction was locally verified; no third CodeRabbit pass was run.

Evidence and original copies: `.codex/artifacts/stabilization-followup/`. Image: `output/stabilization-20261113/sd15_00001_.png`. Live process ownership and API snapshots were checked in that directory. No paid API generation was submitted.

Remaining advisory sources:

- [GHSA-w8v5-vhqr-4h9v: DiskCache has unsafe pickle deserialization](https://github.com/advisories/GHSA-w8v5-vhqr-4h9v) — diskcache 5.6.3, medium; no fixed version listed.
- [GHSA-4j2p-28q2-5m79: Accelerate path traversal and denial of service via sharded checkpoint weight_map entries](https://github.com/advisories/GHSA-4j2p-28q2-5m79) — accelerate 1.12.0, medium; no fixed version listed.

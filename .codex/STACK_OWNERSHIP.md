# Production stack owners and integration gates

Current correction to the November14 holistic audit: a clean Git lock checks versions, origins, install targets and dirty files. It does not prove functional integration, global-hook coverage, model residency correctness or optimization. Batch1 changed two repositories; the installed stack contains14 independent Git roots and15 install paths.

## Critical production components

| Owner | Responsibility | What integration must observe |
|---|---|---|
| Native core: `comfy/model_patcher.py`, `model_management.py`, `comfy_aimdo` | DynamicVRAM, partial weight residency, loading/offloading, pinned buffers and attention execution | Actual model identity, patcher/backend, device, resident bytes, offload and buffer lifecycle |
| `custom_nodes/comfyui_dynamic` | Dynamic script/control nodes; live resource and loaded-model panel; guarded free/unload actions | Script revision; RAM/process/GPU samples; native loaded-model state; queued versus executed cleanup |
| `custom_nodes/ComfyUI_LC123_nodes` | Nodes, frontend tools, optimizer/reporting and global model/sampling hooks | Effective optimizer inputs AND import-time hooks, settings/defaults, wrapper order and cancellation effects |
| `custom_nodes/ComfyUI-H3-Project-Suite` | Project clips, context selection, trim/import, save and reusable stages | Project/shot identity, context provenance, cache identity, automatic chain eligibility versus human acceptance |
| `.codex/repos/agent-panel` | Embedded assistant UI and graph/agent bridge | Correct browser canvas identity, connection, actual tool invocation, input ownership, approvals and session continuity |
| `.codex/repos/fantastic-loras` | LoRA folders, selection/stacking, model routing and strengths | Exact artifact identity, ordered strengths/routes and resulting model patches |
| `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder` | Prompt/reference/RefMod creation and encoding | Authored/resolved prompt parity, reference hashes/roles, encoder inputs and resulting conditioning |
| `custom_nodes/comfyui-minimaxh3-contex-loop` | Chain execution, continuation and recovery | Effective cut/continue, clip identity, stage lifecycle and between-scene cleanup |
| `.codex/worktrees/workflow-monitor-brain` | Evidence collection and report/comparison UI | Observe the above without rewriting creative inputs; unknown stays unknown |
| Parent `studio/` | Production packages, recipes, compiler and run lifecycle | Narrow versioned contracts connecting project/shot/package/prompt/run/output identities |

Project Suite and Agent Panel are separate repositories from LC123. The installed “Fantastic” prompt component is Fantastic MiniMaxH3 PromptBuilder; no distinct installed repository named “Fantastic Computer” was found.

The other six active roots remain in the same lock: Spark H3, Swarm nodes (two install paths), H3 NativeAudioLock, Manager, websocket reconnect fix, and Hermes nodes. They are preserved; zero saved-node occurrences does not establish non-use.

## LC123 correction: saved-node counts missed global behavior

The earlier audit's `frontend dependency / LCNote only` classification is incomplete and superseded here. `ComfyUI_LC123_nodes/__init__.py:49–51` imports FastCancel, Anima LoRA key conversion and FreeTextEncoder regardless of whether a graph contains LC nodes.

- `lc_free_text_encoder.py:70–87` wraps `CFGGuider.outer_sample`; the implementation checks loaded encoders and unloads those meeting its1GiB threshold before sampling.
- `lc_fast_cancel.py:48–97` installs model-block pre-hooks and uses CUDA events/synchronization to bound queued work before checking cancellation.
- Both `LC123.Optimization.FreeTextEncoder` and `LC123.Optimization.FastCancel` are absent from the current persisted settings file; their implementations default to enabled. This is configuration/source evidence, not an under-load measurement.
- These hooks overlap native memory policy and affect execution even without LC nodes in saved graphs. They must be included in the next controlled integration/benchmark matrix. Do not toggle them based solely on README performance claims.

## Common variables and authority

Keep distinct authored, resolved and observed values for project/shot identity, prompt/reference revisions, seed, geometry/FPS/frames, LoRA/model identity, sampler/attention, stage/cache identity and memory/cleanup state. Each row above owns its narrow values; Brain joins evidence by immutable identifiers. Do not introduce one mutable global configuration object or assume the frontend widget equals the executed input.

## Next acceptance gates

1. Inventory import-time hooks/monkey patches and their order across every active pack, alongside nodes/routes/frontend registrations. LC123 is a verified counterexample to node-count-only coverage.
2. Test the Dynamic panel's partial-residency and cleanup accounting against native model state; idle “no loaded models” is insufficient. Include LC123 defaults, Context Loop cleanup and stage reuse.
3. Bind the intended project/shot/canvas in Agent Panel and Master; verify an actual read-only tool round trip without launching duplicate assistants or generating media.
4. Run a bounded, fixed-input benchmark only after resource/queue checks. Record core and pack revisions, effective settings, encoder/sample/decode phases, CPU/GPU memory, temperature/clocks/power/throttle availability and cancellation behavior. Keep technical and creative acceptance separate.
5. Remove code/packs only after node, global-hook, UI, route, dependency and historical-workflow consumers are accounted for, with recovery evidence. LC123, Dynamic, Project Suite and Agent Panel are critical owners, not retirement candidates based on graph counts.

Fresh evidence: `artifacts/browser-stack-readiness/live-stack.json` records all14clean roots/15paths, live registration candidates, Dynamic's idle snapshot and empty queue. `BROWSER_ACCESS.md` defines the visible browser path and remaining connection gaps.

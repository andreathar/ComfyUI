---
name: comfyui-asset-intake
description: Use for reviewing and filing new ComfyUI reference stills.
---

# ComfyUI reference intake

Read `studio/docs/LOCAL_ASSET_WORKER.md` for exact commands. Use one user-supplied project slug and a bounded inbox of new stills. Don't start by renaming existing `input/` files or touching manifests, stages, workflows or the asset database.

1. Scan with `studio.asset_intake scan`; present unreadable, duplicate and skipped candidates separately. Use local files for inventories and reports; don't paste private filenames, images or metadata into a cloud conversation.
2. If local visual suggestions are requested, pass ready IDs to `studio.asset_vision` on the approved llama.cpp build. Verify ComfyUI is stopped and no other GPU job is active. Prefer this bounded classifier to Hermes `vision_analyze` for private files; never fall back to a remote provider. Treat model roles as suggestions, not approval or path instructions.
3. Build `assignments.json` from reviewed roles and slugs, then generate the plan and the local thumbnail preview. Keep the before/after paths, plan digest and selected IDs together. Existing filenames referenced by workflows or frozen takes stay put.
4. Run `apply` only with explicit human approval of the exact digest and selected IDs. Keep the receipt, verify all statuses and do not silently retry blocked entries. Never invoke `apply` from a classification subagent.

The isolated vision worker works around, but does not fix, the managed Hermes idle-refit bug. For other specialists, reuse the separation of bounded inputs, local judgment, deterministic validation and human-approved writes—not the Qwen launch settings.

# ComfyUI production-stack review guidance

Review the exact repository and changed range provided by the caller. The parent ComfyUI checkout and custom-node checkouts are independent Git repositories. A changed parent lock pin is not the component source diff; identify which owner/range you actually reviewed and which boundary consumers were inspected.

Follow the owning repository's AGENTS.md and accepted task constraints. Preserve public node names, input/output shapes, saved workflows, model formats and existing user state unless replacement is explicitly in scope. Favor the smallest owner-layer correction; avoid universal mutable context objects and parallel implementations of native ComfyUI behavior.

Prioritize concrete changed-code defects: crashes, incorrect dtype/device/residency, stale caches, wrong prompt/reference/model identity, broken continuation, lost project state, credential exposure, false monitoring claims and workflow/API incompatibility. Cite path/line, triggering conditions, user impact and a reproducible check. State uncertainty and missing runtime evidence. Do not infer correctness from a graph's missing edges or a passing test count.

Keep pre-existing issues separate from regressions introduced by this change. Do not request unrelated fixes merely because moved or reformatted lines appear in the diff. An older risk relevant to the new boundary can be recorded as an explicit integration limitation.

## Review focus by owner

- **Core / model execution:** native DynamicVRAM and optimized operations; dtype/device contracts; parameter/buffer/cache lifetimes; offload and memory pressure. No new outbound internet paths in core.
- **Dynamic / LC123:** model-residency accounting, safe queue-aware free/unload, sensor attribution/units and overhead. Include import-time monkey patches, sampler wrapper order, text-encoder unloading, fast-cancel CUDA synchronization and effective enabled defaults even if no pack node appears in a saved workflow.
- **Project Suite / Context Loop:** project/shot/canvas identity, context and stage provenance, cut/continue decisions, frame/FPS contracts, recovery and between-scene cleanup. Operational auto_approve is not human creative acceptance.
- **Agent Panel:** actual tool availability, correct session/canvas binding, reconnect/recovery, input ownership and credential/command boundaries. UI presence is not proof of an agent/tool round trip.
- **Fantastic LoRAs / PromptBuilder:** exact artifact, strength and routing identity; model-patcher boundaries; authored versus resolved prompts and references; encode identity and cache invalidation.
- **Brain:** observation versus inference, prompt/node event attribution, large integer precision, missing-evidence qualification, CSV safety and asynchronous stale responses. Completion is not quality approval, and filenames are not model hashes.
- **Parent Studio:** narrow versioned contracts across owners; authored/resolved/executed variables; immutable packages; embedded compiler code in saved graphs; pin consistency and coordinated rollout/rollback.

Check the relevant tests and evidence, including browser/resource checks when the behavior requires them. A skipped or interrupted review is not a clean review. Preserve severity labels, separate findings from suggestions, and state unreviewed owners and untested scenarios. A review verdict does not authorize automatic fixes, paid generation, model downloads, policy changes, push or merge.

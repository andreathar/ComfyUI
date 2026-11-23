# ComfyUI production-stack review guidance

Review the exact repository and changed range provided by the caller. The parent ComfyUI checkout and custom-node checkouts are independent Git repositories. A changed parent lock pin is not the component source diff; identify which owner/range you actually reviewed and which boundary consumers were inspected.

Follow the owning repository's AGENTS.md and accepted task constraints. Preserve public node names, input/output shapes, saved workflows, model formats and existing user state unless replacement is explicitly in scope. Favor the smallest owner-layer correction; avoid universal mutable context objects and parallel implementations of native ComfyUI behavior.

Prioritize concrete changed-code defects: crashes, incorrect dtype/device/residency, stale caches, wrong prompt/reference/model identity, broken continuation, lost project state, credential exposure, false monitoring claims and workflow/API incompatibility. Cite path/line, triggering conditions, user impact and a reproducible check. State uncertainty and missing runtime evidence. Do not infer correctness from a graph's missing edges or a passing test count.

Keep pre-existing issues separate from regressions introduced by this change. Do not request unrelated fixes merely because moved or reformatted lines appear in the diff. An older risk relevant to the new boundary can be recorded as an explicit integration limitation.

## Follow the changed workflow handoff

Use only the checks that intersect the diff or a changed consumer contract. Trace the producer → actual binding → consumer, including the fallback or retry path; don't infer a binding from matching labels, filenames or values.

1. **Author → resolve → freeze.** Check that saving or revising the selected project/shot changes only the intended fields. Check stale selection/conflicting edits, reference role-to-encoder binding, and actual dependencies from each saved output to the frozen prompt, references (including RefMods) and sampler seed. A correct but unused node or an equal literal seed is not proof of lineage.
2. **Freeze → submit → bind.** Check that the active canvas compiles to the frozen prompt, not just that the tab name matches. Preserve queue, cancellation and resource boundaries. If submission is uncertain, reconcile native history before retrying; don't create a duplicate job or rebind a take to a different prompt ID.
3. **Execute → deliver → collect.** Where changed, verify cut versus continue, approved predecessor identity, raw/trimmed frame and FPS contracts, and cleanup between shots. Check exact native history, a unique matching Suite sidecar and actual saved media hashes. A cached success is not evidence of fresh execution. Missing or ambiguous evidence must not silently turn into a successful take or default value.
4. **Collect → review → approve.** Check that retries and recollection don't overwrite approval, that frozen inputs and output hashes are rechecked at review, and that late Brain responses cannot attach evidence to a different run. Keep successful execution, automated advice, explicit human creative approval and advancing the Suite chain separate. Keep a failed write from leaving a partial final record.

Review the closest existing negative/regression test or name one focused test that would fail on the reported behavior. If the browser, model runtime or another owner must be checked, say what remains unverified instead of claiming a live pass.

## Review focus by owner

- **Core / model execution:** native DynamicVRAM and optimized operations; dtype/device contracts; parameter/buffer/cache lifetimes; offload and memory pressure. No new outbound internet paths in core.
- **Dynamic / LC123:** model-residency accounting, safe queue-aware free/unload, sensor attribution/units and overhead. Include import-time monkey patches, sampler wrapper order, text-encoder unloading, fast-cancel CUDA synchronization and effective enabled defaults even if no pack node appears in a saved workflow.
- **Project Suite / Context Loop:** project/shot/canvas identity, context and stage provenance, cut/continue decisions, frame/FPS contracts, recovery and between-scene cleanup. Operational auto_approve is not human creative acceptance.
- **Agent Panel:** actual tool availability, correct session/canvas binding, reconnect/recovery, input ownership and credential/command boundaries. UI presence is not proof of an agent/tool round trip.
- **Fantastic LoRAs / PromptBuilder:** exact artifact, strength and routing identity; model-patcher boundaries; authored versus resolved prompts and references; encode identity and cache invalidation.
- **Brain:** observation versus inference, prompt/node event attribution, large integer precision, missing-evidence qualification, CSV safety and asynchronous stale responses. Completion is not quality approval, and filenames are not model hashes.
- **Parent Studio:** narrow versioned contracts across owners; authored/resolved/executed variables; immutable packages; embedded compiler code in saved graphs; pin consistency and coordinated rollout/rollback.

## Report

- One finding per root cause. Include severity, changed `path:line`, the broken handoff, triggering condition, user impact and a focused verification. Trace existing guards and callers before claiming failure. If an existing guard handles the case, don't report it as a regression.
- Separate verified changed-code findings from suspected risks and pre-existing limitations. State what was not reviewed or tested; zero findings only describes the reviewed scope. The caller must reconcile coverage against the tool's completion record.
- A review verdict does not authorize automatic fixes, paid generation, model downloads, policy changes, push or merge.

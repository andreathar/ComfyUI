# H3 staged shot 75 implementation plan

Approved specification: ../artifacts/h3-local-workflow-research-2026-11-08.md; user approval msg_01M6Y9WW2D4TBEHT8V6EA83G0Z.

Scope: live canvas configuration and local media preparation. Preserve baseline workflow/takes. No core code edits, new model downloads, or automatic paid API requests. Optional Claude nodes are manual/muted review branches.

- [x] Save live workflow as Andre - H3 Staged Masked Shot 0075.
- [x] Prepare separate 73-frame lossless source; verify first 67 decoded frames unchanged and last six repeat frame 66. Record source/reference hashes.
- [x] Add SAM checkpoint and Object Mask branch; execute only that output, inspect overlay across head turn/hand occlusion. Save mask before freeing resources.
- [x] Replace reference-only encoding with Fantastic RefMod Text Encode feeding masked source latent; wire Edit Composite before exact 67-frame output. Pilot 512x288, 20 steps, same seed/LoRA; preserve source audio availability accurately.
- [x] Add separately controlled Claude source/pilot review branches with strict instructions and no connection into generation; add stage instructions and checkpoints. No render can execute an API request accidentally.
- [x] Validate live prompt, run one local pilot only after mask inspection, monitor resource usage and terminal result. Verify decode/frame count, effective-mask source preservation and inspect matched-frame comparison. Leave creative acceptance pending.

Gate: if mask quality is inadequate, stop generation and deliver the mask for correction. No full-resolution render before pilot review. Reusable files under input/andre_staged_shot75 and .codex/artifacts/h3-staged-shot75.

Encoding checkpoint queued: d791933a-7a95-423f-b855-262d156a5c31. Native encoder log confirms 73 frames, 512x288, zero dropped and 21% latent mask coverage. SaveLatent was not retained because it cannot serialize H3 nested streams; Fantastic internal disk cache is used instead. No core/custom-node code was edited.

Completed pilot e4eac79d-b217-4c5d-8209-9c97434ade4b in 8m33s. Lossless protected pixels and original audio verified exactly; see ../artifacts/h3-staged-shot75/README.md and verification.json. Decode-only replay and saved-file Claude review isolation implemented. Final exact-audio mux is a separate local helper because VHS shortest mux truncates the tail. Cache release completed; human creative review remains pending.

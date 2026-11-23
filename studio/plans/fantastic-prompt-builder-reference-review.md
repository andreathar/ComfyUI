# Fantastic Prompt Builder: reference review for Studio

Scope: make the existing Builder easier to use on short, project-bound shots. The first editor slice is implemented without changing node outputs, saved presets, or the production canvas. Keep first/last-frame comparisons for a separate model-specific experiment.

## Node handoffs and acceptance checks

| Owner | Output and consumer | Acceptance check |
| --- | --- | --- |
| Shot package / Hub | Selected project and shot, reviewed asset roles, prompt source and continuation context | Keep selection explicit; do not infer a production role from a filename or promote a reference to the Hub tail. |
| Fantastic Media Loader | `references: H3_REFS` to the Builder/encode route and Reference Map | Enabled pictures, clips and soundtrack selections must match the reviewed shot. |
| Fantastic RefMod Stack | `mods: H3_REF_MODS` to the Builder/encode route and Reference Map; `labels: STRING` for stack inspection | Check look/voice, active copies and budget. Stack-only labels are not the final labels when media precedes them. |
| Fantastic Prompt Builder | `prompt: STRING` and routed `references`/`mods` to Text Encode | Keep `[Shot 1]`, `<Subject 1>` and existing section syntax. Save and reopen the prompt and editor state together; refreshing the panel changes neither. |
| Fantastic H3 Reference Map | `reference_map: STRING` to Preview Any | Review the evaluated labels with the same bundles that reach Text Encode. The browser panel is a graph preview, not this evaluated output. |
| Fantastic H3 RefMod Text Encode | `conditioning: CONDITIONING`, `reference_map: STRING`, `latent: LATENT` | Verify encoder-visible references, then confirm conditioning and starting latent reach the sampler through the selected recipe. Neither the map nor a successful run proves visual quality. |
| Fantastic LoRA stack | Patched model on the sampling route | Check selected LoRAs and weights separately; LoRAs do not supply reference labels. |

The panel shows visible file/channel bindings and RefMod copy and token estimates, and warns when a cited label changes source during the editor session. It does not compare file contents or detect prior-session rebinding. Scratch browser checks covered two stills reordered under a live citation, non-mutation on refresh, and saving and reopening the node. A synthetic CPU fixture covers repeated look copies and disabled picks; the real-media smoke test below covers the encoder-to-sampler route.

### Real-media handoff check

The same Builder outputs drove the CPU Reference Map and Text Encode. With a still, a clip and its paired soundtrack, a separate audio file and one voice RefMod, both maps returned the same five labels in the same order. Native H3 Text Encode produced conditioning; the scratch cut route passed it through disabled H3 Context to Basic Guider and its starting AV latent to the sampler. The sampler ran one step, then the video VAE decoded five preview frames. Exact prompt history, input hashes, output hashes, runtime logs and Brain resources are recorded in the [local evidence folder](../../.codex/artifacts/fantastic-mixed-handoff-20261121/).

This establishes technical routing for the tested cut recipe, not audio output, per-reference influence, production role approval, active continuation, LoRA quality, or creative acceptance. Both maps share label-generation code. Use the runtime encoder and sampler evidence as a separate check, not the string match alone.

## What exists and what is missing

- Master Studio already links the shot package to the Fantastic Prompt Builder, Media Loader and RefMod Stack, and has a CPU Reference Map preview. Keep the existing saved prompt + editor state, linked preset ownership, and save/conflict rules. The extension has in-progress edits to prompt-source saving; do not fold those changes into this feature.
- `refmod_nodes.py:reference_lines` is shared by the Reference Map and Text Encode. The map uses media first, then active RefMods; use the actual map from equivalent inputs rather than recounting widgets. `studio/master_studio_package.py:package_review` deliberately leaves reference coverage unverified for RefMods, video and likely loader overflow. A CPU map verifies resolved labels/order; it does not establish which frames the encoder saw or which conditioning reached the sampler. Preserve that evidence boundary.
- The RefMod stack supports independent look and voice weights. Above 1 adds copies, with a token cost; it is not merely stronger weighting. The stack and encoder caps reject over-budget RefMods rather than downsize them. `stack_pictures` changes presentation to the text encoder, not the full diffusion reference stack. A token estimate is not a VRAM measurement. Keep a source still or clip, its separate role, and the derived RefMod distinct; do not mistake a RefMod for a LoRA or an endpoint frame.

## First change: one read-only panel beside the editor

**“What this shot will use”** — show project, shot, active mode, and rows with role (identity, wardrobe, location, prop, motion, voice, frame), chosen asset or RefMod, resolved label when applicable, and status. Say `not checked` until evaluated. Distinguish `not selected`, `missing`, `label changed`, `bound`, and `needs review`; never call a file approved just because it loads. Reuse the existing CPU map/preview; verify equivalent inputs or display `unverified`. Frame slots use the selected recipe's actual input mapping, not REF numbering guessed from list order.

Show an explicit before/after review when media insertion, reorder, disabling, soundtrack selection, or RefMod copies change numbering. A stale `<Picture 2>` can still exist and point to the wrong source: compare the resolved source/member and channel as well as the label. If stable source identity is unavailable, show an ambiguous mapping and ask the user to check it. Existing prompts may have free text; do not silently rewrite numbers or save preset changes. Design from read-only rows first; consider a structured output from the existing map only if its string interface cannot carry identity cleanly. Preserve its existing output contract and keep the writer separate from the map.

## Second change: help choose a smaller reference set

- Default to **showing suggestions**, never changing the active stack. A reasonable starting suggestion is one clean still per needed identity and a location/prop still only when the shot needs it. Add a second angle, distinct outfit, motion, or voice for a named purpose. Keep the library intact. Disable voice references in the suggested silent profile, not in loaded presets.
- Show channel, weight, expanded copies, and subtotal for each active RefMod using the stack's existing expansion and token accounting. Hint: “Above 1 adds copies”; “The cap stops an expensive run; it doesn't shrink the refs”; “Fewer encoder pictures do not remove diffusion latents.” Keep known RefMod cost separate from media estimates; show unknown rather than guessing total. Surface provenance when available and don't ask users to re-encode or fabricate it for older files just to open the editor.
- Add small, mode-aware hints: `[Shot 1]` opens this clip, `<Subject 1>` identifies a subject, and Camera describes one move in prose. Keep the Builder's REF definition/retention/body structure and enabled sections. **Insert** chips use resolved labels only; Qwen can suggest shot wording from a reviewed slate, not assign tags or save prompt/library changes on its own.

## Verification and rollout

1. CPU-only fixture and scratch canvas: raw picture + image RefMod, mixed video/audio, disabled picks, repeated copies, reordered inputs, and valid-looking stale labels. Verify map against the same loader/stack inputs, preserve REF section order, test slot-role conflicts, and preserve open/edit/save behavior for old presets. No render or existing project changes in this slice. Initial implementation is one read-only Studio/Fantastic UI surface, not a new node chain.
2. With separately approved GPU work, test a short pilot using one identity still plus the reviewed location. Compare one extra reference or one RefMod variant at a time; keep shot, seed, recipe and other settings fixed. Record loaded source, encoder visibility, reference token estimate/actual counts where available, time and memory in Brain evidence. Review identity, setting and action separately. Stop when the decision about reference preparation is answered.
3. Later, compare first-only versus first-plus-last on the same model when the ending matters, then repeat on a different supported model if useful. Freeze each model's recipe for its own comparison, and score landing, motion path and continuity separately. Do not infer universal frame behavior from a single model or change the bootstrap defaults based on unsupported wiring.

Local source anchors: `studio/build_master_movie_studio_workflow.py` (reference UI and subgraph wiring), `studio/master_studio_package.py:package_review`, `studio/prompt_review.py`, Fantastic `refmod_nodes.py:reference_lines` / `MiniMaxH3FantasticReferenceMap` and `refmods.py:MiniMaxH3RefModStack`. See `studio/docs/REFERENCE_STRATEGY.md` and `.codex/artifacts/refmod-audit-20261115/REPORT.md` for prior evidence.

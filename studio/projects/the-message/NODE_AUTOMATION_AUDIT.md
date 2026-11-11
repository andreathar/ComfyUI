# Installed automation nodes — 2026-11-10

Checked the connected server's live node registry and the current 26-node Shot
Template. These nodes are registered but absent from that template. Registration
is not a successful integration test. No extension installation is needed for
the candidates below, and the running tk004 validation graph was not changed.

| Candidate | Useful job | Adoption boundary |
| --- | --- | --- |
| Context Loop: `MiniMaxH3ChainPlanModern`, Preflight, LoopStart, Current, SegmentSave, LoopEnd, Assemble | One scene plan, sequential sampling, durable checkpoints and assembled output | Best installed foundation for a future one-Run production graph. Qualify its reference and recovery contract before replacing the current tracked panel sequence. |
| `MiniMaxH3ProjectAssetCarousel`, Tagged Picture/Video/Audio and Tagged Ref2VA | Named project assets activated by prompt tags, automatic reference numbering | Its typed tagged registry is different from Fantastic's saved RefMod bundle. The documented external_refmod experiment targets another pack and cannot carry reference audio; it is not a drop-in migration for Andre's identity and voice. |
| `MiniMaxH3ChainPlanStudio`, RunManager, CheckpointManager | Scene timeline, saved runs, branches and previews | Plan Studio is marked experimental. Use it as a production workspace after qualifying the core loop. Do not create a separate workflow tab for every shot. |
| `DynamicLoadTextFileNode` and `DynamicScriptNode` | Read one production/shot JSON and extract typed variables | Useful for replacing panel widget writes with file-driven inputs. The loader exposes errors on a separate output; validate them. Keep the parser deterministic and avoid its shared cache or queueing inside scripts. |
| `MiniMaxH3TokenCounter` (KJNodes) | Report text, image/video-reference and audio-reference sequence cost | Best small diagnostic addition after this pinned validation. Attach to encoder latent/conditioning with a PreviewAny; keep sampler connections direct. Counts require encoding and are not a VRAM prediction. |
| `MiniMaxH3FantasticRefModInspect` / Edit / Create | Inspect stored identity/location frames; create and revise reference candidates | Use a reusable reference-preparation workflow and immutable versions. Inspect and approve once per asset version, not once per shot. Never overwrite an approved master. |
| `BFSH3DescribeReferences`, `BFSH3BuildNativePrompt`, native `TextGenerateV2` | Independent image descriptions and structured prompt assistance | Run once during reference preparation with a verified generation-capable local VLM. The H3 text encoder is not automatically a suitable text-generation model. Cache approved descriptions in the asset registry. |
| `GetImagesFromBatchIndexed`, `FastPreviewBatch` (KJNodes); VHS video loaders | Pick source frames and inspect reference batches | Useful in the reference-preparation graph with explicit frame caps. A contact sheet helps review but does not prove identity or geometry consistency. |
| `BFSShotPlanner`, Unpack, Seed, Join | Cut an existing performance video into model-sized shots and reconstruct it | Good for source-video adaptation. It is not a prose-script-to-shot planner; don't replace our script records with it for this production. |

## Recommended order

1. Finish the three prepared tk004 shots and their assembled draft using the
   current graph. Preserve the comparison and provenance baseline.
2. Add the token-cost diagnostic and qualify a file-driven shot-variable input
   against the existing compiled recipe. A changed file must invalidate the
   inputs; a missing file must stop submission rather than reuse stale values.
3. Qualify the installed Context Loop on two short scenes: one run, distinct
   scene outputs, interruption/resume without duplicate takes, preserved RefMod
   identity/voice labels, and draft assembly. Keep the Fantastic encoding path
   until a replacement reproduces its reference contract.
4. Move the qualified sequence into one production workflow with scene and asset
   controls. Keep one separate reference-preparation workflow and saved project
   data. Human approval remains distinct from automatic technical validation.

`MiniMaxH3PendingReview` defers a candidate batch for later review and stops at
that scene; it is not an automatic whole-movie approval switch. Review Gate and
Loop End settings need an explicit draft-versus-approved contract.

Comfy Dynamic's Universal Selector queries names/options; it does not itself
manage model VRAM or guarantee that a selected model fits this GPU. Keep the
qualified model recipe and sequential GPU use. Experimental reference caches,
attention changes and new model downloads are outside this automation audit.

## Evidence

Follow-up wiring inspection found a migration path that does not require Tagged
Ref2VA: Context Loop Current Shot supplies prompt, seed, length, steps, width and
height as ordinary sockets. These can drive Fantastic RefMod Text Encode and
the current sampler directly. A file-driven selector would supply Fantastic
Stack/Media Loader state for the same scene index. This is a compatibility
proposal, not a tested graph.

For the existing hard-cut cafe test, Generation Profile exposes `Independent
scenes` and `Generate fresh audio per scene`. Plan supports explicit raw `length`
to retain the prepared 56-frame timing. Segment Save requires delivered frames
and audio from Loop Trim; use that path even when independent scenes have no
overlap. Review Gate disabled returns "review bypassed", rather than recording
a human decision. Any such automatic run must remain a draft in our ledger.

No matching MiniMax/H3/Context Loop pack was found in the 56 bundled installer
packs returned by the connected tool. The already-installed extension supplies
its own maintained example workflows and documentation.

- Live `comfy_cli search_nodes` and `create_workflow action:node_info` responses,
  saved under the validation folder's `node-audit.json`.
- Installed Context Loop README, `docs/NODE_REFERENCE.md` and
  `docs/SCHEDULED_REFERENCES.md`, especially External RefMod experiment.
- Installed BFS `H3_NATIVE_AUTO_PROMPT.md` and README Shot Loop section.
- Installed Comfy Dynamic README and `nodes/dynamic_load_text_node.py`.
- Installed KJNodes `nodes/minimax_nodes.py`, `MiniMaxH3TokenCounter`.
- Official ComfyUI [node expansion](https://docs.comfy.org/custom-nodes/backend/expansion)
  and [lazy evaluation](https://docs.comfy.org/custom-nodes/backend/lazy_evaluation),
  retrieved through Context7: loops and conditional execution require real
  execution contracts, not simply a list of UI controls.

## Applied reference repair

The template now has 28 nodes: the 26-node generation path plus Fantastic
Create RefMod and Inspect RefMod in a separate muted group. Café background v2
was created and its three independent image latents inspected. Andre's existing
video reference was inspected as a complete clip; independent latent-slice
previews were misleading. No identity replacement was needed.

This audit's original 26-node inventory is historical.

## Executed automation follow-up

The saved **The Message - Automated Draft** now combines Context Loop with
Comfy Dynamic file loading/selectors and the existing Fantastic encoder/sampler.
One recursive execution generated SH01 and SH02, selected their different
reference sets, saved each checkpoint and assembled the draft. The CPU recovery
diagnostic loaded a verified 2/2 manifest and selected scene 2; all ten checked
media/checkpoint files retained their hashes. No crash or resumed sampling was
tested. See [AUTOMATED_DRAFT.md](AUTOMATED_DRAFT.md) for controls and limits.

Token diagnostics, Plan Studio, Tagged Ref2VA and automatic reference description
remain unqualified candidates. The two-shot test does not establish likeness,
dialogue continuity or exact environment reconstruction.

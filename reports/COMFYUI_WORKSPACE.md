# ComfyUI workspace — 2026-11-10

**Direction confirmed by the user:** work inside ComfyUI, customize the existing extensions, and manage local models there. No separate Studio/Argon production application. Pause Andre swap-quality work while organizing and learning the tools.

## Workflow browser

Refresh the browser's workflow list after this reorganization. Graph contents and filenames were preserved; folders changed.

| Folder | What it is for | Current status |
| --- | --- | --- |
| **01 - Images** | SD1.5 draft, Klein Q8 generation, SD1.5 editing, bounded RealESRGAN upscale | Four previously backend-tested workflows; browser load/serialize/reopen now pass with unchanged execution prompts; creative approval remains separate |
| **02 - Video - Experimental** | Complete MMH3 RefMod pipeline, current H3 three-view canvas, staged encode/sample, native H3 image-to-video | RefMod wiring/browser/model-free math checked; full rendering remains unqualified |
| **03 - Project Tools - Review Required** | Existing H3/Andre project tools plus a minimal Project Hub browser | Mixed readiness; see below |
| **04 - Utilities** | LC123 prompt/palette test | Backend-tested composition; does not validate prompt meaning |
| **05 - Video Review** | Bounded local clip frames, no models | Browser roundtrip and 24-frame local decode passed; fixed 512×288 centre crop, no sound preview or H3 import |
| **90 - Lab and Older Workflows** | Other originals, comparison tests, alternatives, recovery canvases and examples | Preserved but not advertised as daily tools |

### Daily image tools

- **PC Test 01 - SD15 512**: fast drafts.
- **PC Test 02 - FLUX2 Klein Q8 512**: the strongest subject match in the earlier small pilot; not certified for identity preservation.
- **01 - SD15 Image Edit 512**: low-strength img2img, not instruction editing or reliable identity transfer; square inputs avoid stretching.
- **02 - RealESRGAN Bounded Upscale**: preserve aspect ratio, limit the longest side to 512, then upscale 4× with native tiling. Decoding a huge source image still happens before resizing.

**Z-Image is retained in Lab:** its current pilot file's SHA-256 differs from the earlier safety-reviewed copy. This may be only a UI edit, but the old runtime receipt cannot certify the current file. Its contents were preserved and the runner's safety hash was not silently updated. The other three pilot hashes still match their reviewed copies.

No image/video batch is running automatically.

## Small toolset worth retaining

| Role | Existing owner |
| --- | --- |
| Image/video sampling and model loading/offloading | Native ComfyUI |
| Quantized Klein loading | GGUF provider; current `UnetLoaderGGUF` owner is `comfyui-gguf-loader` |
| Video/audio input and combination | VideoHelperSuite and native nodes |
| H3 clip-project review and continuation | H3 Project Suite |
| H3 reference/prompt/masked editing | Fantastic MiniMaxH3 PromptBuilder |
| Andre preparation/staging | `comfyui-andre-shot-swap`, currently experimental |
| Shared canvas wiring/controls | KJNodes Set/Get and native primitives |
| Monitoring and deliberate cleanup | `comfyui_dynamic` control panel |
| Optional comparison experiments | ReActor, LC123, iTools; retain until their actual uses are classified |

Some current H3 canvases also require `comfyui-fantastic-loras` and `comfyui_dynamic`. Core already supplies H3 inference, SAM3, math and resolution nodes; extra packs are not needed merely to provide those roles.

## Project management is already partly present

**H3ProjectHub → Open project…** opens the existing H3 project panel. Data lives in `output/h3_projects/`. This manages H3 clip chains, not a complete movie-production database.

Added **Project Hub - Browse Existing (no generation)** under folder 03. It selects the existing `Andre shot0075 three view pilot`, with `create_if_missing=false`, and connects only its status to a preview. It has no model loader or sampler. Static node/link and UI/API correspondence passed. Browser load, serialize/reopen and **Open project…** were subsequently verified: the existing project panel opened with its pending clip, without queueing or approving it. Executing the backend graph was not tested. The existing project's name can be changed in its Hub widget. Optional VAEs are not wired, so this is not a footage-encoding/import preset.

Existing AIO/project-review graphs are not all ready:

- Prompt Builder AIO still references absent rgthree nodes and unavailable model selections.
- Andre Local Review's LM Studio endpoint at port 1234 was unavailable during the audit.
- Andre's replacement-generation service uses **paid Kling**, even without the `kling-direct` extension. No paid generation was run.
- H3 face-refinement/character-sheet examples have missing or disabled dependencies.

Do not reinstall all missing packs simply to make every example pass. Keep these in review/lab until a specific useful operation justifies them.

## MMH3 RefMod automation

Added **MMH3 RefMod - Complete Local Pipeline** under **02 - Video - Experimental**, using the official vanilla topology and local reference-capable models. RefMod/media selection → prompt → encode → AV sampling → video/audio decode → optional edit composite → local save are connected, without the missing switch packs or H3 project-import path.

Browser roundtrip and live-schema/link checks passed; a separate model-free execution verified routing and 608×352/56-frame generation math. **No full render is qualified yet.** Choose/create actual references and write the prompt first. Masked edits use the source's trimmed length and restore source resolution; generation settings do not bound final edit output. [Usage, models and limits](MMH3_REFMOD_WORKFLOW_2026-11-10.md). The approved **MMH3 RefMod - Create New and Generate** variant now connects native RefMod creation directly into generation, with a multi-file source picker. Name/source configuration is required; upload and wiring tests passed, but actual model creation/full rendering remain unqualified. Use the original pipeline for subsequent takes to avoid recreating assets.

## Shared controls inside ComfyUI

For future edits to the selected canvases, use one visible **Controls / Models** group and one source per value:

- Project: the H3 Hub's project name, not a parallel external database.
- Width/height: Hub outputs for an existing H3 chain; a Resolution Selector with `multiple=32` for a new chain. Do not overwrite dimensions of existing clips.
- FPS, seed, steps and prompt: native primitives/widgets, distributed only where necessary.
- Model, text encoder, video VAE and audio VAE: native loader outputs; graph-local KJ Set/Get only to reduce repeated wires.
- Reference image, input clip and masks: explicit graph inputs. The identity master is not yet approved.

The four daily image canvases now use consistent native **Models → Input → Settings/Processing → Output** groups, with clear node titles and initial views. Their links, widgets and generation values are unchanged. These are graph-local controls, **not one global settings panel**. The new MMH3 RefMod canvas has explicit grouped controls; its full model render remains to be qualified. Other large H3 canvases remain experimental.

## Dynamic local model management

These are different features:

1. Native ComfyUI handles automatic model loading, partial unloading and dynamic residency. Keep the canonical launcher's existing 1 GiB reserve and disabled pinned memory; avoid adding a second offload manager.
2. `comfyui_dynamic` monitors residency and offers manual cleanup. Its Free VRAM operation unloads models and empties the device cache; busy cleanup can be deferred. It does **not** promise to release all CPU RAM or node-cache references.
3. Dynamic Switch Any requests only the selected lazy branch. Switching a branch does not itself evict previously cached weights.
4. KJ Set/Get are frontend virtual connections—not global variables, persistent storage or memory management.

Use one generation job at a time on this 6 GiB GPU. Never trigger manual unloading in the middle of a job. Two GGUF packs export overlapping names; provider removal requires a controlled restart and loader test, not a name-based guess.

## Cleanup performed

- Removed nine retired demonstration workflows and three matching sidecars from the active browser: three disabled NVIDIA RTX demos, two Claude API examples and four Agnes API examples.
- Removed three **already-disabled** provider directories from `custom_nodes`: two redundant ReActor installs and the retired NVIDIA RTX pack.
- These were moved into local recovery storage, not irreversibly erased. SHA-256 manifests record every archived regular file.
- Reorganized 61 saved graph/metadata files without changing their contents; added only the small Project Hub browser graph.
- Updated the test runner's source paths. All **195 Studio tests passed** after the reorganization; these remain maintenance/evidence tools, not the chosen production interface.
- Verified an empty server queue, the reorganized filenames through ComfyUI's own workflow-list API, all archive/relocation hashes, and no registered custom-node provider whose corresponding directory/file was absent.

Receipts: `.codex/artifacts/production-cleanup-20261110/retirement-manifest.json` and `workflow-relocation-manifest.json`. A superseded external-Studio experiment is preserved only as audit evidence; its draft sheet/template and code changes were withdrawn after the user's clarification. Its one 512×512 Klein reference test completed, but it is not an adopted production workflow.

**No models, Andre references, source clips, project records or prior renders were deleted.** Model storage resolves through `/home/athar/ComfyUI-models` to shared `/mnt/data/ComfyUI-models`, with intentional NVMe hot copies. No large weight was proven globally unused. Keep SD1.5, Klein, Z-Image, RealESRGAN and the H3/SAM/identity dependencies until their retained consumer paths are qualified; do not remove a shared encoder or an alternate VAE based only on a saved-graph filename search.

## Next bounded work

1. Browser library and Project Hub panel verification: **done**, in an isolated Chrome session, without queueing.
2. Consistent controls layout in the four daily image canvases: **done**; browser-generated execution prompts match the previous layouts exactly, ignoring display titles.
3. H3 tool qualification: **read-only availability and source review done**; [findings and limits](H3_TOOL_QUALIFICATION_2026-11-10.md). Keep the small Hub for browsing. The larger review graphs can start background imports; silent-import AV continuation has a source-level contract defect. The native i2v example selects a model not advertised by the running loader. The bounded [local clip-review graph](LOCAL_CLIP_REVIEW_2026-11-10.md) is now available in **05 - Video Review**, with browser roundtrip and local decoding verified. Next: import-contract fixes/tests before qualifying continuation—not standardizing the large canvases or removing active providers/weights.

4. At the user's request, the complete **MMH3 RefMod** generation/edit chain is now saved in folder 02, with native library/media pickers and local model selections. Wiring and model-free checks passed; actual reference selection and full render qualification remain. The approved connected **Create New and Generate** variant is also saved, with upload/serialization safety checks; see the RefMod report for asset naming, persistent input copies and reuse instructions.

The installed frontend still opens its bundled example in a fresh session. Changing the root `default_workflow.json` did not affect it, so that experiment was rolled back rather than patching installed frontend files. Open a daily workflow from **01 - Images**; existing browser tabs were not changed. Details and screenshots: [browser/controls verification](WORKSPACE_UI_2026-11-10.md).

No new downloads, paid calls, server restart or automatic project-generation jobs were performed in this cleanup.

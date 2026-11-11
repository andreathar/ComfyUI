# MMH3 RefMod — complete local pipeline

Open **02 - Video - Experimental → MMH3 RefMod - Complete Local Pipeline** in ComfyUI.

This is the complete connected generation/editing chain from the official **MMH3_RefMod_Vanilla_Stack_Example**, adapted to the installed models. The original examples are unchanged. It does not add a separate application, a batch runner or automatic creative approval.

## Use

1. In **Choose / create saved RefMods**, click **Browse library…** or **Create…**. Alternatively, use the **Media Loader** picker for one-off pictures, clips or sound. The library was empty during verification; no actor or footage is preselected.
2. Open **Edit prompt**, in REF mode. Draft from selected RefMods if useful, then describe the shot. Check the combined reference map: ordinary media are labelled before RefMods; a multi-photo RefMod may be a `<Video N>`, not several `<Picture N>` references.
3. Choose generation size/duration, sampling steps and seed. **Run** executes the wired chain:

   **RefMods + optional media → prompt → H3 text/reference encode → AV sampling → video and audio decode → optional masked-edit composite → video assembly → local save.**

Outputs go under `output/video/MMH3_RefMod/<date>/`. Sound comes from the generated audio latent; this graph does not promise unchanged source audio. Human review still owns identity, performance and edit acceptance.

### Generation versus masked editing

- **New generation defaults:** 608×352, requested 2 seconds, aligned to **56 frames (~2.33 seconds)** at 24 fps; 20 sampler steps; base video/audio shifts 12/3; fixed seed 0.
- **Masked edits:** select and trim/cap the source in the Media Loader before running. The source's aligned length overrides the generation duration. The resolution selector supplies a **sampling pixel budget**, not a final-output bound. Composite `max_size=0` restores source resolution and source pixels outside the edit area. Long/untrimmed footage is not made safe by the 2-second generation widget.
- RefMods keep their saved reference size; the small generation setting does not bound every reference allocation. Large reference stacks and clips can still be expensive on the 6 GiB GPU.

## Local models, not silent substitutes

The upstream example selects a hybrid diffusion model and a heretic encoder that are not advertised by this installation. This derived graph explicitly selects:

- `minimax_h3_ref2va_pruned_int8_convrot.safetensors`
- `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, CLIP type `minimax`
- `minimax_h3_video_vae_int8_convrot.safetensors`
- `minimax_h3_audio_vae_fp32.safetensors`

REF2VA is reference-capable, but it is **not the upstream hybrid** and no equivalent quality is claimed. No turbo LoRA, approximate Reference Cache patch or duplicated RefMod Apply is inserted. Native ComfyUI owns loading, caching and offloading. Missing rgthree switches, KJ preview overrides and Fantastic seed/LoRA controls are not needed by this vanilla topology.

## Verification and limits

- Built through the running native frontend; load → serialize → reopen produces the same API prompt. Exported JSON omits optional null serializer fields that otherwise trigger frontend schema warnings.
- Opened the RefMod library, Media Loader and native multi-file chooser in an isolated browser. No asset selection/upload, queued model job, page error or schema-warning toast.
- All **25 backend node types**, required inputs, model selections and connected data types checked against the running schemas. Current V3 autogrow math inputs are retained. Known library UI-button literals are ignored by `execution.py` and are not backend dependencies.
- A separate **model-free** execution exercised empty stack/media routing, prompt/reference-map routing and size/duration math. Results: **608×352, 56 frames, “No references.”** Queue empty afterward. This deliberately did not submit the model/sampler/save branch.
- Focused review found that edit duration/output size override generation controls. Node titles and instructions now state this explicitly; no broken AV/composite/save links were found.
- **The derived Scene 01 learning workflow has now completed one configured full render:** 608×352, 56 frames, 20 steps, seed 0, actor reference plus room picture, ~9 min 44 s. The UI’s 4,440-token actor count was not runtime-attested; the later live identity catalog reports 7,104. [Run evidence](THE_MESSAGE_SCENE01_TAKE01.md). This is not a general performance benchmark or identity/source-audio-preservation certification; creative acceptance is pending. The base template's empty selections still require configuration. No cached earlier Andre output is presented as a test.
- No models/packages downloaded, paid calls, server restart, project import, clip approval or background generation enabled. Only the small model-free utility prompt created normal execution history.

Evidence: `.codex/artifacts/mmh3-refmod-20261110/` contains the builder, live schemas, roundtrip prompt, browser result, model-free test and history. The local clip picker fix has its own [verification report](LOCAL_CLIP_REVIEW_2026-11-10.md).

## Create a new RefMod and generate in one run

The approved additional workflow is **02 - Video - Experimental → MMH3 RefMod - Create New and Generate**. Refresh ComfyUI once for the new source-picker button. The existing reuse workflow above is unchanged.

1. On **CREATE NEW RefMod**, click **Choose source media…** and select pictures, clips and/or audio. Each selection replaces the source list. The new button uses the existing local upload endpoint without imposing the ordinary reference loader's 9-picture slot limit.
2. Enter a **new unique asset name**; choose Full/Compressed Reference, concept, reference resolution/frame/audio settings and optional subject descriptions. Sources and name are intentionally empty initially. The picker selects files as-is; it does not add a crop/trim editor. Prepare files beforehand or use the existing library preparation tools when that editing is needed.
3. Write the REF-mode shot prompt before running. With no optional generation media or additional saved RefMods, a single picture is `<Picture 1>`, a photo stack or clip is `<Video 1>`, and a voice is `<Audio 1>`. Adding other media changes label numbering. The new asset's reference map becomes available after creation; frontend drafting cannot inspect a not-yet-created asset.
4. Run once: **Create/save RefMod → Stack → Prompt → Text Encode → Sample → video/audio decode → composite → video save**. The create node's actual `mods` output is connected directly into the generation chain. A filename preview lists the saved asset files.

**Lifecycle:** Create always runs and refuses existing names. A later sampling failure does not roll back a successfully saved RefMod. After creating, select it in the original **Complete Local Pipeline** for further takes; do not repeatedly create it. New creation runs require new names. Existing backend preview-writing failures are not claimed to be transactional.

Uploads are ordinary persistent copies under `input/minimax_h3`, including files uploaded before a later selection fails or is replaced. They are not automatically deleted; originals are untouched. A failed selection retains the previous source list. Saving/queue serialization is blocked while uploads are pending, preventing accidental creation from stale selections.

**Additional verification:** browser roundtrip preserves the new links; actual native multi-file picker and one local image upload passed, including source JSON persistence and independence from the generation Media Loader. Ten-source routing and upload-failure handling were tested with mocked local upload responses; delayed-upload testing verified that prompt serialization is blocked until completion. Submitting the unconfigured graph was rejected with **“Give the RefMod a name.”**, with the library unchanged and queue empty. No RefMod or full video was created as a test, so model creation/render performance and quality remain unqualified.

Evidence and frontend recovery copy: `.codex/artifacts/refmod-create-generate-20261110/`. The only extension change for this addition is the Create node's source-picker integration in `custom_nodes/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder/web/refmodstack.js`; no backend changes, packages, downloads or server restart.

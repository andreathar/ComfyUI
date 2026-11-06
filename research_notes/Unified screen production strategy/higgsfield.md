# Higgsfield: identity, keyframes, performance transfer, and production handoffs

Research date: 2026-10-30. Read-only investigation; no media generation, uploads, training, purchases, model downloads, or application changes. Live account authentication and schema retrieval succeeded. Installed CLI: `higgsfield 1.2.2 (53301eadf7311fc6a6a4c024cf4aff432028e974)`, built 2026-10-16. No generated-output quality claims were tested.

Evidence retention: every `/tmp/opencode/higgsfield-research-*.json` schema cited below is also copied, under the identical filename, to the sibling [higgsfield-evidence directory](higgsfield-evidence/). Exact version, catalog, motion-control workflow schema and naming/help checks are preserved in [cli-discovery.json](higgsfield-evidence/cli-discovery.json). These durable local snapshots are the primary evidence for live CLI claims.

## 1. What should Soul own, and what does character consistency actually mean?

### Takeaway

Use Higgsfield primarily for approved character looks and shot-specific first/last stills, then give the actual motion generation to the user's separately funded Kling account. Soul identity training and Soul V2 image generation are different operations; neither establishes an automatic voice, wardrobe, location, or cross-platform identity lock.

### Cited Findings

- **Soul ID is a reusable trained face reference; Soul V2 is an image generator.** Training returns a Soul reference ID, passed to compatible image generation as `--soul-id` / `custom_reference_id`. Training is not necessary to use prompt-only Soul V2, and a one-shot image reference is not equivalent to training. [Official CLI README](https://github.com/higgsfield-ai/cli#soul-id); [models](https://github.com/higgsfield-ai/cli/blob/main/MODELS.md#text2image_soul_v2--higgsfield-soul-v2).
- Installed `higgsfield soul-id create --help` explicitly offers `--name`, `--soul-2`, `--soul-cinematic`, and repeated `--image` **5–20** times. The public README example shows only three photos: use the installed command's 5–20 contract, not that shortened example. Local photo guidance recommends 8–12 varied, sharp photos of **one person**, clear eyes, varied angles/light/expression, ideally at least 1024×1024; avoid group photos, sunglasses, repeated poses, face-obscuring hats and heavy filters. [Local skill](file:///home/athar/.claude/skills/higgsfield-soul-id/SKILL.md); [photo guide](file:///home/athar/.claude/skills/higgsfield-soul-id/references/photo-guide.md); [conflicting abbreviated README example](https://github.com/higgsfield-ai/cli#soul-id).
- **Live Soul V2 schema:** image output; required `prompt`; scalar nullable `custom_reference_id`; at most **one** `image_references` entry; `quality` `1.5k|2k` (default `2k`); aspect ratios `1:1,16:9,9:16,4:3,3:4,3:2,2:3` (default `1:1`); optional `seed`, `style_id`; `style_id` cannot coexist with an image reference. No `duration`, video, audio, `start_image`, or `end_image` inputs. [Live schema snapshot](file:///tmp/opencode/higgsfield-research-text2image_soul_v2.json); [public model reference](https://github.com/higgsfield-ai/cli/blob/main/MODELS.md#text2image_soul_v2--higgsfield-soul-v2).
- **Soul Cinematic also outputs images**, not video, despite its name. It exposes a scalar Soul ID, at most one image reference, the same quality tiers, and adds `21:9` to Soul V2's ratios. [Live schema](file:///tmp/opencode/higgsfield-research-soul_cinematic.json).
- **Soul Location is prompt-only:** no image reference, identity, or quality field in the live schema. Ratios include Soul V2's set plus `21:9,9:21`. It is suitable for originating a location look, but this schema does not expose reference-conditioned preservation of an existing location. [Live schema](file:///tmp/opencode/higgsfield-research-soul_location.json).
- Seedream 5.0 Pro exposes up to **10 image references**, `resolution=1k|1.5k|2k`, width/height, inpaint and background-removal fields. The installed skill recommends it for character sheets and one-shot face reference work; that is workflow guidance, not evidence of perfect identity preservation. [Live schema](file:///tmp/opencode/higgsfield-research-seedream_v5_pro.json); [generation skill](file:///home/athar/.claude/skills/higgsfield-generate/SKILL.md).
- Reference images, first frame, last frame, reference video and reference audio are distinct roles. The CLI accepts local files or its own upload/job UUIDs and auto-uploads local paths. Higgsfield-hosted Kling 3.0 declares first/last frame roles; this documents that hosted integration, **not** every direct Kling mode. [Media role guide](file:///home/athar/.claude/skills/higgsfield-generate/references/media-inputs.md); [official model reference](https://github.com/higgsfield-ai/cli/blob/main/MODELS.md#kling3_0--kling-v30).

### Inferences

- **Recommended identity package:** separate `CHAR_A` identity from `WARD_A01` wardrobe, `LOC_02` location, `PROP_03`, and the project look bible. Approve front/three-quarter/profile portraits and a full-body wardrobe view. Generate views separately and assemble a sheet locally if a generated multi-view sheet drifts.
- **Multiple characters:** Soul V2's single Soul ID is not a multi-character identity-binding interface. Prepare each character separately, then compose an approved two-person frame locally or use a multi-reference image model such as Seedream. Preserve explicit screen positions and character-to-reference assignments. Feed the approved composition to video, rather than expecting two Soul IDs to work in Soul V2.
- **Keyframes:** generate two distinct still jobs: beginning-state and ending-state, with the same identity, clothing, set, lens, light and screen direction. Use the approved first still as the one image reference when creating the end still if appropriate. Soul does not synthesize a temporal trajectory; downstream Kling must make that trajectory plausible. Two attractive but geometrically incompatible frames are poor endpoints.
- Prefer 16:9 through the first production pass for broad interoperability. Native Soul V2 21:9 is unsupported; use Soul Cinematic or an explicit local crop/outpaint step if the film requires a wider frame. The `2k` label is a model quality tier, not proof of a particular exported pixel dimension.
- A Soul ID is provider-local. Transfer **approved image files**, not the Soul UUID, to Kling and ComfyUI. A character-specific voice must have its own ID and reference record.

### Gaps

- No generation was run; facial accuracy across angles, nonhuman/fictional-character training, wardrobe stability, multi-character separation, and endpoint adherence remain untested.
- Training-variant interchangeability between Soul 2 and Soul Cinematic was not established. Select the variant for the intended image model and verify before training; do not assume one trained reference necessarily works identically everywhere.
- Exact output pixel dimensions, codec/bit depth, determinism across reruns and model updates, and seed behavior are not established by the schemas alone.

## 2. What exactly is Genjutsu, and how should phone performance capture be used?

### Takeaway

Genjutsu is existing-video transformation with two distinct operations: Motion Transfer rebuilds the scene around retained motion/camera/timing; Object Swap selectively replaces elements. It is a strong candidate for difficult, physically staged performances, but not a documented arbitrary start/end-frame animator or a substitute for capturing the desired choreography.

### Cited Findings

- The official page explicitly describes **Motion Transfer** versus **Object Swap**, supports character/outfit/product/location/object references, and says “Shoot on your phone.” Its preservation claims are vendor claims rather than this researcher's measurements. [Genjutsu product page](https://higgsfield.ai/genjutsu).
- The page specifies **4–30-second reference videos** and **up to 30 reference images**. It advertises Genjutsu Lite at up to 30 seconds, 720p/1080p. [Official FAQ and Lite banner](https://higgsfield.ai/genjutsu).
- Unfiltered `higgsfield model list --json` returned four entries: `hf_mult_motion_control` and `hf_mult_replace_object` displayed as **Genjutsu**; `hf_mult_motion_control_flash` and `hf_mult_replace_object_flash` displayed as **Genjutsu Lite**. Live `model get` succeeds for all four. [Motion Transfer schema](file:///tmp/opencode/higgsfield-research-hf_mult_motion_control.json); [Object Swap schema](file:///tmp/opencode/higgsfield-research-hf_mult_replace_object.json); [Lite Motion schema](file:///tmp/opencode/higgsfield-research-hf_mult_motion_control_flash.json); [Lite Swap schema](file:///tmp/opencode/higgsfield-research-hf_mult_replace_object_flash.json).
- All four schemas require, through validation rules, **exactly one video reference and at least one image reference**, even though the individual fields say `required:false`. They accept optional nullable `prompt`, and `resolution` default `720p`. Standard Motion/Swap and Lite Motion enumerate `480p,720p,1080p`; Lite Swap only `720p,1080p`. The Lite Motion 480p schema exceeds the public Lite banner; recheck before relying on it. [Four live schemas above](file:///tmp/opencode/higgsfield-research-hf_mult_motion_control.json).
- These schemas expose **no duration, aspect-ratio, audio, seed, first/last-frame, orientation, mask, per-character slot, or explicit preservation-strength parameter**. They do not encode the public page's 30-image maximum or 4–30-second bounds. Do not infer that the absence of these validation rules makes inputs unlimited. [Live Motion schema](file:///tmp/opencode/higgsfield-research-hf_mult_motion_control.json); [live Swap schema](file:///tmp/opencode/higgsfield-research-hf_mult_replace_object.json); [public limits](https://higgsfield.ai/genjutsu).
- A separate **workflow**, `kling3_0_motion_control`, exists on Higgsfield. Live `higgsfield workflow get kling3_0_motion_control --json` requires exactly one image and one video; exposes `mode=std|pro` and `background_source=input_image|input_video` (default `input_image`). `duration` appears in **cost_params**, not generation params. This is a different interface from Genjutsu. [Workflow discovery procedure](https://github.com/higgsfield-ai/cli#workflows); live command output observed 2026-10-30.

### Inferences

- **Ownership rule:** ordinary cinematic motion, coverage, inserts, establishing shots and most final high-quality video → direct Kling. Difficult choreography already acted on a phone → consider Genjutsu Motion Transfer. Keep an existing shot and change only a costume/prop/actor/location → consider Object Swap. Use a small representative approved test later before assigning an entire complex scene.
- **Document-backed mobile guidance:** shoot the performance and camera movement actually wanted; choose a usable 4–30-second section; prepare visual references for actors, wardrobe and set. The page says these motions/camera/timing are retained and explicitly supports phone-originated production. [Basis](https://higgsfield.ai/genjutsu).
- **Production recommendations, not documented requirements:** capture one readable action per take, stable lighting/focus, visible hands/feet for full-body movement, minimal accidental occlusion, no unwanted zooms or exposure jumps; retain the desired camera motion rather than blindly stabilizing it away. Match orientation/framing to the planned edit, leave brief handles, record several takes, and keep an untouched original. Use the actual number and spatial relationship of performers needed by the scene; separately test crossings, contact, and prop handoffs. These practices reduce ambiguity but are not guarantees of Genjutsu capability.
- For a complicated multi-character scene, approve identity and blocking first, then test the hardest interaction. If identity swaps at crossings, split coverage or composite locally instead of repeatedly spending on the complete scene.
- Use Genjutsu **instead of**, not automatically before, a second full video generation. Passing its result through Kling again may alter timing and identity; do so only for a specific supported editing task.

### Gaps

- Actual output aspect inheritance, FPS, accepted input codecs/file sizes, audio preservation, minimum reference-image dimensions and timing fidelity were not documented in the inspected schemas/page.
- No verified Genjutsu syntax for binding a particular reference to a particular actor beyond natural-language instructions. No guarantee that 30 references means 30 separately controllable characters.
- No separate Higgsfield MCP model connector was exposed in this subagent's available tool catalog. Current **CLI read access** is verified; model submission, UI execution and separately credentialed public API entitlement are not. Historical `models_explore action=get` leads should not be presented as an available connector here.

## 3. How should naming, prompts, audio, exports and provider handoffs converge?

### Takeaway

Keep one local script-derived production manifest as the source of truth and translate it into provider-specific requests. Use Higgsfield's names where available, but never depend on a universal generation-name field, interoperable provider UUIDs, or portable credits.

### Cited Findings

- Installed CLI help verifies `project create --name`, `project folders create <project-id> --name [--parent]`, and named Soul training. `project assets add` attaches a typed source with `--type job|media_input|video_input|audio_input|file_input`, `--source`, and optional `--folder`, or auto-uploads `--file`. It exposes **no asset-name flag**. `project assets` offers add/get/list/move/copy/remove/resolve/confirm-upload, not rename. [Official CLI repository](https://github.com/higgsfield-ai/cli); read-only installed help inspection on 2026-10-30.
- `generate create --help` says parameters are dynamic `--name value` pairs: **“name” there is placeholder notation, not proof of an actual `--name` parameter**. None of the inspected Soul/Genjutsu schemas declares a generation name. `folder_id` appears in some public model schemas but is absent from the inspected Soul/Genjutsu schemas: do not assume it is a universal accepted generation flag. [Public model reference](https://github.com/higgsfield-ai/cli/blob/main/MODELS.md); [live Soul schema](file:///tmp/opencode/higgsfield-research-text2image_soul_v2.json); [live Genjutsu schema](file:///tmp/opencode/higgsfield-research-hf_mult_motion_control.json).
- Completed generation commands return result URLs; jobs can be inspected with `generate get` or listed with `generate list --json`. Media paths submitted as inputs are uploaded automatically. These are file/job handoffs, not a documented cross-editor timeline interchange. [Official README flags and examples](https://github.com/higgsfield-ai/cli#flags); [media handling](https://github.com/higgsfield-ai/cli/blob/main/MODELS.md).
- **Character-specific voices are a separate supported concept.** `text2speech_v2` requires `prompt`, `variant`, `voice_id`, `voice_type=preset|element`; engines are `elevenlabs,minimax,seed_speech,vibe_voice,cozy_voice`. Installed `voices --help` describes `element` as cloned voices; it exposes list/get, not creation. [Live TTS schema](file:///tmp/opencode/higgsfield-research-text2speech_v2.json); [voice docs](https://github.com/higgsfield-ai/cli#voices).
- Seed Audio exposes audio output, optional paired `voice_id`/`voice_type`, formats `wav,mp3,pcm,ogg_opus`, sample rates `8000,16000,24000,32000,44100,48000` (default 24000), speech/pitch/loudness controls. Image and audio references are mutually exclusive; a chosen voice cannot coexist with image references and permits at most two additional audio references. It does not expose a duration parameter. [Live Seed Audio schema](file:///tmp/opencode/higgsfield-research-seed_audio.json).
- Genjutsu runs consume the **Higgsfield credit system**. The CLI also selects a Higgsfield billing workspace. A Kling model run through Higgsfield is still a Higgsfield-hosted job; it is not a route to spending the user's direct Kling credits. [Genjutsu pricing FAQ](https://higgsfield.ai/genjutsu); [CLI account/workspace commands](https://github.com/higgsfield-ai/cli#commands).
- Source freshness matters: Context7 successfully resolved `/higgsfield-ai/cli` and returned indexed `_autodocs` material, but direct fetches of its `api-reference/project.md` and `api-reference/generate.md` returned 404. Public README/MODELS also omit newer live catalog entries. Prefer the live schemas for current parameters; cite the accessible README/MODELS and local snapshots rather than treating indexed pages as current executable contracts. [Current README](https://github.com/higgsfield-ai/cli); [current model reference](https://github.com/higgsfield-ai/cli/blob/main/MODELS.md).

### Inferences

#### Recommended task ownership and handoffs

| Production task | Proposed owner | Concrete handoff |
|---|---|---|
| Script breakdown, scene/event/shot IDs, continuity ledger, reference approval | Local production manifest | Frozen script revision and structured shot records consumed by every provider |
| Hero identity/look discovery, single-character stills | Higgsfield Soul V2; Soul Cinematic where its framing/look is desired | Approved images, prompts, Soul ID recorded only in Higgsfield adapter |
| Character sheets, wardrobe combinations, multi-character keyframes | Local preparation/ComfyUI; optional multi-reference Higgsfield image model | Approved composite plus per-character crops and wardrobe/location IDs |
| Location look development | Soul Location if useful; approved set reference maintained locally | Selected set still/layout, not an assumed persistent location ID |
| First/last stills | Higgsfield Soul V2 preference, locally checked/corrected | Matching aspect/dimensions, pose geometry, screen direction and lighting |
| Most high-quality shot animation and alternate takes | **Direct Kling** | Approved first/last frames and shot motion prompt; direct-account limits verified by the Kling researcher |
| Difficult filmed acting/choreography or selective video replacement | Higgsfield Genjutsu | One phone/source video plus explicit character/wardrobe/location image mapping |
| Masks, reference cropping, frame extraction, endpoint alignment, compositing, cleanup | Local tools/ComfyUI, subject to installed workflow verification | Canonical named files and technical metadata |
| Dialogue/narration per character, optional ambience/foley | Separate audio pipeline; Higgsfield TTS/Seed Audio are candidates | One stable voice record per character; isolated WAV takes linked to dialogue events |
| Assembly, trim, sequencing, titles, audio mixing, final delivery | Openreel-video, subject to its own capability verification | Local media files, ordered shot manifest, dialogue/music/SFX stems |

These are recommendations for the convergent strategy, not claims that every local ComfyUI/Openreel workflow has been tested. Keep direct Kling and Higgsfield budgets separate; platform credits are not transferable in this plan. No transfer mechanism was documented or tested.

#### Canonical naming and record

Use a stable shot ID independent of provider; keep provider/take/revision in the artifact suffix:

```text
project: FILM01
script_revision: R003
shot_id: FILM01_SC012_EV03_SH020
asset_id: FILM01_SC012_EV03_SH020_KFSTART_HF_SOULV2_T02_V003
filename: <asset_id>.png
companion: <asset_id>.json
character: CHAR_A   wardrobe: WARD_A01   location: LOC_02
other artifacts: KFEND, MOTIONREF, VID, DIALOGUE_CHAR_A, AMB, SFX, EDIT
```

Record script/event text, purpose, beginning/end state, characters, wardrobe, location, ordered references with explicit roles, camera/lens/motion, light/look, target aspect/duration, dialogue IDs, provider/model, exact submitted parameters, prompt revision, provider job/upload IDs, local filename, checksum, actual dimensions/FPS/duration/audio presence, approval and lineage. Names remain metadata, not instructions to render text in the image.

#### One semantic prompt template; provider adapters

```text
STORY EVENT: [event from the frozen script; purpose and emotional beat]
IDENTITY / BLOCKING: [CHAR_A left foreground; CHAR_B right rear; visible actions]
CONTINUITY: [wardrobe IDs, props, location, time, screen direction]
BEGIN: [precise starting body/prop/camera state]
ACTION: [ordered observable beats, only for motion tasks]
END: [precise final state; intended cut continuity]
CAMERA / LOOK: [shot size, lens, viewpoint, move, lighting, palette]
REFERENCE MAP: [identity A -> file; wardrobe -> file; location -> file;
                start -> file; end -> file; motion -> file]
PRESERVE / CHANGE: [which identities, timing, camera or scene elements stay/change]
AUDIO PLAN: [dialogue event IDs, voice IDs, ambience/SFX; separate asset plan]
```

**Adapter contracts, not commands executed during this research:**

- **Soul V2 still:** compile the event into **one instantaneous** BEGIN or END visual description. Map identity to `custom_reference_id`, use at most one `image_references`, `aspect_ratio=16:9`, `quality=2k`; optional seed recorded. Omit video duration, motion-reference and audio fields. If using `style_id`, omit image reference. A reference-map paragraph does not override the model's one-image limit.
- **Genjutsu motion:** `job_type=hf_mult_motion_control`; `video_references=[phone_take]`; `image_references=[approved_character,wardrobe,set,…]`; `resolution=1080p`; prompt tells it to preserve the filmed actor/camera/timing and rebuild the specified visual elements. Stay within the public 30-image/4–30-second limits. Do not add unsupported duration/aspect/start/end/audio flags.
- **Genjutsu selective edit:** same media structure, `job_type=hf_mult_replace_object`; prompt names the exact target and what remains unchanged. Avoid asking simultaneously for a new camera trajectory and preservation of the original one.
- **Direct Kling:** adapter receives downloaded KFSTART/KFEND files and motion text; maps them to the **specific direct Kling mode's** supported endpoint/reference fields. Do not pass Higgsfield UUIDs. Omit or explicitly manage native audio if separate character voices are used.
- **Audio:** compile only the spoken line and appropriate supported delivery instruction into TTS `prompt`; bind stable `voice_id`, `voice_type`, `variant` per character. Keep camera/look directions out of spoken text. For Seed Audio use the appropriate audio intent and supported voice/reference fields. Soul identity provides no voice automatically.
- **Openreel/local:** consume approved files plus ordered shot/audio manifest. Media exports are the safe interoperability baseline; do not assume transfer of Soul weights, editable Higgsfield scenes, keyframe metadata, project folders, or an NLE timeline.

**Concrete example:** Script event: “Mara finds the brass key, then conceals it as Leon enters.” Generate Mara's approved still at the desk with the key visible (KFSTART); generate the same camera/set with key concealed and Leon correctly placed in the doorway (KFEND, likely requiring a locally assembled/multi-reference composition). Direct Kling gets these endpoints and the timed action. If hand concealment/contact is unreliable, film the action and use Genjutsu with Mara/Leon/wardrobe/set references. Dialogue `CHAR_LEON_EV03_LINE01` is a separate voice take. Openreel receives the approved video, voice and room-tone files, all linked to `SC012_EV03_SH020`.

### Gaps

- **Generic named reference elements remain unverified.** Named Soul characters and projects/folders are verified; the installed CLI has no generic `element create` command. Existing voice elements are discoverable, but creation/renaming access was not established. Do not repeat the memory lead that all reference elements are nameable as a tested connector capability.
- Generation renaming, universal `folder_id`, export downloads retaining custom names, EDL/XML/OTIO interchange, project export, image metadata retention, URL expiration and original codec delivery were not verified. Keep canonical names locally and attach completed jobs to project folders through the verified project-assets interface if needed later.
- No specific account entitlement to every listed model was tested by submission. Account authentication plus readable model schemas establishes discovery access, not successful paid rendering.
- This research intentionally did not inspect personal generation history, list private voice assets, or test media outputs. Budget figures are volatile and were not used to assign fixed shot counts.

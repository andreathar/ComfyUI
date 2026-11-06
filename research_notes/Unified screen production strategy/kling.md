# Kling production research — unified screen-production strategy

**Verified:** 2026-10-30. **Scope:** documentation and read-only live capability discovery; no generation, upload, login, purchase, provisioning or code change. Recommendations below are planning inferences, not tested image/video quality claims. Higgsfield SoulV2, Genjutsu, local ComfyUI and Openreel-video roles are user-requested integration boundaries; their capabilities require their own research.

## Executive takeaway

Use Kling as the primary finishing/generation destination because the user has more Kling credits, while keeping the screenplay, scene events, character/voice masters and shot IDs outside the provider. **Current live tooling includes Kling 4.0**, not just 3.0: 3–30-second generation, multimodal references and audio. However, **UI, OAuth CLI/connector and public REST are three different contracts**. Do not translate only the model name: translate the mode, references, syntax, limits, audio and task identifiers too. [C1][C2][S1][S2]

The critical production split is **keyframe-driven movement versus subject/reference-driven generation**. Live 4.0 `image_to_video` exposes first/tail/intermediate frames but no Elements; live 4.0 `omni_ref_video` exposes Elements, images, videos and audio but no named first/tail slots. Public REST 4.0 has typed frame and reference inputs in one endpoint. A generic reference still is not a guaranteed first or last frame. [C1][S2]

## 1. What is actually available here?

### Takeaway

An authenticated existing `kling` CLI works; dedicated Kling tools were not present in this session's discovered execute catalog. The CLI's live tools and model schema are the actionable local interface. Public REST features must not be represented as callable local tools. [C1][C2]

### Cited findings

- Existing CLI identified as **kling-cli 0.2.3**. Read-only `kling who_am_i` and `kling tool_list` succeeded. Live identity mode was OAuth; no new login was performed. The response says the server tool list has changed and recommends reconnecting/restarting the host for updated MCP tools. `who_am_i` is more authoritative than cached/offline CLI help. [C1][C2][C3]
- Live tool names: `text_to_image`, `image_to_image`, `text_to_video`, `image_to_video`, `omni_ref_video`, `motion_control`, `motion_library_list`, `element_create`, `element_get`, `element_list`, `element_update`, `element_delete`, `query_tasks`, `file_upload`, `query_membership_and_credits`, `feedback`, `who_am_i`, `logout`. **No standalone voice creation/list, TTS, avatar, face detection or lip-sync tool** appeared. [C2]
- Local paths supplied to CLI generation can trigger automatic upload. This research invoked no generation/upload command. [C3]
- Context7 was consulted after resolving `/websites/kling_ai_document-api`; current official Markdown docs were then read directly. Stripe Directory provider discovery returned `Permission denied`; no installation/login was attempted. No pricing or plan entitlement was inferred from that failure.

### Gaps

No quality benchmarks or generation execution were performed. Membership-specific access, available balance, whether this account's credits apply to a particular REST product, and actual UI controls were not tested. A schema accepting a parameter is evidence of advertised support, not measured fidelity.

## 2. Model/mode matrix — live CLI contract

### Takeaway

Pin both **tool and model**, and snapshot the live schema before a production batch. The same model label is not a single universal input format. The following is the current account-visible schema, not a promise of all memberships or regions. [C1]

| Tool/model | Duration / resolution | Reference and control contract | Audio / multi-shot |
|---|---|---|---|
| `image_to_video`, `kling-video-v4_0` | 3–30s; 720p/1080p; 4K explicitly disabled | `first_image`, `tail_image`, `keyframe_1`…`keyframe_10`; **combined ≤10 images**; no Element argument; keyframes cannot combine with reference video/subjects in this connector route | No audio or multi-shot flag exposed on this entry |
| `omni_ref_video`, `kling-video-v4_0` | 3–30s; 720p/1080p | ≤10 images, ≤5 videos, ≤3 audio URLs, ≤7 Elements including ≤3 video Elements; videos + video Elements ≤5; **all refs combined ≤15** | `enable_audio` versus `keepOriginalSound`: only one true; `prefer_multi_shots` only permits **true** |
| `image_to_video`, `kling-video-v3_0` | 3–15s; 720p/1080p/4k | `first_image` and optional `tail_image`; ≤3 Elements; Elements reinforce subjects already depicted in frame(s) | Native audio and optional multi-shot flags |
| `image_to_video`, `kling-video-v3_0_omni` | 3–15s; 720p/1080p/4k | `image_1`…`image_7` and Elements; these are reference slots, not dedicated first/tail slots | Native audio and optional multi-shot |
| `omni_ref_video`, `kling-video-v3_0_omni` | 3–15s; 720p/1080p/4k; with direct video, 11–15s may be gated downstream | No direct video: images + Elements ≤7, video Elements ≤3. With one direct video: images + Elements ≤4; video Element allowed only with **zero images/image Elements**, maximum one | Native audio **must be false when `video_1` supplied**. Reference-video may force multi-shot true; base-video edit may force false |
| `omni_ref_video`, `kling-video-o1` | 3–10s; 720p/1080p | Images + image Elements ≤7 without video, ≤4 with one direct video; no video Elements | No native-audio argument |
| `image_to_video`, `kling-video-v3_0_turbo` | 3–15s; 720p/1080p | First image only | No audio/multi-shot flags exposed |
| `motion_control`, `kling-video-v3_0` | Reference-driven, nominal 3–30s or 3–10s depending orientation; 720p/1080p | `image` + exactly one of `video` or `motionId`; ≤1 facial Element | `keepOriginalSound` defaults true; no new-dialogue-generation flag |
| `motion_control`, `kling-video-v2_6` | Same orientation-dependent duration classes; 720p/1080p | Image + video/library motion; no Element argument | Source sound option |
| `image_to_image`, `kling-image-v3_0_omni` | Still images; 1k/2k/4k | Up to 10 direct images; image Elements supported, **video Elements rejected**; UI guide total images + Elements ≤10 | `story_mode=true` infers series count and ignores `imageCount` |

All rows: [C1]; 3.0 frame/Element semantics and image combined limit: [S3][S4].

Additional supported generation routes: live T2V includes 4.0 (3–30s), 3.0/3.0 Omni/Turbo (3–15s), O1 (3–10s), and 2.5/2.6 (5 or 10s). T2V exposes no subjects. I2V 2.5/2.6 exposes first/tail images, 5 or 10s, 720p/1080p. Image-to-image O1 supports image Elements; do not confuse it with unsupported video Elements. [C1][C2]

Aspect ratios: live 4.0 T2V/I2V explicitly offers 21:9, 16:9, 9:16, 1:1; Omni 4.0 also offers `auto`, requiring at least one direct image/video. Omni 3.0 offers auto/16:9/9:16/1:1, but direct reference-video needs an explicit ratio (base-video edit can use auto). Standard 3.0 I2V follows its frame inputs rather than exposing an aspect-ratio argument. [C1]

### Input limits relevant to planning

- **Omni 4.0 connector:** images ≤30MB, aspect 0.4–2.5; video each ≤300MB and nominal 3–30s, combined duration including video Elements also 3–30s; reference audio URL-only, nominal 5–30s, ≤50MB. The lower-level validation schema has tolerance margins different from human-readable limits; plan to the documented nominal ranges. It explicitly states input-video seconds count in billed duration. Do not invent a per-second credit price. [C1]
- **Omni 3.0/O1 connector video:** one MP4/MOV, 3–10s, ≤200MB, 720–2160px, 24–60fps. Public REST capability map lists a different 3.0 Omni maximum (15.5s); do not use that to bypass connector limits. [C1][S1]
- **4.0 REST:** images JPG/PNG, each ≤30MB, each dimension ≥300px, aspect 0.4–2.5, ≤10. Videos MP4/MOV, ≤300MB, 3–30s individually and combined including video Elements; dimensions 700–4553px and pixel area ≤8,294,400; 24–60fps input, **24fps output**. Up to five videos + video Elements, at most one base video, ≤7 Elements including ≤3 video Elements, ≤3 voices, ≤15 combined references. [S2]

### Gaps / contradictions to preserve

- The official capability map, updated **2026-10-20**, advertises 4K for 4.0, while the current 4.0 REST endpoint enum and live connector allow only 720p/1080p. Use the endpoint/schema, not the overview. [S1][S2][C1]
- Old 3.0 Omni UI guide lists 720p/1080p; current connector allows 4k. Preserve date/surface differences. [S4][C1]
- Generic `element_create` prose says video subjects work “ONLY” on 3.0/3.0 Omni I2V, but the current `omni_ref_video` model-specific `elementSupport` explicitly includes 4.0 and 3.0 Omni. Treat that generic sentence as stale; no generation was made to resolve runtime behavior. [C1][C2]
- CLI 4.0 Omni requires smart multi-shot enabled. A prompt asking for one uninterrupted take is guidance, **not an exposed hard single-shot switch**. [C1]

## 3. Character, location and voice preparation

### Takeaway

Prepare reusable assets **before shots**: approved character stills, clean per-character voice masters, location plates, wardrobe/prop variants and shot-specific movement endpoints. Keep the original files portable; provider Element/voice IDs are bindings, not canonical identities.

### Cited findings

- UI Elements support Characters, Animals, Items, Costumes, Scenes, Effects and Others. Image Elements use **2–4 separate images**, not a compulsory collage: a main image plus 1–3 reference views. Names are unique in the library; UI selection uses the `@` picker under Assets → Elements. Descriptions can specify core features and details to ignore. [S3]
- Live `element_create`: image `resource.cover` + 1–3 `secondary` entries, or `resource.video`; optional `resource.voice` is a publicly accessible **.mp3 URL**; at least one tag. A secondary entry is `{name,inputType:"URL",url}`. Video Element live constraints: 3–60s, fps >23.8, short edge ≥700px, resolution ≤3840×2160, supported square/unspecified SAR, no HDR. [C2]
- The older UI guide instead describes 3–8s video-character uploads and app-only recording. These are separate surface-specific limits; do not claim one universally replaces the other. Video characters can capture appearance and voice; multi-image characters can bind a voice file or Voice Library entry. Clean single-speaker **5–30s** is the robust shared voice-preparation target; an older paragraph says extraction from ≥3s but its FAQ says 5–30s. [S3][S4]
- UI library capacities documented in February: nonmember 30; Standard 50; Pro/Premier 150; Ultra 500. Existing assets remain usable after downgrade, but over-quota creation/editing is restricted. Element creation is described as free; optional AI multi-view completion is a separate charged operation. These are dated guide claims, not verified current account pricing. [S3]
- `element_update` is a **full overwrite**; omitted fields clear. Cover cannot be replaced; secondary list replaces the old list. Read the whole current object before any eventual update. For production continuity, a new revisioned Element is preferable to silently rewriting an already-used asset. [C2; final sentence is recommendation]

### Voice, dialogue and lip sync: separate capabilities

1. **Custom voice (public REST):** `POST /v1/general/custom-voices`, `voice_name` ≤20 characters, exactly one of `voice_url` or eligible `video_id`. Clean single-human 5–30s MP3/WAV/MP4/MOV; eligible generated video IDs are specified as 2.6 sound-enabled, Avatar or LipSync outputs. Creation returns a task; query for the resulting `voice_id` and trial audio. Portable clone-weight export is **not documented**. [S5]
2. **Native audiovisual generation:** use a character-associated voice or, in 4.0 REST, up to three explicit `voice_id` inputs and prompt bindings. Live 4.0 Omni instead accepts up to three **audio URLs**, referenced as `音频1` etc. A voice reference guides vocal identity; it is not automatically a sample-accurate finished dialogue track. [S2][S3][C1; final sentence is production inference]
3. **Dialogue prompting:** assign speaker, exact words, language, emotional delivery, turn order and timing. Official 3.0 guide material discusses Chinese, English, Japanese, Korean and Spanish native audio. Treat language coverage as model/version-specific. [S4][S10]
4. **Lip sync (public REST):** `POST /v1/videos/advanced-lip-sync` requires a face-detection `session_id`; currently selects **one person**. `audio_id` from the last 30 days XOR `sound_file` URL/base64; 2–60s, ≤5MB MP3/WAV/M4A/AAC; explicit audio crop/insert timing in milliseconds, ≥2s overlap with the face interval, volume 0–2. Not present as a live CLI tool. [S6][C2]
5. **Avatar (public REST):** `/v1/videos/avatar/image2video` uses image plus audio (`sound_file` or `audio_id`); audio 2–300s, ≤5MB MP3/WAV/M4A/AAC. This is a talking-avatar route, not evidence that arbitrary multi-person film footage accepts 300s lip sync. [S7]

### Production inferences

- Have SoulV2 deliver the user-approved visual identity, then export separate approved views for Kling image Elements. Do not assume a Soul identity/model ID transfers into Kling.
- For each character, store a clean voice reference, transcript, language/accent/delivery notes, and any exact line recordings separately. Bind the same canonical `CHAR_ID` to a Kling Element and, if used, a Kling voice ID. Keep voice identity independent of wardrobe revisions.
- Character sheets are overview artifacts; feed individually cropped views to the Element builder. Prepare locations as clean wide/reverse/lighting-state plates, then bind them as images or Scene Elements.
- For exact dialogue timing, preserve an approved external dialogue track and use a verified lip-sync route or editorial assembly. Omni 3.0 reference-video + new native audio is specifically unsupported; split those tasks or route to eligible 4.0.

## 4. Filmed mobile motion references

### Takeaway

Use a purpose-shot phone performance for choreography, then choose **Motion Control 3.0** for direct single-character performance transfer or **4.0 Omni feature-reference** for broader action/camera reference. Keep appearance, movement, camera and source audio roles explicit. [C1][S2][S8][S9]

### Cited findings

- Motion Control requires an appearance image and video (or library `motionId`). `motion_direction` follows the video's orientation/camera, nominal 3–30s; `image_direction` keeps the still's orientation and permits prompt-guided camera, nominal 3–10s. [C1][S8]
- 3.0's optional Element is a **facial reference**, not a clothing/hair/prop replacement. Guide says this binding is available when orientation matches the video. One subject is targeted: largest visible person; equal-sized subjects can fail selection. [S8]
- Recommended input: clear, single continuous take; matched full/half-body framing between still and footage; no cuts, occlusion or unnecessary camera movement; moderate motion, visible limbs and room to move. Guide limits include shortest edge ≥340px, longest ≤3850px. Complex fast motion can be truncated if only a usable segment ≥3s is extracted; guide says no refund for that case. [S8]
- Live source-sound preservation defaults true. Choose deliberately whether to retain phone audio; this is not a new-dialogue-generation control. [C1]
- 4.0 REST distinguishes `feature_video` (reference) from `base_video` (the video being edited). Official examples transfer fighting movement/rhythm or camera style while using different identity references. Prompt scope should say which features to copy and which not to copy. [S2][S9]

### Inferences / fallbacks

Plan per-event motion takes with readable anticipation → action/contact → follow-through, and extract named start/end stills. Keep the original phone take as a canonical asset usable by a separately verified Genjutsu route. For multi-person choreography, use 4.0 feature reference or break into separate controlled shots; Motion Control's single-person targeting is not multi-character choreography control. If a start/end composition is mandatory, choose an actual keyframe route rather than hoping a reference-image slot pins an endpoint.

## 5. Thin adapter and exact prompt conventions

### Takeaway

Store a **structured shot intent**, not one universal prompt. Compile only the last layer: input roles, slot references, syntax, supported options and provider IDs. Semantic event order and identity stay common; surface-specific bindings remain distinct.

### Recommended canonical records (design proposal)

```text
PROJECT → SCRIPT_REV → SCENE_ID → EVENT_ID → SHOT_ID → TAKE_ID
CHAR_ID / VOICE_ID / LOCATION_ID / PROP_ID / WARDROBE_REV
ASSET_ID + revision + local path + content hash + media metadata
shot: framing, camera, duration, aspect, start_state, event_beats,
      end_state, characters, location, dialogue, sound, continuity
reference: asset_id, role, scope, immutable_features, excluded_features
binding: platform, surface, model, provider_asset_id, provider_type,
         request_slot, prompt_token, schema_date
result: canonical_take_id, provider_task_id, provider_output_id,
        prompt/request snapshot, source hashes, local media path,
        returned_url, retrieved_at, documented_url_expiry
```

Example canonical names (not provider fields): `FILM_SC012_EV03_SH02_T01`; `FILM_CHAR_ANA_VIS_v003`; `FILM_CHAR_ANA_VOICE_v001`; `FILM_LOC_STATION_NIGHT_v002`; `FILM_SC012_EV03_SH02_START_v002.png`; `..._END_v002.png`; `..._MOTION_v001.mp4`. A shot can cover several events; a multi-shot generation should map its internal shot spans back to multiple `SHOT_ID`s. Do not rename canonical events when changing platforms.

### Binding translation table

| Surface | Asset binding | Prompt token / syntax |
|---|---|---|
| Kling UI | Pick library Element with UI `@` picker | UI mention object; do not assume pasted CLI IDs become valid mentions [S3] |
| CLI `omni_ref_video` | `elements` is a **JSON array string** of `{id,bindName,type}`, `type` image/video | `<<<PROVIDER_ELEMENT_ID>>>`; direct `image_1` → `图片1`, `video_1` → `视频1`, `audio_1` → `音频1` [C1] |
| Older CLI I2V / Motion Control Element argument | JSON array string of `{id,bindName}` | `<<<PROVIDER_ELEMENT_ID>>>`; use route-specific schema, not Omni's fields [C1] |
| 4.0 REST | Typed `contents`: `element` + `element_id` + task-local unique `id`; `voice` + `voice_id` + `id`; typed images/videos | `@id`, e.g. `@ana`, `@station`, `@motion`, `@anaVoice` [S2] |
| Older multi-element REST edit | Separate older endpoint and input object contract | `<<<video_1>>>`, `<<<image_1>>>`; not equivalent to 4.0 `@id` [S11] |

**Illustrative CLI 4.0 Omni prompt** (replace placeholders with real provider IDs; no request executed):

```text
Identity: <<<ELEMENT_ID_ANA>>> is Ana. Preserve her face and approved wardrobe.
Location: use 图片1 for the station architecture and night lighting only.
Motion: use 视频1 for Ana's step, turn and hand-contact timing only;
do not copy the performer's appearance or the phone video's background.
Voice: use 音频1 for Ana's vocal identity.
12-second sequence, 16:9, naturalistic cinema.
0–4s: medium tracking shot; Ana enters left-to-right and notices the envelope.
4–8s: closer framing; she stops, turns toward it, then grips it with her right hand.
8–12s: hold on Ana's reaction; preserve the envelope in her right hand.
Ana says in English, quietly and urgently: "We leave tonight."
Only Ana speaks. Station ambience; no music. Preserve screen direction.
```

Associated binding concept: `elements='[{"id":"ELEMENT_ID_ANA","bindName":"Ana","type":"image"}]'`, location → `image_1`, motion → `video_1`, voice reference → `audio_1`; `enable_audio=true`, `keepOriginalSound=false`. Exact visual/audio adherence remains to be evaluated. Live 4.0 requires `prefer_multi_shots=true`; this example intentionally describes a shot sequence. [C1]

**REST 4.0 compiler:** render the same intent with `@ana`, `@station`, `@motion`, `@anaVoice`; construct typed `contents` using `element`, `refer_image`, `feature_video`, `voice` respectively. For explicit movement endpoints, emit `first_frame`/`last_frame` instead of labeling generic refs as endpoints. Set `settings.duration`, `settings.aspect_ratio`, `settings.resolution`; `adaptive` is REST's token, not CLI `auto`. Use unique `options.external_task_id` for the take. REST English prompt cap is 26,000 characters, non-English 11,000, mixed `E/26000 + N/11000 <= 1`. [S2]

**I2V compiler:** pass the actual approved start/tail images; write only necessary movement, camera, timing and end-state continuity. For CLI 4.0 do not add unsupported Elements/audio fields; use a different route if those requirements are essential. For 3.0 I2V, frame-present subjects may be reinforced with up to three Elements. [C1][S3]

## 6. Naming, persistence and task ownership

### Takeaway

The local production manifest must own names and permanence. Provider URLs and IDs are references to remote state, not archival assets.

### Cited findings

- Live generation schemas expose no output filename/title/name parameter. `taskTraceId` is a UUIDv7 trace grouping related operations, **not a shot name**. `query_tasks` takes `generationId`. Elements have names; motion-library records expose id/name/url/cover/duration/audio metadata. [C1][C2]
- Public REST `options.external_task_id` is account-unique and queryable, but does not overwrite the system task ID. `GET /tasks` permits either task IDs or external task IDs, not both at once. [S2]
- CLI `query_tasks` says result **URLs expire in 24 hours**. REST says generated results are **retained for 30 days** and uses hotlink-protected URLs. These are different statements, not proof that every URL lasts 30 days. Older multi-element selection `session_id` also lasts 24h; that is a third, unrelated lifetime. [C2][S2][S11]

### Inferences

On future authorized generation, ingest successful results promptly into canonical local paths and record hashes, provider task/output IDs, raw request, model/mode and asset versions. Send local media paths and timing/shot mapping into the verified editorial/Openreel adapter rather than expiring URLs. Keep the provider filename/ID in metadata; no need to force the provider UI to adopt the whole naming tree. Voice names have a 20-character REST limit, so use compact aliases and retain the full canonical ID in the manifest. [S5]

## 7. Task routing aligned with credit preference

The following is a proposed policy, not a measured cost/quality ranking:

1. **Script breakdown first:** lock scene/event/shot and character IDs; identify dialogue, blocking, locations, continuity and exact start/end requirements.
2. **Initial assets before production:** user-selected SoulV2 character work → approved views; record clean per-character voice references early; create separate local masters and later provider voice/Element bindings. Location/prop/wardrobe references and movement-frame pairs inherit script IDs.
3. **Kling-first main generation:** Omni 4.0 for rich identity/location/motion/audio references and longer sequences; 3.0/3.0 Omni where their exact controls (e.g. explicit 4k availability or optional multi-shot) fit better. Latest model alone is not a quality guarantee.
4. **Exact start/end motion:** CLI 4.0 I2V for up to ten keyframe inputs, or 3.0 I2V when frame-present Element binding/native audio is essential. REST 4.0's combined typed-input endpoint is a separate integration option, not an automatic way to spend existing consumer credits.
5. **Complex filmed movement:** Motion Control 3.0 for clear single-performer transfer; 4.0 Omni feature-reference for action/camera/reference combinations. Genjutsu remains a separately verified alternative using the same local take and canonical IDs.
6. **Exact dialogue / close-up delivery:** native dialogue for suitable shots; verified lip-sync/Avatar route for their narrower cases. Preserve final voice tracks independently so revisions do not require regenerating all visuals.
7. **Local ComfyUI:** preparation, frame repair/variants or other capabilities established by the local research; keep canonical reference roles. Do not assume a workflow or model is installed from this Kling report.
8. **Editorial/Openreel:** assemble accepted local takes, conform duration/framerate, place approved dialogue/ambience/music and map multi-shot spans back to script events. No claim here about unverified Openreel features.
9. **Fallbacks preserve intent:** if a route lacks required subject/keyframe/audio support, split the operation or choose a compatible route. Never silently drop a required reference. For timed-out/failed paid jobs, inspect status and preserve request identity rather than silently submitting duplicates. The live query tool specifically says timeout/service-error resubmission requires explicit user request. [C2]

Kling 4.0 live Omni bills by seconds including input video duration; trimming a motion reference to the necessary event reduces input duration, but no exact price or cross-plan credit equivalence was established. [C1]

## Sources and verification record

All URLs accessed 2026-10-30. Dates below are page dates when observed; undated pages are not assigned a guessed publication date.

- **[C1]** Existing authenticated CLI: `kling who_am_i`, live `body.availableModels`, read-only on 2026-10-30. Rechecked model/tool combinations, limits and prompt bindings. Local capability evidence, not a public URL. Sensitive account identity omitted from these notes.
- **[C2]** Existing CLI: `kling tool_list`, live `body.tools`, read-only on 2026-10-30. Rechecked complete tool list, Element schemas and query URL-expiry statement. Local capability evidence, not a public URL.
- **[C3]** Existing CLI version/help, `kling-cli 0.2.3`, observed 2026-10-30; help explains local-file auto-upload and cached-help behavior.
- **[S1]** Official video capability map, updated **2026-10-20**: https://kling.ai/document-api/guides/capability-map/video.md
- **[S2]** Official Kling 4.0 Omni REST schema, undated: https://kling.ai/document-api/api/video/4-0/video-omni.md
- **[S3]** Official Element Library 3.0 user guide, **2026-02-05**: https://kling.ai/quickstart/klingai-element-library-3-user-guide
- **[S4]** Official Video 3.0 Omni user guide, **2026-02-06**: https://kling.ai/quickstart/klingai-video-3-omni-model-user-guide
- **[S5]** Official custom voice REST schema, undated: https://kling.ai/document-api/api/video/4-0/voice-customization.md
- **[S6]** Official advanced lip-sync REST schema, undated: https://kling.ai/document-api/api/video/lip-sync.md
- **[S7]** Official Avatar REST schema, retrieved through Context7: https://kling.ai/document-api/api/video/avatar
- **[S8]** Official Motion Control user guide, **2026-03-05**: https://kling.ai/quickstart/motion-control-user-guide
- **[S9]** Official Kling 4.0 prompt guide, undated: https://kling.ai/document-api/api/usage-guide/kling-4-0-prompt-guide.md
- **[S10]** Official 3.0 Omni reference-workflow guide, **2026-06-29**: https://kling.ai/blog/kling-video-3-omni-reference-workflows-multi-element
- **[S11]** Official older multi-element editing REST schema, retrieved through Context7: https://kling.ai/document-api/api/video/multi-elements
- Official documentation index used to discover current endpoints: https://kling.ai/document-api/llms.txt

### Remaining decisions / verification gaps

- Which already-funded Kling surface should production use: web/OAuth CLI, separately billed REST, or both? Do not infer shared balances.
- Does the current UI/account offer controls absent from the CLI (especially voice library, hard single-shot control and combined keyframe/Element workflows)? No browser inspection was performed.
- Quality, repeatability, exact voice similarity, complex contact fidelity and cross-shot consistency need user-authorized small production tests; official consistency language is not empirical evidence.
- Parent synthesis must verify SoulV2, Genjutsu, local ComfyUI and Openreel capabilities independently, then combine their bindings with this adapter rather than reuse Kling tokens globally.

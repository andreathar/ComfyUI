# Production context, event naming, and character-voice workflow

Research date: 2026-10-30. Research only; no production state, existing documents, code, voices, media, models, provider accounts, or services changed. This is a handoff to the integrating researcher, not a new production board or authorization to generate. **Existing evidence**, **dated plans**, **proposals**, and **unknowns** are distinguished below.

## 1. What production did the user already plan?

### Takeaway

Recover the existing film before inventing a replacement pipeline. *The Table Between Centuries* / `andre-time-travel` already has a complete T01–T21 board, W01–W68 workflow decomposition, a 96-work-package execution plan, stable dialogue IDs, and an audio-first guide/dub decision. The newer Argon restaurant test is a separate scene, not a revision of the Galileo screenplay. [L1–L7, L16]

### Cited findings

- The authoritative film inputs are the current production plan, board, English script/dialogue CSV, scoped decisions, and cost ledger. The October 13 active Galileo baseline is **G-L03/G-L04**, with seven candidate sources and **G-P04** as the next first-speech test after continuity repair. The older 16-second animatic is timing reference only; a reported Galileo v2 was not found in the bounded locations examined. A 42-second historical target is not evidence of an accepted current cut. [L1–L4]
- English script v2 covers opening, Caesar (`C`), Genghis Khan (`K`), Galileo (`G`), Napoleon (`N`), Oppenheimer (`O`), ending. Dialogue is fictional; the script says actual approved audio drives editing rather than accelerated speech. Stable IDs are `IN-L01`, each chapter's `*-L01` through `*-L04`, and `OUT-L01`: **22 dialogue rows**. The checked CSV scratch paths are `edge-tts-v2`, all marked unapproved. [L5]
- The prior comprehensive execution plan contains **96 work packages / 111 stage-edition-chapter instances**; it is a plan, not a second live board. The requirements audit covers the full 21-task/68-workflow-step demand, including ancillary cleanup, memory, handoff, and hook work. Its October 10 snapshots are historical observations, not current balances or approval. [L6–L7]
- Existing dramatic requirements are causal: a difficult line motivates a visible reaction and changes Andre. They reject a mechanical identical reaction duration/order in every chapter. Continuity includes the oak table's ring/chip, selected seating/scale, Andre left with camera-right gaze, and a consistent screen axis. Historical faces are excluded under the film's selected coverage contract; inspect intermediate frames and reflections, not just endpoints. [L7 §§2,6]
- The separate October 28 restaurant design uses `TEST`, `SC02-SH01` walk/sit, `SC02-SH02` “She said eight. It’s twenty past.”, `SC02-SH03` “Then again, I was late last time.” Each is proposed as five seconds; approved last frames feed the next approved starting still. It claims Andre's Element has an ElevenLabs voice, but explicitly leaves external audio/TTS/lip-sync outside its scope. That claim does not resolve the current voice-binding uncertainty. [L16, L18]

### Inferences / proposals

Use the existing film as the concrete continuity and naming example; retain separate project/scene identities for the restaurant test. Carry the user's present strategy into planning: initial voice references for every speaking character, character sheets and location images first; Kling for most high-quality generations because of existing credits; Higgsfield SoulV2 for visual identity and start/end movement frames; phone-filmed performances for Genjutsu/motion-control complex action. These are **user-requested routing preferences**, not capabilities verified by this research; platform agents own route-specific feasibility.

### Gaps

The latest active script for any production beyond the recovered film and restaurant test is not established. No narrative event-ID contract was found in the targeted film JSON / Argon searches; OpenReel “events” located during research concerned editorial cuts, not story events. Event-rooted identity below is therefore a proposal. Media was not listened to or visually accepted in this research.

## 2. Complete recovered production inventory and dependency graph

### Takeaway

Keep T01–T21 as the accountable production milestones. Use the existing finer-grained plan to expose parallel work, especially voice auditions, reference review, and playback. Do not let a coarse completed speech-route flag hide the blocked final-voice task. [L2, L6–L7]

### Cited findings: live-board milestone inventory

Recorded statuses and dependencies below come from the checked board; acceptance/residual requirements are condensed from the existing task specifications and requirements audit. They are not new acceptance decisions. “Complete” preserves the original approved scope; it does not approve new image angles, voices, editions, or paid batches. [L2, L7 §3]

| Task / recorded state | Accountable owner | Recorded prerequisites | Required result / acceptance still relevant |
|---|---|---|---|
| T01 Brief — complete | Producer | — | Five encounters/two editions; explicit current scope and cost envelope. Historical budget is not live authority. |
| T02 Receive/select references — complete | Continuity; Andre likeness judgment | — | Exact selected sources/provenance; retain front-weighted photo limitations; new angles need their own review. |
| T03 Continuity bibles — complete | Continuity; producer integration | T02 | Wardrobe/grooming/table/axis consistent; integrate selected later studies without promoting undecided proposals. |
| T04 Provider Element — complete | Producer | T01,T03 | Exact supported Element/reference binding; old creation is not proof of voice attachment or new route compatibility. |
| T05 English screenplay/history — complete | Historian/director | — | Canonical v2 text and IDs; sourced facts separated from fictional dialogue; current causal beat sheets. |
| T06 Historical languages — blocked | Dialogue-sound + qualified reviewers | T05 | Target language/convention, translation, back-translation, pronunciation, actual route support and named reviewer. |
| T07 Voices/dry dialogue — blocked | Dialogue-sound + Andre | T01,T05 | Approved voice identity/sample for each speaker; exact dry line files, rights/provenance, performance and measured timing. |
| T08 Four-shot pilot — complete | Continuity + Andre | T03,T04 | Existing accepted pilot envelope; determine applicability to new angle/composition, not blanket likeness acceptance. |
| T09 Speech route — complete, scoped | Dialogue-sound/continuity | T07,T08 | Proven English guide/picture route only; final-dub and historical mouth-visible evidence still required. |
| T10 Cost forecast — in progress | Producer | T08,T09 | Useful accepted seconds, reuse, per-shot ceiling/reserve, observed charges and unresolved charge uncertainty. |
| T11 Audio-led animatic — blocked | Storyboard/editor | T05,T07,T10 | Versioned measured timing, line windows, pauses, causal reaction and axis. Scratch preparation can proceed independently. |
| T12 Era/eye keyframes — in progress | Storyboard/continuity/lighting | T03,T08,T11 | Exact selected/hash-pinned references; material/identity/table/seat/light review and correct IN/OUT/reference roles. |
| T13 Galileo — in progress | Producer + editor/QC | T09,T10,T12 | Inspect existing exact files first; active-baseline shot coverage, final speech proof, whole-chapter playback and costs. |
| T14 Caesar — blocked | Producer + continuity/QC | T13 | Tested recipe applied only to missing Rome coverage; complete accepted chapter and causally correct performance. |
| T15 Genghis — blocked | Producer + continuity/QC | T13 | Tested recipe; scoped robe/armour choice, tent and rug/wood contact continuity; complete chapter playback. |
| T16 Napoleon — blocked | Producer + continuity/QC | T13 | Tested recipe; scoped hat/costume, explicit Longwood uncertainties, separate historical-language decision. |
| T17 Oppenheimer — blocked | Producer + continuity/QC | T13 | Missing bible/interpretation reconciled; fictional near-Trinity setting, meaningful silence, full chapter review. |
| T18 Opening/ending + English cut — blocked | Director/editor | T13,T14,T15,T16,T17 | Real accepted sources, reproducible in/out points, table motif/transitions and whole-film gap list. |
| T19 Measured corrections — blocked | Producer/QC | T18 | Defect range + revised hypothesis per replacement; reviewed corrections and cost reconciliation before picture lock. |
| T20 Historical edition — blocked | Dialogue-sound/editor/reviewers | T06,T07,T19 | Reviewed localized dry dialogue, captions, mouth-visible variants where necessary, explicit edition mapping. |
| T21 Both masters/QC — blocked | Independent QC + producer + Andre | T19,T20 | Exact exported files decoded and played end-to-end; technical/audio/caption/likeness/story review, stems and archive. |

**Important discrepancy:** T09 is recorded complete while T07 remains blocked; the prior audit explicitly preserves the completed English guide proof and separates final-dub / Edition H proof. STATE also describes delivered T12 review work while its board milestone remains in progress. These are scope/granularity differences to reconcile, not evidence that final voices or keyframes are accepted. [L3, L7 §§3–4]

### Cited findings: full finer-grained package coverage

The existing audit's P01–P30 are **proposed package labels**, not provider jobs or a replacement board. The table preserves every package and its accountable role, dependency/successor, and completion evidence. For per-instance details use the already-existing `work-packages.json` and `execution-graph.json`; do not recreate their 96 packages from memory. [L6–L7 §5]

| Package(s) | Owner / work | Dependency or successor | Acceptance evidence |
|---|---|---|---|
| P01 Baseline/authority | Producer | Canonical sources → P02/P03/P07/P26 | Dated baseline, ownership, source versions and categories. |
| P02 Handoff/task contract | Producer + management implementer | P01 → P03/P28 | Compatible schema, role boundaries, verifiable claims and named accepting successor. |
| P03 Readiness reconciliation | Producer | P01/P02 → P04/P11/P15 | Scoped board/approval/manifest consistency; stale flags do not confer readiness. |
| P04 Read-mostly tooling | Management implementer | Approved design/P03 → P05/P28 | Isolated checks for cycles, scope/hash/path conflicts, idempotent ingest. |
| P05 Backfill/plan pointers | Producer | Existing handoffs/P04 → close P03 | Every handoff classified; current-plan pointer without rewriting history. |
| P06 Existing Galileo playback | Editor/QC | Existing delivery, independent of new still branch → recipe/repair | Located exact file/hash; full playback, time/frame defects, honest review limits. |
| P07 Candidate review | History/material + continuity/lighting | Current candidates → P08 | Per-file findings, shortlist, explicit art-versus-fact and face-safe margins. |
| P08 Repairs/likeness | Continuity/desktop operator + Andre | P07 → P09/P10/P11/P15 | Only supported repairs, changed-only review, exact likeness/use approval. |
| P09 Dramatic trigger sheets | Director/storyboard + historian/sound | Current lines/research → P10/P11 | Five causal sheets: intention, difficult line, trigger, gesture, consequence. |
| P10 Bible/space/light integration | Continuity/lighting + producer | P08/P09 → P11/P15 | One coherent revision, current dialogue hash, selected geometry and uncertainties. |
| P11 Measured guide/animatic | Dialogue/editor | Current scratch + selected stills → P15/P16 | Measured line/pause windows, candidate-labelled timeline/animatic. |
| P12 Final English voice/dry lines | Dialogue + Andre | Existing auditions, scoped recording/render route → P14/P21/P22 | Approved samples, rights, dry stems, duration/performance/pronunciation evidence. |
| P13 Historical languages | Dialogue + qualified reviewers | Frozen script/target decisions → P14/P23 | Supported reviewed route or explicit adaptation/defer blocker for each chapter. |
| P14 Final speech proof | Dialogue/continuity | P12; P13 for H → P16/P23 | Hardest mouth-visible sample fully reviewed, or approved mouth-hidden coverage. |
| P15 Exact shot packet/release | Producer | Selected assets, guide, cost/route scope → P16–P20 | Input/request hashes, actual schema, framing/motion risk, ceiling and stop rule. |
| P16 Galileo recipe | Producer/editor/QC | P06/P15 + speech evidence → P17–P20 | Complete accepted-use chapter mapping, playback, identity/sync/space, cost reconciliation. |
| P17 Caesar | Producer/editor/QC | P15/P16 → P21 | Accepted C coverage, whole chapter, sound contacts and costs. |
| P18 Genghis | Producer/editor/QC | P15/P16 → P21 | Accepted K coverage, scoped materials, whole chapter and costs. |
| P19 Napoleon | Producer/editor/QC | P15/P16 → P21 | Accepted N coverage, uncertainty/edition mapping and playback. |
| P20 Oppenheimer | Producer/editor/QC | P15/P16 + interpretation → P21 | Accepted O coverage, measured consequence/silence and playback. |
| P21 English rough cut | Director/editor | P16–P20 + approved opening/ending → P22 | Reproduction timeline, asset map, whole cut and measured gap list. |
| P22 Corrections/sound/lock | Producer/QC + dialogue-sound | P12/P21 → P23/P24 | Reviewed fixes, sync/foley/ambience/music, stems, measured loudness/peaks, locked picture. |
| P23 H edition/captions | Dialogue/editor/reviewers | P13/P14/P22 → P24 | Reviewed H cut, translations/captions/voice/sync, line-level edition mapping. |
| P24 Export/independent acceptance | Editor + independent QC + Andre | P22/P23 → P25 | Exact-hash masters, decode/metadata/full audio playback/temporal and caption checks. |
| P25 Delivery/archive/continuation | Producer | P24 → closure | Usable masters/captions/stems/source-rights/ledger inventory; recovery evidence if requested; next episode requires its own brief. |
| P26 Documentation/lifecycle cleanup | Producer/maintainer | P01, existing consolidation → P27/P30 | Semantic authority graph, reversible change manifest, originals retained. |
| P27 Skills/manual verification | Maintainer/provider operator | P26 → P28/P15 | Reviewed local bindings/source revisions; documented versus runtime-tested distinction. |
| P28 Lifecycle adapter/hooks | Management implementer | Runtime audit/approved implementation/P02 → P29 | Deduplication/replay/failure/successor tests and actual receipt proof; no paid execution from hooks. |
| P29 Controlled activation | Producer/runtime operator | P28 → P30 | Harmless local event chain, restart/no-duplicate evidence, rollback. |
| P30 Cold-start audit/return | Independent reviewer + producer | Enabled infrastructure → unfinished P06/P07 | Cold agent finds authority/input/stop/next owner; production approvals unchanged. |

### Inferences / proposed common dependency graph

```text
Script version + scene EVENTS + stable line IDs                 [new event layer]
 ├─ character/wardrobe/prop sheets ─┬─ selected shared-space/location references
 ├─ voice ownership/casting ────────┤
 │   └─ recorded OR designed source → approved reusable voice → approved dry lines
 └─ dramatic trigger/action map ───┴─ measured guide/animatic + coverage plan
                                      ├─ start/end frames + phone motion reference
                                      └─ exact shot/provider/audio-role packet
                                                ↓
                           Galileo/bounded pilot → temporal/voice/sync/continuity QC
                                                ↓
                         accepted recipe → remaining shots/chapters → English cut
                                                ↓
                       approved localized lines + mouth-visible variants → H cut
                                                ↓
                         sound/stems/captions → exact-master QC → delivery/archive
```

Independent branches: existing auditions can be listened to while stills are reviewed; old Galileo footage can be inspected while missing references are prepared; language review need not block English guide editing. Final delivery still requires final voice/language/sync evidence. Enabling cleanup or hook work is not a blanket prerequisite to useful local review. This follows the prior package plan, not a proposal to launch work now. [L7 §5]

### Proposed missing work packets for the unified strategy

These are **new planning additions**, not completed tasks or new board IDs:

| Packet | Proposed owner | Dependency | Acceptance |
|---|---|---|---|
| Script-event crosswalk | Director + producer | Chosen script/version | Every event has stable identity, before/after state, line/shot links; old IDs retained as aliases. |
| Character asset pack | Continuity + user | Script cast + selected identity | Character sheet, wardrobe/expression/angle variants; genuine source versus synthetic derivation explicit; chosen references approved. |
| Location pack | Art/continuity | Script locations + scene geography | Establishing and coverage angles, table/seat/prop map, light direction; shared-space continuity across shots. |
| Voice ownership matrix | Dialogue lead + user | Cast list + existing audition inventory | Each character assigned recorded-consented, designed, or unresolved source; explicit language/use scope. |
| Voice source/clone pack | Dialogue lead | Ownership choice + available route | Clean source, exact transcript, provenance/hash, reusable voice reference ID and audibly approved identity; generation and cloning recorded separately. |
| Performance/phone capture brief | Director + performer | Event action, blocking, camera and dialogue timing | Exact action/camera/start/end, usable framing, reference take ID; phone scratch audio never silently becomes final dialogue. |
| Provider input translation | Platform operators + producer | Shared shot packet | Actual supported tokens/slots, identity/motion/start/end/audio roles mapped; unsupported inputs left explicit. |
| Approved-audio editorial bridge | Dialogue lead + editor | Approved dry lines + selected picture | Line-to-shot timing, immutable source takes, sync derivative lineage, stems/EDL handoff and tested export. |

### Gaps

This inventory recovers planned obligations, not runtime readiness. The prior 41-slot plan is coverage accounting, **not 41 paid generation orders**. Existing approval flags, take counts, plan completion, and file existence do not substitute for listening, full playback, or scoped creative acceptance. [L7 §§1,6–7]

## 3. What exact naming and continuity contract should cross platforms?

### Takeaway

Share **story identity and provenance**, not one filename grammar. Existing ComfyUI, Argon and OpenReel conventions differ. Add an immutable event crosswalk above their adapters, preserving their parsers, legacy shot IDs and dialogue IDs. [L8–L12]

### Cited findings

| Existing surface | Verified convention / constraint |
|---|---|
| Film | `G-L03`/`G-L04` dialogue; `G-P03` listening, `G-P04` speaking; `G-MASTER`, `G-LISTEN-KF`; reference roles `G-ID`, `G-TABLE`, `G-ERA`, `G-IN`, `G-OUT`. G-P04 asks warmth/firmness, fixed camera, exact line, one low gesture and mouth closing afterward; its proposed 11 seconds is not a measured final-voice duration. [L4–L5] |
| Argon human handles | `@CHAR_AndreAthar`, `@ENV_ZenCafe`, `@PROP_Smartwatch`; example element `CHAR_AndreAthar_v2`, sheet `CHAR_AndreAthar_v2_ref03_three-quarter-left.png`. Human handles differ from provider rich tokens; existing element names are not uniformly normalized. [L8] |
| Argon asset catalog | `[YYYYMMDD]_[ProjectCode]_[Category]_[MediaType]_[Descriptor]_[Spec]_v[NN].[ext]`; project code allows 2–12 uppercase alphanumerics; descriptor/spec are normalized alphanumeric/hyphen. Categories include `CHAR,PROP,ENV,SFX,VOX,MUS,KFRM,SHOT,EDIT`. [L9] |
| OpenReel script naming | Entity kinds `CHR,LOC,PRP,VOX`; scene `S012`, shot `HSTL_S012_SH03`, take `HSTL_S012_SH03_kl-v3o_T02.mp4`; project parser length 2–6; provider Element names capped at 32 characters in its helper. Its strict shot/take parser does not admit a new `_EV...` segment. [L10] |
| ComfyUI studio | Lowercase-slug project/scene/shot. Input `input/refs/<project>/`; sheet `studio/shots/<project>-<scene>.json`; output `output/refs/<project>/<scene>/<shot>/<scene>-<shot>_<model>_<aspect>_s<seed>_00001_.png`, with sidecars/index. Structured prompt fields `shot_size,camera,subject,action,location,lighting,look,lens`; subject required. [L11] |
| Argon handoff | Original ComfyUI images are manually imported as candidates, then selected as starting frames for existing shots. Preserve original bytes/SHA256/dimensions/native metadata; do not infer provider job/model IDs or create two-store synchronization. [L12] |

### Inferences / proposal: event-rooted crosswalk

**Illustrative assignments only**—no existing event or scene IDs were renamed or created:

```yaml
project: andre-time-travel
projectCode: ATT                 # proposed; 3 chars works across checked parsers
scriptVersion: en-v2-2026-10-09
sceneId: S003                    # illustrative mapping; producer must approve order
sceneAlias: galileo
eventId: ATT-S003-EV020          # immutable narrative beat, not an EDL cut event
eventLabel: andre-answers-what-survives
eventSource: G-L03-to-G-L04
shotId: G-P04                   # preserve existing authority
shotAliases:
  openreel: ATT_S003_SH04       # crosswalk only, not an already registered shot
  comfy: g-p04
lineIds: [G-L04]
characterId: CHAR_AndreAthar
voiceId: VOX_AndreAthar_v01      # proposed internal identity, not provider voice ID
references:
  identity: G-ID
  sharedSpace: G-TABLE
  locationEra: G-ERA
  startFrame: G-IN
  endFrame: G-OUT
audioIntent: post_dub
approvalScope: pending
```

Recommended rules:

1. Freeze event IDs when the initial script is broken down. Later insertions receive new IDs; changing display order does not renumber existing events. Split/merge records retain `derivedFrom` links. Keep script revision and current source text/hash separately from identity.
2. Store project → scene → event → shot → dialogue line → take relationships in the owning production record/crosswalk. One event may need multiple shots and one line may span cuts. Do not embed mutable wording, actor choice, or platform in the permanent event identity.
3. Keep character ID, visual-identity version, voice-identity version, wardrobe/look, location, motion-reference take, and audio take separate. An approved face image does not approve a voice; a voice reference is not a final line.
4. Preserve `G-L04`; attach edition/language/take as metadata or in new audio filenames, e.g. proposed `ATT_G-L04_E_en_T03.wav` and `ATT_G-L04_H_it_T02.wav`. Keep the same line ID through translation; text revisions get version/hash changes.
5. Translate into existing filename grammars. Proposed Argon example: `20261030_ATT_VOX_AUDIO_S003-EV020-G-L04-E-en_DRY_v01.wav` (descriptor/spec use hyphens). OpenReel example stays `ATT_S003_SH04_kl-v3o_T02.mp4`, with event identity in metadata/manifest. ComfyUI keeps lowercase scene/shot directories and native generated names; attach the crosswalk in sidecars/ingest records.
6. Store exact provider IDs/tokens and input roles separately, including the actual model/route, source hashes, request/prompt version, output lineage, status and approved use. A friendly `@CHAR_...` string is not proof a provider received an Element, voice, start frame or motion video.
7. Preserve original masters and derivative lineage. Never rename an old source in place to make it look accepted or erase its actual seed/model provenance.

### Proposed shared prompt bridge

The common packet should contain `scriptVersion`, `sceneId`, `eventId`, `shotId`, `lineIds`, exact spoken text, edition/language, character/voice identities, reference IDs and their roles, action before/after states, causal trigger, camera/blocking, light/lens/look, wardrobe/props/table/axis continuity, duration/handles, and `audioIntent`. **Prompt prose is only one output of this packet.**

For the recovered example: G-P03 listens to G-L03, “And what survives of the question?”; G-P04 carries G-L04, “Your observations. And one lesson from your trial that people keep relearning: silencing a man does not settle a question.” Preserve the exact line and its warmth/firmness, one low gesture, fixed camera and closed mouth after speech. The checked scratch durations are 2.83s and 8.62s respectively; they are not final performance timings. [L4–L5]

- **Visual adapter:** compile the existing ComfyUI prompt fields or provider-native identity/start/end slots from this packet. Higgsfield identity preparation and Kling final generation retain the same event/shot lineage; platform agents verify model-specific limits.
- **Motion adapter:** phone footage is labelled performance/motion reference with event/shot/take and start/end poses. Decide whether its sound is scratch, performance timing, or authorized voice source; do not infer that role from the `.mp4` extension.
- **Voice adapter:** exact text + language + voice reference + performance brief + pronunciation notes. Omit camera descriptions. Unsupported emotion controls stay in the actor/audition direction rather than being invented as API parameters.
- **Editorial adapter:** approved source take, source in/out, line-relative word timings, shot-relative dialogue placement, handles, guide-mute policy and sync derivative link. Argon owns its shots/takes/cuts when operating inside Argon; do not make the OpenReel fork's independent production store a competing authority. [L13]

### Gaps

The event crosswalk is not implemented. Argon's auto-cut goal is V1-only with no separate audio tracks, while its broader EDL types support audio and A1–A4. Therefore neither “Argon has no audio support” nor “the proposed final-dialogue mix already round-trips through auto-cut” is justified. Audio ingest, placement, preview/export, and stems need an explicit implementation proof from the editorial agent. [L13–L14]

## 4. Which voices and tools actually exist, and who owns them?

### Takeaway

There is a historically documented Athar ElevenLabs clone and existing unreviewed opening auditions. Local Qwen3-TTS code is installed, but this research did not locate its weights or an approved saved voice in the checked locations. An Argon image Element is not a voice clone, and its current attachment remains unresolved. [L15–L20]

### Cited findings

- The October 9 reference-sheet plan records Athar's ElevenLabs professional voice `xxSch4PcHFM1VKvYKjt2`, tagged Portuguese/Brazilian Portuguese, and explicitly requires English/Italian auditions. This is evidence of a prior recorded account observation, not proof of present accessibility, ownership verification, subscription, language quality, or production approval. [L15]
- `04_audio/voice-tests/codex-opening-v1/provenance.json` records four `IN-L01-athar-v2-ref-{1..4}.mp3` generated candidates, roughly 7–8 seconds, each `audioQualityReviewed=false`, `approved=false`. Review these before paying to reproduce equivalent auditions. [L15]
- The restaurant design reports Element `323980733525179` has an ElevenLabs voice. However, Argon's checked co-director context sets `elementHasVoice: null`, image Element creation passes name/description/tags/resource/taskTraceId without voice, and BACKLOG identifies voice registration as missing. The older film Element `323525046658711` is another identity record. Neither name similarity nor image registration establishes a usable voice binding. [L7, L16, L18]
- Two local wrappers exist: `custom_nodes/qwen3-tts` documents clone/design/custom and RoleBank `.qwen3tts`; `custom_nodes/qwen3-tts-comfyui` documents SaveVoice/LoadSpeaker `.qvp`. These formats are wrapper-specific; no interoperability was verified. [L19]
- Read-only metadata inspection in the activated ComfyUI venv found `qwen-tts 0.1.1`, `transformers 4.57.3`, `torch 2.14.1+cu130`, `soundfile 0.12.1`. No model was imported/loaded. Bounded filesystem checks found `models/qwen-tts` with an empty `voices/`, no `models/TTS/Qwen`, no `extra_model_paths.yaml`, no top-level Qwen-TTS entries in the checked Hugging Face hub cache, and no checked ModelScope hub. The read-only approved model catalog listed sd15, z-image-turbo and flux2-klein-4b, not Qwen TTS. Other locations were not exhaustively searched. [O1]
- Targeted discovery of voice/audio/speech/clone tools returned no direct callable voice tool in this session. That is a session discovery result, not a global claim that the machine or providers have none. [O1]

### Inferences / proposed casting matrix

| Character | Existing lead | Decision / acceptance needed |
|---|---|---|
| Andre/Athar film lead | Historical Athar professional clone; four opening candidates | Confirm this remains the intended voice; listen and approve exact sample; decide whether a fresh recording is needed. |
| Andre restaurant test | Separate Element claimed voice-bearing | Confirm whether it is the same speaker/voice as the film and which provider binding is actually usable. |
| Caesar | No approved final voice found in checked sources | Cast a designed voice or authorized actor; approve English identity and Latin convention separately. |
| Genghis | No approved final voice found | Designed/authorized actor; approve English identity and explicit historical Mongolian approximation/reviewer. |
| Galileo | No approved final voice found | Designed/authorized actor; English audition and reviewed period/region Italian target. |
| Napoleon | No approved final voice found | Designed/authorized actor; resolve Corsican/Tuscan childhood target rather than silently substituting French. |
| Oppenheimer | No approved final voice found | Distinct fictional performance, not imitation of a contemporary film actor; English pronunciation/performance review still applies. |

Historical figures' lines are offscreen in the existing D14 route. They still need distinct approved voices, but do not automatically require visible-face lip-sync jobs. [L17, L21]

### Gaps / decision boundary

**Voice ownership means three different things:** the source speaker's authorization, the creative character-to-voice assignment, and control of the provider voice record. Resolve each explicitly. Do not turn the phrase “clone each character” into cloning an actor or assigning the user's voice to every character. There is no need to introduce a fifth paid provider by default: first establish the previously used ElevenLabs account's suitability. The existing task specification says to record voice separately and **not silently switch away from ElevenLabs**; evaluating or adopting local Qwen as a replacement is therefore an explicit route decision, not an assumed migration. If neither is available/adequate, a new paid service is a user decision, not an automatic recommendation. [L2:47–58,86–97]

## 5. What is the documented reference-to-clone workflow?

### Takeaway

Separate **voice design**, **recording**, **cloning**, **speech generation**, **performance conversion**, and **lip-sync**. A designed sample may become a repeatable clone reference; generating speech or a video with sound does not by itself establish a reusable cloned identity. [V1–V4]

### Cited findings: primary documentation

| Route | What it actually does | Reference / acceptance implications |
|---|---|---|
| Qwen3-TTS **Base** | Clones from reference audio and transcript; reusable clone prompt | Official flow uses `create_voice_clone_prompt(ref_audio, ref_text)` then `generate_voice_clone(..., voice_clone_prompt=...)`. Transcript omission is the `x_vector_only_mode=True` path with possible quality loss; it is not the preferred full-context route. [V1] |
| Qwen3-TTS **VoiceDesign** | Produces a new voice from descriptive instruction | Official example designs a sample, then uses that sample and its exact text in Base to stabilize future speech. This is a designed-source clone, not a recording of a real speaker. [V1] |
| Qwen3-TTS **CustomVoice** | Uses preset speakers / model-supported controls | A preset speaker is not a clone of the supplied character. Do not transpose every CustomVoice instruction parameter onto Base. [V1] |
| Local Qwen wrapper advice | Clean single-speaker reference, usually 5–15 seconds, exact transcript/language | Wrapper recommendation, not a universal requirement or proof local weights are present. Keep local model loading from silently downloading during a later unapproved test. [L19] |
| ElevenLabs Instant Voice Cloning | Creates reusable voice identity from recordings | Official guidance recommends clear consistent material around 1–3 minutes, at least a minute; more than 3 minutes generally provides little benefit. Required rights/consent apply. Short Qwen examples are not automatically suitable IVC datasets. [V2] |
| ElevenLabs Professional Voice Cloning | Higher-data training/verification route | Official guidance is roughly 30 minutes–3 hours; the source must be the user's own verified voice under its PVC policy. Do not propose uploading another actor's recordings to the user's PVC slot. [V3] |
| ElevenLabs Voice Design | Designs voice options from a description; selected voice can be saved | No recorded-speaker clone is implied. Audition and save the selected designed identity before creating production lines. [V4] |

Qwen's official language list covers Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish and Italian. This does **not** establish support or quality for Classical Latin, thirteenth-century Mongolian, Corsican/Tuscan historical targets, or period Italian pronunciation. The checked historical-language matrix has no assigned reviewer and all rows unapproved. [V1, L21]

### Inferences / proposed voice-production sequence

1. **Inventory and casting:** link every speaker to a stable character/voice record; retain existing audition paths. Resolve recorded versus designed source and who approves its identity. Listen to existing Andre candidates before commissioning more.
2. **Reference capture or design:** for a real speaker, capture clean, dry, single-speaker speech without music/reverb and with natural delivery; select material appropriate to the chosen route. For a designed character, author a specific voice brief (age range, timbre, accent target, resonance, rhythm, emotional baseline), audition options, and approve one. Record `sourceKind=recorded-consented|designed`, not just `cloned=true`.
3. **Reusable identity:** preserve original reference audio, exact transcript, language, source provenance/authorization, file hash, tool/model/version/settings, and any provider voice ID or local saved-prompt path. Store the actual sample rate/channels/duration rather than assuming every provider needs one format. Clone/save only through the documented route.
4. **Identity acceptance:** audition the same short test text across the relevant languages and at least neutral, warm, strained and quiet performance intentions. The user's listening approval is separate from a tool's successful response. Retain selected and rejected takes; do not require every tool to expose the same emotion controls.
5. **Pronunciation/performance sheet:** per line store exact canonical text, edition, language/locale/convention, speaker/voice version, name pronunciation or phonetic guidance, emphasis, emotional intent, trigger, pauses, and reviewer. Where the route supports dictionaries or instruction controls, the platform operator maps them; otherwise use a directed performance/reference and audition. No unsupported API syntax is prescribed here.
6. **Dry dialogue takes:** generate or record one stable line ID per take, with natural lead/tail silence. Measure actual duration and word/phrase timing after the take is approved. Save original and editorial derivative separately. Do not compress speech to satisfy an old shot duration.
7. **Editorial timing:** build/update the animatic from those approved durations, with causal reactions and breathing room. Re-cut or extend coverage before considering destructive speech/face time warping. If scratch remains in a draft, label it unmistakably.
8. **Reuse:** a character identity can remain fixed while language, emotion, line text and take vary. Replace a voice version only through an explicit casting decision; propagate only its dependent line takes and sync derivatives.

### Gaps

This sequence is proposed, not run. Local readiness requires a later authorized weights/license/resource check. Provider-account access, current price, clone ownership verification and language performance remain unverified. No audio was played, generated, converted, uploaded or cloned in this research.

## 6. How does approved audio reach video, lip-sync, and the final edit?

### Takeaway

The already-chosen film route is **Kling native guide → approved external final dub → measured sync review**. An external audio asset must be attached through a verified supported route or added in editorial/post-sync; writing its name in a video prompt is not audio conditioning. [L17, L21, V5]

### Cited findings

- D14 specifies Andre's Kling native audio **ON as guide only**, final ElevenLabs clone dub with word timing (faster-whisper), and visible-word drift around **120ms** as a trigger for lip-sync fallback or approved listener/insert coverage. It is Edition E-scoped and timing proof remains pending. The threshold is a local investigation trigger, not universal perceptual acceptance. Figure lines stay offscreen; scratch is edge-tts, final voices designed/consented. [L17, L7 P14]
- The film language strategy explicitly says the selected Kling I2V external speech-audio input is not established; do not invent an `--audio` flag. The accepted Argon dialogue/motion ADR concerns native dialogue and motion-library/video inputs; it does not prove the final external clone path. [L21, L18]
- Current ElevenLabs Image & Video documentation lists **Sync 3** and **Sync Lipsync 2 Pro** with **Source Video + Speech Audio** inputs. Sync 3 is explicitly a video-to-video lip-sync tool, not a full video generator; detectable figures are recommended. Costs vary. This documents a potential route within an already historically used provider, not present account entitlement or approval to purchase/use it. [V5]
- Edition E is all English. Edition H uses both speakers in each target language with English subtitles; reuse non-mouth footage when appropriate. Napoleon's target cannot silently become French, and Oppenheimer's intended voice is distinct from an actor imitation. [L21]

### Inferences / proposed handoff contract

For every final line/shot pair, pass an **approved audio handoff** containing:

`projectId, scriptVersion, eventId, shotId, lineId, edition, language, characterId, voiceVersion, audioTakeId, originalPath, sha256, actualDurationMs, sampleRate, channels, transcriptHash, pronunciationReview, wordTimings, shotStartOffsetMs, sourceInMs, sourceOutMs, leadTailHandlesMs, audioIntent, approvalScope`.

Then select one explicitly verified route:

1. **Documented audio-conditioned video/performance route:** attach approved audio in its actual audio slot, distinguish identity/reference audio from the exact speech-to-perform, and verify whether output preserves words, timing and voice. Platform agents must establish this for the selected provider/model; general “native audio” marketing is insufficient.
2. **Native-guide video + post-dub (existing D14):** mute/replace guide speech in the edit, align approved dry audio, inspect every visible phrase and full normal-speed playback. Use listener/insert coverage where already artistically appropriate; do not claim perfect sync just because the total durations match.
3. **Post lip-sync derivative:** selected picture + approved speech track enter a documented lip-sync tool. Retain original picture/audio and label the derivative's parent IDs, version and cost. Re-review identity, teeth/jaw, gaze, framing, hand/contact timing, exact spoken text, audio quality and the entire clip. An approved original face does not automatically approve the derivative.
4. **Offscreen speech:** place the approved dry line against listener/detail coverage; no mouth-sync job is required merely because dialogue exists. Preserve reaction-after-trigger logic.

The editor receives separate dialogue, ambience, Foley, music and guide identities/stems; guide speech must not leak into final delivery. Derive final captions from the approved line text and timing, not solely from automatic transcription. Preserve source timing in milliseconds through Argon and convert only at the existing editorial boundary. For final sound, choose/confirm delivery loudness/peak targets from the production specification rather than inventing new targets in this research. [L13, L7 P22–P24]

### Gaps / decisions for the integrating researcher

1. Which exact project/script/version is the unified strategy executing first: active Galileo film, restaurant test, or a new script?
2. Is Athar's previously documented voice still the approved casting target? Are the existing four auditions accessible and worth approving? Is the restaurant Element intended to bind that same identity?
3. Which characters should be **designed voices** and which use authorized recorded performances? Who supplies/reviews each historical language?
4. Can existing ElevenLabs access supply the intended clone/dub/lip-sync route, or should an authorized local Qwen setup be evaluated? **Do not add a fifth paid service by default.**
5. Which exact video models accept exact speech versus identity audio versus guide sound? Other agents must resolve provider-specific capability and costs.
6. Where will the event crosswalk and approved audio take mappings live under the chosen production authority? The crosswalk is a proposed contract; no schema migration occurred.
7. Does the chosen Argon/OpenReel path support final separate dialogue tracks, stems, captions and tested exports, beyond the V1-only auto-cut goal?

## Sources and verification boundaries

Local paths below were read directly. Line references identify particularly relevant evidence, not the only useful content. Dated plans are cited as plans. Web references were fetched on 2026-10-30; Qwen API details were additionally checked via Context7 library resolution followed by docs for `/qwenlm/qwen3-tts`. No account/runtime voice test was performed.

- **L1:** `/mnt/data/Projects_SSD/Movies_Projects/docs/PRODUCTION_PLAN.md:7–31,109–133` — source authority, active baseline, audioIntent semantics.
- **L2:** `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/tasks/board.json`; `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/tasks/specs/production-tasks.md:47–97,114–125` — board and acceptance specification; voice-route ownership, distinct designed/consented cast, dry tracks, both-edition sync proof. The older audit's shortened task-spec path is stale; the verified path includes `tasks/specs/`.
- **L3:** `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/memory/STATE.md:5,64–70` — active Galileo scope and existing work limitations.
- **L4:** `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/05_storyboard/source/production-plan.json:431–575` — actual Galileo shot/reference/line registry and performance directions.
- **L5:** `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/01_script/script-en.md:1–8`; `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/01_script/dialogue-lines.csv:1–23` — canonical script, IDs/text, measured scratch and approval flags.
- **L6:** `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/tasks/execution-plan-v1/README.md:3–13,67–77`; `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/tasks/execution-plan-v1/work-packages.json`; `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/tasks/execution-plan-v1/execution-graph.json`; `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/tasks/plans/workflow-map-v1.md:5–12,69–104` — complete prior plan/index and graph, not a second board.
- **L7:** `/mnt/data/Projects_SSD/Movies_Projects/reports/execution-plan-v1/requirements-audit/requirements-audit.md:41–143,172–204` — complete T/P/W coverage, continuity, acceptance, enabling-work boundaries; October 10 audit, not a live status query.
- **L8:** `/mnt/data/Projects_SSD/argon-studio/docs/platform-presets.md:7–30` — human handles, reference naming, provider tokens.
- **L9:** `/mnt/data/Projects_SSD/argon-studio/packages/asset-catalog/src/naming.ts:3–46`; `/mnt/data/Projects_SSD/argon-studio/packages/shared-types/src/asset.ts:3` — catalog filename rules/categories.
- **L10:** `/mnt/data/Projects_SSD/openreel-video/packages/core/src/script/naming.ts:14,42–83` — scene/shot/take/entity helpers, strict parser and Element-name length.
- **L11:** `/mnt/data/Projects_SSD/ComfyUI/studio/README.md:10–16,34–56,58–90` — local naming, structured fields, provenance and worker distinctions. Z-image refs are recorded rather than conditioning; Klein supports conditioning refs in the documented worker.
- **L12:** `/mnt/data/Projects_SSD/argon-studio/docs/COMFYUI_REFERENCE_FRAMES.md:3–25` — original-image manual import/candidate/approval contract.
- **L13:** `/mnt/data/Projects_SSD/argon-studio/goals/argon-auto-edit/facts.md:6–22` — Argon authority, V1-only auto-cut goal, integer-millisecond boundary.
- **L14:** `/mnt/data/Projects_SSD/argon-studio/packages/shared-types/src/edl.ts:5,34–39` — broader audio-track type support.
- **L15:** `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/docs/reference-sheets-plan.md:12,64–68`; `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/04_audio/voice-tests/codex-opening-v1/provenance.json:3–32` — historical clone observation, language audition need, unapproved opening candidates.
- **L16:** `/mnt/data/Projects_SSD/argon-studio/docs/superpowers/specs/2026-10-28-andre-dialogue-motion-scene-design.md:8–18,69,80–82` — separate restaurant scene design and limited voice claim.
- **L17:** `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/00_brief/decisions/D14-dub-strategy.json:10–18` — English guide/dub decision, offscreen figures, unresolved timing proof.
- **L18:** `/mnt/data/Projects_SSD/argon-studio/docs/ARCHITECTURE_DECISION_RECORD.md:141–174`; `/mnt/data/Projects_SSD/argon-studio/apps/studio-server/src/codirector/tools.ts:198`; `/mnt/data/Projects_SSD/argon-studio/apps/studio-server/src/assets/register.ts:42–45`; `/mnt/data/Projects_SSD/argon-studio/docs/BACKLOG.md:34` — native-dialogue/motion design and voice-registration uncertainty in checked code.
- **L19:** `/mnt/data/Projects_SSD/ComfyUI/custom_nodes/qwen3-tts/README.md:139–150,177–178`; `/mnt/data/Projects_SSD/ComfyUI/custom_nodes/qwen3-tts-comfyui/README.md:195–206` — installed wrapper capabilities/reference recommendations, not execution proof.
- **L20 / O1:** Direct read-only package metadata under `/mnt/data/Projects_SSD/ComfyUI/.venv` and bounded filesystem inspection of `/mnt/data/Projects_SSD/ComfyUI/models/qwen-tts`, `/mnt/data/Projects_SSD/ComfyUI/models/TTS/Qwen`, `/mnt/data/Projects_SSD/ComfyUI/extra_model_paths.yaml`, `/home/athar/.cache/huggingface/hub`, `/home/athar/.cache/modelscope/hub`; read-only model catalog and tool-discovery results. These are research-session observations, not persisted readiness certifications.
- **L21:** `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/01_script/language-matrix.csv:1–6`; `/mnt/data/Projects_SSD/Movies_Projects/projects/andre-time-travel/01_script/language-strategy.md:6–16,37–39` — E/H contract, language decisions/review gaps, unsupported external-audio assumption.
- **V1:** [QwenLM/Qwen3-TTS official repository](https://github.com/QwenLM/Qwen3-TTS) — model distinctions, languages, clone/reference and VoiceDesign-to-Base examples; Context7-confirmed API flow.
- **V2:** [ElevenLabs Instant Voice Cloning](https://elevenlabs.io/docs/creative-platform/voices/voice-cloning/instant-voice-cloning) — sample quality/duration and authorization.
- **V3:** [ElevenLabs Professional Voice Cloning](https://elevenlabs.io/docs/creative-platform/voices/voice-cloning/professional-voice-cloning) — longer recording dataset and own-voice verification.
- **V4:** [ElevenLabs Voice Design](https://elevenlabs.io/docs/creative-platform/voices/voice-design) — designed candidates and saved voice identity.
- **V5:** [ElevenLabs Image & Video](https://elevenlabs.io/docs/eleven-creative/playground/image-video), sections **Sync 3** / **Sync Lipsync 2 Pro** — source-video plus speech-audio post-sync. Fetched excerpt retained at `/home/athar/.local/share/opencode/tool-output/tool_18c96987e0015Np6VT6U1zqLpu:2315–2365`.

Research boundaries: targeted shared-memory recall was used only as a lead; unverified memory did not supply factual conclusions. Local source contents and primary documentation drive this note. No exhaustive claim is made about every historical conversation, cache, model directory, provider entitlement, or generated media file.

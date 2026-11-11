# Learning production: The Message

A small, proposed Andre Athar film made inside ComfyUI, one reviewed step at a time. This is new reference-guided generation, not an Andre face-swap test or an external Studio project.

## Two scenes, initially one shot each

| Scene | Action | Continuity |
| --- | --- | --- |
| 01 — The desk | Andre Athar sits at a desk and notices a folded note. No readable writing or intricate hand action required. | Modest apartment, soft late-afternoon light; proposed dark jacket over a plain shirt. |
| 02 — The doorway | Andre Athar pauses at the apartment's glass doorway and looks back. | Same actor, clothes, apartment and lighting. |

Start with a short diagnostic take, not a finished film. Review scene 01 before queueing scene 02. The first take had no dialogue or additional actors; the current lesson adds a separate own-voice test. H3's generated audio is not automatically an approved character voice or final soundtrack.

## Asset board

- **Actor reference exists:** library item `refmod-Andre_Athar`; subject `Andre_Athar`; concept `identity`.
- **Current identity metadata:** photo-stack visual RefMod, kind `video`, 7,104 reference tokens and eight image entries. The initial check/UI metadata showed 4,440/five; that earlier widget count is not proof of the previous render’s runtime budget. No paired voice is embedded in this identity file.
- **Meaning of `<Video 1>`:** with no other video references, H3 labels this saved photo stack as a video reference. That does not mean these were motion-video inputs or that it contains an actor performance.
- **Location approved by the user:** `output/The_Message/assets/apartment_00001_.png`, an empty room with cream walls, wooden flooring and large glass doors. The desk/note are not in this image; they must be supplied by the shot prompt or later prop assets.
- **Wardrobe locked:** take 01’s dark jacket and light-gray crew-neck shirt; chest reference saved under `input/The_Message/wardrobe/`.
- **Own voice encoded:** standalone `The_Message/Andre_Athar_voice_v1`, 8 seconds / 640 tokens. The user approved the off-camera “Not again” test as good enough for the learning film. [Voice test 01](THE_MESSAGE_VOICE_TEST01.md); [wardrobe/voice assets](THE_MESSAGE_VOICE_AND_WARDROBE.md).
- **Reference cost:** the current actor package is substantial at 7,104 visual tokens. Small output settings do not reduce that reference. Do not silently compress or recreate it.

## Step 1 — actor selection (confirmed by the user)

A working copy is saved at **06 - Learning Production → The Message - Scene 01**. It copies the reuse pipeline; it is not a newly configured or render-qualified shot.

1. Open that working copy, **not Create New and Generate**.
2. On the RefMod Stack, choose **Browse library… → refmod-Andre_Athar → Add to stack**. Add it once.
3. Leave the separate generation Media Loader empty for now, so the initial label mapping is easy to understand.
4. On Prompt Builder, open **Edit prompt**, keep **REF** mode, and use **Draft from RefMods**. Check that `Andre_Athar` is associated with `<Video 1>`.
5. Save the working copy. **Do not Run yet.** Next we add the location/look and scene-01 action; drafting from a RefMod alone is not a shot description.

The user confirmed selecting the actor and seeing the reference label. The RefMod already exists: creation is no longer on the critical path. This avoids re-encoding it or colliding with its existing filename on every take.

## Step 2 — location image (generated and approved by the user)

Open **06 - Learning Production → 00 - Create Apartment Asset**. This is a separate native ComfyUI image workflow, derived from the local SD1.5 daily tool. The original daily tool is unchanged.

- The prepared prompt describes an **empty apartment**, with the desk on the left, a doorway on the right, cream walls and afternoon window light. No actor appears in this reference, to avoid competing identity cues.
- Settings: **768×432, one image, fixed seed, 20 steps**, using the already-installed `v1-5-pruned-emaonly-fp16.safetensors`. This is not H3 video or RefMod creation.
- **Run this asset workflow once.** Review the output: plausible room, usable desk and doorway, consistent light, no people. It saves a PNG under `output/The_Message/assets/`.
- The user generated and approved `apartment_00001_.png` before the first H3 take. We inspected the approved image and adjusted the planned doorway to match its actual glass doors.
- After approval, upload that PNG through Scene 01's **Media Loader**. It will be `<Picture 1>` while the actor photo-stack stays `<Video 1>` (with no other video references). Then we supply the shot action and framing.

Why a separate asset workflow? We want to reuse one approved location across shots, not silently regenerate a different apartment on every take. A reference still guides the set's look; it does not guarantee exact room geometry across camera angles.

## Current lesson — review Scene 02 before assembly

The user ran the configured workflow successfully. Output: `output/The_Message/scene01/take_00001_.mp4`, **608×352, 56 frames / 24 fps (~2.33 seconds)**, observed execution **9 min 44 s**. Actor `<Video 1>`, room `<Picture 1>`, 20 steps and seed 0 are confirmed in the run history. The model generated the added desk/paper and downward gaze. Scene 01 remains unchanged; Scene 02 was generated separately.

The user considers this a good local baseline and defers sharpening/face refinement. They chose its jacket/light-gray shirt as the shared wardrobe and supplied their own recording. An 8-second voice RefMod is now saved separately, without changing the identity package. Subsequent voice and Scene 02 tests use separate outputs. The user approved the separate “Not again” voiceover test (~3 min 1 s). Scene 02 has now rendered with the shared actor, room, clothing and voice references: 56 frames in ~10 min 32 s. Review its continuity, new speech and visible mouth opening before assembling the film. [Scene 02 take 01](THE_MESSAGE_SCENE02_TAKE01.md); [approved voice test](THE_MESSAGE_VOICE_TEST01.md). [Wardrobe and voice lesson](THE_MESSAGE_VOICE_AND_WARDROBE.md); [take 01 evidence](THE_MESSAGE_SCENE01_TAKE01.md); [input recipe](THE_MESSAGE_SCENE01_INPUTS.md).

## What the automation needs

| Gate | We supply or decide | Existing workflow does |
| --- | --- | --- |
| Actor | Correct saved reference and its label | Load the RefMod bundle; present references to the encoder |
| Scene / shot | Location reference, wardrobe, action, framing and lighting | Encode the supplied prompt and references; it does not invent production intent |
| Take | Output settings, seed and sampling recipe | Sample, decode video/audio, optionally composite, save a take |
| Review | Accept/reject likeness, continuity, action and artifacts | Objective file checks alone cannot approve a performance |
| Next scene / assembly | Approved take choices, shot order, sound choice | Generate scene 02 with shared assets; assemble approved clips in a later bounded step |

Generation-pipeline defaults remain 608×352, 56 frames (~2.33 s at 24 fps), 20 steps, fixed seed 0. These are diagnostic starting values, not a measured runtime guarantee. The user generated the approved room still and one successful H3 Scene 01 take. One Scene 02 take has completed; no batch or assembly is queued. The Scene 01 baseline is retained, and Scene 02 approval is pending; no final-film approval is implied. Check available resources before subsequent renders and retain human review between scenes.

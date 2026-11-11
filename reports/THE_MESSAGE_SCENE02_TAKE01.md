# The Message — Scene 02, take 01

**Rendered successfully; continuity and listening review pending. No assembly yet.**

Workflow: **06 - Learning Production → The Message - Scene 02**.

Output: `output/The_Message/scene02/take_00001_.mp4`.
Audio-only listening copy: `output/The_Message/scene02/take_00001_audio.wav`.

## Shared assets and shot

- `<Picture 1>`: the approved apartment.
- `<Picture 2>`: the selected take-01 jacket/light-gray crew-neck shirt crop, used only for clothing.
- `<Video 1>`: existing actor identity `refmod-Andre_Athar`, current 7,104 visual tokens.
- `<Audio 1>`: approved voice reference `The_Message/Andre_Athar_voice_v1`, 640 audio tokens.
- Each saved RefMod is used once at strength 1. No asset recreated or silently compressed.
- One static medium shot: actor already standing inside at the glass doorway, small head turn back toward the room, no walking/door action.
- Prompted line: **“Not again.”**, English, once, in voiceover with lips closed. This take generates speech again; the approved standalone voice-test waveform is not pasted in.

## Verified execution

- Native prompt `56f19e36-27d5-4061-aed7-8615e5c62efa`: success.
- Observed execution: 1794339799885–1794340431750, **631.865 seconds (~10 min 32 s)**. One run, not a general performance benchmark or cold-load measurement; input-routing nodes were cached from preflight.
- Existing REF2VA INT8 model, H3 NVFP4 encoder, native H3 VAEs; 20 beta-schedule steps, SA solver, seed 0.
- FFprobe: H.264, **608×352, 56 frames, 24 fps, 2.333333 seconds**. AAC stereo, 32 kHz, 2.325 seconds; audio decodes to the listening WAV.
- Browser roundtrip and model-free map/dimension checks passed. The reference map contains exactly the four labels above.
- Scene 01 workflow/take, approved standalone voice-test video and existing identity/voice RefMod files have identical before/after hashes.
- Queue empty after this single take; no retry, batch or Scene 02 revision queued.

## Sampled-frame observations

The four frames show the requested glass-doorway setting, dark jacket/light-gray shirt, and a head turn from side profile toward the room/camera. This is visual agreement with the brief, not a likeness certification.

**The mouth visibly opens in a later sampled frame despite the lips-closed voiceover instruction.** Do not call this a successful mouth-lock or lip-sync test. The user may accept it for this learning film or request a targeted revision. Full playback is also needed for motion/continuity, and listening is needed for the actual words, voice likeness and sound quality.

![Frames 0, 18, 36 and 55](../.codex/artifacts/the-message-scene02-20261110/contact.png)

## Next gate

Approve this take for the simple two-scene learning film, or specify a revision. After approval, assemble the unchanged Scene 01 baseline followed by this take; do not silently regenerate either shot. Keep sharpening and face refinement deferred as requested.

Evidence: `.codex/artifacts/the-message-scene02-20261110/` includes the prompt, browser/routing checks, native generation history/result, FFprobe data and contact sheet.

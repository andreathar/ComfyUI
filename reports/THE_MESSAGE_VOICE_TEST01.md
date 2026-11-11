# The Message — voice test 01: “Not again.”

**One local generation completed successfully. The user approved it as good enough for this learning film.**

## Open in ComfyUI

**06 - Learning Production → 02 - Voice Test - Not Again**

This is a separate copy, not a replacement for Scene 01. The user chose the English line **“Not again.”**

- `<Picture 1>`: approved empty apartment reference.
- `<Audio 1>`: `The_Message/Andre_Athar_voice_v1`, 8-second reference / 640 tokens, once at strength 1.
- No actor identity photo-stack or wardrobe image in this test. No visible speaker, so this is **not a lip-sync or face-continuity test**.
- REF prompt requests a single off-screen male voiceover, no other words or music. That request is not proof of what was audibly generated.
- Existing REF2VA INT8 / H3 NVFP4 encoder / H3 video and audio VAEs; 608×352, 56 frames, 24 fps, 20 beta-schedule steps, SA solver, seed 0.

## Outputs

- Video: `output/The_Message/voice_test/not_again_00001_.mp4`.
- Audio-only listening copy: `output/The_Message/voice_test/not_again_00001_audio.wav`, decoded from that MP4 without gain, pitch, noise or sample-rate processing.
- Source excerpt for comparison: `input/The_Message/voice/andre_athar_reference_02s_10s.wav`.

The output audio comes from **sampler → VAEDecodeAudio → CreateVideo**, not a source-WAV passthrough. The reference guides newly generated audio; this does not certify an exact voice clone.

## Verified checks

- Browser save/reopen preserves the API prompt, with no page errors or workflow-schema warning.
- Model-free routing check: exactly `<Picture 1>` and `<Audio 1>`; dimensions 608×352 / 56 frames. Independent read-only review found no concrete wiring blocker.
- Native generation prompt `9aa1a74a-b93a-4cb9-be79-f300b65c46e1`: success, execution timestamps 1794339191054–1794339372516, **181.462 seconds (~3 min 1 s)**. One observed run, not a general speed benchmark. Input routing nodes were cached from preflight; this is not a cold-load measurement or a controlled comparison with Scene 01.
- FFprobe: H.264 video, 608×352, 56 frames, 2.333333 seconds; AAC stereo audio, 32 kHz, 2.325 seconds.
- Audio decodes and is non-silent (mean −31.1 dB, peak −6.2 dB). These numbers do not establish speech content, timbre, noise quality or intelligibility.
- Four sampled frames show an empty room with no visible person, consistent with the off-camera test setup.
- Scene 01 workflow, Scene 01 take, existing identity files and saved voice RefMod have identical before/after hashes. Queue empty after completion. No second speech take or Scene 02 queued.

## Human listening gate

Play the generated audio and compare it with the source excerpt:

1. Does it clearly say **“Not again”**, once, without extra words?
2. Does it sound recognizably like the user's natural voice and accent?
3. Is it understandable and free enough of noise/distortion for this learning film?

The user listened and approved this test as good enough for the learning film. This is human acceptance of this test, not proof that every later generated take will sound identical. The assistant has not listened/transcribed the output and does not independently certify these points. Keep the raw test before attempting prompt/voice-strength/duration changes; change one factor at a time if revision is needed. Do not move to lip-sync or Scene 02 until the user judges this test.

Evidence: `.codex/artifacts/the-message-speech-test-20261110/` contains the saved API prompt, browser and routing receipts, generation submission/history/result, FFprobe data and four-frame contact sheet.

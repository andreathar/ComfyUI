# The Message — wardrobe and voice assets

The user chose **take 01’s dark jacket and light-gray shirt**. Keep its output as the visual baseline; defer sharpening/upscaling and face refinement. One Scene 02 take has since rendered and awaits human review.

## Wardrobe lock

**Dark charcoal blazer over a plain light-gray crew-neck shirt.** Use this description consistently rather than requesting a different shirt color or costume in later shots.

Reference: `input/The_Message/wardrobe/take01_dark_jacket_light_gray_shirt.png`, a face-excluding 182×107 chest crop from frame 0 of `output/The_Message/scene01/take_00001_.mp4`. This is a low-resolution continuity guide, not a newly generated or sharpened clothing texture. A clothing RefMod is not required for this initial reference.

![Selected jacket and shirt](../input/The_Message/wardrobe/take01_dark_jacket_light_gray_shirt.png)

The existing actor identity RefMod and Scene 01 workflow were not modified.

## Own-voice recording

- Received recording: **31.64 seconds, 48 kHz, stereo, 24-bit PCM WAV**.
- Original Inbox upload preserved; identical master copied to `input/The_Message/voice/andre_athar_recording_20261110.wav`.
- Candidate excerpt: **2.00–10.00 seconds**, saved as `input/The_Message/voice/andre_athar_reference_02s_10s.wav`.
- Excerpt preserves the original sample rate, channels and PCM bit depth. No denoising, pitch change, gain normalization or voice transformation applied.
- Selection excludes the first two seconds, but was **not listening-qualified**. The user should play the attached excerpt and flag an unsuitable section, noise or another voice. No transcript, language or timbre claim is inferred from technical metadata.

## Saved voice RefMod

**Library → The_Message → Andre_Athar_voice_v1**

- File: `models/refmods/The_Message/Andre_Athar_voice_v1.safetensors`.
- Concept `voice`, subject `Andre_Athar`, standalone audio reference: **8 seconds / 640 tokens**.
- Created successfully through native `MiniMaxH3FantasticRefModCreate` using only the existing H3 audio VAE. No video VAE, diffusion model or text encoder was part of this job.
- This is encoding a reference, **not training a voice clone**. The user approved the first off-camera speech test as good enough for the learning film; lip-sync remains untested. See [voice test 01](THE_MESSAGE_VOICE_TEST01.md).
- Native job: `8c8fc851-8189-4dee-8e42-309c0cd9e75b`. The original identity asset’s before/after hashes match; queue empty afterward.

Creation recipe: **06 - Learning Production → 01 - Create Voice Asset (no video generation)**. It shows audio VAE → Create RefMod → saved filename. **Already executed successfully. Do not rerun it under the same name:** native creation refuses existing names. For later takes, select the saved voice in the library; do not recreate it each time. A different candidate needs a fresh name.

## Next test

The user chose **“Not again.”** One off-camera test over the approved room has completed successfully, without the heavier actor visual package. It is saved under `output/The_Message/voice_test/` and took ~3 min 1 s for 56 frames. **The user approved that voice test**. One separate Scene 02 take has since rendered; it needs its own continuity and listening review before assembly. [Scene 02 take 01](THE_MESSAGE_SCENE02_TAKE01.md). [Test output and listening gate](THE_MESSAGE_VOICE_TEST01.md).

## Reference-budget correction

The live identity library now reports **8 source images / 7,104 visual tokens**, whereas the earlier UI stack metadata showed 5 / 4,440. The saved UI metadata is not proof of the exact runtime tensor budget for the previous take. We leave the identity package unchanged and do not silently compress it. Future scene preflights must use current file/catalog information, not the old widget count.

Receipts: `.codex/artifacts/the-message-voice-20261110/` contains the browser roundtrip, submitted asset-only prompt, creation history, catalog snapshots and identity hash comparison. No download, installation, server restart, paid service or outbound recording upload was used.

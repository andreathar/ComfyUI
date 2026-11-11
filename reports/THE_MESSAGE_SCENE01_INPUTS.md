# The Message — Scene 01 inputs

The user approved `output/The_Message/assets/apartment_00001_.png`. It shows an empty cream-walled room with wooden flooring and large glass doors. It does **not** contain the desk or note; those are additions requested by the shot prompt. Scene 02 should use this glass doorway rather than the previously imagined wooden door.

**Current status:** take 01 has now rendered successfully; creative approval is pending. These are its input/setup instructions, not a request to queue it again. See [take 01 review](THE_MESSAGE_SCENE01_TAKE01.md).

## 1. Add the location, without recreating the actor

Open **06 - Learning Production → The Message - Scene 01**.

- Keep the existing **refmod-Andre_Athar** selection once in the RefMod Stack.
- On the separate **Media Loader**, open its window, click **Load files…**, and select `apartment_00001_.png` from `ComfyUI/output/The_Message/assets/`.
- Keep it as one ordinary picture reference. Do not create a new RefMod or mark anything as a video edit.
- Check the combined reference labels: **room = `<Picture 1>`; actor photo stack = `<Video 1>`**.

The room is a setting reference, not the first frame of an existing video. The actor and furniture must be generated into it.

## 2. Fill the REF prompt

Open **Edit prompt**, in **REF** mode. Keep the actor definition and identity-retention entry created by **Draft from RefMods**. If those sections are empty, add this subject definition: `<Subject 1> is Andre_Athar, the man whose identity is shown in <Video 1>.` Then add a retention entry for `<Subject 1>`, marker `fully_preserved`, note `Preserve his facial identity from <Video 1>.` These are prompt instructions, not a guarantee of identity fidelity.

In the **summary** text box, paste this paragraph (the task checkbox supplies its own bracketed prefix):

```text
Andre_Athar, the man whose identity is referenced in <Video 1>, sits at a small wooden desk in the apartment shown in <Picture 1> and notices a folded note. A quiet, thoughtful moment in natural daylight.
```

The editor splits **detailed_description** into TWO boxes. In **style opening (before [Shot 1])**, use:

```text
Live-action cinematic realism. Soft natural daylight.
```

In **detailed_description — shots**, paste the following, including the `[Shot 1]` prefix. Do not put this whole action paragraph in the style-opening box:

```text
[Shot 1] One continuous, static, eye-level medium shot. Use <Picture 1> for the room's cream walls, wooden floor, large glass doors and natural daylight; the room must no longer be empty. Add a simple small wooden desk along the left wall, with one folded white paper note on it. Andre_Athar from <Video 1> is seated at the desk, wearing a plain dark jacket over a light gray shirt. His face is clearly visible in a gentle three-quarter view. He remains mostly still and lowers his eyes toward the note once, with a calm, thoughtful expression. Keep the hands below the frame. No walking, camera movement, readable writing or dialogue.
```

In **overall_soundscape**, use:

```text
Quiet indoor room tone. No speech.
```

Keep **non_diegetic_music** as `N/A`. There is no approved voice RefMod; the H3 workflow still generates audio internally. We are not requesting a character voice or treating generated sound as a finished soundtrack.

## 3. Keep the first take bounded and named

- Generation size: **16:9, 0.2 MP, multiple 32 → 608×352**.
- Requested duration: **2 seconds → 56 aligned frames (~2.33 seconds)**.
- Sampler: retain the prepared **20-step** recipe and **fixed seed 0**.
- Save Video prefix: **`The_Message/scene01/take`**, giving output under `output/The_Message/scene01/`.
- Inputs are now saved and preflight-checked. The assistant tidied the duplicated shot markers and output prefix without changing the selected references/story; a before-copy is retained in `.codex/artifacts/the-message-learning-20261110/scene01-before-preflight.json`.
- Close the old Scene 01 workflow tab without saving over the corrected file, then reopen it from the workflow list. Confirm one `[Shot 1]` in the prompt and the `The_Message/scene01/take` prefix. **Run once**, with queue/batch count 1. Do not queue Scene 02 yet.

These small generation settings do not shrink the saved actor RefMod's 4,440 reference tokens. Runtime and memory behavior of this full configured graph remain unqualified on this laptop. Resource preflight found the shared queue idle, ~17,058 MiB available RAM, and 2,338/6,144 MiB VRAM resident at 0% GPU activity. This supports attempting one take, not a memory/runtime guarantee. No H3 job was queued by the assistant. Native offloading remains in charge; do not click Free VRAM or Free RAM during generation.

## First-take review criteria

1. Does the face resemble the approved actor references?
2. Does the setting resemble the approved room?
3. Are the new desk/note and chosen clothing coherent?
4. Is the brief glance plausible, without distracting artifacts?

A successful execution is not an approval. If the room or props drift, we can strengthen the visual assets after seeing the actual result rather than add speculative nodes in advance.

# Production rules (draft v1, for user review)

Governs how a strong model turns the user's free dictated script into a validated `production.schema.json`
document. Items marked **[USER]** are defaults I invented; replace them with the user's own rules.

## 0. Process (in order; never skip ahead)

1. On initial creation, copy the full dictation verbatim into `project.source_text`. On revision, preserve that full script and apply only explicit script edits; technical shot edits leave it unchanged. Never replace it with the incremental edit request. Recompute affected `script_ref` offsets against the full revised script; ask when an edit is ambiguous.
2. Extract banks: characters, voices, locations, props, motions. Ask about anything missing that a shot will need
   (voice for a speaking character, wardrobe, driving clip for complex motion).
3. Split into scenes, then shots. Every scene/shot carries `script_ref` offsets into the source text.
4. Validate against the schema. Fix and re-run until it passes; do not hand back invalid JSON.
5. Run the continuity pass (section 5) and record results in `continuity_checks`.
6. Tooling (not the model) renders `prompt` per shot and derives `tasks`.

## 1. Hard rules for the model

- Output JSON only, matching the schema; no prose around it. Unknown values: ask, do not guess.
- Never invent plot, characters, dialogue or locations absent from the source text. Additions the user must
  approve go in a separate `proposals` message, not the document.
- Ids follow the naming grammar: entity `<PROJ>-<KIND>-<SLUG>` (<=32 chars), shot `<PROJ>_S###_SH##`.
  Scenes and shots are numbered consecutively, never reused after deletion.
- Every shot references only ids that exist in the banks. Every character in a shot is in its scene's cast.
- `appearance` and `wardrobe` text is written once in the bank and reused verbatim; shots never restate or alter it.
- `action` is observable and present tense. No thoughts, no "feels", no "suddenly".
- One primary action and one camera move per shot. Shot duration 1-30 s; prefer 3-8 s **[USER]**.

## 2. Camera rules **[USER]**

- Each scene opens with an establishing or master shot, then coverage medium -> close-up, then inserts/reactions.
- Default lens from `style_bible.lens_default`; portrait close-ups 85 mm, wides 24-35 mm. Change lens only with a reason.
- Handheld only for tense/documentary beats; otherwise static, slow dolly or slow pan.
- Respect the 180-degree rule within a scene; a deliberate break is noted in `camera_move.note`.
- Do not cut between two shots of the same character at the same size and angle.

## 3. Character persona rules **[USER]**

- Persona drives action wording and dialogue `delivery`, never appearance. Persona `rules` are hard constraints.
- Speaking characters must have a `voice` (VOX entity) before any DIALOGUE task is created.
- A wardrobe change needs a new wardrobe id and a scene mapping; no silent costume changes.

## 4. Lighting and location rules **[USER]**

- Lighting is set per scene (from the location's default unless overridden) and inherited by its shots; a shot
  may override only `quality` or `mood`, not time of day.
- `time_of_day` must match the scene `time`. Interiors with windows get a key direction consistent with
  `location.geography`.
- Keep the project palette; one dominant color temperature per scene.

## 5. Continuity pass (model + image-level where possible)

Record one `continuity_checks` entry per concern: identity, wardrobe, screen-direction, lighting, props,
location-geography, timeline. `fail` blocks task creation for the affected shots. After generation, the same
checks run on keyframes (identity against the character reference, ViMax-style) before video is paid for.

## 6. Prompt rendering (tooling, fixed order)

`[shot_size + angle], [camera_move + speed], [subject + action], [lens], [lighting], [style look]`, with entity
text injected from the bank. Positive phrasing; keep under ~200 tokens; image-to-video prompts describe motion
only. Platform specifics: Kling/Higgsfield use `<<<elementId>>>` placeholders; ComfyUI gets reference images.

## 7. Routing defaults (see convergent-production-strategy.md section 2)

- `complexity: complex-motion` + a MOT entity -> hf-genjutsu-motion or kling-motion-control (test to pick).
- Hero shots -> kling-v4-omni at 720p draft first; finalize at 1080p after approval.
- Cheap previews -> hf-seedance-2-5 480p draft or kling-v3-turbo. Local stills -> comfy-klein / comfy-zimage.
- Any `paid` task starts `needs-approval` with a credit estimate; nothing paid runs unapproved.

# Repeatable shot workflow

For multiple shots in one Run, use the saved **The Message - Automated Draft**
workflow and [its controls](AUTOMATED_DRAFT.md). The instructions below describe
the preserved individual-shot template.

Use **06 - Learning Production / The Message - Shot Template** as one stable
26-node generation graph plus two separate reference creation/inspection nodes.
Keep the reference factory muted during shot renders. The original shot tabs remain evidence copies. Reuse the topology;
new scenes change data, not sampler wiring or model choices.

## Variables and ownership

| Input | Owner | Canvas destination |
| --- | --- | --- |
| Action, characters, duration, dialogue, location | Production document | Prompt Builder; duration node |
| Framing preset, must_show, gaze_target, expression, screen_position, props | Binding shot_controls | Compiled prompt and synchronized builder state |
| Asset aliases and audio_mode | Bindings | Media Loader, RefMod Stack, prompt labels |
| Identity, background, wardrobe, voice files and hashes | Asset registry | Resolved selections; automatic Picture/Video/Audio numbering |
| Steps, model stack, resolution, frame alignment | Qualified render recipe | Existing native loaders, scheduler, ResolutionSelector, math node |
| Seed | Binding | RandomNoise |
| Shot and attempt IDs | Preparation command | Versioned SaveVideo prefix and receipt |

Framing presets are `establishing` (wide/35mm), `environment_reaction`
(medium-wide/35mm), `character_action` (medium/50mm), and `portrait_reaction`
(medium-close/85mm). They are prompt presets, not physical camera guarantees.
Keep camera/action text compatible with the preset. `must_show` lists what the
frame must contain. Refer to recurring props by ID so descriptions come from the
same production record. Asset instructions distinguish identity from visual background and audio ambience.

## One preparation command

```bash
.venv/bin/python studio/film.py prepare studio/projects/the-message \
  --production production.cafe-study-v1.json \
  --bindings bindings.reusable-v2.json \
  --recipe recipes/h3-ref-four-view-candidate-v1.json \
  --shot MSG_S003_SH03 --attempt tk006 \
  --out .codex/artifacts/the-message-production
```

Use a fresh attempt ID. Repeat `--shot` to select several; omit it for all shots
in that document. `check` accepts the same selectors without creating takes.
The example attempt is not reserved; preparation refuses existing directories.

Apply the resulting `panel-edits.json` through panel tools to the same template.
There are nine data writes and no added nodes or changed connections. Capture
the live resolved graph, verify it against the prepared shot, inspect modes,
perform fresh preflight, then queue once and bind the prompt ID. Preparation
does not render or approve anything. Manual Run clicks are outside this ledger.

Write `prompt_text` last and verify the live readback. The current panel serializer
can omit subject-name suffixes when only `builder_state` is written. Writing the
complete prompt preserves the text but reparses names into definition text; receipt
verification accepts that equivalent representation and rejects content changes.

Shot 03 tk005 completed with the v2 background reference: 56 frames at 24 fps,
608×352. Its room arrangement is recognizable, but an extra tabletop object and
unapproved likeness remain. The take is `review_pending`; audio has not been
auditioned. This is a reference/control test, not final movie acceptance.

## Reference creation

`reference-presets.json` records reusable creation settings and source-quality
checks for the installed Fantastic Create RefMod node. Fill profile variables
once per character/location/voice version. Store immutable files and register
their hash and role; select those aliases in shots. These are configuration
presets, not a newly installed UI or an automatic creation service.

The current creator's Full Reference mode encodes sources; its displayed 500
refinement steps apply to Compressed Reference instead. Inspect actual metadata,
stored encoder images and tokens, not just the thumbnail. A location bundle is
design context; keep one primary-angle picture for composition. Prefer consistent
source geometry to contradictory views. Wardrobe/props need useful full-detail
masters, independently of cropped identity pictures.

The template now contains Fantastic Create RefMod (28) and Inspect RefMod (29).
The saved `Cafe_Industrial_background_v2` uses all three original café pictures,
Full Reference, 768 short edge, background semantics and 3096 tokens. The original
reference is preserved. Use Inspect's `frames` mode for independently encoded
photo stacks and `video` mode for temporal video references: independently decoding
temporal slices can produce misleading texture artifacts. Validate the complete
clip before judging the identity asset. Create once, inspect, register the hash,
then reuse; do not recreate references for each shot.

## Node selection and limits

Live registration confirmed Fantastic Prompt Builder, Media Loader, RefMod Stack,
Reference Map and Create RefMod. Keep these with the tested native sampler chain.
Also found BFS Build Native Prompt / Describe References, BFS Shot Planner and
experimental H3 Plan Studio. They are not drop-in replacements: BFS planner is
source-video oriented; Plan Studio has its own chain-state and resume contracts.
Do not add them merely to make this graph look automated. Qualify an adapter
before replacing the existing RefMod/receipt path.

The expanded [installed-node audit](NODE_AUTOMATION_AUDIT.md) identifies Context
Loop as the strongest existing foundation for a one-Run production graph,
Comfy Dynamic for file-driven variables, and KJNodes for reference-cost checks.
Their registration is verified; integration into this template remains untested.

This is repeatable data-driven preparation and a live template. Applying edits
still uses the panel agent; there is no single-click shot selector or unattended
batch runner yet. The resumable run manifest now supports draft assembly after
technical checks without approving its takes. See `studio/FILM_AUTOMATION.md`.
Runtime validation and creative acceptance remain separate.

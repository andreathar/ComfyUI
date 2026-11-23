# Reference strategy for movie production

Use the model's intended reference interface. Our default for planned shots is:
**entity references → composed shot frame → animation; add an end frame when the ending matters.**
This is a production preparation rule, not a claim that one model or reference mode wins every shot.

## Choose the reference mode

| Need | Inputs to prepare | Current H3 route |
|---|---|---|
| Establish a character, location, wardrobe or prop; explore compositions | A small set of separate, clearly labelled images | Ref2VA, or an available reference-capable still model |
| Animate a planned shot with established people, objects and framing | One composed first frame | FL2VA first-frame input |
| Control both starting and ending pose, framing or object state | A consistent first frame and end frame | FL2VA first_frame + last_frame inputs |
| Transfer motion, performance or voice | A deliberate motion clip or clean audio reference | Only a model/mode explicitly supporting that modality |

Do not add an end frame automatically when the ending is open. It adds another
constraint and must agree with the start on identity, clothing, objects, lighting
and scene layout, except for intended changes. Endpoint conditioning does not
guarantee the exact motion path or perfect physical interaction between endpoints.

## Prepare a reusable bank, select a small shot package

- **Identity:** one clean representative face image; keep complementary three-quarter/profile views in the bank and select them when the shot needs those views. A video is not the default identity input merely because one exists.
- **Wardrobe/body:** a separate outfit/full-body reference when these details matter.
- **Location:** a clear establishing view; add a reverse view only when needed and consistent with the same space.
- **Props/food:** a clear view showing shape, scale, orientation and relevant state. Include a handling angle when needed.
- **Motion/voice:** separate assets, used only for their intended purpose.

Store individual source images, roles and provenance. Contact sheets help people
review the bank; do not feed a collage by default. Keep alternative angles in the
library rather than loading the whole library into every generation. A composed
shot frame resolves the selected identity, outfit, environment and props into one
spatial arrangement before motion generation.

## Adapt the package to the selected model

For each recipe, record accepted modalities, reference roles/order, supported
count and size/duration guidance, resize/crop behavior, and prompt syntax. Verify
what the encoder actually consumes. UI slots and saved filenames are not proof
of model support. Follow documented model guidance without inventing hard
rejections solely for quality-oriented recommendations.

- **H3 Ref2VA:** name the actual Picture/Video/Audio labels and state what each reference should retain. Published guidance permits up to 9 images, 3 videos and 3 audio inputs, with at most 12 files mixed; use the official duration guidance for clips. Prefer the smallest sufficient set.
- **H3 FL2VA:** use frame inputs for the shot composition and describe the transition/action. Separate identity RefMods are not interchangeable with a first frame.
- **H3 RefMods:** derived, model-specific cached conditioning. Keep their original media; do not treat the safetensors file as a portable reference or a trained identity LoRA. Extra encoded frames can add cost without useful information.
- **Other models:** use their own reference adapter and documented limits. Do not copy H3 labels, RefMods, limits or prompt templates into another model family by assumption.

## H3 RefMod efficiency rule

Use the lightest approved reference that passes the shot's identity check. For
Andre Athar, start with one clean face still; add one complementary view only
for a demonstrated angle failure. Keep the existing video RefMod as the
comparison baseline, not an automatic input. For a reusable compact RefMod,
encode only the selected stills at a practical face crop and size. Keep those
source files, crop and order, and record the derived file, recipe and actual
latent token count. Keep voice and motion separate; a silent likeness test needs
neither. Never substitute a generated face for an approved named identity.

Start at weight 1. Increasing weight above 1 adds copies; reducing a positive
strength softens the reference without shrinking it. `stack_pictures` changes
which stack pictures the text encoder sees, not the saved generator latents.
`max_total_tokens` rejects expensive RefMods; it does not compress them or cap
ordinary media. Reduce generator reference cost at preparation time: remove
redundant material, crop and size usefully, or shorten a clip to the distinct
motion it is meant to supply. Don't change these variables together when
testing which one helped.

The operator confirmed one still preserves Andre's likeness through the tested
small head turn. Use it as the starting rule for comparable shots, not as a
guarantee for larger turns or profiles. Eye movement and expression refinements
belong to final creative work, not this reference test.

If a later shot has a specific angle failure, compare the same still against
that still plus one approved complementary view. Keep recipe, seed, action,
framing and other references fixed. Record generator reference tokens,
prompt/vision tokens, sampling and wall time, and peak memory separately in
Brain. Expression and lip sync remain separate user-led tests, not gates for
the scaffold.

## Evidence and stopping rule

Our local tests support a composed first frame as the preferred starting point
for planned object interactions: continuity was cleaner than in the tested
separate-reference attempts. A single identity image also proved a useful
lower-cost candidate than the tested Andre video RefMod. These are practical
choices from limited tests, not universal quality rankings.

First-and-last-frame inputs are supported by the installed H3 route, but a
comparative first-and-last result has not been established here. Use them when
both endpoints are specified; do not describe them as a proven universal winner.

A strategy test answers whether the model receives the intended references and
whether that preparation method is useful. Once answered, record the rule and
move on. Do not turn it into repeated tuning of one shot's gesture, pixel height
or expression unless the user explicitly asks to finish that shot. Review enough
to catch unusable references and gross failures; creative acceptance stays human.
Brain should retain the reference mode, selected inputs, recipe, measured cost
and concise outcome, so reports compare preparation methods rather than chase
incidental defects in a test shot.

Sources: [official H3 model contract](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/README.md),
[reference audit](../../.codex/artifacts/refmod-audit-20261115/REPORT.md),
[identity strategy test](../../.codex/artifacts/refmod-ab-20261115/REPORT.md),
[first-frame strategy test](../../.codex/artifacts/kitchen-first-frame-20261116/REPORT.md).
Dated runtime measurements remain in `.codex`; this guide does not change live presets.

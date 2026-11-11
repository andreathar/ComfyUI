# Reference coverage and video identity trial

The new assets were supplied and authorized for testing by the user. Input-use
authorization is recorded separately from output likeness/creative approval.
Original files, original two-scene script and previous take receipts are retained.

## Identity trial

`bindings.video-ref-test-v1.json` selects `andre-identity-video-v1` instead of the
old eight-picture identity. `MSG_S002_SH01/tk005` retains tk004's prompt byte for
byte, seed, dimensions, sampling, old apartment, wardrobe and reviewed voice.
The live copy is **06 - Learning Production / The Message - Video Ref Test**.

The new visual bundle contains seven latent temporal positions at 86×48, 7224
reference tokens and two stored text-encoder frames (timestamps 0 and 0.5 s).
Both inspected frames are sharp, near-frontal portraits. This is video-derived
conditioning, not evidence of complete multi-angle coverage. The stack-picture
selector affects picture stacks only; it does not expand this video's two saved
encoder frames. No reference is upweighted or duplicated.

The separately uploaded audio bundle is preserved but not selected. Mixing it
with the existing voice would confound the identity comparison. Its candidate
record is `.codex/artifacts/andre-video-refmod-audit/new-audio-candidate.json`.
The user's original loader and stack selections are preserved in that audit
directory's `manual-selections.json`.

## Cafe coverage study

All three new pictures are 1376×768. Treat them as a coherent design reference,
not a measured floor plan: counter placement and viewpoint geometry need visual
continuity review. One primary location picture is selected for each shot.

| Asset alias | Original input | Primary use |
| --- | --- | --- |
| cafe-counter-wide-v1 | minimax_h3/Gemini_Generated_Image.jpeg | Left foreground espresso counter, window-table area to the right |
| cafe-window-table-v1 | minimax_h3/Gemini_Generated_Image_1_.jpeg | Round window table, brown chairs, plants and concrete walls |
| cafe-reverse-counter-v1 | minimax_h3/Gemini_Generated_Image_2_.jpeg | Reverse toward espresso counter, foreground table and right-side windows |

`production.cafe-study-v1.json` adds an explicitly optional Scene 03 study to a
copy of the existing script. `bindings.cafe-study-v1.json` maps its three shots:

1. `MSG_S003_SH01`: static wide empty cafe, counter-wide reference.
2. `MSG_S003_SH02`: Andre at the window table glances down at a folded note.
3. `MSG_S003_SH03`: seated reverse reaction toward the counter, no dialogue.

Each has a prepared `tk002` record under
`.codex/artifacts/the-message-production/`, including compiled prompts and panel
edits. The unsubmitted tk001 preparations were superseded to remove character
language from the empty establishing shot. Queue status lives in each take.json;
none has creative approval. The room-tone shots deliberately omit
speech conditioning; they are useful follow-up tests of closed-lip performance.
The folded note is prompt-generated, not an established reference prop.

Tk005 passed technical checks but still shows mouth movement and wider framing;
it does not establish improved likeness over tk004. Use its identity provisionally
for this study without promoting it as the final character reference. Preserve
the table/seat assignment, screen direction, window-light direction and wardrobe
across coverage. Do not automatically treat a successful render as an accepted
identity or as permission to assemble final movie footage.

## Three-angle cafe RefMod

The user created and enabled `refmod_German_Cofee` for the reverse shot.
Inspection found three stored encoder images and a 1×24×3×48×86 latent,
3096 reference tokens, source=stack, mode=encode and zero optimization steps.
All three stored images were inspected. The current up-to-4 selector includes
all three; increasing it adds no views. These generated angles are design
references, not proof of a geometrically consistent floor plan.

`bindings.cafe-refmod-study-v1.json` retains the reverse-angle picture as camera
guidance and adds the bundle as ambience `<Video 2>`, separate from Andre's
identity `<Video 1>`. Both remain at strength 1, once each, without voice.
Shot 03 now uses immutable `tk003`; unsubmitted tk002 was superseded. The
prompt explicitly retains the folded note. The shot compiler supports ambience
RefMods tied to the shot location; its recipe, receipt and preflight tests pass.

The three-shot study is rendered and reviewed in `CAFE_STUDY_RESULTS.md`.
Shot 03 tk003 passes technical checks but misses the counter-facing composition;
the ambience bundle is not promoted as a quality improvement.

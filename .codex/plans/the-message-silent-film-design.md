# The Message: silent production proof

Status: proposed implementation design, prepared from the live Automated Draft
canvas and installed extension source. This document does not change the canvas
or authorize a new render. It supersedes the two-shot test as the next target;
the completed test remains an untouched baseline.

## Outcome

Deliver an approximately 18-second, six-shot silent short with a beginning,
reaction and resolution, plus reusable production data and saved workflows.
The operator changes story/shot/asset data, runs preflight, and queues one
production. Shot-specific graph editing is not part of the normal process.

Proposed output: 832×480, 24 fps, six 73-frame shots, 438 frames / 18.25 seconds,
H.264 MP4 with zero audio streams. These are aligned widescreen dimensions, not
an assertion of exact 16:9. Keep the existing local model family, 20-step beta /
sa_solver recipe, shifts 12/3, SDPA and no torch.compile. Medium resolution is a
qualification target, not already proven on the 6 GB GPU. Do not silently fall
back to 608×352 or upscale a low-resolution run and call it native medium.

## Story: A quiet decision

Morning light enters an industrial café. A folded cream note rests on the round
table beside the window. Andre sits there, notices the note and lowers his gaze.
He pauses, looks toward the window and gives a small nod. The café remains calm.

No speech, music, captions, readable note text, walking, object pickup, complex
hand action or extra characters. One action per shot; locked cameras. The final
film tests controlled coverage, not expressive acting or camera choreography.

| Shot | Frames in final (end exclusive) | Shot/action | Main reference and acceptance |
| --- | --- | --- | --- |
| MSG_S001_SH01 | 0–73 | Empty café wide; hold the room | Counter-wide image; espresso counter left, window tables right; no Andre |
| MSG_S001_SH02 | 73–146 | Medium at the window table; Andre lowers his gaze to the note | Window-table image + identity + wardrobe + note; one seated person, note stays on table |
| MSG_S001_SH03 | 146–219 | Insert of the folded note; no face or hands | Note asset + a reviewed crop of the same table; same paper/fold and tabletop |
| MSG_S001_SH04 | 219–292 | Medium-close reaction; Andre raises his gaze toward the window | Reviewed tighter window-table view + identity + wardrobe; no speech, modest head angle |
| MSG_S001_SH05 | 292–365 | Reverse medium; Andre holds his gaze toward the light | Reverse-counter image + identity + wardrobe + background; counter/windows keep their agreed relation |
| MSG_S001_SH06 | 365–438 | Return wide; Andre gives one slight nod and holds | Counter-wide image + identity + wardrobe; same seating/light, readable closing beat |

All shots have a committed seed. The same seed does not guarantee bit-identical
GPU output; it is a provenance/control input. Actual durations come from the
aligned frame counts, not an assumed three seconds.

## Scope of “all features”

Exercise every feature needed by this silent production: script-to-shot data,
framing presets, reusable identity/background RefMods, selected location angle,
wardrobe/prop pictures, prompt construction, reference numbering, frame alignment,
sequential generation, checkpoints, resume, reassembly, review and discoverable
delivery. Review every existing canvas node and classify other useful installed
nodes as used, diagnostic, optional or deferred.

Voice, lip-sync, audio continuity, paid APIs, model swaps, training/compressed
RefMods, arbitrary-video editing, upscaling and speculative caches are outside
this proof. A giant graph exercising every installed node would not establish a
clean movie workflow. Optional features need their own small qualification before
being advertised as supported.

## Architecture and ownership

Two reusable saved surfaces: Reference Preparation and Silent Film Production.
The latter retains the installed Fantastic encoder, native sampler and Context
Loop. Comfy Dynamic supplies typed variables from one compiled immutable bundle.
Keep technical controls in a clearly named advanced group; expose production
file, run identity, range/resume and output location together.

Production JSON owns story, shots and entities. Bindings own named references,
framing and action constraints. The asset registry owns provenance, hashes and
review status. A recipe owns dimensions, timing rules, sampler and delivery
audio policy. The bundle owns the complete resolved run configuration. A run
receipt owns exact prompt IDs, clip revisions, checksums and review outcomes.
No property has competing editable defaults in the normal execution route.

Automatic technical success means review_pending. The user's likeness and
creative selection remain separate. Existing `approved: true` asset entries
sometimes mean authorized for testing only; preserve that distinction instead
of treating them as final visual approval.

## Reference policy

Freeze one character identity and one wardrobe for the proof. Andre's current
video identity is near-frontal; do not claim it covers strong profiles. The
182×107 wardrobe crop needs a larger, clean source or a clearly provisional
replacement. No sharpen/upscale step may be presented as recovered detail.

The three café pictures are generated design references, not a measured 3D room.
Compare landmarks and seating before treating them as one location. If a view
contradicts the others, derive a consistent replacement from a chosen master,
version it, and review it before any full batch. Choose one primary angle per
shot; background RefMod supplies appearance, not an exact camera/layout lock.

The note needs a real image asset and a named prop binding. Identity, wardrobe,
environment and prop instructions must remain separate. Keep a consistent seat,
table, window side, lighting direction, paper/fold and screen axis. RefMods are
selected once each at strength 1 initially; never duplicate references to force
strength or silently drop references to fit memory.

## Delivery and proof

`output/The_Message/silent-proof-v001/` contains the user-facing film, shot copies,
contact sheets and an index mapping friendly names to original clip revisions.
Context Loop's original media/checkpoints remain intact in its own run directory.
The delivery index shows technical status and review status separately.

Completion requires: all 42 current nodes audited; six shots with correct assets
and action; native medium-resolution decode verified; no final audio stream;
correct order/count/duration; one continuous automatic run without per-shot edits;
bounded stop/resume proof; reassembly without sampling; unchanged source hashes;
and clear output links in the panel. A failing shot stays visibly failed until
repaired or explicitly excluded; the film is not automatically promoted to final.

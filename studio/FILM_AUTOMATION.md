# Local film preparation and take tracking

The separate [Automated Draft workflow](projects/the-message/AUTOMATED_DRAFT.md)
uses `h3_loop.py` to export compiled shots to installed Context Loop and Comfy
Dynamic nodes. Its two-shot generation/checkpoint/assembly test passed. The
single-take tracking protocol below remains a separate execution path.

`film.py` compiles the existing canonical production document into Fantastic H3
shot proposals. It never queues a render or invokes a text provider. The panel
agent applies the prepared edits to the visible working-copy workflow and owns
the queue operation. Existing `production_generate.py` remains the optional
script breakdown tool; its provider selection is explicit and may incur cost.
The current assistant can also produce the same validated document directly.

The included project is `studio/projects/the-message`. Its short script was
reconstructed from the two existing scene prompts, not recovered from an original
screenplay. The original live prompt/editor configurations are in `baseline.json`.
New compiler output is an editable proposal, not byte-identical baseline prompts.
Preparation defaults to the `The_Message/shots/` output namespace. For another
film, pass `--output-namespace Second_Film` and its own `--out` take-record folder.
The selected namespace is saved in each new take and checked during preflight
and reconciliation. Previously prepared takes retain their original paths.

## Prepare

For reusable framing variables, named script/binding/recipe selection and the
stable live template, see `projects/the-message/REUSABLE_WORKFLOW.md`.

From the ComfyUI checkout:

```bash
.venv/bin/python studio/film.py check studio/projects/the-message
.venv/bin/python studio/film.py prepare studio/projects/the-message \
  --out .codex/artifacts/the-message-production --attempt tk004
```

Use a new attempt ID for revisions. Existing attempt directories are never
overwritten. Preparation writes `compiled.json`, `prompt.txt`, editor/refmod/media
state, `panel-edits.json`, and `take.json`. No model loads. Models are pinned by
SHA-256; routine checks compare size/mtime and asset hashes. A full model rehash
is available through `h3_preflight.check(..., rehash=True)`. File stamps are not
a substitute for byte verification after suspected tampering.
Model resolution supports this checkout's default local model folders and its
default `extra_model_paths.yaml`, including preferred external copies. Its config
hash is pinned too. Verify the serving process before dispatch: `--base-directory`,
`--models-directory`, extra `--extra-model-paths-config` flags, or custom nodes that
register competing model roots require an explicit resolver adapter. They are
not certified by this file check. Resolved paths are recorded in runtime evidence.

`production.json` owns source text, characters, locations, scene wardrobe, shots
and dialogue. `bindings.json` selects versioned assets, audio mode, seed, blocking
and quality warnings. `assets.json` resolves those aliases to existing files,
hashes, roles, owners, preprocessing and approval evidence. Never update a hash
merely to suppress a mismatch: inspect and approve the changed asset first.
The original media stays in place. `existing-media.json` records protected bytes
and inherited review states; Scene 02 is still pending.

`h3-ref-diagnostic-v1` remains the baseline. The optional
`h3-ref-four-view-candidate-v1` changes only text-encoder picture presentation to
`up to N`, N=4. For the eight-picture identity stack this selects indices 0, 2,
5 and 7; all eight diffusion reference latents remain intact. This is a candidate
requiring runtime memory and likeness review, not an established quality gain.
The model stack, shifts, sampler and 0.2 MP output remain unchanged. Different duration
and visible dialogue produce qualification warnings. Arbitrary reference video,
editing masks, motion control, recorded-track muxing, alternate model families
and continuous-shot chaining are not supported by this compiler. They require
separate adapters and qualification; references are never silently dropped.

## Apply and validate the visible canvas

Reuse **06 - Learning Production / The Message - Shot Template** for the
current sequence. It retains the original 26 nodes and five groups; earlier
Auto Shot and Scene tabs remain evidence copies. Node IDs in `panel-edits.json`
and `h3_graph.py` target this shared topology. Read the active graph first, pin
it, apply each edit through `panel_set_widget`, then inspect modes and save.
Editing node IDs or wiring requires updating the graph contract deliberately.

Use `panel_strip_workflow` to obtain the current executable graph. Pass its
`structuredContent.graph` to `h3_graph.verify(graph, compiled, output_prefix)`.
This checks every execution node and link, including seed, model filenames,
reference order, committed prompt, editor state, resolution and duration drivers.
Ignore canvas titles/positions; do not ignore execution differences. Check the
actual graph with `list_packs(action="check_runtime")` before loading/running.

Before a render, collect fresh connected-server health, registered node names,
queue state and conflicting-export status. Record a Unix `observed_at` timestamp
and explicit fields `running`, `pending`, `free_ram_bytes`, `free_vram_bytes`,
`conflicting_export`. Unknown export state blocks submission. Free memory is
recorded, but this does not certify peak fit or reserve the GPU. Recheck queue
immediately before `panel_run`; the panel has its own busy-queue fence.

```bash
.venv/bin/python studio/film.py preflight TAKE_DIR \
  --graph LIVE_API_RECEIPT.json --resources RESOURCE_SNAPSHOT.json \
  --models studio/projects/the-message/models.json \
  --nodes REGISTERED_NODE_NAMES.json --workspace "$PWD"
.venv/bin/python studio/film.py submitting TAKE_DIR
```

Then queue **exactly once with `panel_run`**, and immediately persist the returned
ID with `film.py bind TAKE_DIR PROMPT_ID`. A preflight expires after two minutes.
The CLI does not enforce manual frontend Run clicks: use this protocol for tracked
production takes. It cannot guarantee exactly-once network delivery; the
`submitting` state deliberately refuses retries after an uncertain result.

On completion, obtain that exact prompt's history via the connected tools, save
the returned history envelope, and run:

```bash
.venv/bin/python studio/film.py reconcile TAKE_DIR HISTORY.json \
  --output-root /actual/connected/output/directory
```

The output path comes from history and the configured output root, never a guess
at the newest file. Temporary previews, changed execution settings, decode errors,
wrong frame count/dimensions/fps and missing audio cannot pass. This recipe always
decodes an audio stream, including room tone. `silent` is a prompt instruction,
not proof that the soundtrack contains zero samples. Success becomes
`review_pending`. Reconciliation of the same output preserves an existing review.
If the response was lost before binding an ID, inspect queue/history and verify the
unique take prefix and full recipe before binding it. Never automatically reroll.

## Review and assemble

For an explicitly requested end-to-end draft validation, `plan-run --take ...`
records ordered immutable take recipes and a `--draft-output`. `run-status RUN`
returns render, wait, reconcile_submission, blocked, assemble_draft, or
draft_complete. A completed draft is rechecked against its source hashes,
receipt, decoded media and expected timing. Repeating `assemble-run` then returns
that same file without rewriting it. An incomplete output/receipt pair blocks
automatic publication rather than overwriting either artifact. The panel
agent executes the render action on the live template and resumes on completion;
this CLI is not a standalone submission daemon. `assemble-run RUN` joins only
technically passed candidates into a clearly labeled draft receipt without
changing their review state. `assemble EDIT --draft` exposes the same explicit
draft mode. Default assembly still requires approved takes.

Human acceptance checks likeness, wardrobe, room geometry, action, mouth behavior,
dialogue and sound. Technical validation does not make that decision.

```bash
.venv/bin/python studio/film.py review TAKE_DIR --decision approve \
  --reviewer 'human reviewer' --note 'Describe the actual visual and listening review'
```

An edit is a JSON list of `{ "take": "TAKE_DIR", "in_frame": 0,
"out_frame": 56 }` entries. Out frame is exclusive. `assemble EDIT.json --out CUT.mp4`
checks approved hashes, trims exact frames/audio ranges, concatenates with CPU
FFmpeg and verifies decoded frame count. It never submits ComfyUI work or changes
source clips. Existing output and receipt names are protected. The assembled cut
still needs human review. FFmpeg/ffprobe must be available.

## Qualification limits

Automated tests cover compilation, reference integrity, expiry/retry controls,
history matching, real synthetic-video decode and reviewed-only assembly.
They do not qualify new generated performances or prove GPU memory peaks.
Runtime qualification requires the actual generated outputs, exact receipts,
visual inspection and listening review. The current sequence is tracked in
`.codex/artifacts/the-message-production/validation-20261110/run.json`; consult
`run-status` and its take records for observed progress. The separate Context
Loop prototype has a completed two-shot draft and CPU manifest/resume-selection
check; it does not use these single-take ledger transitions. Arbitrary unattended
batch submission, automatic creative selection, Plan Studio migration,
cached-conditioning reuse and silent Project Suite imports remain unqualified.

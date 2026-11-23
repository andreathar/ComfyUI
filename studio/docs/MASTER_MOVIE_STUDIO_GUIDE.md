# The Message · Master Movie Studio

Unified production canvas after the F1–F5 corrections from the read-only review.

Workflow:

`user/default/workflows/06 - Learning Production/The Message - Master Movie Studio.json`

Guide companion review: [`MASTER_MOVIE_STUDIO_REVIEW.md`](MASTER_MOVIE_STUDIO_REVIEW.md)

## Start a storyboard draft

After loading the updated frontend, use **Open storyboard…** on the Prompt
Builder. Enter a title and story, then **Analyze story**. This queues local Qwen
analysis separately from image/video work. Close and reopen the workspace to
resume its status; **Cancel analysis** targets only that job. A lost response
does not automatically repeat model work. Review **Job details** if recovery is
needed.

After completion choose **Review analyzed plan**, then **Create project**. The
first version supports one silent scene of up to four shots and asks questions
for unsupported stories. Newer text stays intact when an earlier analysis
finishes. **Manual paragraph draft** remains available: provide a place and use
**Review shot plan** to turn paragraphs into shots without a model request.

The workspace preserves the original story in the project scaffold. Edit shot
actions, seconds, camera choices and character appearance, then **Save shot
and descriptions**. Changing a character's appearance can require selecting
and reviewing its references again. **Open project**
reopens a saved project after refresh; **Reopen saved plan** recovers the latest
saved version after an explicit warning about discarding unsaved edits. A stale
save never overwrites a newer revision.

**Prepare references** opens the project's reference bank. Choose an identity,
outfit, place or prop, search the native media library, then preview an existing
still. Confirm permission and choose **Use this image** to bind it to that role.
Review it separately with **Keep reference**, **Wrong face**, **Wrong outfit**,
**Characters mixed up** or **Reject**. The same source can serve different
characters without sharing their outfits or approvals. Source changes and
changed descriptions require a new binding or review; old decisions remain in
revision history. This step preserves original files and generates no images.

For each shot, save the start/end descriptions, choose **Prepare start frame**
and select reviewed references. **Review start prompt** shows the scene,
character words, action and ordered references, followed by the full Klein
prompt. Check that character descriptions agree with their identity references;
the reminder does not detect every conflict or guarantee likeness. Generate a
candidate, inspect it, then keep or reject it. **Use on timeline** selects a
kept candidate. Preparing the end frame uses a kept start as a reference.

**Download shot list** exports saved frame timing and explicit missing-frame
status. Candidate images are local drafts; reference generation, complete
pair approval and video submission are separate steps. The workspace does not
replace the selected Master shot package.

## Integration check before extending a workflow

Use the selected project and shot as the shared source for prompt-builder
state, media and RefMod bindings, seed, timing and output namespace. Verify the
actual inputs and links consumed by the Builder, Reference Map, encoder, sampler
and Project Hub; matching labels alone are not enough. Keep model-specific prompt
and reference formats at their model boundary. A still draft does not by itself
establish a Master Studio handoff.

Run `.venv/bin/python -m pytest studio/tests/test_e2e_pipeline.py studio/tests/test_master_take.py -q`
when changing these connections. These checks cover the existing H3 graph and
Master take contracts; a new project's handoff still needs its own two-project
isolation test and a live, non-rendering canvas check. The project-aware resolver
work is described in [Production bootstrap](../plans/production-bootstrap.md).

## Local story-analysis prototype

**Storyboard — Analyze story** is a separate queued output node. Supply a story,
title and a project code of 2–8 uppercase letters or digits. Run it separately
from image/video branches, with an optional enabled Brain monitor. The current
route drafts one silent scene of up to four shots; unsupported stories can return
questions. It preserves the source and saves a proposal under
`user/studio_storyboard/jobs/<prompt_id>/`. It does not create or approve frames.

The beginner workspace uses this same native node and an enabled Brain monitor.
Review the proposal before project creation. Technical success does not establish
creative acceptance.

## Save an edit for the selected shot

The Master Prompt Builder has an explicit library binding to Shot Tag. Opening
it loads that shot's saved prompt. **Save to shot library** updates the source
read by the resolver; the node widgets remain previews. Saving refuses a changed
shot selection or a newer library edit. Reopen the selected shot to resolve that
conflict. Drafts are separate per shot; older unbound node drafts are preserved.

**+ Camera** inserts text at the focused text field. Check the generated prompt
for conflicting camera instructions before saving. Text reaching the encoder
does not establish that the resulting video follows it.

A draft owning media/RefMods cannot publish those through a prompt save. Its
recovery action **Use shot presets; keep draft text** discards only the draft's
reference overrides. Existing preset libraries and draft text stay intact.

## Controlled take records

Run the storage audit from the checkout root to inspect Storyboard projects,
Master takes, Suite manifests, native asset paths and Brain coverage.

```bash
.venv/bin/python studio/storage_audit.py report
```

The report uses each store's existing records. It verifies archived take
history against the frozen prompt and compares recorded media hashes with
files on disk. It includes alternate project layouts, reference binding
status and a dry-run retention inventory. Asset flag discrepancies are
findings to investigate. The command applies no cleanup.

To rehearse recovery, select a current Storyboard project with a bound
reference and an approved take, then pass a new destination outside the
production stores.

```bash
rehearsal=$(mktemp -d .codex/artifacts/studio-rehearsal.XXXXXX)
.venv/bin/python studio/storage_audit.py rehearse \
  --project creator-qualification-20261121 \
  --take user/master_studio/takes/MSG_S001_SH05/tk001 \
  --destination "$rehearsal/restore-test"
```

The destination contains the backup, restored files and a JSON record of the
checks. The rehearsal maps absolute paths in existing take receipts onto the
restored root without modifying the receipts. The asset database snapshot
includes all metadata and the sample includes the selected media. The
rehearsal checks both SQLite stores, rebuilds the Brain index and simulates
an omitted output on the restored copy.

`studio/master_take.py` prepares and reconciles a single Master take. It does
not intercept the ordinary Run button or submit jobs automatically. Export the
visible canvas and its compiled API prompt, then use:

```bash
.venv/bin/python studio/master_take.py prepare --shot MSG_S001_SH05 --prompt prompt.json --workflow workflow.json
```

The returned `user/master_studio/takes/<shot>/<take>` folder holds frozen prompt,
package, workflow and prompt-review records. Preparation checks that the encoder
and both output paths depend on the selected prompt and references. New review
videos use `The_Message/shots/<shot>/<take>/video`; Suite's paired files retain
their own names.

Programmatic `prepare()` also accepts package fields `project` and
`output_project` for separate test projects; both must be safe path identifiers.
Existing packages retain the `MSG` / `The_Message` defaults. The CLI shot
resolver still lists The Message packages. Preparation follows actual saved
video/latent/image dependencies; a filename link cannot satisfy that check.
Before allocating a take, each saved media path must also consume a Master
`SamplerCustomAdvanced` whose `noise` comes from `RandomNoise` output 0.
Its `noise_seed` must use frozen resolver output 5, directly or through
`FantasticSeeds` output 0. Literal seeds (even equal values), unrelated sources
and unused correctly wired noise nodes cannot establish this dependency.

After checking the live queue/resources/model files, mark the take `submitting`,
submit its `prompt.json` through the connected visible browser, and bind the
returned ID with `bind --take <folder> --prompt-id <id>`. An uncertain submission
must be reconciled with history before retrying; the tool refuses rebinding.

`collect --take <folder> --suite-project <project>` requires successful history
with the exact frozen prompt, uniquely matches the Suite sidecar, hashes saved
outputs and links the Brain run. `review --take <folder> --verdicts <json> --note
<text>` records pass/fail/uncertain judgments. Use `--approve` only for an explicit
human selection. This review does not advance the Suite chain or automatically
publish a reference asset; those remain separate human choices.

Review rechecks both the frozen prompt and video hashes. Preparation follows the
actual media inputs, not filename dependencies. Start with a browser-compiled
API graph: arbitrary programmatic JSON integers can lose precision when later
serialized by the browser. Large-integer preflight validation is not implemented.

## Reference and camera feature tests

Use [Reference strategy](REFERENCE_STRATEGY.md) to choose separate references,
a composed first frame, or first-and-last frames for the selected model.
Strategy tests establish reusable preparation rules; do not keep tuning an
individual shot after that question is answered.

Without a script, write observable targets rather than judging dramatic meaning:
which character stands where, starting/ending gaze and expression, framing, and
camera movement. Give each reference one explicit role; identity-only reuse must
exclude unwanted source clothing, background and action. Check the H3 guide's
reference labels against the encoder's actual map, not just asset filenames.

Inspect generated reference images before using them. Preserve rejected images,
metadata, seed and the exact correction. A prompt asking for an empty location
can conflict with wording about where people should stand. A successful single
correction is evidence for that case, not a universal prompting rule.

Verify the loaded canvas and compiled inputs before queueing; opening a workflow
tab alone can leave the prior graph active. After rendering, inspect the media:
tighter framing alone does not prove dolly motion, and a smile already present
at the first frame does not prove a neutral-to-smile transition.

The farm example reuses the Master topology with a separately frozen package;
it does not add generic project selection to the canonical shot resolver.
See [the verified farm test](../../.codex/FARM_REFERENCE_LAB.md) for assets,
reference roles, measurements and the Brain advisor limitation.

## Hardware defaults (this PC)

| Knob | Value | Why |
| --- | --- | --- |
| Resolution | 832×480 | Proven 6 GB path |
| Length | 3.0 s request | Compiler shows **raw vs delivered** frames |
| Overlap | 22 frames when continuing | H3 Context head pin + Trim |
| Sampler | `sa_solver` / `beta` / 20 steps | Silent-proof recipe |
| Shifts | video 12 / audio 3 | Native H3 flow |
| Attention | `.codex/launch.sh` (`--use-ck-attention`) | Locked launch |
| Audio decode | **muted** | Silent path; AV unmute needs trim wiring (F7) |

## How to use

1. Set **Var · Project Name** (feeds Hub directly — panel follows this link).
2. Set **Var · Shot Tag** (`MSG_S001_SH0N`). The **Shot Package Resolver** loads matching prompt, media, RefMod stack, seed, and transition.
3. Read the **Live Production Plan Summary**: project, shot, transition mode, raw/delivered frames.
4. Read the live `/queue` immediately before submission and wait for a coordinated idle window; never interrupt or duplicate active work. Queue. For a **cut**, context stays off even if an approved clip exists. For **continue**, approve the predecessor first, then queue with that shot’s transition=`continue`.
5. Open project… on Hub → review → Approve before the next continue take.
6. Monitor Brain records digests for steps/duration/prompt/LoRA under `user/workflow_monitor` (not `user/default/workflow_monitor`).

## Transition policy

- Package defaults in `studio/projects/the-message/silent-proof-v001/shot_transitions.json` are all **`cut`**.
- `continue` arms H3 Context only when Hub `chain_active` is true and adds 22 overlap frames before H3 frame-grid rounding. A 3-second request at 24 FPS samples 107 frames, trims 22, and delivers 85 (about 3.542 seconds). Check the raw/delivered summary for the actual duration.
- Project Save uses integer FPS. The generated controls round FPS before computing frame counts and display that same playback rate.
- Do not rely on “any approved predecessor continues automatically.”

## Out of scope until later

- F6 full CPU preflight gate
- F7 AV unmute path
- F8 finishing muted labs
- Multi-shot Act assembly / creative qualification

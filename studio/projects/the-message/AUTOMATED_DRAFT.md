# One workflow, multiple shots

Use **06 - Learning Production / The Message - Automated Draft** for the
file-driven sequence. **The Message - Shot Template** remains saved separately
for individual shot experiments. Save workflow edits with Ctrl+S before closing;
the production JSON, source references, checkpoints and rendered files are
separate assets and are not embedded in the workflow.

## What changes between productions

Edit the production document for story, shots and dialogue; bindings for framing,
action and asset selections; the asset registry for versioned reference files.
Compile a new bundle rather than hand-editing its fingerprint or changing nodes
for each shot. The same compiler numbers Picture/Video/Audio references and
builds the model's structured prompt from the actual selected assets.

Example from the checkout root; use an unused run name and output folder:

```bash
.venv/bin/python studio/h3_loop.py studio/projects/the-message \
  --production production.cafe-study-v1.json \
  --bindings bindings.reusable-v2.json \
  --recipe recipes/h3-ref-four-view-candidate-v1.json \
  --shot MSG_S003_SH01 --shot MSG_S003_SH02 \
  --run-name The_Message_AutoDraft_v002 \
  --out .codex/artifacts/the-message-production/auto-draft-v002/production-bundle.json
```

Export refuses to overwrite an existing bundle. It does not queue generation.
Use the same qualified model recipe and 608×352 plan dimensions; changing model,
resolution or audio policy requires a separate qualification, not just a new
JSON file. Before generation, verify selected files/hashes, model availability,
free RAM/VRAM, the idle queue and absence of a conflicting GPU export.

## Canvas controls

| Node | Purpose | Normal setting |
| --- | --- | --- |
| 30 · Production variables | Absolute path to the new compiled bundle | Change once per run |
| 31 · Validate bundle | Check content fingerprint; emit plan and run name | Leave script unchanged |
| 32 · Generation profile | Shot/audio continuity policy | Independent scenes; fresh audio |
| 33 · Chain plan | Shared dimensions and encode policy | Qualified 608×352 recipe |
| 34 · Start/resume | First shot and optional scene range | Start 1; blank range; verify history on |
| 35–36 · Current shot | Prompt, seed, frames, steps and matching reference selections | Linked automatically |
| 38–39 · Save/advance | Persist each clip/checkpoint and advance recursively | Active |
| 40 · Assemble | Assemble and copy the final draft | Fresh output subfolder; checkpoint deletion off |
| 41–43 · Recovery diagnostic | Load saved manifest and preview resume selection | Muted during generation |

Set node 40's output subfolder to match the new version, such as
`The_Message/drafts/auto-v002`, then save and Run once. No per-shot widget edits
are needed. The old Prompt Builder/output branch and reference factory remain
muted. The loop feeds the compiled prompt directly into Fantastic Text Encode.

Files live under `output/h3_chains/<run_name>/`: revisioned clips and separate
audio under `generation/`, resume data under `.h3/checkpoints/`, and the canonical
assembly under `exports/`. Node 40 also copies `draft.mp4` to its chosen output
subfolder. Preserve all of these when retaining a resumable run.

## Resume and reassembly

After interruption, inspect the exact prompt history and saved checkpoints first.
Keep the same bundle/run name. Set node 34 to the first incomplete scene, with
history verification on; do not rerun completed scenes blindly. Revisions retain
earlier clip files, but a rerender can change the selected checkpoint pointers.

For the CPU diagnostic, activate 41–43 and run **only to node 43**. It reports
the selected scene and verifies the saved manifest. Restore start 1 and mute
41–43 afterward. A full Run is generation, not this diagnostic.

For reassembly without sampling, the installed Manifest Load output can feed
Assemble in place of Loop End. Use an unused assembly filename/subfolder and
run only that output branch; this alternate wiring has not been executed in
this qualification. Keep the normal generation wiring saved separately.

## What passed, and what remains

The first run generated two independent 56-frame shots and assembled a
112-frame, 24 fps draft in one recursive execution. Reference selections changed
with the shot index; stored prompt sidecars matched the compiled prompts. Both
clips and the draft decoded successfully. The saved manifest verified 2/2 clips;
the CPU resume selector identified scene 2 without changing the ten checked
checkpoint/media files.

This is a tested two-shot draft pipeline, not full autonomous creative acceptance.
The observed shots were an empty café and Andre seated by its window. Exact
likeness, prop continuity, facial performance and soundtrack need review. Longer
runs, actual process-crash recovery, continuous shots and dialogue/voice continuity
are not qualified by this test. Raw prose still needs a reviewed production/shot
document; no automatic text-provider call or paid video generation is included.

Machine-specific receipts and timings are in
`.codex/artifacts/the-message-production/auto-draft-v001/`.

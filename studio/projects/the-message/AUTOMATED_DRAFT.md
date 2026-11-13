# One workflow, multiple shots

Use **06 - Learning Production / The Message - Silent Film Production** for the
consolidated silent 832×480 sequence on the 6 GB RTX 3060 Laptop.
**The Message - Reference Preparation** holds one-time asset cropping, RefMod
creation (`refinement_steps=0`, encode-only) and RefMod inspection.
**The Message - Automated Draft** and **The Message - Shot Template** remain
saved separately as historical baselines. Save workflow edits with Ctrl+S
before closing.

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

## Executed six-shot silent production (`The_Message_Silent_Proof_v003`)

Use **06 - Learning Production / The Message - Silent Film Production** with
`.codex/launch.sh` (`--reserve-vram 1.0 --disable-pinned-memory --use-ck-attention --enable-assets --preview-method latent2rgb`):

1. **Prepare**: `.venv/bin/python studio/h3_loop_run.py prepare --root ATTEMPT_DIR --bundle BUNDLE.json --graph LIVE_GRAPH.json --models MODEL_PINS.json --workspace "$PWD"`
2. **Preflight**: `.venv/bin/python studio/h3_preflight.py snapshot --out RESOURCES.json` (checks idle queue, free RAM, usable ComfyUI VRAM, zero foreign GPU processes such as `llama-server`, and GPU `< 88 °C`), or run **only Node `41`** on CPU (`0.01s`).
3. **Run**: Submit once from the connected ComfyUI browser tab so passive `WorkflowMonitorBrain` (`Node 44`) records complete phase timings and 2-second resource samples into `/workflow_monitor/runs`, then bind `PROMPT_ID`.
4. **Reconcile & Publish**: `.venv/bin/python studio/h3_loop_run.py reconcile RUN_DIR HISTORY.json --output-root output` followed by `publish RUN_DIR DELIVERY_DIR --output-root output`.
5. **Resume / Reassemble**: Keep `verify_resume_history=true` on `Node 34`; unmute `Nodes 47–49` and run only to `49` for CPU manifest verification, or wire `ManifestLoad (47) -> Assemble (40)` for sampling-free reassembly (`verified in prompt e17581f4`).

Saved tabs safe to close after `Ctrl+S`: `The Message - Silent Film Production.json`, `The Message - Reference Preparation.json`, `The Message - Stress Pilot 73f - Monitored.json`, and `The Message - Shot 04 Reaction 73f - Monitored.json` (preserve any unsaved `*Monitor draft` tab if still editing).

Delivery folder: `/mnt/data/Projects_SSD/ComfyUI/output/The_Message/deliveries/silent-proof-v003/` (`The_Message_Silent_Proof_v003.mp4`, `shots/01_cafe_wide.mp4` … `06_closing_wide.mp4`, `contact-sheet-6shots.png`, `index.json`, `README.md`). Status remains `review_pending`: Shot 03 transitions mid-shot from the tabletop note insert to a wide empty cafe view and awaits human creative decision before any single-shot replacement.

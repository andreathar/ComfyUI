# Farm reference lab — verified 2026-11-15

The user requested a reference/prompt feature test without a story: retain
Andre, create a fictional adult blonde woman with blue eyes and a warm smile,
move to a farm, and test two characters with camera movement. Story coherence
and dramatic motivation were outside this experiment.

## Package and evidence locations

| Item | Location relative to the checkout |
| --- | --- |
| Experiment source | `studio/projects/farm-reference-lab/v001/` |
| Initial still prompts | `studio/shots/farm-reference-lab-refs.json` |
| Corrected location prompt | `studio/shots/farm-reference-lab-clean-plate.json` |
| Clara reference | `input/refs/farm-reference-lab/clara-v001.png` |
| Farm reference | `input/refs/farm-reference-lab/farm-v002.png` |
| Workflow | `user/default/workflows/Farm Reference Lab - two characters.json` |
| Frozen take | `user/master_studio/takes/FARM_S001_SH01/tk002/` |
| Review video | `output/Farm_Reference_Lab/shots/FARM_S001_SH01/tk002/video_00001_.mp4` |
| Suite video, latent and sidecar | `output/h3_projects/Farm_Reference_Lab/clips/clip_001_take1.*` |

Generated media/user state are local evidence, not all tracked Git assets;
preserve them separately. `tk001` was never submitted: its farm reference had
two unwanted men. Removing the positive prompt's human-placement cue with the
same seed/model/settings produced the empty plate used by `tk002`. Both outputs,
prompts and hashes remain preserved. This is one correction, not a universal rule.

Existing Z-Image weights generated the references through `studio/shot.py`.
No download or SD15 baseline replacement occurred. Copies retained PNG metadata
and sidecars without re-encoding.

## Reference binding and observed result

The encoder received Picture 1 = farm environment, Picture 2 = Clara identity,
hairstyle and clothing, Video 1 = Andre identity-only RefMod. The prompt excluded
Andre's source background/action/clothing, selected navy clothing and used no
speaker IDs for the silent test. The farm was not an exact first-frame constraint.
Confirm labels anew when reference order changes.

Inspection of 12 sampled frames, first and final frames showed two distinct
characters in the requested positions/clothing, recognizable farm architecture,
mutual head/gaze turns, Clara's smile broadening and framing tightening with both
faces retained. Full decode and browser playback to the end passed. Exact Andre
likeness, blue-eye fidelity at this scale, true dolly versus zoom and fine temporal
quality remain separate judgments. Clara already smiles slightly at the start;
this does not establish a neutral-to-smile transition. The agent recorded no
creative approval.

| Measurement | Observed value, not a performance guarantee |
| --- | --- |
| Output | 832×480, 73 frames, 24 fps, 3.041667 seconds, silent |
| Recipe | H3 ref2va, 20 steps, sa_solver/beta, shifts 12/3, seed 151103, cut |
| Wall / sampling | 1,199.50 s / 1,119.79 s |
| Conditioning / decoding | 41.30 s / 27.69 s |
| Brain | 590 resource samples; complete browser events; recorded intervals closed |
| Reference tokens | Farm 390 + Clara 391 + Andre RefMod 7,224 = 8,005 |
| Conditioning tokens | 2,548 |
| GPU peak | 90°C; separate NVIDIA snapshot reported thermal slowdown |

Andre's RefMod dominated reference tokens. Reducing it is a proposed
speed/likeness experiment, not a proven improvement. These measurements do not
establish cooling effectiveness or model superiority.

## Take and browser safeguards

`master_take.py` accepts safe explicit `project` / `output_project` fields,
retaining `MSG` / `The_Message` defaults. It validates actual saved-media ancestry,
reconciles exact prompt history and Suite files, hashes outputs, checks decode
and links Brain. Review rechecks frozen inputs and video hash. The canonical
CLI shot resolver still enumerates The Message; this farm package reuses existing
nodes without implementing generic project selection.

Opening the farm tab initially left the café graph active. Explicit graph loading
and comparison of all 44 compiled node types/inputs caught this before submission;
only an explanatory display title differed. A tab name is not proof of the canvas.
An oversized CLI argument also failed before browser launch. That confirmed local
failure differs from an uncertain HTTP submission: reconcile queue/history before
retrying any uncertain submission.

27 focused tests and four subtests passed. Two CodeRabbit rounds completed;
verified filename-ancestry and review-provenance findings were fixed. Raw
programmatic graphs with nonrepresentable large JSON integers remain a browser
serialization limitation. Review completion is not a clean-review guarantee.

## Brain: delivery passed, production advice failed

Run: `c6e2ceed-708a-4a69-b439-97f1d0859f22`.
Video SHA-256: `74c8c9e75c433f162e275865797f6d3dfae913c1ca7f513df986f0d78095806a`.

Dedicated CPU llama.cpp `brain-qwen35-9b` completed automatic report
`b3418723-2780-4f4e-a8fc-cd8b62716cdc` and review-informed report
`eb048120-8160-45b9-a123-6552e1879f2b` under
`user/workflow_monitor/analysis/reports/`. The take records their paths/hashes.
The second model view contained all six output-bound assistant review fields,
but its advice ignored the smile/camera findings and remained generic. No
recommendation was applied or retried into acceptance.

The index then held 44 runs. The `visual_review` gap cleared; loaded-code/model
identity, scalar, sampling, input-package, decode and thermal qualification gaps
remained. External receipts are not automatically consumed by Brain qualification.
Next work: check that advisor proposals cite supplied visual findings, and connect
existing take/decode/reference-token receipts to Brain. Keep SQLite. For another
render, isolate a question such as neutral starting expression or camera parallax.

[Detailed result](artifacts/farm-reference-lab-20261115/RESULT.md),
[playable review](artifacts/farm-reference-lab-20261115/review.html),
[encoder evidence](artifacts/farm-reference-lab-20261115/encoder-evidence.json),
[metrics](artifacts/farm-reference-lab-20261115/render-metrics.json),
[report assessment](artifacts/farm-reference-lab-20261115/report-assessment.json),
[review disposition](artifacts/farm-reference-lab-20261115/review-disposition.json),
and [verification](artifacts/farm-reference-lab-20261115/final-verification.json)
are local receipts in the ignored artifact directory. Use
[BROWSER_ACCESS.md](BROWSER_ACCESS.md) and [BRAIN_ANALYSIS.md](BRAIN_ANALYSIS.md)
for operations. Browser/server were left open with an empty queue at handoff;
recheck live state before reuse.

## Model and parameter screening follow-up

The four-job `farm-model-comparison-v001` batch completed and its output hashes,
native history, full decode, Suite files and Brain records were reconciled.
See the [comparison report](artifacts/farm-model-comparison-20261115/REPORT.md)
and [execution ledger](artifacts/farm-model-comparison-20261115/batch.json).
Assistant sampled-frame review shortlists FL2VA Turbo 8-step for first-frame
motion drafts and Ref2VA 12-step for separate-reference drafts. These are
single-shot candidates, not human approval or changed production defaults.

Use native execution start/end for render cost: Brain admitted duration includes
queue wait. Three pending entries withdrawn during queue ordering remain queued
in Brain's historical records and are excluded from SQLite; they are not live
renders. Keep these monitoring gaps visible when comparing reports.


## Second action and seed confirmation

The `farm-confirmation-v002` screen completed both shortlisted recipes with seed
151104: Clara turns camera-left first, then Andre follows, with fixed framing.
Sampled frames support ordered head motion in both clips. Full-size endpoints
support broadly stable background framing; an initial Turbo widening impression
was withdrawn. Exact gaze timing, likeness and fine defects remain unverified.
Ref2VA 12-step executed in 14m16s; first-frame Turbo 8-step in 7m55s. These are
role-specific draft candidates, not changed defaults or human acceptance.

Turbo's main Sampling interval is incomplete: Brain's 0.6472s value is a surviving
fragment, not total sampling time. Operator metrics mark that total unavailable.
Driver samples directly recorded software thermal slowdown during both renders;
no cooling benefit or causal speedup is inferred. Both automatic CPU advisor jobs
finished, both hash-bound visual reviews are saved, and SQLite/comparison were
refreshed. Advice remains generic and all reports remain benchmark-unqualified.
Prioritize incomplete-timing exclusion and existing-evidence ingestion before
broadening the model sweep.

[Confirmation report](artifacts/farm-confirmation-v002-20261115/REPORT.md),
[ledger](artifacts/farm-confirmation-v002-20261115/batch.json), and
[advisor assessment](artifacts/farm-confirmation-v002-20261115/advisor-assessment.json).


## Timing and advisor repair

The [November 15 repair](artifacts/brain-timing-advice-20261115/RESULT.md) excludes
incomplete phase totals from derived reports, exposes coverage, and carries both
saved reviews into the paired advisor input. Turbo Sampling is unavailable;
Ref Sampling remains 718.3011s, while Ref Saving/assembly is also incomplete.
Raw records remain unchanged. A 44.45s receipt gap crossed the recorder's 30s
stale threshold despite consecutive event numbers; delivery-delay cause is open.

The advisor now cites production findings for both shots and acknowledges timing
gaps, but still recommends decoding/rerendering to verify visual quality. Those
recommendations were rejected; inspect existing frames before new experiments.
Fresh analysis workers use the correction; the live server's imported comparison
code awaits a guarded restart. No new media or production defaults were changed.

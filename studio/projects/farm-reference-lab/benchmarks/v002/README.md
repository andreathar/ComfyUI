# Farm confirmation v002 — ordered gaze, fixed camera

Shot `FARM_S001_SH02` tests the two draft recipes shortlisted by v001. Clara
looks just off-screen camera-left first; Andre follows after she completes her
small turn. Both then hold that direction. The camera stays on a locked tripod.
No walking, contact, props, dialogue or additional people are requested.

| Take | Recipe | Conditioning |
| --- | --- | --- |
| tk001 | Ref2VA, 12 steps, sa_solver/beta | Existing Andre RefMod, Clara portrait and farm plate |
| tk002 | FL2VA Turbo 8-step v1.0, strength 1, euler/simple | Existing composed farm first frame |

Both use seed **151104**, 832×480, 73 frames at 24 fps, silent output, sigma
shifts 12/3, and the same installed encoder and video VAE. Automatic Brain
analysis remains enabled; execution uses the native sequential queue.

The frozen REF package is [package.json](package.json). The FL2VA prompt expresses
the same action using first-frame conditioning syntax. Identity sources and
prompt formats differ between recipes. Action and seed both change from v001;
this checks robustness and does not isolate either change's causal effect.

Review criteria:

- Clara initiates the camera-left glance before Andre; their turns are not merely
  simultaneous and they do not exchange mutual gaze instead.
- Both finish looking toward the same off-screen direction, with visible faces.
- Background framing and apparent character scale remain stable; no push-in.
- Faces, wardrobe and left/right assignment remain stable, with no extra people.
- Inspect motion continuity and facial artifacts separately from successful decode.

Outputs belong under `output/Farm_Reference_Lab/shots/FARM_S001_SH02/tk001/` and
`tk002/`. Suite clips and latents belong to `Farm_Benchmark_v002`. Local frozen
graphs, submission receipts, measurements and reviews are under
`.codex/artifacts/farm-confirmation-v002-20261115/`; `batch.json` binds prompt IDs.
Compare native execution time and sampling time separately from queue wait and
cached work. Keep unsuccessful action/camera results visible. No automatic
production adoption or human acceptance follows from passing technical checks.

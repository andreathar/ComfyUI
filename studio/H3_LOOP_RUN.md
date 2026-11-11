# Silent Context Loop run records

`h3_loop_run.py` tracks the fixed bundle-driven, independent-scene workflow.
It does not queue generation, load models, retry jobs or approve images.
The single-take `film.py` contract is unchanged.

Prepare from the compiled bundle, a live API graph receipt and verified model
pins. Use a separate attempt directory for each deliberately authorized attempt;
an existing run directory is never overwritten.

```bash
.venv/bin/python studio/h3_loop_run.py prepare \
  --root ATTEMPT_DIR --bundle BUNDLE.json --graph LIVE_GRAPH.json \
  --models MODEL_PINS.json --workspace "$PWD"
```

This prints `RUN_DIR`. Its atomic `run.json` stores the bundle, graph, model and
asset pins, ordered shot IDs, delivery contract and event history. It is only
`prepared`: the graph receipt and model pins are not fresh runtime evidence.

Collect live registered node names and a resource snapshot with Unix
`observed_at`, `running`, `pending`, `free_ram_bytes`, `free_vram_bytes` and
`conflicting_export`. Confirm the connected server uses the supplied workspace
and default model resolver. The free-memory snapshot does not qualify peak fit;
the resource pilot and human reference review remain separate production gates.

```bash
.venv/bin/python studio/h3_loop_run.py preflight RUN_DIR \
  --resources RESOURCES.json --nodes NODE_NAMES.json
.venv/bin/python studio/h3_loop_run.py submitting RUN_DIR \
  --graph LIVE_GRAPH.json --resources RESOURCES.json --nodes NODE_NAMES.json
```

Both steps verify the source bundle, asset hashes, model file stamps, node
registration, execution links and resources. Preflight expires after two minutes.
Input-use authorization does not imply likeness or creative approval.

Inspect live node modes, queue **once through `panel_run`**, then immediately run:

```bash
.venv/bin/python studio/h3_loop_run.py bind RUN_DIR PROMPT_ID
```

If the acknowledgement is lost, mark it explicitly and inspect authoritative
queue/history. No retry is allowed from `submitting` or `unknown`.

```bash
.venv/bin/python studio/h3_loop_run.py unknown RUN_DIR 'Queue acknowledgement lost'
.venv/bin/python studio/h3_loop_run.py recover RUN_DIR HISTORY.json
```

Recovery binds only one exact graph with an execution-start timestamp after the
recorded submission. Missing, ambiguous or not-yet-started history stays unknown.
Do not use an empty history response as permission to submit again.

After the completion event, fetch that exact prompt's history and reconcile:

```bash
.venv/bin/python studio/h3_loop_run.py reconcile RUN_DIR HISTORY.json \
  --output-root ACTUAL_CONNECTED_OUTPUT_DIRECTORY
```

Only node 40's saved MP4 qualifies. Its embedded native v3 manifest must match
the bundle and ordered shots. Revision metadata, checkpoint/video/prompt hashes,
path containment, decoded dimensions/fps/frame counts, absence of audio and the
decoded frame order are checked. This supports unchanged hard-cut assembly;
color correction, blends, editorial rearrangements and other graph topologies
require their own deliberate contract. Partial manifests remain partial.

A valid full result becomes `review_pending`, with `review` still unset.
Duplicate completion is idempotent; changed completed media invalidates the old
technical pass. Human acceptance, final delivery publication and native resume
qualification are separate steps. These commands never overwrite media.

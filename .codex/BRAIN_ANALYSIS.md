# Brain analysis operations

Studio owns the analysis CLI; Brain owns raw recording and report-quality rules. No ComfyUI restart, model load or network call is needed to index records or generate deterministic reports. Raw records under `user/workflow_monitor/runs/` remain authoritative. The separate SQLite generations live under `user/workflow_monitor/analysis/generations/`; `current.json` selects the last successfully published generation. Old generations remain available, with no automatic raw-record deletion.

Run from the ComfyUI checkout using `.venv/bin/python`:

```sh
.venv/bin/python studio/brain_analysis.py index
.venv/bin/python studio/brain_analysis.py runs --limit 20
.venv/bin/python studio/brain_analysis.py runs --gap model_identity
.venv/bin/python studio/brain_analysis.py report BASELINE_UUID CANDIDATE_UUID
```

`runs` shows snapshot metadata, age and excluded-run diagnostics; it is not a live view. A report rechecks the selected source files and Brain/index analyzer fingerprints. Rebuild after raw evidence or analyzer changes. Missing streams and stored-versus-declared sample-count differences are explicit gaps. Active, unsupported, malformed or unstable runs are excluded with reasons. A failed build preserves the current generation. Readers already using a previous generation can finish against it. Generation files are immutable by application convention, not protected against manual filesystem edits.

The read API provides bounded status/gap filters (at most 100 rows), sample-resource aggregates and evidence for at most six runs. Queries use a two-second SQLite progress deadline. Report packets are capped at 64 KiB; select fewer runs when that limit is reached. Large integers use exact decimal strings. NULL means unavailable, not zero. Brain retains ownership of qualification and coverage; SQL does not reinterpret missing evidence as success.

Reports are saved to `analysis/reports/UUID/` with `packet.json`, `report.json`, and `report.md`. The packet records generation, analyzer and source hashes, observed metrics, evidence gaps and differing fields. Reports distinguish outcomes and coverage from intended experimental interventions. The first selected run is only the comparison reference; selecting it does not adopt it as a production baseline. Historical records currently do not establish a qualified model ranking or a cooling-effect claim.

## Existing Brain quality report

Brain's active `workflow-monitor.quality.v1` report checks source snapshot digests, dirty/unknown owners, unresolved scalar parameters and missing runtime, sampling, model, output, review and thermal evidence. Multiple scene attestations remain distinct. A matching digest proves internal consistency, not the running server's loaded code. Historical records are not rewritten; quality gaps are not generation failures or a quality score.

The [SQLite evaluation and decision](artifacts/brain-sqlite-evaluation/SQLITE_DECISION.md) supplied the contract implemented here. The preceding [live quality activation](artifacts/brain-sqlite-evaluation/ACTIVATION.md) verified matching benchmark and comparison metadata while preserving raw/workflow hashes. Future Brain source activation still requires a guarded restart through `.codex/launch.sh`, empty queue, preserved unsaved canvas and observed reconnection. This Studio-only analysis change requires no restart.

## Experiments and decisions

Prepare a small JSON controls file describing known and unknown conditions: workload/reference identities, cache state, thermal starting state, launch settings, repetitions and order. Use exact difference paths from `packet.json` for intended changes:

```sh
.venv/bin/python studio/brain_analysis.py experiment BASELINE_UUID CANDIDATE_UUID \
  --hypothesis 'Describe the measurable hypothesis' \
  --changed-field /resolved_primitive_inputs/NODE/steps \
  --controls /absolute/path/controls.json
.venv/bin/python studio/brain_analysis.py decision EXPERIMENT_UUID \
  --value test_further --reviewer athar --rationale 'Explain the explicit human decision'
```

Experiment records pin the packet and its hash. Each decision is a new immutable record and includes the experiment hash. `adopt` records a human decision only; it never edits workflows, model settings or the production baseline. Agents must not invent a human decision or reviewer identity. The CLI is a local operator interface, not an authentication system.

## Local model interpretation

The dedicated Qwen3.5 9B llama.cpp deployment is documented in
[BRAIN_LLAMA.md](BRAIN_LLAMA.md). Select `--runtime llama.cpp` with the explicit
loopback endpoint and model alias. It uses `/health` and `/v1/models` instead
of LM Studio's inventory API, and allows a 600-second CPU inference timeout.
The LM Studio-specific behavior and earlier tests below remain historical.

The first adapter targets the existing LM Studio OpenAI-compatible endpoint. It is a test bridge; the preferred future deployment is a dedicated llama.cpp runtime with an explicit model, context, offload and lifecycle configuration. This batch does not install or configure that runtime.

Before inference, check available RAM/VRAM, temperatures and other GPU consumers; prevent concurrent ComfyUI/Argon generation operationally. The adapter checks the ComfyUI queue twice, refuses another loaded LM Studio text model, and requires the selected model to be already loaded unless the caller explicitly passes `--allow-load`. It cannot reserve the GPU or prevent a human from starting a render after those checks. It does not start a model server, download weights or unload another application's model.

```sh
.venv/bin/python studio/brain_analysis.py report RUN_UUID \
  --endpoint http://127.0.0.1:1234 --model qwen3.5-4b
```

HTTP targets are literal loopback origins, proxies are disabled and redirects refused. Requests are bounded to 64 KiB of evidence and 1024 output tokens; responses to 256 KiB and a 120-second socket timeout. The model receives a compact view omitting source-file manifests and full provenance; the full packet is retained, and the model-view hash is saved. Reasoning is requested off for brief reports, but runtime compliance must be verified. The model has no SQL, shell, tools or write access. A completed model response must identify the requested model, match the report schema and cite existing run IDs and fields. This checks structural validity, not the truth of the prose. No unsupported recommendation is promoted to a human decision.

Failed calls are recorded separately under `analysis/failed_reports/` and never become successful reports. Reports save the model inventory observation, response model, packet/template/schema hashes, usage and elapsed time. Model filenames/IDs are not weight-content hashes. The exact loaded weights, runtime binary and causal performance remain unverified. Raw report data can include project metadata; all analysis/model traffic in this adapter remains local.

Official API references: [LM Studio structured output](https://lmstudio.ai/docs/developer/openai-compat/structured-output), [JIT loading](https://lmstudio.ai/docs/developer/core/headless). Documentation was fetched using Context7 for this implementation.

## Validation

```sh
PYTHONPATH=studio:studio/tests .venv/bin/python -m unittest test_brain_analysis test_brain_reports test_brain_local_model -v
```

Tests cover immutable generations, failed publication, source changes, active/corrupt/symlink exclusions, exact unsigned seeds, NULL aggregates, read-only SQLite, bounded packets, immutable experiment/decision records, busy queues, unloaded-model rejection, real loopback HTTP and redirect rejection. Live inference and review evidence are recorded separately in `.codex/artifacts/brain-analysis-index/`.

## Live adapter check on 2026-11-14

The user loaded `qwen3.5-4b` in LM Studio and authorized the test. Its inventory reported a 98,048-token loaded context. The first request timed out at 120 seconds; LM Studio logged the client disconnect and stopped generation. GPU temperature was observed at 87°C during that request (not a complete thermal benchmark).

A smaller 933-input-token request with `reasoning: "off"` returned `finish_reason: length` after 1024 completion tokens in its reasoning stream, with no finished report. The adapter rejected it. No successful local-model analysis is claimed. This resembles the [LM Studio structured-output reasoning issue](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1773), but local observations, not that issue's version assumptions, establish this failure. No automatic retries or runtime setting changes were made after those two bounded tests.

At that check, the standalone binary had not been started for Brain. The subsequent dedicated deployment in [BRAIN_LLAMA.md](BRAIN_LLAMA.md) pins the executable and GGUF hashes, bounds context/caches/offload, disables thinking and provides queue-aware startup. Do not repurpose LM Studio's internal authenticated backend or stop the shared Hermes router.

## Delivery verification

The production index imported 38 runs, 5,525 events and 9,932 samples. Direct-source status counts, sample counts and temperature aggregates match SQL; integrity and foreign-key checks pass. All 114 original source slots and 78 saved workflow/project files match their prior hashes. Eighteen focused tests pass with both unittest and Studio's pytest configuration.

CodeRabbit attempted the seven new source/test files and returned `review_completed` with `outcome: failed`, zero findings and all seven files unreviewed. This is unavailable external review, not a clean review. Native inspection and test evidence remain separate. See `artifacts/brain-analysis-index/verification.json`, `tests.txt`, `coderabbit-result.json`, and `live-model-verification.json`.

## Automatic follow-up analysis

Enable `analyze_when_finished` on Workflow Monitor Brain to request a separate **Brain — Analyze completed run** native queue job. It waits for terminal evidence/provenance, three seconds of stable source files and an empty render queue. Later renders wait while analysis runs. The dedicated CPU llama.cpp runtime must already be running; nothing starts or downloads models automatically.

A succeeded run with observed Sampling time receives local-model interpretation. Cached, failed and runs without observed sampling receive deterministic evidence summaries. Neither policy selects a baseline or changes workflow settings. Incomplete evidence remains visible.

The original render keeps its own success/failure status. In Brain's existing report panel, refresh the run to see the analysis attempt and **Open advisory analysis** link. Attempts/logs live in `user/workflow_monitor/analysis/jobs/`; immutable report packets remain in `analysis/reports/`. Cancellation disconnects the owned worker and holds the native queue until the dedicated llama.cpp slot reports idle. If the runtime becomes unreachable during cleanup, the queue remains held until it can confirm idle; restore that same runtime to finish cleanup.

Waiting requests are durable and resume after restart, including records evicted from the monitor cache. Once claimed for enqueue, attempts are never retried implicitly after cancellation, restart or failure; those need an explicit manual analysis prompt. A restarting server waits for the dedicated runtime to be idle before accepting new work if an analyzing attempt was interrupted. To retry or analyze an older recording, run **Brain — Analyze completed run** alone in a separate workflow with its source run UUID. Do not insert it inside a generating graph. The toggle defaults off and existing saved workflows are not rewritten.

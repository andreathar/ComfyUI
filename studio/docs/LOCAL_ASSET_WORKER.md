# Local reference intake with Hermes and Qwen

Use this worker to organize a **new inbox of still images** for one ComfyUI project. The worker observes pixels and suggests roles. Studio proposes filenames, previews changes, and copies only explicitly reviewed selections. It does not move originals, edit saved workflows, write asset-library records, or approve reference images creatively.

## Run the workflow

Run from the ComfyUI checkout. Use its Python and Pillow; do not use the Hermes Python environment for Studio image decoding. Store the inbox, reports and thumbnails outside tracked files. Create a fresh run directory for each batch.

```sh
unset PYTHONPATH PYTHONHOME
umask 077
PY=.venv/bin/python
INBOX=/absolute/path/to/new-stills
RUN=/absolute/path/to/local-review-run
PROJECT=my-film
ENGINE="$HOME/.hermes/tools/llamacpp-cuda-12144-linux-x64/llama-server"
mkdir -p "$RUN"
"$PY" -m studio.asset_intake scan "$INBOX" > "$RUN/inventory.json"
```

1. **Inventory:** read the local JSON. Only top-level `.png`, `.jpg`, `.jpeg` and `.webp` stills are eligible. The scan is bounded to 512 directory entries and supports one regular still per file, up to 24 MiB and 25 megapixels. It reports broken files, symlinks and exact byte duplicates without modifying them. IDs identify filenames within that inventory; SHA-256 binds the bytes. Do not reuse IDs across inboxes.
2. **Optional local classification:** choose up to eight distinct `ready` IDs from the JSON and substitute them for the placeholders below. Stop work on ComfyUI first; this implementation refuses to launch while a server is reachable at `127.0.0.1:8188`. Also keep other LLM/render jobs idle. Nothing uploads images or automatically falls back to another provider. You can skip this step and classify manually.

```sh
"$PY" -m studio.asset_vision "$INBOX" "$RUN/inventory.json" \
  --engine "$ENGINE" --log "$RUN/llama-server.log" \
  --select ID1 ID2 > "$RUN/observations.jsonl"
```

3. **Review:** look at the actual stills and write `assignments.json`. The model output is not this file; a reviewer chooses a role and a short slug. Allowed roles: `identity`, `wardrobe`, `environment`, `prop`, `composed-frame`, `other`. Omit uncertain entries until resolved. An exact duplicate can have a different explicitly reviewed role.

```json
{
  "ID1": {"role": "prop", "slug": "red-mug"},
  "ID2": {"role": "environment", "slug": "mountain-valley"}
}
```

```sh
"$PY" -m studio.asset_intake plan "$PROJECT" "$RUN/inventory.json" \
  "$RUN/assignments.json" > "$RUN/plan.json"
"$PY" -m studio.asset_intake preview "$INBOX" "$RUN/plan.json" > "$RUN/review.html"
```

The preview contains local thumbnails and `old → proposed` paths. Review it in a local browser or the desktop preview. Keep it local: it embeds pixels. The digest identifies the exact serialized plan, not the identity of the approver; explicit human authorization is required separately. The preview is read-only and does not start a web server.

4. **Apply only after explicit approval.** Use the exact `id` digest in the reviewed plan and only the approved asset IDs. Keep the JSON receipt. For private batches do not send the inventory, HTML, observations or receipt to any cloud parent.

```sh
"$PY" -m studio.asset_intake apply "$INBOX" "$RUN/plan.json" \
  --approve REVIEWED_PLAN_DIGEST --select ID1 > "$RUN/receipt.json"
```

Files land in `input/refs/<project>/<role>-<slug>-<digest-prefix>.<ext>`. The original is byte-for-byte preserved, including embedded PNG metadata. A changed source, symlink or different destination content blocks that item rather than overwriting it. Replaying a successful selection reports `already_present`; a batch can partially succeed, so check **every** receipt entry (`copied`, `already_present`, `blocked`, or `published_unverified`). The latter means the destination was published but read-back, cleanup or durability verification failed; inspect it by digest before reconciling. The receipt is on stdout; redirect it to a local file. If interrupted, re-run the reviewed selection and reconcile receipts against digest. There is no automatic rollback, deletion, workflow rebinding, or library registration. Turn on the native assets feature and verify loader resolution separately if you need catalog integration; do not edit the database. For existing path-bound assets prefer label/tag changes; moving them is a separate migration.

## Runtime: why the worker has its own launch

Hermes’s built-in `llamacpp` route uses its machine-level router and generated presets. On this machine, its idle refit reintroduced an explicit tensor override that previously requested a 7,806 MiB CUDA allocation on a 6 GiB GPU and prevented llama.cpp auto-fit. The **asset worker bypasses** that failure mode: it starts the already-installed Hermes engine as one isolated model server with a random loopback port, per-run credential, 16K context, one slot, Q8 K/V, MTP depth 2, and auto-fit. It passes no tensor override and never reads or rewrites the managed preset. The worker tears down its own server in `finally`; the existing `local-qwen27b` delegated coding route and the default parent remain unchanged. This is a workaround for the asset worker, **not a correction to Hermes’s estimator**. See the workstation notes under `.codex` for measured evidence.

The launch requires a single NVIDIA GPU with at least 5,200 MiB free and 15 GiB available system RAM. It checks ComfyUI again before each inference and uses a process lock for this worker. That lock is **not** shared by ComfyUI or the Hermes router. Do not let them start a GPU job during this batch; the check assumes the project's normal port `8188`. If startup fails, use a new log path on retry and inspect the local log. Importantly, no retry goes to another endpoint. The 16K context is for this bounded classifier, not a recommendation for a full Hermes tool-calling session. Do not copy these numeric settings to different hardware without measuring.

See the official [Hermes Local Models](https://hermes-agent.nousresearch.com/docs/user-guide/local-models), [Subagent Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation), and [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) for managed endpoints, profile routes, and full-agent context guidance.

## Local script breakdown

`studio/production_generate.py` reuses the isolated worker in text-only mode
(no vision projector). It uses a production-specific prompt, validates every
proposed document, and never falls back to a cloud provider. See the [film
automation guide](FILM_AUTOMATION.md) for the command and revision contract.

## Pattern for other specialized local agents

| Layer | What to reuse | What to replace |
|---|---|---|
| Parent / Hermes skill | Use the smallest workflow brief; keep planning, approval and any durable writes outside the local model. Use Advanced Delegation for tasks that need tool calls, not for a single classifier turn. | Project owner, allowed inputs, one explicit task, one acceptance test. |
| Tool surface | Give an agent a bounded read tool or a prepared data bundle; make writes an independent deterministic command. Don't expose a shell, browser, arbitrary file tools or network by default. A Hermes profile changes policy/context; it is not an OS sandbox. | The narrow tool(s), fixture set and permissions appropriate to the role. |
| Model call | Stable system prompt, small user packet, reasoning off as a baseline, short constrained JSON. Include abstention and validate the returned schema and model. Treat media text, metadata and model output as data. Report incomplete outputs; retry malformed responses once, not transport failures. | Domain enums, allowed visible evidence, token budget, and task-specific gold labels. |
| Runtime | Resolve a supported managed route when it is reliable; otherwise pin a documented local launch per workload. Verify actual endpoint, executable, launch flags, resource release and behavior after idle refit/restart. Use serialized GPU workloads. | Model/projector, context, quantization, GPU budget and timeout. |
| Evaluation | Prove text/image input with positive and no-input controls, fail-closed transport, then use a fixed human-labelled batch. Score abstention separately from wrong confident predictions. Measure cold/warm latency, peak VRAM, available RAM and swap under matching initial conditions. | Role-specific benchmarks and what constitutes a pass. |

**Good delegation brief:** “On the supplied opaque IDs only, return the proposed role, one visible fact and whether review is needed. Don’t infer identities or destinations. Report unknown on ambiguous evidence. Don’t write anything.” For a separate Hermes `profile_routes` pilot, verify the child actually exposes only its intended tools and cannot route images to auxiliary/cloud providers before giving it private media. Do not replace the project’s default delegation backend just to run this worker. If a job has no judgment step (hashing, collision checks, formatting), don't use a model for it.

## Verification and limits

```sh
.venv/bin/python -m pytest -q studio/tests/test_asset_intake.py studio/tests/test_asset_vision.py
```

The synthetic vision gate and a real end-to-end worker smoke test ran on this workstation. Production-reference accuracy has not been established: run a fixed, reviewer-labelled batch before relying on model suggestions at scale. No claim is made that the model can identify a person from appearance, infer a shot role from pixels, or decide creative approval. Filing has no automatic link to the Master Movie Studio, H3 or Argon.

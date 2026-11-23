# Studio storage and recovery plan

## What the live audit found

ComfyUI served the Studio, asset and node APIs from this checkout after startup. The queue was idle and native prompt history was empty. The checks read local records without submitting jobs or changing production data. The [workstation evidence](../../.codex/artifacts/studio-storage-audit.osZc4J/evidence.json) records counts and status without story text or prompts. Refresh it with `.venv/bin/python .codex/artifacts/studio-storage-audit.osZc4J/audit.py` from the checkout root.

| Store | What it owns | What the audit verified |
| --- | --- | --- |
| `studio/projects/<slug>/` | Story, production outline, asset references, bindings, transitions and previous revisions. The manifest records the approved creation digest. | All three projects listed by Storyboard opened and their live revisions matched disk. Eight unbound requirements and one reference awaiting review appeared in the API. `the-message` and `farm-reference-lab` contain additional production or reference documents outside the current discovery layout. |
| `user/studio_storyboard/{requests,jobs}/` | Outlines awaiting review, original requests and local inference evidence. The prompt queue owns active execution. | Four job directories had matching source hashes. One request-backed draft was `needs_review` on disk and `unknown` through the API. A request-backed cancelled job also appeared as `unknown`. Two other drafts lacked request records and returned 404. Both reproduced the same project creation digest, so the digest identifies the approved content while leaving the producing job ambiguous. |
| `user/master_studio/{packages,prompt_reviews,takes}/` | Frozen prompts and workflows, take history receipts, and human review tied to the output digest. | Eleven of twelve takes had archived native history. The twelfth was rejected before submission. The one approved take had its output, Suite video, sidecar and latent present with matching recorded SHA-256 values. The linked Brain run existed. |
| `output/h3_projects/` and `output/h3_stages/` | Project Suite clip selection and stored takes. The stage directory holds reusable encoded intermediates. | Across 26 manifests, the 28 referenced take basenames all had MP4, JSON sidecar and latent files. This check covered file presence and the approved Master Studio sample's hashes. |
| Native media and `user/comfyui.db` | The filesystem holds media. SQLite indexes asset IDs, loader paths, tags and metadata. Studio reference binding verifies SHA-256 of the native file. | The API reported 2,306 assets. SQLite quick check passed with zero foreign-key violations. Only 16 of 2,299 content rows have a BLAKE3 hash. Of 1,001 rows flagged missing, 88 stored paths resolved to files and 913 did not at inspection time. Link those flags to project references before acting on them. |
| `user/workflow_monitor/{runs,analysis}/` | Per-prompt raw telemetry and rebuildable analysis generations, reports and comparisons. | The active SQLite generation checked clean and covered 57 of 73 raw run directories. Thirteen absent records had a `run.json` modification time later than the generation build. Three runs were recorded as skipped at build time. Thirty-one raw directories lacked at least one stream file. Report coverage alongside timing. |
| `user/default/workflows/` | Editable visual workflow snapshots. The frozen take owns the effective graph used for an individual render. | The default profile contains 43 workflow JSON files. |

## Plan

### 1. Restore Storyboard drafts after a restart

- Use `StoryJobs.read()` in the Fantastic PromptBuilder fork. Its current terminal-state checks require native prompt history. Add a regression scenario with an empty queue and history, a persisted request, matching source hash and prompt UUID, a verified terminal state, and an exited planner. Exercise it in `tests/test_production_jobs.py` in the fork and reuse `studio/tests/test_production_runtime.py` for state publication.
- Define the durable terminal receipt where native completion and job ownership can both be verified. Store its version, job ID, request and proposal digests, terminal status and process-exit evidence. For existing jobs, evaluate available state, request, ID and release evidence explicitly and surface missing completion proof. Evaluate the two drafts without request records separately.
- Verify that a completed draft can reopen for review after a restart without reanalysis, that a cancelled job stays cancelled, and that a mismatched proposal or interrupted write cannot become an approved draft. Keep creation gated on the user's approved proposal digest.

### 2. Reconcile projects, takes and assets with a read-only report

- Start with the three current Storyboard projects, the two alternate project layouts and all twelve Master Studio takes. Use `studio/storyboard_workspace.py`, `studio/production_store.py`, `studio/production_references.py`, `studio/master_take.py` and the Suite manifest reader as the schema owners. Use the approved Master Studio take as a positive control for the archived-history path.
- Trace project revision, scene, shot and take ID to prompt UUID, frozen graph digest, output bytes, Suite files and Brain run. Preserve explicit statuses for records that are missing, changed, ambiguous, intentionally skipped, or awaiting review. Use native asset IDs and loader paths as locators. Track BLAKE3 and SHA-256 with their algorithms.
- Identify native asset paths that exist despite a missing flag, then rank them by active project references. Test moved, replaced and inaccessible files with copies. Decide whether each alternate project should be discoverable as an archive, become a current Storyboard project, or stay a separate lab. Leave its files in place during classification.
- Require an actionable status and responsible store for every broken or ambiguous link in the sample. The approved take must resolve from its archived receipt with native history empty. Two matching candidate jobs must be reported as ambiguous unless stronger evidence names the producing job.

### 3. Prove restoration into a disposable directory

- Use one current Storyboard project, one bound reference and the approved Master Studio take. Inventory the required files and provenance, including the linked Suite and Brain records. Store root-relative locators in the backup inventory and document how existing absolute paths are resolved during restore.
- Use the SQLite online backup API for `user/comfyui.db` so committed WAL contents are included. Restore the snapshot and referenced files under a different root. Reopen the project, verify the take, hashes, review identity and Suite links, and rebuild the Brain index from the restored raw records. Check SQLite integrity and foreign keys in the copies.
- Deliberately omit one file from a restore copy to exercise failure reporting. Record recovery time, backup size, verified records and each dependency that prevented complete recovery. Keep the original checkout and asset database outside the restore destination.

### 4. Verify write recovery and make retention decisions

- Test concurrent edits and simulate interruption immediately before and after publication. Check the Storyboard revision guard, the derived `reference_plan` after a requirements change, and Suite publication across manifest and video, latent and sidecar writes. Verify that a conflict preserves the prior readable state and that an incomplete clip cannot be approved as a continuity source.
- Report Brain index age and eligible unindexed runs separately from absent streams. A fresh generation should include every eligible fixture run and explain exclusions. Reuse the Brain tests and compare the current generation against the raw inventory before deciding on a refresh policy.
- Inventory approved work, other takes and telemetry, and rebuildable stages. Produce a dry-run retention report with bytes, dependencies, recovery evidence and named exceptions. Production cleanup needs a separately authorized change and verified restore.

Implement the first recovery fix in the Storyboard job owner and use an independent read-only report for cross-store visibility. Evaluate a derived index if direct reconciliation becomes too slow for day-to-day use. Keep the existing stores as owners of their records.

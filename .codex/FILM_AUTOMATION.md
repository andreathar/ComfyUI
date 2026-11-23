# The Message automation — implementation status

Implemented 2026-11-10 in the existing checkout. Source was developed in the
isolated `codex/film-automation` worktree and only new owned files were copied to
the main checkout. Existing dirty files, model/launch settings, original scene
tabs and media were preserved. Nothing was committed, merged, downloaded or
restarted.

## Delivered

- Canonical production document and script spans for the two existing scenes,
  with versioned identity/voice/location/wardrobe bindings and preserved live
  prompt/editor snapshots.
- Deterministic H3 compiler, synchronized Prompt Builder state, reference labels,
  fixed diagnostic preset and complete execution-graph verification.
- Model/asset preflight, fresh resource evidence, durable attempts and prompt-ID
  reconciliation. Submission is performed visibly through the panel, not by the CLI.
- Human review records and approved-only CPU FFmpeg assembly with exact frame trims.
- New saved tabs: `06 - Learning Production/The Message - Auto Shot 01` and
  `The Message - Auto Shot 02`. Each retains the 26-node/5-group baseline topology.
- Prepared records: `.codex/artifacts/the-message-production/MSG_S001_SH01/tk003`
  and `MSG_S002_SH01/tk003`. Earlier unsubmitted tk002 proposals are superseded.

Use [the operating guide](../studio/docs/FILM_AUTOMATION.md). Check the project with:

```bash
.venv/bin/python studio/film.py check studio/projects/the-message
```

## Verification

The 20 existing production tests and 26 new compiler/preflight/take tests passed.
Tests include real synthetic-video decode and trimmed assembly; no GPU model load.
Independent code review is clear after fixing model-resolution provenance and
resource timestamp expiry.

Both saved canvases reloaded with exact executable graph equality; all nodes were
active, and runtime classification was local/free. Graph contracts match the
compiled records. Evidence: [canvas receipt](artifacts/the-message-canvas-verification.json).
All four protected source/output media hashes remain unchanged.

Full streaming SHA-256 checked both the four original model files and their
preferred NVMe runtime copies. All matched. Actual serving PID 268448 owned port
8188 in this checkout during inspection, without model-directory override flags.
Evidence: [resolved model pins](artifacts/the-message-model-verification.json).
The standard extra-model-path config hash is pinned; alternate launch roots need
an explicit resolver adapter. Resource snapshots do not reserve the GPU or certify
peak memory fit.

The panel briefly rejected tab switching with `root-state-unreadable`. Recovery
was list open workflows → reopen the same active target → verify prompt → reload
the saved working copy. Save/reload checks subsequently passed. The report-bug
skill currently disables issue submission, so no issue was filed.

## Remaining qualification

This delivers the script-to-visible-shot preparation milestone, plus offline
execution bookkeeping and assembly controls. These newly compiled prompts have
not rendered. One controlled H3 take with measured resource peaks and complete
receipt/visual/audio review is the next runtime gate. Existing Scene 02 still
needs human review; neither it nor a final cut was automatically approved.

Unattended batching, Plan Studio migration, cached-conditioning reuse, silent
Project Suite imports, larger output presets and continuous-shot extension remain
outside the qualified path. The take runner currently uses The_Message's output
namespace. The original screenplay was not supplied: the included short script
is explicitly reconstructed from the two existing scene prompts.

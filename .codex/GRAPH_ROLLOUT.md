# Production graph rollout

The parent and all 14 canonical custom-node repositories have independent indexes in the existing VS Code store. [graph-indexes.json](graph-indexes.json) is the access manifest: 15 owners and 15 installation aliases, including Swarm's two aliases mapped to one owner. The unrelated Swarm application index and Codebase Memory development index are preserved separately.

## Verification

At verification, every owner had a matching indexed Git HEAD, representative exact-file coverage with matching metadata, a real symbol lookup, and a source-backed call or registration case. Dynamic/Brain pilots covered Python and JavaScript; additional LC123 probes cover `lc_free_text_encoder.py` and `lc_fast_cancel.py`. NativeAudioLock uses its literal registration plus live `/object_info` as the relationship check because external imports are not represented by graph IMPORTS edges. This does not certify every call edge or every source file.

All component source HEADs and clean Git states were preserved. The final stack-lock check reports reproducible; all 78 sampled saved workflow/project files retain their baseline hashes. ComfyUI responds on port 8188 with an empty queue, and headed Chrome remains open on the movie workflow. No model loading, generation, browser closure, component source change, package update or remote code review was performed. The model/creative workflow remains untouched.

The configured Codex command now matches VS Code's production binary; arguments no longer disable the shared graph UI. Future connections join the existing production store. Running cross-host clients retain their original process/config until their hosts reconnect them. Their experimental wrapper/store were not deleted or changed. Fresh CLI requests successfully query the production store; an actual refreshed editor/panel agent invocation remains unverified.

## Cost and limits

The 16 index invocations covered 14 unique component roots: the two pilots were rechecked once by the continuation runner before its skip-key was corrected. Total recorded indexing time 89.1 seconds; the Spark full index took 56.49 seconds. Sampled aggregate production-CBM RSS peaked at 6,296 MiB; available host RAM stayed above 10,014 MiB, with zero swap in the observed post-run check. This sampling is not a unique-page or instantaneous allocation measurement.

The complete production cache contained 17 projects, about 3.58 million graph nodes and 5.87 GiB of database files at verification. Spark contributed about 2.75 million nodes, so avoid gratuitous full-stack reindexing. Index growth is not evidence of better coverage. Component indexes created by CLI are not automatically watched from the parent session; refresh the changed owner before relying on its graph.

Known partial parsing remains:

- Parent: 14 GLSL blueprint files and pytest.ini (pre-existing 15 partial files).
- Agent Panel: one unit-test file and one SQL migration (2).
- Spark: upstream and installed copies of `native/spark_split/producer.cu` (2).
- Swarm owner: documentation, HTML and Razor templates (9); sampled installed node paths pass.
- Fantastic PromptBuilder: `web/refmodstack.js` (1), with multiple error ranges. Use raw source/browser checks for this frontend; do not assume the entire file is represented.

The complete file/range details are in `artifacts/graph-rollout/owner-verification.json`. No parse-unusable files were reported by these index results.

## Cross-owner map

Automatic `cross-repo-intelligence` for Dynamic with parent/Brain targets returned no result after several minutes. Only that CLI request was terminated; the shared daemon continued answering reads and the editor's parent index completed successfully. Published Dynamic cross-repo metadata remained `never_run`. Do not claim automated linking succeeded or retry it in a loop.

Use these source-backed boundaries until that capability is separately diagnosed:

| Producer / consumer | Verified boundary | Graph limitation / acceptance |
|---|---|---|
| Core → Dynamic | Dynamic `core/control_panel.py:353` reads native `model_management.current_loaded_models`; unload/free delegates to core | Instance attributes and runtime objects require source/runtime checks |
| Dynamic → Brain | Brain `workflow_monitor/provider.py:39` discovers Dynamic's loaded `control_panel.py` through `sys.modules`, then calls `get_snapshot` and normalizes it | Runtime module discovery is not a regular static import edge |
| LC123 → Core | `lc_free_text_encoder.py:70` captures/wraps `CFGGuider.outer_sample`; FastCancel also wraps sampling and adds block hooks | Wrapper order and enabled defaults must be inspected; per-repo symbol existence is insufficient |
| Project Suite / Context Loop / Studio | Projects, clips, context/stages and generated package/runtime contracts remain owned by their existing modules | Use STACK_OWNERSHIP.md and contract-decisions.md; indexing did not execute a continuation or validate creative output |
| Browser / Agent Panel → workflow | The person confirmed headed Chrome visibility; the fresh profile rendered Agent Panel, disconnected | No assistant launched or session migration; do not claim tool invocation from panel visibility |

## Recovery and operation

Per-call argv/exit/timing/resource observations: `artifacts/graph-rollout/invocations.json`; per-owner query evidence: `verification-commands.json` and `owner-verification.json`. Source baseline: `manifest-before.json`. Config change and private backup location: `client-change.json`.

Restore only the exact old Codex Codebase Memory stanza if rollback is needed, preserving unrelated later settings. New indexes live in the existing cache with persistence=false; no graph artifact was written inside component repositories. Do not delete the existing cache or indexes to undo client configuration. Component pins remain unchanged.

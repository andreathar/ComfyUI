# New-run provenance implementation

Approved scope: capture component revisions and effective/configured settings alongside new monitored runs. Execute sequentially in the installed Brain worktree; parent owns the integration lock and operational guidance.

- [x] Add failing tests for Git/worktree/symlink discovery, dirty/unknown state, settings allowlisting and immutable per-run lifecycle.
- [x] Add a local bounded provenance collector to Brain and schedule it only for newly observed live queue records. Serialize metadata work outside the event loop; capture errors remain explicit and never change generation status.
- [x] Store capture timestamps, content digest, repository commit/dirty state and installation aliases. Separate filesystem source evidence, configured launch/settings values, sampled native policy, and unknown loaded-code identity. Do not promote unresolved graph inputs.
- [x] Run Brain's Python and browser-event suites, a real local collector check and scoped code review. Commit Brain first, then reconcile the parent lock and affected query evidence.
- [x] Preserve saved workflows and existing run files. Prepare guarded activation for review after implementation; do not silently restart the running server.

Acceptance: active run gets one immutable snapshot; historical/late admissions cannot acquire current provenance; completion after eviction/deletion/cancellation cannot rewrite a record; subprocess failure and time budget produce qualified metadata; secret settings/argv/remotes are not exported. No models, external telemetry or new dependencies.

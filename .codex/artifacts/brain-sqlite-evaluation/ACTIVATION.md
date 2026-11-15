# Brain data-quality activation

Approved in Inbox message `msg_01M7EB9B1JZE6PM0YEXQJDDXDJ`. Activated Brain `40e316bc1d73f92df82e1db6d0ecdfe7cc45ed0a` through the canonical launcher after verifying queue, resources, baseline model-file presence and exact process ownership.

Observed PID 546006 stop with SIGINT and port 8188 go down. New PID 683283 registered Brain and served the API with canonical flags. The existing headed browser reconnected with the same client ID; its unsaved movie canvas remained unchanged (SHA256 `71067011f187e8c30e5698114af6944159ef58c27eb213b7911cfa68163ffabd`). The local process record now points to the current server and log.

Live checks used only existing runs:

- CPU smoke `e3ead456-950b-4b5e-840a-e51e3f4e4751`: valid provenance digest, source metadata observed, original Brain source revision `d0cf1c4` retained. Report generation did not replace historical execution provenance with today's revision.
- Historical generation `60dd87b2-e8bd-400e-b565-5958effbf5c9`: absent provenance remains unavailable, with explicit evidence gaps.
- Run detail and benchmark export return matching `workflow-monitor.quality.v1` data.
- Comparison JSON and CSV preserve the same quality objects for each selected run. This comparison was an export-contract check, not a controlled performance experiment.
- `benchmark_qualified` remains false for both records.

All original run/event/sample hashes and 78 saved workflow/project hashes remain unchanged. The queue is empty. No new prompt, model inference, SQLite production deployment or local-model invocation was requested.

Evidence: `activation-down.json`, `activation-up.json`, `activation-server.log`, `browser-identity-before.txt`, `browser-after-activation.txt`, two `live-benchmark-*.json` files, `live-comparison.json`, `live-comparison.csv`, and `activation-validation.json` beside this report. Raw source/backup artifacts remain local. The SQLite analysis index and local-model adapter are still the next proposed implementation, not activated by this restart.

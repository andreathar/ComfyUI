# Brain provenance live activation

Authorized in Inbox message `msg_01M7E9NTCCW4EX0YDY387PQQBH`. Executed November 14, 2026 local time (November 15 UTC).

ComfyUI was restarted only through `.codex/launch.sh`: verified old PID 37847, cwd/command/port and empty queue; SIGINT; observed port down; new PID 546006; observed ready backend and Brain registration. Canonical flags are retained. Updated local `server-process.json` records the actual process and log.

The existing headed browser reconnected with the same client ID. Its unsaved movie canvas hash before and after is `71067011f187e8c30e5698114af6944159ef58c27eb213b7911cfa68163ffabd`; no canvas was replaced or reloaded. A local backup and screenshot are retained outside the committed evidence.

## Single CPU-only check

Run `e3ead456-950b-4b5e-840a-e51e3f4e4751`, label **Provenance activation - CPU-only smoke**, completed successfully in 5.01 seconds. The prepared DynamicScriptNode slept for five seconds with restricted imports, zero dynamic ports/modules and no shared cache operations; Brain remained enabled. Browser history reported success with no node errors; no script exception/traceback appeared in the server log.

- Provenance: collected while running, 117.3 ms capture window, 15 owners, 16 aliases, complete discovered-source metadata coverage.
- Parent revision at capture: `031808b2f2dc7dbd87ddcd636c314b8982790fcc`; Brain: `d0cf1c48727a46673e3e1ba23787d509e4b6eafb`, clean. Parent, Spark H3 and Swarm were explicitly dirty; no dirty source was represented as reproducible from its SHA alone.
- Snapshot SHA256: `59171a7cacd5ce1031a473915c12f43d78c8044242c07f738aaed38580e71153`, verified against the exported snapshot.
- Launch options: reserve VRAM 1.0, CK attention configured, pinned memory disabled. Sampled native policy: NORMAL_VRAM, smart memory enabled, pinned memory disabled, 1 GiB reserved.
- LC123 FreeTextEncoder and FastCancel: configured default true and last cached true. The CPU-only test does not exercise their sampling hooks. A false explicit enable_dynamic_vram launch option is not a disabled runtime: startup independently reports native DynamicVRAM enabled.
- Browser events complete; five resource samples. Benchmark and comparison JSON preserve identical provenance. The comparison used the same run twice solely to test serialization, not to infer a performance change.

All 37 historical run files and 78 saved workflow/project files match pre-implementation hashes. Queue is empty. GPU memory remains 444 MiB used / 5363 MiB free after the check; no generation model was loaded. The visible movie workflow remains open.

## Limits and evidence

`benchmark_qualified` remains false: no generated artifact/model identity, executed generation settings or creative review were established. `loaded_code_identity` remains unverified by design. This validates live monitoring and export integration; it does not measure cooling effectiveness or generation speed.

Raw local evidence: `activation-down.json`, `activation-up.json`, `activation-browser-identity-before.txt`, `activation-browser-down.txt`, `activation-browser-up.txt`, `activation-browser-final.txt`, `activation-server.log`, `activation-history.json`, `activation-run-detail.json`, three `activation-*-export.json` files and `activation-validation.json`. Screenshot: `output/playwright/provenance-activated.png` in the parent checkout. The server and run records remain local; no push or merge was performed.

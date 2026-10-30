---
name: comfyui-upstream-sync
description: Use when updating this local ComfyUI fork from Comfy-Org/ComfyUI upstream, checking whether upstream changes conflict with local changes, or rolling back a failed update.
---

# ComfyUI upstream sync

Run from `/mnt/data/Projects_SSD/ComfyUI`. Remotes: `origin` (private fork), `upstream` (Comfy-Org).

## 1. Review (read-only)

```bash
git fetch upstream
git log --oneline master..upstream/master
git diff master...upstream/master --stat
git diff master...upstream/master -- requirements.txt manager_requirements.txt comfy/cli_args.py
git merge-tree --write-tree master upstream/master >/dev/null && echo CLEAN || echo CONFLICTS
```

Also check indirect breakage, which text merges miss:
- Pin bumps in `requirements.txt` vs `.codex/requirements.lock.txt` and the venv.
- Removed/renamed CLI flags used by `.codex/launch.sh`.
- `comfy.*` symbols imported by `custom_nodes/*` — grep them against the upstream diff.
- New outbound-network or feature-flag paths (AGENTS.md forbids adding them; know what upstream added).

Report findings and ask the user before merging.

## 2. Safety net

Server stopped (`ss -ltnp | grep 8188` empty), then:

```bash
D=$(date +%F)
git tag -a local/known-good-$D -m "Known-good before upstream sync" master
tar --exclude='__pycache__' -I 'zstd -T0' -cf /mnt/data/backups/comfyui/$D-ignored-state.tar.zst custom_nodes user .codex/artifacts
chmod 600 /mnt/data/backups/comfyui/$D-ignored-state.tar.zst
uv pip freeze --python .venv/bin/python > /mnt/data/backups/comfyui/$D-freeze.txt
```

## 3. Merge and dependencies

```bash
git merge --no-edit upstream/master        # merge, never rebase master
uv pip install --python .venv/bin/python --torch-backend cu130 --link-mode copy --strict -r requirements.txt
```

Then regenerate `.codex/requirements.lock.txt` from `uv pip freeze` (keep its header lines) and commit it as `Update local lock for ComfyUI <version>`.

## 4. Validate

1. `.codex/launch.sh` starts; log has no `IMPORT FAILED` for custom nodes and shows the new version.
2. `curl -s 127.0.0.1:8188/object_info | python -c 'import json,sys;print(len(json.load(sys.stdin)))'` — node count not lower than before without explanation.
3. Queue the baseline workflow from `.codex/README.md`; compare time/VRAM with `.codex/artifacts/generation-benchmark.json`.
4. Stop the server. Push only with the user's approval: `git push origin master --follow-tags`.

## Rollback

```bash
git reset --hard local/known-good-<date>
uv pip sync --python .venv/bin/python /mnt/data/backups/comfyui/<date>-freeze.txt --torch-backend cu130
tar -I zstd -xf /mnt/data/backups/comfyui/<date>-ignored-state.tar.zst
```

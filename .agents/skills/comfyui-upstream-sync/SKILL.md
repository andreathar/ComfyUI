---
name: comfyui-upstream-sync
description: Use when updating this local ComfyUI fork from Comfy-Org/ComfyUI upstream, checking whether upstream changes conflict with local changes, or rolling back a failed update.
---

# ComfyUI upstream sync

Run from the ComfyUI repository root. The current checkout can be on a work or
stabilization branch; never assume that the intended target is named `master`.
`origin` is this checkout's GitHub remote and `upstream` is Comfy-Org/ComfyUI.

## 1. Inspect before integrating

Check `git status --short`, `git branch --show-current`, and `git remote -v`.
Preserve all existing edits. Custom nodes are separate repositories and ignored
by the ComfyUI root; inspect them with `.venv/bin/python .codex/check_custom_nodes.py`
and review each dirty repo independently.

Fetching updates remote-tracking refs and Git's object database, but does not
change checked-out files. `merge-tree --write-tree` may also write tree objects;
it does not update the index or working tree. After fetching, identify the
intended local branch and upstream base explicitly; use the configured
`upstream/HEAD` when it is available, otherwise ask which upstream branch to
compare. Compare those exact refs:

```bash
git fetch upstream
git log --oneline <local-branch>..<upstream-ref>
git diff <local-branch>...<upstream-ref> --stat
git diff <local-branch>...<upstream-ref> -- requirements.txt manager_requirements.txt comfy/cli_args.py
git merge-tree --write-tree <local-branch> <upstream-ref>
```

Also inspect indirect breakage: dependency pins versus
`.codex/requirements.lock.txt` and the active venv; CLI flags used by
`.codex/launch.sh`; `comfy.*` imports in installed custom nodes; and any new
network or feature-flag behavior against `AGENTS.md`. Report the findings and
get approval before integrating upstream.

## 2. Protect local state

Before a merge, inspect the ComfyUI status, the custom-node lock report, and the
queue. Do not stop or restart a running server while work is queued; start or
restart ComfyUI only through `.codex/launch.sh` after confirming the queue is
clear and identifying the exact process.

Choose and verify a backup destination with enough space before copying state.
Do not blindly archive `user/`, `.codex/artifacts/`, or nested repos: they may
contain credentials, private data, large artifacts, or independent Git state.
Preserve only the specific state needed, and keep it outside the source tree.
Do not create a backup at a hard-coded path unless it has been confirmed to
exist and be appropriate for this machine.

## 3. Integrate and handle dependencies

After approval, merge the selected upstream ref into the explicitly selected
local branch. Do not rebase a shared branch or install dependencies
automatically. Review dependency changes first; use this checkout's documented
`uv pip` workflow, CUDA backend and lock constraints where compatible. Do not
run `uv sync`. Update `.codex/requirements.lock.txt` only after an approved
resolution has been installed and verified.

## 4. Validate and publish

Run relevant tests and `bash -n .codex/launch.sh`. If runtime validation is
needed, launch only through `.codex/launch.sh`, check `/queue` before submitting
the baseline workflow documented in `.codex/README.md`, and compare measured
resources with the recorded baseline. Report skipped checks and limitations.
Push only after the user explicitly approves the target branch and push.

## Rollback

Prefer a revert of the integration commit/merge on the same branch. Do not run
`git reset --hard`, restore broad archives, or overwrite dirty worktrees unless
the user explicitly approves the exact destructive operation after a verified
backup. For an in-progress merge, inspect the status and ask before aborting if
it would discard or obscure existing changes.

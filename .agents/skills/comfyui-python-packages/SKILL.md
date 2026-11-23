---
name: comfyui-python-packages
description: Review and manage Python dependencies for this workstation's customized ComfyUI checkout. Use for uv and Visualizer changes, package upgrades or conflicts, CUDA wheel compatibility, dependency drift, and dependency changes in locally maintained custom-node forks.
---

# ComfyUI Python packages

Work from the ComfyUI root. Read `.codex/README.md` for the active setup and
`.codex/STACK_OWNERSHIP.md` when a change touches a production node pack.

## Ownership

- Use the root `pyproject.toml` to declare the local runtime and compatibility
  constraints. Let uv generate `uv.lock` for the exact resolution.
- Use Antigravity's Python Package Visualizer for routine managed additions.
  **Tools → Migrate to uv (Automatic)** uses the additive workstation installer
  in `.codex/uv_workspace.py`. Use `.venv/bin/python` explicitly and
  `uv pip --python .venv/bin/python` for package operations. Keep host PATH
  under pathman.
- Upstream `requirements*.txt` and node pack manifests describe their consumers'
  requirements. Import relevant changes through the local manifest. Keep the
  November 13 `.codex/requirements.lock.txt` as historical recovery evidence.
- Use `.codex/custom_nodes.lock.json` for node-pack Git revisions and install
  paths. An installed package and a node pack may have distinct versions and
  owners. Keep ComfyUI Manager from changing the workstation resolution.
- Preserve extra installed packages until their role is established. An absent
  import or ownership match is insufficient evidence for removal. Use the
  additive installer for the existing environment. A bare `uv sync` can prune
  node-pack dependencies.

## Evaluate a candidate

Start with the read-only report. Use `--json` for per-package ownership,
conditional requirements, compatibility-file differences, and import-name
overlaps. Check the full environment and the local lock independently.

```bash
.venv/bin/python .codex/package_review.py
uv pip check --python .venv/bin/python
uv lock --offline --check --python .venv/bin/python
.venv/bin/python .codex/check_custom_nodes.py
```

Review an exact version when a release, applicable advisory, observed bug, or
measured workload gives a reason. Include the source and the improvement under
test. Add `--resolve` to produce a temporary candidate lock diff and
`--offline` to restrict it to cached metadata.

```bash
.venv/bin/python .codex/package_review.py PACKAGE VERSION \
  --reason 'Observed behavior to improve' --evidence 'Release, issue, or run reference' \
  --resolve --json
```

Use `--workflow FILE` with `--object-info FILE` to map selected saved workflows
to providers from a known localhost schema snapshot. Resolve incomplete
ownership with imports, source inspection, and the affected workflow. An
advisory or version badge is evidence for investigation. A successful resolution
is evidence for testing.

## Test, fix, and promote

1. Keep a candidate worktree and environment separate from the running stack.
   Resolve only the change and the packages it needs. Read the whole diff and
   check the installed-only consumers as well. Keep Torch, torchvision,
   torchaudio, Triton, and CUDA libraries on a coherent cu130 stack unless the
   experiment explicitly changes that stack.
2. Own the custom-node code for this PC. Fix stale constraints or real API
   incompatibilities in the maintained fork and add a focused regression
   test when it catches the failure. Preserve independent Git histories and
   uncommitted work. Pin the tested node revision and matching Python
   resolution together. Upstream release timing does not control local fixes.
3. Check package metadata, affected imports, and actual node registration.
   For GPU/runtime changes use Balanced SD15 as the fast smoke test and the
   affected local workflow for production acceptance. Read `.codex/SETUP_PLAN.md`,
   the model manifest and benchmark, and `.codex/BRAIN_ANALYSIS.md` before
   generation. Compare repeated runs with the same inputs, model, seed, and
   launch flags. Record timing, VRAM/RAM, stability, and human quality verdicts
   separately. Verify idle queue and GPU availability before a generation test.
4. When promotion is in scope, apply only the tested manifest, lock, and
   custom-node revisions. The Visualizer's routine actions preserve their
   single-package guard. For an intentional multi-package release, export the
   verified candidate lock to a temporary `pylock.toml` and apply that exact
   export with additive `uv pip install --python .venv/bin/python --no-deps`.
   Keep the previous accepted pair of Python and node revisions recoverable.
   Verify the active environment and affected workflow after promotion. Report
   findings as keep, test, fix our fork, or promote, with evidence, blockers,
   and checks still pending.

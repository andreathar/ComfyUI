# Visible browser access for local agents

Use standalone headed Chrome for ComfyUI inspection on this workstation. The editor's integrated preview is a separate surface; a disconnected browser bridge does not mean ComfyUI or Chrome is missing.

## Reuse the visible session

From `/mnt/data/Projects_SSD/ComfyUI`, first inspect existing sessions:

```bash
playwright-cli list
playwright-cli -s=comfy-visible snapshot
```

If `comfy-visible` does not exist, open it explicitly:

```bash
playwright-cli -s=comfy-visible open http://127.0.0.1:8188 --config=.codex/browser-playwright.json --headed
```

Use fresh snapshot references for clicks, and store screenshots under `output/playwright/`. This session is an isolated browser profile, not the user's existing editor canvas. Its profile is ephemeral when closed; export any unsaved work before closing. Never silently substitute a headless session when the person expects to watch.

Agents with local shell access can reuse this named CLI session. Coordinate one operator at a time in the project Inbox; inspect the current tab/canvas before acting. Do not open duplicate sessions per agent, close another agent's window, submit a prompt, free models or attach to a different canvas as an incidental browser test. Do not launch an agent merely to test the panel. A screenshot proves rendered UI; ask whether the person sees the window before claiming desktop visibility confirmed.

## Existing Playwright MCP

`~/.codex/config.toml` already registers Playwright. Its arguments now specify the installed executable:

```text
--browser chrome --executable-path /home/athar/.local/opt/google-chrome-stable/current/opt/google/chrome/chrome --isolated
```

Playwright MCP is headed by default. Existing connections retain their launch arguments until the client reconnects them. Do not add another MCP registration/server or force-stop shared processes to repair this. After a supported client reconnect, call `browser_tabs` and navigate to the local URL to verify the tool, not just its config. MCP starts its own isolated context; it is not automatically attached to the CLI session. Prefer the already-open CLI session for coordinated visible work.

The exact config-only backup location and before/after Playwright stanza are recorded in `artifacts/browser-stack-readiness/config-change.json`; the full backup is private under `~/.codex/backups/`. Undo only this stanza, preserving later unrelated config changes.

## What is installed / what is proven

- Google Chrome exists under the stable `current` path above. `google-chrome` and `chromium-browser` on PATH both resolve through the same Chrome wrapper; their names do not establish a separate Chromium installation.
- `playwright-cli` works in the current agent environment. Host PATH remains owned by pathman. No browser download, PATH edit or shell-startup repair was needed.
- November14: `comfy-visible` successfully launched headed, loaded ComfyUI, opened Agent Panel via a real UI click and captured its rendered panel. Dynamic's live resource panel is visible too. Agent Panel showed disconnected in this fresh profile; no assistant session was launched and no existing session was migrated.
- Existing Playwright MCP failed at the missing `/opt/google/chrome/chrome`; corrected config awaits client reconnect and live verification.
- CUA/editor bridge reported `The browser access host is unavailable`. That connector remains unavailable; no conclusion about a specific VS Code preview defect follows from it.
- Other agent hosts can use the CLI if they have this same local filesystem, display and tool access. Their native MCP connections and remote/headless environments have not been individually certified. Do not claim “all agents verified” from one session.

Official configuration reference: https://github.com/microsoft/playwright-mcp#configuration

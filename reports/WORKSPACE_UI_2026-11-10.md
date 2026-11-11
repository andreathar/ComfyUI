# ComfyUI browser and controls verification

## Completed

Opened ComfyUI in an isolated headless Chrome session using the already-installed browser/automation tools. Only local ComfyUI URLs were allowed. No extension, browser, model or package installation was needed, and the user's existing tabs were not controlled.

All four workflows under **01 - Images** loaded and compiled without missing-node warnings or JavaScript page errors. The small **Project Hub - Browse Existing** workflow also passed.

Applied the same native canvas layout to the four image workflows:

**Models → Input → Settings/Processing → Output**

Only group rectangles, node positions/sizes/titles and initial view changed. Node IDs, types, links, widgets, seeds, model selections, prompts, dimensions, sampler settings and output prefixes stayed unchanged. RealESRGAN is labelled Processing rather than sampling; its resize can enlarge a small image. The SD1.5 editor explicitly labels its fixed square resize, which can stretch non-square references.

![Consistent native controls in the SD1.5 draft](../.codex/artifacts/workspace-ui-20261110/controls-overview.png)

These are ordinary editable ComfyUI nodes, not another app, custom control framework or global variable store. Current workflows retain their tested settings; grouping does not imply every input is interchangeable across models.

## Browser roundtrip checks

After editing, all five graphs were loaded, compiled, serialized, reloaded from that serialization, and compiled again. Their executable API prompts matched the before-layout browser prompts, ignoring display-only `_meta` titles. A second source-JSON comparison independently confirmed that all execution-relevant fields were unchanged.

This tests browser serialization/reopening, **not the Save/Save As menu or overwriting a user's active tab**. The source files were saved directly and remain accessible through the server's workflow browser.

The original SD1.5 adapted API receipt includes a `control_after_generate` field that the browser correctly omits from its backend prompt. The seed-control widget remains fixed; it is frontend behavior, not a sampler input. No generation-value change was needed.

## Project panel verified

Opened **Project Hub → Open project…** for the existing `Andre shot0075 three view pilot`. The panel displayed its three-second pending take, 512×288 project size, zero approved clips and inactive chain.

![Existing H3 project panel](../.codex/artifacts/workspace-ui-20261110/project-panel.png)

No clips were approved/rejected, no projects were created, and no generation, export, import or cleanup button was pressed. This confirms panel access, not swap quality or production readiness.

## Additional cleanup and limits

- Moved the loose `MiniMax H3 Character Sheet (AusBoss).mp4` embedded-workflow example from the workflow-browser root into **90 - Lab and Older Workflows**, alongside its example material. Content hash unchanged; no media deletion.
- A fresh browser still opens the installed frontend's bundled RPG example. Replacing root `default_workflow.json` did not change that behavior because this frontend did not request that endpoint. **Rolled the experiment back** rather than modifying installed frontend files. Open a daily graph from **01 - Images**. Existing browser sessions were not reset.
- Updated only the SD1.5/Klein pilot safety pins after source/browser equivalence checks. The unrelated Z-Image hash mismatch stays guarded in Lab; it was not silently approved.
- **195 Studio maintenance tests passed.** Focused review found no concrete bugs. A mechanical layout scan returned no findings; actual browser checks and source/prompt comparisons provide the useful evidence here.
- No new render was submitted in this UI pass. Previous output-quality/resource limitations still apply. No server restart, further model deletion or memory-manager change occurred. Queue empty at handover.

Evidence and pre-edit recovery copies: `.codex/artifacts/workspace-ui-20261110/`. Key files: `layout-manifest.json`, `verification.json`, `before/`, `confirm/`, `project-panel-results.json` and `originals/`. One browser-helper attempt failed on an ambiguous sidebar selector; the stable test-id selector fixed the helper, and the final complete run passed.

Next: qualify a useful H3 project/video workflow before extending the same controls layout there. Do not restore every missing example dependency or introduce a second automatic offload manager merely to make the library appear complete.

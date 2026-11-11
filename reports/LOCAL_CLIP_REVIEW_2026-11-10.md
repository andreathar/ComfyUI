# Local clip frame review

Open **05 - Video Review → 01 - Local Clip Frames (no models)** in ComfyUI. Refresh the page once to load the VHS preview fix, then reopen the saved workflow.

1. Choose an existing clip from **video**, or click **choose video to upload**. Drag-and-drop onto the loader also uses its native upload feature. Upload copies the file into ComfyUI's local input folder; no path typing is required.
2. Set **start_time** in seconds to inspect another window.
3. Run. **Preview Image** shows the decoded frames; **Preview Any** shows source and loaded-window information.

Defaults: **12 fps, at most 24 frames, 512×288 centre crop**—about two seconds. Both dimensions deliberately produce a fixed 16:9 review crop; this is not a full-frame editorial inspection. Set one dimension to zero to preserve source aspect ratio, but the other dimension will no longer be bounded. Keep a nonzero frame cap: zero means unlimited. The saved example selects the existing `bench_src.mp4` fixture.

This is frame-only review: **no sound playback, video export, model loading or H3 project import/approval**. Frames go to ComfyUI's temporary preview storage, not the output folder. Existing loaded models may remain resident; this workflow does not unload them.

## Picker and hidden-preview fix

The first version used a separate path-text node to avoid VHS's independent video player. That workaround has been removed in favour of native **VHS_LoadVideoFFmpeg** upload/selection.

A small local change in `custom_nodes/comfyui-videohelpersuite/web/js/VHS.core.js` makes hidden video previews unload their sources and skip preview/metadata requests. Show/Hide uses that same lifecycle, while hidden previews are excluded from Resume and Sync actions. Only new FFmpeg-upload nodes default hidden/paused; other preview types retain their prior defaults. Existing saved visible previews can still be shown.

Leave the embedded player hidden for frame-only review. Deliberately choosing **Show preview** permits a separate video/metadata request; the preview may use display-derived dimensions rather than the backend's 512×288. No claim is made that hiding cancels every server operation already started while a preview was visible.

## Verification of the final upload version

- Isolated Chrome opened the native file chooser, uploaded a test copy of the local fixture to the local ComfyUI server, and selected it successfully. The test-only copy was hash-checked and removed; the saved selection remains `bench_src.mp4`.
- Canvas load, serialize and reopen produced the same executable API prompt. **Zero preview/media/metadata GETs** occurred during hidden workflow loading, file upload/selection and return to the saved selection. No page errors.
- Show restored a paused preview; Hide removed its media source. Changing the source and invoking Sync while hidden produced no media requests. A Video Combine node retained visible/unpaused preview defaults.
- Focused review caught a delayed metadata response restoring stale state after Hide. A per-preview generation guard now discards it; a deferred-response hide/change-source browser test passes.
- Submitted only the **three-node decode/preview prompt** on an empty queue. Successful local fixture run: **24 temporary PNG previews, each 512×288**, all decoded and dimension-checked. Observed wall time: **1.094 s**, including polling/retrieval—not a general benchmark. Queue empty afterward.
- No sampler, model loader, H3 project node or video-export node is in the executable graph.
- The existing **AnimateDiff** loader alignment preset preserves 8-pixel dimensions; it does not load a model. The **None** preset produced NaN dimensions after browser roundtrip during the earlier experiment and was not published.

![Decoded local fixture frame](../.codex/artifacts/local-clip-picker-20261110/first-frame.png)

Current evidence and recovery copies: `.codex/artifacts/local-clip-picker-20261110/`, including `VHS.core.before.js`, `workflow.before.json`, `browser-results.json`, `preview-lifecycle.json`, API prompt/history and decode results. Earlier path-version evidence remains under `.codex/artifacts/local-clip-review-20261110/`.

No models, packages, source clips or H3 projects changed; no server restart or paid call. Temporary previews and normal execution-history records were created. The H3 silent-import/continuation issue remains unresolved; this review graph deliberately bypasses it.

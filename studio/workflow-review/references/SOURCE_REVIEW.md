# Next-batch source review

These are selected execution-path findings, not a security audit of entire extensions. No extension was imported by the inspection code. Current node schemas were read from localhost.

## Tested reduced capabilities

| Original example | Reduced test | Scope |
|---|---|---|
| `custom_nodes/comfyui-rmbg/example_workflows/image_mask_preview.json` | Core LoadImage → AILab image and mask previews | Preview transport only; segmentation removed |
| `custom_nodes/comfyui-rmbg/example_workflows/V2.7.0_ImageStitch.json` | Two local 512² images → right-side stitch → preview | Verified 1024×512 output |
| `custom_nodes/comfyui-itools/example_workflows/PromptRecord.json` | Literal text → iToolsPromptRecord | Backend text only; no timeline UI qualification |
| `custom_nodes/comfyui-itools/example_workflows/KSamplerOverlay.json` | Local image → literal text overlay → preview | No KSampler or metadata-extraction qualification |
| `custom_nodes/comfyui-videohelpersuite/tests/converted-format-input.json` | Two local image frames → ImageBatch → GIF | Pillow GIF path; no FFmpeg/audio/video decoder coverage |
| `custom_nodes/ComfyUI_LC123_nodes/workflows/LC123 Examples - Image Tools & Post Processing.json` | Local image → LCImageDesaturate → preview | Gallery is unwired; constructed test of Rec.709 full desaturation |

Implementation references:
- RMBG previews and stitching: `custom_nodes/comfyui-rmbg/py/AILab_ImageMaskTools.py:79–123`, `custom_nodes/comfyui-rmbg/py/AILab_ImageMaskTools.py:255–305`, `custom_nodes/comfyui-rmbg/py/AILab_ImageMaskTools.py:1356–1661`.
- iTools: `custom_nodes/comfyui-itools/nodes/prompt_record.py:5–48`, `custom_nodes/comfyui-itools/nodes/add_overlay.py:30–55`, `custom_nodes/comfyui-itools/backend/overlay.py:4–64`.
- VHS GIF branch: `custom_nodes/comfyui-videohelpersuite/videohelpersuite/nodes.py:406–446`.
- LC math and previews: `custom_nodes/ComfyUI_LC123_nodes/lc_image_tools.py:2065–2083`, `custom_nodes/ComfyUI_LC123_nodes/lc_image_tools.py:44–65`.

Source hashes used by the first test batch are in each receipt and `studio/review_utilities.py`. They attest to disk files only. Four iTools files are newer than the live server process; further execution is refused until process/source consistency can be established. Existing iTools outcomes remain backend observations with uncertain loaded-source identity. No live-bytecode attestation is available.

## Do not blindly queue

- RMBG model nodes may call `download_model` when weights are absent: `custom_nodes/comfyui-rmbg/py/AILab_RMBG.py:116–135`, `custom_nodes/comfyui-rmbg/py/AILab_RMBG.py:607–610`. Empty extracted filename lists do not prove model-free execution.
- RMBG image loaders can make URL requests: `custom_nodes/comfyui-rmbg/py/AILab_ImageMaskTools.py:553–582`. Tests use core local LoadImage instead.
- AILab Canvas invokes cache cleanup on every call: `custom_nodes/comfyui-rmbg/py/AILab_Canvas.py:349–350`, `custom_nodes/comfyui-rmbg/py/AILab_utils.py:19–31`. Not executed in this shared-server utility batch.
- Complete iTools examples load models and sample; VaePreview decodes a VAE: `custom_nodes/comfyui-itools/nodes/vae_preview.py:20–29`, `custom_nodes/comfyui-itools/nodes/vae_preview.py:52–58`.
- VHS URL-capable media loaders can download: `custom_nodes/comfyui-videohelpersuite/videohelpersuite/load_video_nodes.py:510–511`, `custom_nodes/comfyui-videohelpersuite/videohelpersuite/load_video_nodes.py:611–612`, `custom_nodes/comfyui-videohelpersuite/videohelpersuite/nodes.py:648–649`.
- LC optimization galleries include download paths: `custom_nodes/ComfyUI_LC123_nodes/lc_optimizer_engine.py:641`, `custom_nodes/ComfyUI_LC123_nodes/lc_optimizer_engine.py:702`, `custom_nodes/ComfyUI_LC123_nodes/lc_optimizer_engine.py:800`.
- LCNote is frontend virtual, not a missing backend node: `custom_nodes/ComfyUI_LC123_nodes/web/lc_note.js:548`.
- CustomCodeNode intentionally executes code: `custom_nodes/comfyui-CustomCodeNode/nodes.py:46`, `custom_nodes/comfyui-CustomCodeNode/nodes.py:103`, `custom_nodes/comfyui-CustomCodeNode/nodes.py:192`. Excluded from unattended execution.

## Reproduce safely

```sh
# Source-file and schema-provider preflight only:
.venv/bin/python studio/review_utilities.py
# Requires a verified live PID and refuses newer disk source files:
.venv/bin/python studio/review_utilities.py --run --server-pid <verified-local-server-pid>
```

A server/source mismatch is not permission to restart a shared runtime. The restart decision remains with the person.

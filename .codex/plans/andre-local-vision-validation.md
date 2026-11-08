# Andre workflow: local vision selection

Date: 2026-11-07. Scope: existing-model selection and bounded local validation,
before workflow implementation. No weights downloaded or paid jobs submitted.

## Selection

Use **Qwen3.5-4B Q4_K_M** and its existing **BF16 vision projector**, served by
the user's existing LM Studio/Bionic installation on `127.0.0.1:1234`.
The combined installed files are 3,383,082,464 bytes (3.15 GiB). Both GGUF files
were opened, hashed and successfully loaded with image input. Hashes are in
`../artifacts/andre-local-vision-validation/model.json`.

The installed Qwen3.5-9B Q4_K_M is also vision-capable, but its inventory size
is 6,548,927,711 bytes, exceeding the 5.4 GiB initially free VRAM before inference
overhead. It was not loaded or benchmarked. Nemotron 3 Nano 4B reports no vision.
ComfyUI's existing diffusion text encoders are not validated standalone analyzers.

The upstream model and GGUF distribution specify Apache-2.0:
https://huggingface.co/Qwen/Qwen3.5-4B
https://huggingface.co/lmstudio-community/Qwen3.5-4B-GGUF

## Runtime evidence

- ComfyUI live health: RTX 3060 Laptop, 5.4/5.7 GiB available/allocatable VRAM,
  approximately 12.2 GiB available RAM, no running or pending ComfyUI jobs.
- Existing listener owners verified: port 1234 Bionic PID 1447699 in `/opt/Bionic`;
  port 8188 Python PID 2054461 in this ComfyUI checkout. No services started.
- LM Studio initially had no loaded models. Test instance was uniquely named
  `andre-vision-validation`, loaded in 5.25 seconds with a 600-second idle TTL.
- Requested 8K context/full GPU estimate was 3.76 GiB. Existing saved overrides
  instead set `--ctx-size 40000`, `--n-gpu-layers 28`, parallel 1, Q8 K/V caches
  and a reasoning budget. `lms ps` reported context length 40192. Settings were
  not changed. This is not an 8K/full-offload benchmark.
- Actual process used llama.cpp CUDA13 runtime 2.71.0, mapped `libggml-cuda.so`,
  and runtime log reported 28/33 layers offloaded. The projector was supplied.
- Connected ComfyUI statistics during validation reported 1.88 GiB free VRAM
  and 10.88 GiB free RAM. These are snapshots, not measured peak usage.
- Only the test instance was unloaded after it became idle. Other services and
  the user's shared model defaults were preserved.

## Input and validation

Used the source selected in node 1: `driving_outdoor_dance.mp4`, verified SHA256
`29616c58ddb9c7ef8b11173153ed3ab4050fd759bf007391a8c4507b649a999d`.
Sampled 0.25, 3.5 and 6.5 seconds to three 640-pixel-wide JPEGs and inspected
them visually. No source media was changed. Requests used only localhost.

1. OpenAI-compatible structured-output trial, reasoning enabled: failed with
   incomplete JSON. Of 1100 output tokens, 953 were reasoning; finish reason
   was `length`. Preserve this failure as a validation case.
2. Native `/api/v1/chat`, `reasoning: off`, `store: false`: complete response,
   203 output tokens, zero reasoning tokens. JSON was wrapped in a single code
   fence despite instructions; removing that exact wrapper allowed validation.
   Scene, clothing, lighting and broad poses matched the frames. Facial
   expression and an activity label were more specific than the evidence allowed.
3. Refined uncertainty instructions: **11.24 seconds**, 189 output tokens,
   **19.52 output tokens/second**, 1.54 seconds to first token, zero reasoning
   tokens. Complete JSON passed schema/type validation and had three action rows.
   Correctly described one person, white crop top and wide trousers, ocean/tree/
   building, natural light and long shadows. Facial expression became
   `not reliably visible`; target selection was flagged for human review.

The final response still called the first pose a martial-arts stance despite an
instruction to describe posture only. This is a known semantic error. Do not
automatically transfer such labels into an approved Kling prompt.

## Decision and limits

**Suitable as the initial local draft analyzer with mandatory review.** Not
validated for unattended target selection or automatically approved prompts.
This one-source test does not validate multi-person selection, identity tracking,
all shot types, fine facial expressions, or temporal motion. Model inference is
not proof that the future ComfyUI integration works.

Keep per-request reasoning off, bounded samples, complete-response schema
validation and explicit uncertainty. Show actual loaded settings, since the
user's saved overrides can supersede requested context/offload. Do not modify
those overrides implicitly. Require the local service and exact existing model;
if unavailable, stop with an actionable message instead of downloading or using
a cloud analyzer. Keep target review and paid-generation authorization separate.

No workflow/custom-node implementation was performed. Andre Element
`323525046658711` and the Andre-reference-clothes default remain in the design.

Evidence directory: `../artifacts/andre-local-vision-validation/` contains source
frames, model hashes, runtime process evidence, first-attempt failure, both local
responses, schema, validation script and the final `source-test.json`.

API reference used for per-request reasoning and image inputs:
https://lmstudio.ai/docs/developer/rest/chat

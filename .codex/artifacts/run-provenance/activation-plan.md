# Pending live activation

1. Preserve the open unsaved movie canvas. Recheck exact port owner, empty queue, RAM/VRAM and model paths. Confirm no export is using the GPU.
2. Stop only the verified ComfyUI process with SIGINT; observe port down. Start through `.codex/launch.sh` and verify canonical flags, startup logs and `/object_info` readiness; observe browser reconnection without changing its canvas.
3. Submit `activation-cpu-prompt.json` once with the connected browser client identity, without loading/replacing its canvas. It uses the installed DynamicScriptNode for a five-second `time.sleep` and an enabled WorkflowMonitorBrain output. No model or media node, network script, shared module/cache mutation or import restriction change is included.
4. Check `/history` and Brain's run record: success, collected provenance, content digest, new Brain revision, all expected owners, explicitly dirty/unknown states, actual launch options/native policy and configured/cached LC123 values. Check both JSON exports and event/resource coverage separately. The script node captures its exceptions, so inspect its exception output/log as well as overall success.
5. Confirm queue empty, server responsive, existing runs/workflows unchanged and original canvas still open. Retain the labeled test record as evidence. This is integration validation, not a generation benchmark or creative approval.

This plan is prepared but has not been executed. The running server still uses its previously imported Python modules.

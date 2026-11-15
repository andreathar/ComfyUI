---
name: debug-issue
description: Systematically debug issues using graph-powered code navigation
---

## Debug Issue

Trace a bug through the current Codebase Memory graph before reading source.

### Steps

1. If the project identifier is unknown, call `mcp_codebase-memo_list_projects`; then call `mcp_codebase-memo_get_architecture` before searching.
2. Use `mcp_codebase-memo_search_graph` to find relevant functions, classes and tests.
3. Use `mcp_codebase-memo_trace_path` with `direction="inbound"`, `"outbound"` or `"both"` to trace callers and callees from the suspected symbol.
4. Read the implementation with `mcp_codebase-memo_get_code_snippet`; use `mcp_codebase-memo_search_code` for literal names, dynamic attribute calls or other graph-coverage gaps.
5. Use `mcp_codebase-memo_detect_changes` to correlate the issue with the current diff, and `mcp_codebase-memo_query_graph` when a multi-hop relationship or test link needs checking.
6. Confirm the trigger path and reproduce the smallest failing case before proposing a fix. Add or run a regression test for the observed failure.

## Token Efficiency Rules
- Use one targeted graph search first; request broader architecture or graph output only when needed.
- Budget: about five tool calls and 800 tokens of graph output per task.
- Read the implementation and its tests before changing code. The graph narrows scope; it does not replace the source.

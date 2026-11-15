---
name: refactor-safely
description: Plan and execute safe refactoring using dependency analysis
---

## Refactor Safely

Plan refactors from the current Codebase Memory dependency graph, then verify the actual editor changes and affected tests.

### Steps

1. If needed, identify the project with `mcp_codebase-memo_list_projects` and call `mcp_codebase-memo_get_architecture` for relevant boundaries.
2. Use `mcp_codebase-memo_search_graph` and `mcp_codebase-memo_trace_path` to identify definitions, callers, dependencies and impacted flows; supplement with `mcp_codebase-memo_search_code` for dynamic or literal references.
3. For symbol renames, use the editor's language-aware rename preview and inspect the proposed edits before applying them. Do not assume a graph MCP tool applies refactors.
4. Keep the change scoped to the owning layer, update affected tests, and run those tests.
5. Use `mcp_codebase-memo_detect_changes` after the edit to confirm the actual impact matches the intended scope.

## Token Efficiency Rules
- Begin with targeted graph queries and expand only when a specific dependency question remains unresolved.
- Budget: about five tool calls and 800 tokens of graph output per task.
- Read the implementation and its tests before changing code. The graph narrows scope; it does not replace the source.

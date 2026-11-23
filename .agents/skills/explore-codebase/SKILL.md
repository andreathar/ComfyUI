---
name: explore-codebase
description: Navigate and understand codebase structure using the knowledge graph
---

## Explore Codebase

Use the current Codebase Memory MCP tools to navigate the repository.

### Steps

1. Call `mcp_codebase-memo_list_projects` if the project identifier is unknown, then `mcp_codebase-memo_get_architecture` to understand its structure and boundaries.
2. Use `mcp_codebase-memo_search_graph` to locate functions, classes, files or tests by name and path.
3. Use `mcp_codebase-memo_trace_path` to inspect callers, callees or data flow from a relevant symbol.
4. Use `mcp_codebase-memo_get_code_snippet` for a symbol's source and `mcp_codebase-memo_query_graph` for multi-hop relationships.
5. Use `mcp_codebase-memo_search_code` for literal text, dynamic attribute access and other cases the graph may not index.
6. Call `mcp_codebase-memo_get_graph_schema` only when relationship names or graph coverage are unclear.

## Token Efficiency Rules
- Start with one targeted query; expand the graph scope only if it leaves a concrete question unresolved.
- Budget: about five tool calls and 800 tokens of graph output per task.
- Read the implementation and its tests before changing code. The graph narrows scope; it does not replace the source.

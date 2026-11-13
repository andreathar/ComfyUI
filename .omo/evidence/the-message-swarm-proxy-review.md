# Focused Swarm custom-node proxy review

codeQualityStatus: CLEAR
recommendation: APPROVE
blockers: []

Scope: /mnt/data/Projects_SSD/SwarmUI/SwarmUI/src/BuiltinExtensions/ComfyUIBackend/ComfyUIRedirectHelper.cs and SwarmUITests/ComfyUIRedirectTests.cs. Read-only inspection; no builds, test execution, restart, AGENTS changes or implementation edits. Existing dirty notebook and untracked lscache files were left untouched.

## CRITICAL
None.
## HIGH
None.
## MEDIUM
None.
## LOW
No material findings for the authorized local deployment.

## Security and correctness assessment

- Helper at ComfyUIRedirectHelper.cs:76 forwards only X-MiniMaxH3-Token and Sec-Fetch-Site, plus explicitly handled Origin, under minimax_h3/ or api/minimax_h3/. It does not forward general Authorization, Cookie, arbitrary X-* headers or generate a token for a caller without one.
- Same-public-origin comparison includes scheme, host and port; only that value is rewritten to the selected upstream authority. Other Origin values, including null/foreign strings, are retained. Multi-valued origins do not match the public authority and remain malformed/foreign rather than being upgraded into a valid origin.
- Existing Swarm user/PermDirectCalls checks run before this helper. The diff does not widen those permissions or change backend selection.
- POST call site at line 487 runs after target construction on the existing generic send branch. GET/token and other non-POST methods use the second call site at line 542. Special prompt/queue/interrupt routes are outside the custom-node prefix and unaffected.
- Inspected installed Fantastic web_api.py:_cross_origin: present cross-site and same-site Sec-Fetch-Site values are rejected; absent metadata falls back to Origin/Host matching. Forwarding those browser signals preserves upstream checks instead of dropping them. This helper does not bypass the mutation token check.
- Source tests cover same-origin rewrite/token propagation, no unrelated Authorization forwarding, foreign-origin and cross-site preservation, missing token, unrelated route and similarly named prefix exclusion, and api/ route variant. These are behavioral boundary tests, not implementation-constant snapshots.

## Validation and limits

Inspected full scoped git diff, full new test file, surrounding request-routing code, installed backend origin-guard source and git status. Tests were not executed by this reviewer under the no-build instruction; the lead agent's full suite was still running at review time. No independent claim of live 403 resolution, deployment, restart success or passing compiled suite is made here. Approval is scoped source review; lead must retain build/test and guarded-restart evidence separately.

The authority comparison intentionally fails closed for public-origin representations that differ textually (for example explicit default ports or an unaccounted upstream TLS terminator). The authorized direct local host/port case is covered. Header-prefix filtering is not a canonical-path security boundary: dot segments could normalize a manually constructed request to another endpoint on the same configured backend, but this helper only relays a caller-supplied custom token and adds no server secret or target-host selection. No material exploit or regression established from that observation in the current scope.

## Skill-perspective check

remove-ai-slops/programming skill files remain unavailable as documented in prior reviews. Applied the documented reviewer criteria: no useless tests, unnecessary parsing, untyped escape hatch or needless abstraction found. The small helper avoids duplicating policy at both send sites and keeps routing scope explicit.

Report stored at the explicitly requested path. This review does not modify or reinterpret AGENTS.md; user authorization and build/restart decisions remain with the lead agent.

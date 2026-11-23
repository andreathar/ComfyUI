# Identity instruction review

codeQualityStatus: WATCH
recommendation: APPROVE
blockers: []

CRITICAL: none.
HIGH: none.
MEDIUM: none.
LOW: studio/still_recipe.py:60 always asks to preserve facial identity, including valid faceless/nonhuman characters. A manually compiled two-character fixture with Orb described as a faceless floating metal sphere retained that description but also asked to preserve Orb's facial identity. Prefer species-neutral identity wording, or qualify facial preservation when applicable. This is a prompt ambiguity, not a demonstrated render regression; no model job was run.

Actual reference numbering follows the same ordered refs list passed to worker.add_references; multiple identity entries receive their own entity names and indices. The new instruction is included in both graph text and References review. Source story fields and other graph/model input construction are unchanged by the narrow instruction insertion. Prompt and graph digest intentionally change. Both files are untracked in the root repository, so no independent before-file diff is available; scope was assessed from the current code and parent's stated insertion.

Independent focused test run: 46 passed (studio/tests/test_still_recipe.py and studio/tests/test_reference_requirements.py). An additional in-memory two-character/nonhuman fixture compiled successfully with correct individual indices, preserved appearance, and all review section text present in graph prompt. The initial ad hoc fixture attempts failed schema validation and were corrected before this verification. No implementation or runtime state changed.

Skill perspective check: named remove-ai-slops and programming skills unavailable; applied developer-supplied criteria. No unnecessary abstraction, parsing, or extraction found. The exact sentence assertions are narrow wording checks, supplemented by meaningful ordering and graph/review consistency checks; not a blocker. Existing tests lack a persistent multicharacter/nonhuman fixture. Browser/model effectiveness was not tested.

Fallback artifact path used; no active ULW attempt available. Notepad: .codex/artifacts/storyboard-implementation/progress.md.

# The Message · Master Movie Studio

Unified production canvas after the F1–F5 corrections from the read-only review.

Workflow:

`user/default/workflows/06 - Learning Production/The Message - Master Movie Studio.json`

Guide companion review: [`MASTER_MOVIE_STUDIO_REVIEW.md`](MASTER_MOVIE_STUDIO_REVIEW.md)

## Hardware defaults (this PC)

| Knob | Value | Why |
| --- | --- | --- |
| Resolution | 832×480 | Proven 6 GB path |
| Length | 3.0 s request | Compiler shows **raw vs delivered** frames |
| Overlap | 22 frames when continuing | H3 Context head pin + Trim |
| Sampler | `sa_solver` / `beta` / 20 steps | Silent-proof recipe |
| Shifts | video 12 / audio 3 | Native H3 flow |
| Attention | `.codex/launch.sh` (`--use-ck-attention`) | Locked launch |
| Audio decode | **muted** | Silent path; AV unmute needs trim wiring (F7) |

## How to use

1. Set **Var · Project Name** (feeds Hub directly — panel follows this link).
2. Set **Var · Shot Tag** (`MSG_S001_SH0N`). The **Shot Package Resolver** loads matching prompt, media, RefMod stack, seed, and transition.
3. Read the **Live Production Plan Summary**: project, shot, transition mode, raw/delivered frames.
4. Queue. For a **cut**, context stays off even if an approved clip exists. For **continue**, approve the predecessor first, then queue with that shot’s transition=`continue`.
5. Open project… on Hub → review → Approve before the next continue take.
6. Monitor Brain records digests for steps/duration/prompt/LoRA under `user/workflow_monitor` (not `user/default/workflow_monitor`).

## Transition policy

- Package defaults in `studio/projects/the-message/silent-proof-v001/shot_transitions.json` are all **`cut`**.
- `continue` arms H3 Context only when Hub `chain_active` is true, and inflates raw length by 22 so delivered duration matches the request.
- Do not rely on “any approved predecessor continues automatically.”

## Out of scope until later

- F6 full CPU preflight gate
- F7 AV unmute path
- F8 finishing muted labs
- Multi-shot Act assembly / creative qualification

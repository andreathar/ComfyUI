"""Master Movie Studio frame / transition planning (CPU-pure)."""

CONTEXT_LENGTH = 22


def align_h3_frames(count):
    count = max(5, int(count))
    return int(count + (5 - count % 17) % 17)


def plan_frames(duration_s, fps, transition="cut", chain_active=False, context_length=CONTEXT_LENGTH):
    """Return raw sampler length, delivered length, and head trim.

    Continue only when transition is continue *and* an approved Hub tail exists.
    Otherwise treat as a cut so a first clip never pays for unused overlap.
    """
    fps_f = float(fps)
    requested = max(5, round(float(duration_s) * fps_f))
    continuing = str(transition).strip().lower() == "continue" and bool(chain_active)
    ctx = int(context_length)
    if continuing:
        raw = align_h3_frames(requested + ctx)
        trim = ctx
        delivered = raw - trim
    else:
        raw = align_h3_frames(requested)
        trim = 0
        delivered = raw
    return {
        "raw_frames": raw,
        "delivered_frames": delivered,
        "trim_frames": trim,
        "continuing": continuing,
        "fps": fps_f,
        "delivered_s": delivered / fps_f,
        "raw_s": raw / fps_f,
    }


def format_summary(project_name, shot_tag, width, height, plan, steps, shift_video, shift_audio, transition="cut"):
    mode = "continue" if plan["continuing"] else "cut"
    return (
        f"Project: {project_name} · Shot: {shot_tag} · Transition: {transition} ({mode})\n"
        f"Canvas: {width}×{height} (16:9 multiple-of-32) · "
        f"raw {plan['raw_frames']}f / delivered {plan['delivered_frames']}f "
        f"({plan['delivered_s']:.3f}s @ {plan['fps']:g} fps)"
        + (f" · trim {plan['trim_frames']}" if plan["trim_frames"] else "")
        + "\n"
        f"Schedule: {int(steps)} steps · sa_solver / beta · "
        f"shifts {float(shift_video):g}/{float(shift_audio):g} · CK int8 attention"
    )

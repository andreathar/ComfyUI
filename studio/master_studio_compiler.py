"""Master Movie Studio frame / transition planning (CPU-pure)."""

SETTINGS_REPORT_CODE = '''import json
summary = json.dumps({'schema': 'workflow-monitor.runtime.v1', 'kind': 'settings', 'summary': summary,
                     'values': {'width': int(width), 'height': int(height), 'raw_frames': int(raw),
                                'delivered_frames': int(delivered), 'fps': int(round(fps_f)), 'steps': int(steps),
                                'shift_video': float(shift_video), 'shift_audio': float(shift_audio),
                                'transition': mode, 'continuing': bool(continuing)}}, ensure_ascii=False, indent=2)
'''


def with_runtime_report(code):
    return code.replace('outputs[:] =', SETTINGS_REPORT_CODE + '\noutputs[:] =', 1)

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

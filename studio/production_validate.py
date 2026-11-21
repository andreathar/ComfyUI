#!/usr/bin/env python3
"""Validate a production document: JSON Schema plus the cross-reference rules in production-rules.md."""

import json
from pathlib import Path
import sys

import jsonschema

SPEC = Path(__file__).resolve().parent / "specs/production"
SCHEMA = SPEC / "production.schema.json"


def check(doc):
    """Return a list of human-readable problems; empty means valid."""
    schema = json.loads(SCHEMA.read_text())
    problems = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
                for e in sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))]
    if problems:
        return problems  # cross-checks assume a schema-valid shape

    code = doc["project"]["code"]
    text_len = len(doc["project"]["source_text"])
    banks = {kind: {e["id"] for e in doc.get(kind, [])} for kind in ("characters", "locations", "props", "motions", "voices")}
    everything = set().union(*banks.values())
    scenes = {s["id"]: s for s in doc["scenes"]}

    def need(ref, kind, where):
        if ref not in banks[kind]:
            problems.append(f"{where}: {ref} is not in {kind}")

    def span(ref, where):
        if ref["end"] < ref["start"] or ref["end"] > text_len:
            problems.append(f"{where}: script_ref {ref['start']}-{ref['end']} is outside source_text (length {text_len})")

    for kind, entities in (("characters", doc["characters"]), ("locations", doc["locations"]),
                           ("props", doc.get("props", [])), ("motions", doc.get("motions", [])),
                           ("voices", doc.get("voices", []))):
        ids = [e["id"] for e in entities]
        for dup in {i for i in ids if ids.count(i) > 1}:
            problems.append(f"{kind}: duplicate id {dup}")
        for i in ids:
            if not i.startswith(code + "-"):
                problems.append(f"{kind}: {i} does not start with project code {code}-")
    kind_of = {"characters": "CHR", "locations": "LOC", "props": "PRP", "motions": "MOT", "voices": "VOX"}
    for kind, tag in kind_of.items():
        for i in banks[kind]:
            if f"-{tag}-" not in i:
                problems.append(f"{kind}: {i} must contain -{tag}-")

    for c in doc["characters"]:
        voice = c.get("voice")
        if voice and "-VOX-" not in voice:
            problems.append(f"{c['id']}: voice {voice} must be a VOX id")
        if voice:
            need(voice, "voices", c['id'])

    numbers = [s["number"] for s in doc["scenes"]]
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append(f"scenes: numbers must be consecutive from 1, got {numbers}")
    for s in doc["scenes"]:
        where = s["id"]
        if s["id"] != f"{code}_S{s['number']:03d}":
            problems.append(f"{where}: id does not match project code and number {s['number']}")
        need(s["location"], "locations", where)
        for c in s["characters"]:
            need(c, "characters", where)
        for p in s.get("props", []):
            need(p, "props", where)
        if s.get("lighting") and s["lighting"]["time_of_day"] not in (s["time"], "interior-artificial"):
            problems.append(f"{where}: lighting time_of_day {s['lighting']['time_of_day']} contradicts scene time {s['time']}")
        span(s["script_ref"], where)

    per_scene = {}
    seen = set()
    for sh in doc["shots"]:
        where = sh["id"]
        if sh["id"] in seen:
            problems.append(f"{where}: duplicate shot id")
        seen.add(sh["id"])
        scene = scenes.get(sh["scene"])
        if scene is None:
            problems.append(f"{where}: scene {sh['scene']} does not exist")
            continue
        if not sh["id"].startswith(sh["scene"] + "_SH"):
            problems.append(f"{where}: id does not belong to scene {sh['scene']}")
        per_scene.setdefault(sh["scene"], []).append(int(sh["id"][-2:]))
        need(sh["location"], "locations", where)
        if sh["location"] != scene["location"]:
            problems.append(f"{where}: location {sh['location']} differs from scene location {scene['location']}")
        for c in sh["characters"]:
            need(c, "characters", where)
            if c not in scene["characters"]:
                problems.append(f"{where}: {c} is not in the cast of {sh['scene']}")
        for p in sh.get("props", []):
            need(p, "props", where)
        if sh.get("motion"):
            need(sh["motion"], "motions", where)
        if sh.get("complexity") == "complex-motion" and not sh.get("motion"):
            problems.append(f"{where}: complex-motion needs a motion (MOT) entity")
        speakers = {c["id"]: c for c in doc["characters"]}
        for d in sh.get("dialogue", []):
            if d["character"] not in sh["characters"]:
                problems.append(f"{where}: dialogue by {d['character']}, who is not in the shot")
            elif d["character"] in speakers and not speakers[d["character"]].get("voice"):
                problems.append(f"{where}: {d['character']} speaks but has no voice (VOX) entity")
        for ref in sh.get("refs", []):
            owner = ref.split("/")[2]
            if owner not in everything:
                problems.append(f"{where}: ref {ref} belongs to unknown entity {owner}")
        span(sh["script_ref"], where)
    for scene_id, nums in per_scene.items():
        if sorted(nums) != list(range(1, len(nums) + 1)):
            problems.append(f"{scene_id}: shot numbers must be consecutive from 1, got {sorted(nums)}")
    for scene_id in scenes:
        if scene_id not in per_scene:
            problems.append(f"{scene_id}: scene has no shots")
    return problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: production_validate.py <production.json>", file=sys.stderr)
        return 2
    problems = check(json.loads(Path(argv[0]).read_text()))
    for p in problems:
        print(p)
    print("valid" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

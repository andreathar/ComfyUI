#!/usr/bin/env python3
"""Turn a dictated script into a validated production document (model call + validate/fix loop)."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

import production_validate as pv

PROMPT = pv.SPEC / "generate-prompt.md"
RULES = pv.SPEC / "production-rules.md"
MAX_ROUNDS = 3
DEFAULT_MODEL = "claude-sonnet-5-5"


class GenerateError(Exception):
    pass


def system_prompt():
    return PROMPT.read_text().split("\n---\n", 1)[1].strip()


def user_message(dictation, style_bible="", existing=""):
    return "\n".join([
        f"<rules>\n{RULES.read_text()}\n</rules>",
        f"<schema>\n{pv.SCHEMA.read_text()}\n</schema>",
        f"<style_bible>\n{style_bible}\n</style_bible>",
        f"<existing>\n{existing}\n</existing>",
        f"<dictation>\n{dictation}\n</dictation>",
    ])


def extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise GenerateError("model reply contains no JSON object")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise GenerateError(f"model reply is not valid JSON: {error}") from error


def claude_cli(system, messages, model):
    """Run on the Claude subscription through the claude CLI (no API key)."""
    transcript = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
    result = subprocess.run(["claude", "-p", "--model", model, "--append-system-prompt", system],
                            input=transcript, capture_output=True, text=True, timeout=900)
    if result.returncode:
        raise GenerateError(f"claude CLI failed: {result.stderr.strip()[:500]}")
    return result.stdout


def anthropic_api(system, messages, model):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise GenerateError("ANTHROPIC_API_KEY is not set")
    body = json.dumps({"model": model, "max_tokens": 16000, "system": system, "messages": messages}).encode()
    request = urllib.request.Request("https://api.anthropic.com/v1/messages", body, {
        "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return "".join(b.get("text", "") for b in json.load(response)["content"])
    except urllib.error.HTTPError as error:
        raise GenerateError(f"Anthropic API error {error.code}: {error.read().decode()[:500]}") from error


BACKENDS = {"claude-cli": claude_cli, "api": anthropic_api}


def generate(dictation, backend, model=DEFAULT_MODEL, style_bible="", existing=""):
    """Return {"document": ...} when valid, or {"questions": [...]} / {"problems": [...]} otherwise."""
    system = system_prompt()
    messages = [{"role": "user", "content": user_message(dictation, style_bible, existing)}]
    problems = []
    for _ in range(MAX_ROUNDS + 1):
        reply = backend(system, messages, model)
        try:
            doc = extract_json(reply)
        except GenerateError as error:
            problems = [str(error)]
        else:
            if "schema_version" not in doc and doc.get("questions"):
                return {"questions": doc["questions"]}
            problems = pv.check(doc)
            if not problems:
                if doc["project"]["source_text"] != dictation:
                    problems = ["project.source_text must be the dictation, unchanged"]
                else:
                    return {"document": doc}
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": "These problems remain. Fix only these; change nothing else. "
                      "Reply with the full corrected JSON only.\n" + "\n".join(problems)}]
    return {"problems": problems}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dictation", type=Path, help="Text file with the dictated script")
    parser.add_argument("--out", type=Path, required=True, help="Where to write the production JSON")
    parser.add_argument("--backend", choices=sorted(BACKENDS), default="claude-cli")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--style", type=Path, help="Project style bible / settings text file")
    parser.add_argument("--existing", type=Path, help="Current production JSON to revise")
    args = parser.parse_args(argv)
    if args.out.exists():
        print(f"Refusing to overwrite {args.out}", file=sys.stderr)
        return 2
    result = generate(args.dictation.read_text(), BACKENDS[args.backend], args.model,
                      args.style.read_text() if args.style else "",
                      args.existing.read_text() if args.existing else "")
    if "document" in result:
        args.out.write_text(json.dumps(result["document"], indent=2) + "\n")
        print(f"valid: wrote {args.out}")
        return 0
    key = "questions" if "questions" in result else "problems"
    print(f"Not written. Model {key}:")
    for item in result[key]:
        print(f"- {item if isinstance(item, str) else json.dumps(item)}")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GenerateError, OSError) as error:
        print(f"Generate error: {error}", file=sys.stderr)
        raise SystemExit(1)

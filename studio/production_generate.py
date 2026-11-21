#!/usr/bin/env python3
"""Turn a dictated script into a validated production document (model call + validate/fix loop)."""

import argparse
import json
from pathlib import Path
from functools import partial
import subprocess
import sys

if __package__:
    from . import production_validate as pv
    from .asset_vision import MODEL as DEFAULT_MODEL, MODEL_HOME, check_comfyui, http, local_server, owns_listener
else:
    import production_validate as pv
    from asset_vision import MODEL as DEFAULT_MODEL, MODEL_HOME, check_comfyui, http, local_server, owns_listener

PROMPT = pv.SPEC / "generate-prompt.md"
RULES = pv.SPEC / "production-rules.md"
MAX_ROUNDS = 3
DEFAULT_ENGINE = Path.home() / '.hermes/tools/llamacpp-cuda-12144-linux-x64/llama-server'


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


def local_completion(port, key, pid, system, messages, model):
    check_comfyui()
    if not owns_listener(pid, port):
        raise GenerateError('The isolated model no longer owns its listener')
    reply = http(port, '/v1/chat/completions', key, {
        'model': model, 'messages': [{'role': 'system', 'content': system}, *messages],
        'response_format': {'type': 'json_object'}, 'temperature': 0, 'max_tokens': 4096,
        'chat_template_kwargs': {'enable_thinking': False},
    }, timeout=1800)
    if reply.get('model') != model:
        raise GenerateError('Unexpected local model')
    try:
        choice = reply['choices'][0]
        content = choice['message']['content']
        if choice['finish_reason'] != 'stop' or not isinstance(content, str) or not content.strip():
            raise GenerateError('Incomplete local reply; use a smaller script or revision')
    except (KeyError, IndexError, TypeError) as error:
        raise GenerateError('Invalid local completion response') from error
    return content


def generate(dictation, backend, model=DEFAULT_MODEL, style_bible="", existing="", revised_script=None):
    """Return {"document": ...} when valid, or {"questions": [...]} / {"problems": [...]} otherwise."""
    source = dictation
    if existing:
        try:
            source = json.loads(existing)["project"]["source_text"]
            if not isinstance(source, str):
                raise TypeError
        except (ValueError, KeyError, TypeError) as error:
            raise GenerateError("Existing production has no valid project.source_text") from error
    if revised_script is not None:
        if not existing:
            raise GenerateError("A revised script requires an existing production")
        source = revised_script
    system = system_prompt()
    message = user_message(dictation, style_bible, existing)
    if revised_script is not None:
        message += f"\n<revised_script>\n{revised_script}\n</revised_script>"
    messages = [{"role": "user", "content": message}]
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
                if doc["project"]["source_text"] != source:
                    problems = ["project.source_text must match the authorized full script, unchanged"]
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
    parser.add_argument('--engine', type=Path, default=DEFAULT_ENGINE, help='Hermes-installed CUDA llama-server executable')
    parser.add_argument('--log', type=Path, required=True, help='New local llama-server log path')
    parser.add_argument("--style", type=Path, help="Project style bible / settings text file")
    parser.add_argument("--existing", type=Path, help="Current production JSON to revise")
    parser.add_argument("--revised-script", type=Path, help="Complete replacement source text for a revision")
    args = parser.parse_args(argv)
    if args.revised_script and not args.existing:
        parser.error("--revised-script requires --existing")
    if args.out.exists():
        print(f"Refusing to overwrite {args.out}", file=sys.stderr)
        return 2
    dictation = args.dictation.read_text()
    style = args.style.read_text() if args.style else ''
    existing = args.existing.read_text() if args.existing else ''
    revised = args.revised_script.read_text() if args.revised_script else None
    with args.log.open('x') as log, local_server(args.engine, MODEL_HOME / f'{DEFAULT_MODEL}.gguf', None, log) as (port, key, pid):
        result = generate(dictation, partial(local_completion, port, key, pid),
                          style_bible=style, existing=existing, revised_script=revised)
    if "document" in result:
        with args.out.open('x') as stream:
            stream.write(json.dumps(result['document'], indent=2) + '\n')
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
    except (GenerateError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Generate error: {error}", file=sys.stderr)
        raise SystemExit(1)

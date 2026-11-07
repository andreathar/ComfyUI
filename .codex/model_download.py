#!/usr/bin/env python3
"""Download explicitly selected model sets into native ComfyUI folders."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import urllib.parse
import urllib.request


PROJECT = Path(__file__).resolve().parent.parent
CATALOGUE = Path(__file__).with_name("models.json")
CHUNK = 4 * 1024 * 1024
HEADROOM = 5 * 1024 ** 3
LEGACY_FOLDERS = {"diffusion_models": "unet", "text_encoders": "clip"}


def storage_root(catalogue):
    mount = Path(catalogue["storage"]["mount"]).resolve()
    root = (PROJECT / catalogue["storage"]["root"]).resolve()
    if not mount.is_mount() or not root.is_relative_to(mount):
        raise ValueError(f"Required data drive is not mounted at {mount}, or model root is outside it")
    existing = root
    while not existing.exists():
        existing = existing.parent
    if existing.stat().st_dev != mount.stat().st_dev:
        raise ValueError(f"Model root is not on the required data drive: {root}")
    return root


def model_path(root, model):
    folder, name = model["folder"], model["filename"]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", folder) or not name or name in (".", "..") or Path(name).name != name:
        raise ValueError("Model folder and filename must be single safe path components")
    target = root / folder / name
    # ComfyUI also reads these older folder names; reuse a file already there.
    legacy = root / LEGACY_FOLDERS.get(folder, folder) / name
    if not target.exists() and legacy.exists():
        target = legacy
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Model path escapes storage or is a symlink: {target}")
    return target


def verified(path, model):
    if not path.is_file() or path.stat().st_size != model["bytes"]:
        return False
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest() == model["sha256"]


def publish(partial, target, model):
    if not verified(partial, model):
        raise ValueError(f"Size or SHA-256 mismatch; incomplete file retained: {partial}")
    os.link(partial, target)
    partial.unlink()


def download(root, model):
    url = urllib.parse.urlsplit(model["url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("Model source must be a public HTTPS URL")
    if not isinstance(model["bytes"], int) or model["bytes"] <= 0 or not re.fullmatch(r"[0-9a-f]{64}", model["sha256"]):
        raise ValueError("Model metadata requires a positive byte size and SHA-256 hash")
    target = model_path(root, model)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(target.name + ".download.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(f"Another download owns {target.name}; retry after it finishes") from error
        if target.exists():
            if verified(target, model):
                return "verified"
            raise ValueError(f"Existing file differs from the catalogue; preserved without overwrite: {target}")
        partial = target.with_name(target.name + ".part")
        if partial.is_symlink() or (partial.exists() and not partial.is_file()):
            raise ValueError(f"Partial file must be a regular file: {partial}")
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > model["bytes"]:
            raise ValueError(f"Partial file exceeds expected size; inspect {partial}")
        if offset == model["bytes"]:
            publish(partial, target, model)
            return "verified"
        needed = model["bytes"] - offset + HEADROOM
        if shutil.disk_usage(target.parent).free < needed:
            raise OSError(f"Not enough free space for {target.name} plus 5 GiB headroom")
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        request = urllib.request.Request(model["url"], headers=headers)
        with urllib.request.urlopen(request, timeout=45) as response:
            if response.status == 206:
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                if not match or int(match[1]) != offset or int(match[3]) != model["bytes"] or not offset <= int(match[2]) < model["bytes"]:
                    raise ValueError("Server returned an invalid resume range; partial file preserved")
            elif response.status == 200:
                offset = 0
            else:
                raise ValueError(f"Unexpected download response: HTTP {response.status}")
            received, last_report = offset, offset
            with partial.open("ab" if offset else "wb") as output:
                while block := response.read(CHUNK):
                    if received + len(block) > model["bytes"]:
                        raise ValueError("Download exceeds the declared model size; not published")
                    output.write(block)
                    received += len(block)
                    if received - last_report >= 256 * 1024 ** 2:
                        print(f"  {received / 1024 ** 3:.2f} / {model['bytes'] / 1024 ** 3:.2f} GiB", flush=True)
                        last_report = received
                output.flush()
                os.fsync(output.fileno())
        publish(partial, target, model)
        return "resumed" if offset else "downloaded"


def hugging_face_entry(url, folder):
    match = re.fullmatch(r"https://huggingface\.co/([\w.-]+/[\w.-]+)/(?:resolve|blob)/([^/]+)/(.+)", url)
    if not match:
        raise ValueError("Use a https://huggingface.co/<owner>/<repo>/resolve/<revision>/<path> URL")
    repo, revision, path = match.groups()
    api = f"https://huggingface.co/api/models/{repo}"
    with urllib.request.urlopen(f"{api}/revision/{revision}", timeout=45) as response:
        info = json.load(response)
    sha = info["sha"]
    with urllib.request.urlopen(f"{api}/tree/{sha}/{path.rpartition('/')[0]}", timeout=45) as response:
        file = next((f for f in json.load(response) if f["path"] == path), None)
    if file is None or "lfs" not in file:
        raise ValueError(f"{path} is not a large file at revision {sha}")
    licenses = [tag.removeprefix("license:") for tag in info.get("tags", []) if tag.startswith("license:")]
    return {
        "folder": folder, "filename": path.rpartition("/")[2],
        "url": f"https://huggingface.co/{repo}/resolve/{sha}/{path}",
        "bytes": file["lfs"]["size"], "sha256": file["lfs"]["oid"],
        "license": licenses[0] if licenses else "unknown",
    }


def main(argv=None):
    catalogue = json.loads(CATALOGUE.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "plan", "download", "verify", "add"))
    parser.add_argument("profiles", nargs="*", help="One or more catalogue profiles")
    parser.add_argument("--key", help="add: catalogue key for the new model")
    parser.add_argument("--folder", help="add: ComfyUI model folder, such as vae or loras")
    parser.add_argument("--url", help="add: Hugging Face file URL; the revision is pinned")
    args = parser.parse_args(argv)
    if args.command == "add":
        if len(args.profiles) != 1 or not (args.key and args.folder and args.url):
            parser.error("add needs one profile plus --key, --folder and --url")
        if args.key in catalogue["models"]:
            parser.error(f"Model key already exists: {args.key}")
        entry = hugging_face_entry(args.url, args.folder)
        model_path(PROJECT / catalogue["storage"]["root"], entry)
        catalogue["models"][args.key] = entry
        catalogue["profiles"].setdefault(args.profiles[0], []).append(args.key)
        CATALOGUE.write_text(json.dumps(catalogue, indent=2) + "\n")
        print(json.dumps({args.key: entry}, indent=2))
        return 0
    if args.command == "list":
        for name, ids in catalogue["profiles"].items():
            size = sum(catalogue["models"][key]["bytes"] for key in ids)
            print(f"{name}: {len(ids)} file(s), {size / 1024 ** 3:.2f} GiB")
        return 0
    if not args.profiles:
        parser.error("Select a profile; use 'list' to see available model sets")
    unknown = set(args.profiles) - catalogue["profiles"].keys()
    if unknown:
        parser.error(f"Unknown profile(s): {', '.join(sorted(unknown))}")
    root = storage_root(catalogue)
    print(f"Storage: {root} (required drive: {catalogue['storage']['mount']})")
    keys = dict.fromkeys(key for profile in args.profiles for key in catalogue["profiles"][profile])
    failures = 0
    for key in keys:
        model = catalogue["models"][key]
        target = model_path(root, model)
        if args.command == "plan":
            state = "present; verify before use" if target.exists() else "missing"
            print(f"{key}: {state}; {model['bytes'] / 1024 ** 3:.2f} GiB; license: {model.get('license', 'unknown')} -> {target}")
        elif args.command == "verify":
            valid = verified(target, model)
            failures += not valid
            print(f"{key}: {'verified' if valid else 'missing or invalid'} -> {target}")
        else:
            print(f"{key}: checking {target}", flush=True)
            print(f"{key}: {download(root, model)}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"Model download error: {error}", file=sys.stderr)
        raise SystemExit(1)

"""Connect the installed Python Package Visualizer 3.3.2 to this checkout."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = "fabervi.python-package-visualizer-community-3.3.2-universal"
ORIGINAL_SHA256 = "135fa17874d7e688f27a253d0c03eca1beab51860284e5cc10f829d455010a91"
HOOK = "let c=new On(n,e,t,s,r,i,o,a);c.registerAll();"
PATCH = ('let c=new On(n,e,t,s,r,i,o,a);'
         'require("./comfyui-uv-bridge.cjs")(c,H,Rr.parse);c.registerAll();')


def write(path, data):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def install(extension, root, uv):
    dist = extension / "dist"
    bundle = dist / "extension.js"
    original = dist / "extension.js.comfyui-original"
    source = bundle.read_bytes()
    if b'require("./comfyui-uv-bridge.cjs")' in source and original.is_file():
        source = original.read_bytes()
    if hashlib.sha256(source).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("Unexpected Visualizer bundle. Review the installed version before patching.")
    if source.count(HOOK.encode()) != 1:
        raise ValueError("Could not find the Visualizer activation hook.")

    if not original.exists():
        write(original, source)
    write(dist / "comfyui-uv-bridge.cjs", (ROOT / ".codex/package_visualizer.cjs").read_bytes())
    write(dist / "comfyui-uv.json", json.dumps({"root": str(root), "uv": str(uv)}).encode())
    write(bundle, source.replace(HOOK.encode(), PATCH.encode(), 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extension", type=Path,
                        default=Path.home() / ".antigravity-ide/extensions" / EXTENSION)
    args = parser.parse_args()
    uv = shutil.which("uv")
    if not uv:
        parser.error("uv is missing from the current PATH")
    try:
        install(args.extension, ROOT, Path(uv).absolute())
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    parser.exit(0, "Installed the ComfyUI uv bridge for Python Package Visualizer.\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
apply_patch.py - Read and write Bambu Studio 3MF project settings.

Usage:
  python apply_patch.py read <3mf_path>
      Prints current project_settings.config as JSON to stdout.

  python apply_patch.py write <3mf_path> <patch_json_path>
      Applies patch (delta only) and writes <name>_optimized.3mf
      to the same directory. Never modifies the original file.
"""

import sys
import json
import zipfile
import shutil
import os
import tempfile
from pathlib import Path

CONFIG_PATH = "Metadata/project_settings.config"


def read_3mf(path: str) -> dict:
    """Read project_settings.config from a Bambu 3MF. Returns parsed dict."""
    if not Path(path).exists():
        raise FileNotFoundError(f"File not found: {path}")
    with zipfile.ZipFile(path, 'r') as z:
        if CONFIG_PATH not in z.namelist():
            raise ValueError(f"project_settings.config not found in {path}")
        raw = z.read(CONFIG_PATH).decode('utf-8')
    return json.loads(raw)


def write_3mf(src_path: str, patch: dict) -> str:
    """Apply patch delta to 3MF. Writes <name>_optimized.3mf. Returns output path."""
    src = Path(src_path)
    dst = src.parent / f"{src.stem}_optimized{src.suffix}"

    fd, tmp_path = tempfile.mkstemp(suffix='.3mf')
    os.close(fd)

    try:
        with zipfile.ZipFile(src_path, 'r') as z_in:
            with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as z_out:
                for item in z_in.infolist():
                    if item.filename == CONFIG_PATH:
                        current = json.loads(z_in.read(item.filename).decode('utf-8'))
                        current.update(patch)
                        z_out.writestr(item, json.dumps(current, indent=4))
                    else:
                        z_out.writestr(item, z_in.read(item.filename))
        shutil.move(tmp_path, str(dst))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return str(dst)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    path = sys.argv[2]

    if mode == 'read':
        settings = read_3mf(path)
        print(json.dumps(settings, indent=2))

    elif mode == 'write':
        if len(sys.argv) < 4:
            print("Error: write mode requires <patch_json_path>", file=sys.stderr)
            sys.exit(1)
        patch_path = sys.argv[3]
        with open(patch_path, 'r') as f:
            patch = json.load(f)
        out = write_3mf(path, patch)
        print(f"Written: {out}")

    else:
        print(f"Error: unknown mode '{mode}'. Use 'read' or 'write'.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

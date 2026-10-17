"""
clean.py - remove build artefacts, portably.

The Makefile used `rm -rf ... **/__pycache__` and `find ... -exec`, neither of
which exists on a stock Windows shell, so `make clean` was Linux-only. This does
the same job in Python and prints what it removed, so a typo'd path is visible
rather than silently absent.

Run:
    python src/scripts/clean.py
    python src/scripts/clean.py --dry-run
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Kept out: anything under .git, any model weights, and the datasets themselves.
PROTECTED = {".git", "models", "node_modules", ".venv", "venv", "data", "results"}
PROTECTED_SUFFIXES = {".gguf", ".safetensors", ".bin"}

TARGET_DIRS = {".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove build artefacts.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    removed_dirs = 0
    removed_files = 0
    freed = 0

    for path in sorted(ROOT.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        rel = path.relative_to(ROOT)
        top = rel.parts[0]

        if top in PROTECTED or ".git" in rel.parts:
            continue

        try:
            if path.is_dir() and path.name in TARGET_DIRS:
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                if not args.dry_run:
                    shutil.rmtree(path, ignore_errors=True)
                freed += size
                removed_dirs += 1
            elif path.is_file() and path.suffix == ".pyc":
                size = path.stat().st_size
                if not args.dry_run:
                    path.unlink()
                freed += size
                removed_files += 1
        except OSError:
            continue

    verb = "would remove" if args.dry_run else "removed"
    mb = freed / 1e6
    print(f"  {verb} {removed_dirs} director(ies) and "
          f"{removed_files} file(s) — {mb:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
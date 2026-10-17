"""
help_text.py - `make help`, without a shell.

This used to be a block of `@echo` lines in the Makefile. Two of those lines are
unsafe on Windows:

  * `@echo` with nothing after it prints "ECHO is off." and exits non-zero on cmd;
  * text containing `<...>` is read as INPUT REDIRECTION, so the innocuous
    "(override with: make PYTHON=python <target>)" became a redirect from a file
    named "target" and make died with "The system cannot find the file specified."

Neither failure points at its cause. Printing the text from Python removes the
whole class of problem: no shell, no quoting, no redirection, and the em dashes
and box characters survive.

Run:
    python src/scripts/help_text.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TARGETS = [
    ("make run", "spin up in Docker (offline; add LLM_BASE_URL for live)"),
    ("make build", "build the image without running"),
    ("make verify", "offline verification, no Docker, no model"),
    ("make verify-test", "held-out seal pre-flight only"),
    ("make test", "every automated check (13 suites)"),
    ("make shell", "container with the project mounted"),
    ("make clean", "remove build artefacts"),
]


def interpreter() -> str:
    """The interpreter Make will use, by the same probe the Makefile performs."""
    for cand in ("python3", "python", "py"):
        if not shutil.which(cand):
            continue
        try:
            r = subprocess.run([cand, "--version"], capture_output=True,
                               text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0 and "not found" not in (r.stdout + r.stderr).lower():
            return cand
    return "python3"


def main() -> int:
    w = max(len(t) for t, _ in TARGETS)
    print("\n  Swiss Reality Check \u2014 Hack Apertus, Track 1B")
    print("\n  available targets:")
    for name, desc in TARGETS:
        print(f"    {name:<{w}}  {desc}")

    py = interpreter()
    print(f"\n  interpreter: {py}")
    print("  override it with:  make PYTHON=<name> <target>")

    if not (ROOT / "src" / "run.py").is_file():
        print("\n  WARNING: run this from the repository root.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
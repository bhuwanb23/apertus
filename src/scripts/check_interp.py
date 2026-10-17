"""
check_interp.py - fail with an actionable message instead of "not found".

`make test` died with "The system cannot find the path specified." on Windows,
with nothing pointing at the cause. The Makefile's default interpreter was
`python3`, and on Windows `python3` is a Microsoft Store *alias stub*: it is on
PATH, it is not a Python, and when invoked it tries to open the Store and exits
9009. The stub swallows the real problem behind a message about a missing path.

Every target that needs an interpreter now depends on this, so the one case a
contributor is likely to hit produces the one message that fixes it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

# Ordered by how likely each is to be the right answer. `py` is the Windows
# launcher and is a genuine interpreter, unlike `python3`.
CANDIDATES = ["python3", "python", "py"]


def works(exe: str) -> bool:
    if not shutil.which(exe):
        return False
    try:
        r = subprocess.run([exe, "--version"], capture_output=True,
                           text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and "not found" not in (r.stdout + r.stderr).lower()


def main() -> int:
    if works(sys.executable):
        return 0

    good = [c for c in CANDIDATES if works(c)]
    here = sys.executable
    print()
    print("  The interpreter this target was asked to use does not work.")
    print(f"    tried : {here}")
    print(f"    detail: {(subprocess.run([here, '--version'], capture_output=True, text=True).stderr or '').strip()[:200]}")
    print()
    if good:
        print("  A working interpreter IS available. Re-run with an override:")
        print()
        print(f"    make PYTHON={good[0]} <target>")
    else:
        print("  No working Python found. Install Python 3.9+ and ensure that")
        print("  either `python3` or `python` resolves to it.")
    print()
    print("  Note: on Windows, `python3` is usually a Microsoft Store alias stub.")
    print("  It exists on PATH, is not a Python, and fails with a message about")
    print("  a missing path rather than about the interpreter. That is the usual")
    print("  cause of 'The system cannot find the path specified.' from make.")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
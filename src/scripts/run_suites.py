"""
run_suites.py - the single entry point for the project's automated checks.

This existed as a shell `for` loop inside the Makefile. Three problems with that,
all of which bit during the n=90 rescale:

1. `set -e` plus `exit 1` on the first failure meant a suite failure was only
   visible as a non-zero exit code - you never learned WHICH suite failed or why.
2. Output was `>/dev/null 2>&1`, so a failing suite printed nothing at all.
3. The loop needs `sh`. GNU Make on Windows (GnuWin32) has no reliable `sh`, so
   `make test` died with "The system cannot find the path specified." on any
   contributor machine that was not using Git Bash.

Here every suite runs and every failure is printed in full. The exit code is
non-zero if any suite failed, so this is still correct as a CI gate.

Run:
    python src/scripts/run_suites.py
    python src/scripts/run_suites.py --only eval/test_judge.py
    python src/scripts/run_suites.py --list
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SUITES: list[str] = [
    "src/fix/test_error_taxonomy.py",
    "src/fix/test_select_target.py",
    "src/fix/test_improvement.py",
    "src/fix/test_validation.py",
    "src/fix/test_phase4.py",
    "src/fix/test_statistics.py",
    "src/fix/test_charts.py",
    "src/fix/test_narrative.py",
    "src/eval/test_knowledge_scoring.py",
    "src/eval/test_judge.py",
    "src/eval/test_dialect.py",
    "src/eval/test_baseline_report.py",
    "src/eval/smoke_test.py",
]

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def _colour(s: str, code: str) -> str:
    """Colour only when stdout is a terminal, so CI logs stay readable."""
    return f"{code}{s}{RESET}" if sys.stdout.isatty() else s


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the project's automated checks.")
    ap.add_argument("--only", action="append", default=None,
                    help="run just these suites (repeatable)")
    ap.add_argument("--list", action="store_true", help="list suites and exit")
    ap.add_argument("--quiet", action="store_true", help="summary only")
    args = ap.parse_args()

    if args.list:
        for s in SUITES:
            print(f"  {s}")
        return 0

    suites = args.only or SUITES
    missing = [s for s in suites if not (ROOT / s).is_file()]
    if missing:
        print(f"  no such suite: {', '.join(missing)}", file=sys.stderr)
        return 2

    print(_colour("=" * 72, DIM))
    print(f"  SWISS REALITY CHECK — {len(suites)} suites")
    print(_colour("=" * 72, DIM))

    failed: list[tuple[str, str, float]] = []
    t_all = time.time()

    for s in suites:
        t0 = time.time()
        p = subprocess.run([sys.executable, s], cwd=ROOT,
                           capture_output=True, text=True)
        dt = time.time() - t0
        ok = p.returncode == 0
        print(f"  {_colour('PASS', GREEN) if ok else _colour('FAIL', RED)}  "
              f"{s:<44} {dt:6.1f}s")
        if not ok:
            failed.append((s, p.stdout + p.stderr, dt))

    print()
    passed = len(suites) - len(failed)
    total_s = time.time() - t_all
    if not failed:
        print(_colour(f"  {passed}/{len(suites)} suites passed  ({total_s:.1f}s)", GREEN))
        return 0

    print(_colour(f"  {passed}/{len(suites)} suites passed, "
                  f"{len(failed)} FAILED  ({total_s:.1f}s)", RED))
    for s, out, dt in failed:
        print()
        print(_colour("=" * 72, RED))
        print(f"  FAILED: {s}  ({dt:.1f}s)", RED)
        print(_colour("=" * 72, RED))
        lines = [l for l in out.splitlines() if l.strip()]
        for l in lines[-60:]:
            print(f"    {l}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
"""
test_dockerfile.py - the image must contain what the code needs to run.

This exists because `make run` was broken in Docker and nothing said so.

Every module in src/ finds the project root by walking up from its own file until
it sees a directory holding BOTH `data/` and `Makefile`:

    ROOT = next(p for p in Path(__file__).resolve().parents
                if (p / "data").is_dir() and (p / "Makefile").is_file())

That pair is the root marker, and it appears in 43 files. The Dockerfile copied
`src` and `data` but not `Makefile`, so inside the container every one of those
modules raised StopIteration and the run died on its first line of work. It went
unnoticed because a bind mount used to bring the Makefile in by accident.

Three ways this has already broken, and the check for each:

  * the root marker is not in the image      -> StopIteration on every module
  * `results/` is not in the image            -> the run reports no arms present
  * compose mounts over a copied directory   -> silently re-creates the first bug

Run:  python src/scripts/test_dockerfile.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FAILURES: list[str] = []
PASSES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    (PASSES if ok else FAILURES).append(label if ok else f"{label} — {detail}")
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f"  ({detail})" if detail and not ok else ""))


def copies(dockerfile: str) -> set[str]:
    """Destination paths the image will contain."""
    out: set[str] = set()
    for m in re.finditer(r"^COPY\s+(.*)$", dockerfile, re.M):
        parts = m.group(1).split()
        if not parts:
            continue
        dest = parts[-1]
        dest = dest.replace("./", "").strip("/")
        if dest in (".", "./"):
            out |= {"."}
            continue
        if parts[0] in (".", "./"):
            out.add(dest)
        else:
            # multiple sources -> dest is a directory, keep its name
            out.add(dest.rsplit("/", 1)[-1])
    return out


def main() -> int:
    print("=" * 72)
    print("  DOCKERFILE — the image must contain what the code needs to run")
    print("=" * 72)

    df_path = ROOT / "Dockerfile"
    check("Dockerfile exists", df_path.is_file())
    if not df_path.is_file():
        return 1
    df = df_path.read_text(encoding="utf-8")

    have = copies(df)

    # ---- 1. the root marker ------------------------------------------------
    check("image contains data/ (root marker part 1)", "data" in have,
          f"copied: {sorted(have)}")
    check("image contains Makefile (root marker part 2)", "Makefile" in have,
          f"copied: {sorted(have)}")
    check("image contains src/ (the harness itself)", "src" in have,
          f"copied: {sorted(have)}")

    # ---- 2. the evidence ----------------------------------------------------
    check("image contains results/ (archived arms + reports)", "results" in have,
          f"copied: {sorted(have)}")
    for f in ("README.md", "technical_report.md", "DATASHEET.md"):
        check(f"image contains {f}", f in have, f"copied: {sorted(have)}")

    # ---- 3. compose must not shadow what the image copied ------------------
    comp_path = ROOT / "docker-compose.yml"
    if comp_path.is_file():
        comp = comp_path.read_text(encoding="utf-8")
        mounts = re.findall(r"^\s*-\s*\"?([^\"'\n]+):([^\"'\n]*)\"?\s*$",
                            comp, re.M)
        shadow = []
        for host, container in mounts:
            c = container.strip()
            for marker in ("Makefile", "data", "src", "results", "docs"):
                if c in (f"/app/{marker}", "/app") and marker not in ("Makefile",):
                    shadow.append(f"{host} -> {c}")
        check("compose does not bind-mount over project content",
              not shadow, f"shadows: {shadow}")

        if "APERTUS_8B_API_KEY" in comp:
            line = next(l for l in comp.splitlines() if "APERTUS_8B_API_KEY" in l)
            # The earlier typo read ${LLM_API_KEY}, which the shell expands to
            # empty, so a live run was sent with no key and failed at request time
            # with an auth error pointing nowhere near the compose file.
            check("APERTUS_8B_API_KEY interpolates from LLM_API_KEY",
                  "LLM_API_KEY" in line, f"line reads: {line.strip()}")

    # ---- 4. no secret can be baked in ---------------------------------------
    check("Dockerfile does not COPY .env", ".env" not in have or
          "src/eval/.env.example" in df,
          "a real .env must never be copied; only .env.example")

    # ---- 5. CMD is the offline entry point ---------------------------------
    check("container CMD runs src/run.py",
          re.search(r'CMD\s+\[\s*"python",\s*"src/run\.py"\s*\]', df) is not None)

    print()
    if FAILURES:
        print(f"  FAILED  {len(FAILURES)} of {len(PASSES) + len(FAILURES)} checks")
        for f in FAILURES:
            print(f"    - {f}")
        return 1
    print(f"  PASSED  all {len(PASSES)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
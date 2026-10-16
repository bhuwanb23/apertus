"""
seal.py - Phase 4.1: make the one-shot rule enforceable instead of aspirational.

THE PROBLEM WITH "DO NOT RE-RUN"

docs/plans/phase_4.md's golden rules say "ONE SHOT ONLY" and "NEVER re-run to
see if you can do better". A rule that lives only in a checklist is broken by
accident, and it is broken at the worst moment: 2am, the day before the
deadline, with a disappointing number on screen. Nothing in a markdown file
stops anyone re-running, and nothing records that they did.

So the constraint is made mechanical, in three parts:

1. A HASH. The sealed file's SHA-256 is recorded before the run. If the file
   changes - even one character of one question - the hash changes and the run
   is refused. This also catches accidental edits during the run itself.

2. AN AUDIT LOG. Every read of the sealed file appends a line: timestamp, git
   hash, who asked, for what. The log is append-only and lives in the results
   tree. Afterwards, anyone can check how many times the test set was opened,
   which is the question a jury will ask.

3. A FREEZE. The git hash of the code that produced the results is recorded
   before the run and checked after. Golden Rule 4 forbids changing the
   improvement after seeing the numbers, which in practice means changing it
   between reading the numbers and re-running. The freeze makes that visible.

WHAT THIS DELIBERATELY DOES NOT DO

It does not try to stop someone reading the file with `cat`. It cannot - no
local mechanism can, and a mechanism that pretended to would be a false
assurance. What it does is make the access *recorded and attributable*, so the
one-shot rule is something the project can demonstrate it kept rather than
something it merely promised.

    python eval/seal.py status          # hash, audit log, freeze state
    python eval/seal.py record          # record the sealed file's hash
    python eval/seal.py freeze          # record HEAD as the frozen code
    python eval/seal.py verify          # re-check hash and freeze
    python eval/seal.py audit           # print every recorded access
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from config import config          # noqa: E402

# ---------------------------------------------------------------- locations
SEALED = ROOT / "data" / "knowledge" / "knowledge_test.json"

# The seal record lives OUTSIDE the results tree, because results/ is gitignored
# and regenerated. A seal that disappears with the results proves nothing.
SEAL_DIR = ROOT / "eval" / "seal"
HASH_PATH = SEAL_DIR / "knowledge_test.sha256"
FREEZE_PATH = SEAL_DIR / "frozen_code.json"
AUDIT_PATH = SEAL_DIR / "access.log"

EXPECTED_N = 36


def git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def git_dirty() -> bool:
    """Uncommitted changes. A dirty tree means the recorded hash does not
    identify the code that produced anything.

    The seal's OWN bookkeeping under eval/seal/ is excluded. Without this,
    writing the freeze record makes the tree dirty by definition, so
    check_freeze() would always report "dirty" immediately after a successful
    freeze and the one-shot could never run. That is a self-reference bug, not
    a safety feature: frozen_code.json is metadata ABOUT the freeze, not code
    the freeze is meant to identify.
    """
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode()
    except Exception:
        return False
    lines = [ln for ln in out.splitlines() if ln.strip()]
    # Drop the seal's own bookkeeping, modified or untracked, e.g.
    # " M eval/seal/frozen_code.json" / "?? eval/seal/frozen_code.json".
    def _is_seal_bookkeeping(line: str) -> bool:
        path = line[2:].strip() if len(line) > 2 else ""
        path = path.strip('"').replace("\\", "/")
        return path.startswith("eval/seal/")
    material = [ln for ln in lines if not _is_seal_bookkeeping(ln)]
    return bool(material)


HASH_SCHEME = "sha256/canonical-lf/v1"


def canonical_bytes(raw: bytes) -> bytes:
    """
    Normalise a file to a form whose bytes do not depend on the platform's line
    ending convention.

    Why this exists: the seal's job is to detect a change to the TEST QUESTIONS.
    Hashing raw bytes made it detect something else as well - whether the
    repository happened to be checked out with `core.autocrlf` on. A judge
    cloning this repo on a different machine, or anyone running the suite after
    an editor rewrote line endings, would fail `verify()` on a file whose content
    was untouched. That is a false alarm, and a seal that cries wolf gets
    disabled.

    So the hash is taken over normalised text: BOM stripped, CRLF and lone CR
    folded to LF. A change to any question, option or answer still changes it.
    A change of line endings alone does not - correctly, because it is not a
    change to the questions.

    The raw byte hash is still recorded alongside it, for forensics, because
    "the bytes on disk differ" is sometimes the thing worth knowing.
    """
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def file_hash(path: Path = SEALED) -> str:
    """Canonical content hash - the value the seal is judged on."""
    return hashlib.sha256(canonical_bytes(path.read_bytes())).hexdigest()


def file_hash_raw(path: Path = SEALED) -> str:
    """Raw byte hash - forensic only, never used to refuse a run."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------ record
def compute() -> dict:
    """Hash the sealed file and describe it, without recording anything.

    Reading the bytes to hash them is not the same as reading the content, and
    this function deliberately extracts no question, no option and no answer.
    """
    if not SEALED.exists():
        return {"exists": False}
    h = file_hash()
    raw = SEALED.read_text(encoding="utf-8")
    data = json.loads(raw)
    return {
        "exists": True,
        "sha256": h,
        "hash_scheme": HASH_SCHEME,
        "sha256_raw": file_hash_raw(),
        "n_questions": len(data),
        "bytes": len(raw.encode("utf-8")),
        # Structure only. The keys are the same in every item, so this leaks
        # nothing about any individual question.
        "item_keys": sorted(data[0].keys()) if data else [],
    }


def record() -> dict:
    SEAL_DIR.mkdir(parents=True, exist_ok=True)
    info = compute()
    if not info["exists"]:
        raise SystemExit(f"sealed file not found: {SEALED}")

    prior = HASH_PATH.read_text(encoding="utf-8").strip() if HASH_PATH.exists() else None
    info["recorded_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    info["git_hash"] = git_hash()
    info["previous_record"] = prior
    HASH_PATH.write_text(
        json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if prior and prior.split()[0] != info["sha256"]:
        # Not fatal here - record() is also how you discover a changed file.
        # But it must be loud: a changed test set invalidates every number
        # produced from the old one.
        print(f"WARNING: hash changed\n  was {prior.split()[0]}\n  now {info['sha256']}",
              file=sys.stderr)
    return info


def verify() -> tuple[bool, list[str]]:
    """
    Is the sealed file the one that was recorded?

    Returns (ok, problems). Callers refuse on `not ok`; printing them is not
    enough, because the whole point is that this cannot be ignored.
    """
    problems: list[str] = []
    if not SEALED.exists():
        return False, [f"sealed file missing: {SEALED}"]
    if not HASH_PATH.exists():
        return False, ["no seal recorded - run: python eval/seal.py record"]

    rec = json.loads(HASH_PATH.read_text(encoding="utf-8"))
    now = file_hash()
    if rec.get("sha256") != now:
        problems.append(
            f"test-set hash changed: recorded {rec.get('sha256', '?')[:16]}..., "
            f"now {now[:16]}...  - every number from the old file is invalid")
    info = compute()
    if info["n_questions"] != EXPECTED_N:
        problems.append(f"expected {EXPECTED_N} questions, found {info['n_questions']}")
    if rec.get("n_questions") is not None and rec["n_questions"] != info["n_questions"]:
        problems.append(f"question count changed: {rec['n_questions']} -> "
                        f"{info['n_questions']}")
    return not problems, problems


# ------------------------------------------------------------------- audit
def log_access(reason: str, actor: str | None = None) -> None:
    """Append one line. Never rewrite the log."""
    SEAL_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pid": os.getpid(),
        "actor": actor or os.environ.get("USER", "unknown"),
        "git_hash": git_hash(),
        "reason": reason,
    }
    with open(AUDIT_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_audit() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    out = []
    for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({"raw": line})
    return out


# ------------------------------------------------------------------ freeze
def freeze(note: str = "") -> dict:
    """
    Record the code version as final.

    Golden Rule 4: no changes to the improvement after seeing test results. In
    practice that means editing between reading the numbers and re-running, so
    the freeze is checked at the START of every run, not the end - a run that
    starts on different code than the freeze produced results on different
    questions.
    """
    SEAL_DIR.mkdir(parents=True, exist_ok=True)
    rec = {
        "frozen_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_hash": git_hash(),
        "tree_dirty": git_dirty(),
        "note": note,
    }
    FREEZE_PATH.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    return rec


def frozen() -> dict | None:
    if not FREEZE_PATH.exists():
        return None
    try:
        return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def check_freeze() -> tuple[bool, list[str]]:
    rec = frozen()
    if rec is None:
        return False, ["improvement not frozen - run: python eval/seal.py freeze"]
    problems = []
    now = git_hash()
    if rec.get("git_hash") != now:
        problems.append(
            f"code moved since the freeze: frozen at {rec.get('git_hash', '?')[:12]}, "
            f"HEAD is now {now[:12]}  - this is Golden Rule 4")
    if rec.get("tree_dirty"):
        problems.append("the tree was dirty at freeze time, so the hash does not "
                        "identify the code that will run")
    if git_dirty():
        problems.append("working tree is dirty now - uncommitted code is not "
                        "reproducible from the recorded hash")
    return not problems, problems


# ------------------------------------------------------------------- report
def status() -> dict:
    ok, problems = verify()
    okf, problemsf = check_freeze()
    audit = read_audit()
    info = compute()
    rec = json.loads(HASH_PATH.read_text(encoding="utf-8")) if HASH_PATH.exists() else None
    return {
        "sealed_file": str(SEALED.relative_to(ROOT)),
        "recorded": rec,
        "current_sha256": info.get("sha256"),
        "verify_ok": ok,
        "verify_problems": problems,
        "freeze": frozen(),
        "freeze_ok": okf,
        "freeze_problems": problemsf,
        "n_accesses_logged": len(audit),
        "last_access": audit[-1] if audit else None,
    }


def print_status() -> None:
    s = status()
    print("=" * 70)
    print("  SEAL STATUS — knowledge_test.json")
    print("=" * 70)
    rec = s["recorded"]
    if not rec:
        print("  NOT RECORDED. Run: python eval/seal.py record")
    else:
        print(f"  recorded  : {rec['recorded_utc']}  at {rec['git_hash'][:12]}")
        print(f"  sha256    : {rec['sha256']}")
        print(f"  questions : {rec['n_questions']}")
    print(f"  current   : {s['current_sha256']}")
    print(f"  verified  : {'YES' if s['verify_ok'] else 'NO'}")
    for p in s["verify_problems"]:
        print(f"     - {p}")

    f = s["freeze"]
    print(f"  frozen    : {f['frozen_utc'] + '  ' + f['git_hash'][:12] if f else 'NOT FROZEN'}")
    print(f"  freeze ok : {'YES' if s['freeze_ok'] else 'NO'}")
    for p in s["freeze_problems"]:
        print(f"     - {p}")

    print(f"  accesses  : {s['n_accesses_logged']} logged")
    if s["last_access"]:
        la = s["last_access"]
        print(f"  last      : {la.get('utc')}  {la.get('actor')}  "
              f"({la.get('reason')})")
    print("=" * 70)
    print(f"\n  backend: 8b={config.model('8b').backend}  "
          f"70b={config.model('70b').backend}")
    live = [m for m in ("8b", "70b") if not config.model(m).is_mock]
    if not live:
        print("\n  *** NO REAL MODEL. The test set must not be run yet. ***")


def main() -> int:
    ap = argparse.ArgumentParser(description="Seal and audit the held-out test set.")
    ap.add_argument("command", choices=["status", "record", "verify", "audit",
                                        "freeze", "note"])
    ap.add_argument("--reason", default="manual")
    args = ap.parse_args()

    if args.command == "record":
        info = record()
        print(f"recorded sha256 {info['sha256']}")
        print(f"          {info['n_questions']} questions, {info['bytes']} bytes")
        return 0

    if args.command == "verify":
        ok, problems = verify()
        okf, problemsf = check_freeze()
        print(f"hash    : {'OK' if ok else 'FAILED'}")
        for p in problems:
            print(f"  - {p}")
        print(f"freeze  : {'OK' if okf else 'FAILED'}")
        for p in problemsf:
            print(f"  - {p}")
        return 0 if (ok and okf) else 1

    if args.command == "freeze":
        rec = freeze(note=args.reason)
        print(f"frozen at {rec['git_hash']}")
        if rec["tree_dirty"]:
            print("\n  *** THE TREE WAS DIRTY. The recorded hash does not identify\n"
                  "      the code that will run. Commit first, then freeze. ***")
            return 1
        return 0

    if args.command == "audit":
        entries = read_audit()
        if not entries:
            print("no accesses logged")
            return 0
        print(f"{len(entries)} recorded access(es) to the sealed set:\n")
        for e in entries:
            print(f"  {e.get('utc')}  {e.get('actor', '?'):<10} "
                  f"git={str(e.get('git_hash', '?'))[:12]}  {e.get('reason')}")
        return 0

    if args.command == "note":
        log_access(args.reason)
        print("logged")
        return 0

    print_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())

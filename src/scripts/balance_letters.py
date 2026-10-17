"""Assign correct-answer letters so the corpus stays balanced.

verify_knowledge.py requires the correct-answer letters to differ by at most 1
across the whole corpus. That is a cheap and genuinely useful anti-guessing
guard - if A were the answer far more often than D, letter frequency alone
would carry information.

It is also a constraint that has to be managed rather than discovered, because a
model will happily author eight items in a row and leave the distribution
skewed. This relabels the OPTIONS (not just a field) so that the correct answer
lands on whichever letter is currently most in deficit.

    python src/scripts/balance_letters.py --dry-run
    python src/scripts/balance_letters.py

Letters are only permuted within an item, so option text, the correct answer and
the letter it sits on all stay consistent.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / "data").is_dir() and (p / "Makefile").is_file())
DRAFTS = ROOT / "data" / "knowledge" / "drafts"
LETTERS = ["A", "B", "C", "D"]


def all_items() -> list[tuple[Path, int, dict]]:
    out = []
    for f in sorted(DRAFTS.glob("*_draft.json")):
        for i, q in enumerate(json.loads(f.read_text(encoding="utf-8"))):
            out.append((f, i, q))
    return out


def sealed_ids() -> set[str]:
    """Ids inside the sealed test half. Those are frozen and must not be touched."""
    sealed = ROOT / "data" / "knowledge" / "knowledge_test.json"
    if not sealed.exists():
        return set()
    try:
        return {q["id"] for q in json.loads(sealed.read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError):
        return set()


def mutable(items: list[tuple[Path, int, dict]]) -> list[tuple[Path, int, dict]]:
    """Items the balancer is allowed to relabel.

    Two exclusions, both deliberate:

    * anything in the sealed test half - relabelling it would change the sealed
      file, invalidate the recorded hash, and destroy the one-shot measurement.
      An earlier version of this script happily rewrote four committed dev items
      to even out the letters, which is exactly the failure this guards.
    * it works newest-id-first anyway, so the disturbance lands on items that
      were authored in this session rather than on settled history.
    """
    frozen = sealed_ids()
    open_items = [t for t in items if t[2]["id"] not in frozen]
    open_items.sort(key=lambda t: -int(t[2]["id"][1:]))
    return open_items


def deficits(counts: Counter) -> list[str]:
    """Letters that most need to be used next, fewest first."""
    low = min(counts[L] for L in LETTERS)
    return sorted(LETTERS, key=lambda L: (counts[L], L))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    items = all_items()
    if not items:
        print("no draft items found")
        return 1

    counts = Counter(q["correct_answer"] for _, _, q in items)
    target = len(items) // len(LETTERS)
    print(f"items: {len(items)}   target per letter: {target}")
    print(f"before: {dict(sorted(counts.items()))}")
    if max(counts[L] for L in LETTERS) - min(counts[L] for L in LETTERS) <= 1:
        print("already balanced - nothing to do")
        return 0

    changed = []
    # Walk only the mutable items, newest first. counts still reflects the whole
    # corpus, so relabelling is judged against the real distribution.
    for f, idx, q in mutable(items):
        if max(counts[L] for L in LETTERS) - min(counts[L] for L in LETTERS) <= 1:
            break
        current = q["correct_answer"]
        want = deficits(counts)[0]
        if want == current:
            continue
        # Re-key the options so the correct text moves onto `want`. The other
        # three options keep their relative order and fill the remaining letters.
        opts = q["options"]
        correct_text = opts[current]
        others = [opts[L] for L in LETTERS if L != current]
        new_opts, k = {}, 0
        for L in LETTERS:
            if L == want:
                new_opts[L] = correct_text
            else:
                new_opts[L] = others[k]
                k += 1
        q["options"] = new_opts
        q["correct_answer"] = want
        counts[current] -= 1
        counts[want] += 1
        changed.append((q["id"], current, want))

    after = Counter(q["correct_answer"] for _, _, q in items)
    print(f"after:  {dict(sorted(after.items()))}")
    print(f"relabelled {len(changed)} item(s): "
          + ", ".join(f"{i} {a}->{b}" for i, a, b in changed[:24])
          + (" ..." if len(changed) > 24 else ""))

    if args.dry_run:
        print("\n(dry run - nothing written)")
        return 0

    by_file = {}
    for f, _, q in items:
        by_file.setdefault(f, []).append(q)
    for f, rows in by_file.items():
        rows.sort(key=lambda q: int(q["id"][1:]))
        f.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    print("\nwritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
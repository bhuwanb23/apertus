"""
human_worksheet.py - the two blind scoring sheets B5 needs.

The values side already has a tool (`crosscheck.py select`). The KNOWLEDGE side
had none: there was no way to produce the sheet, no way to score it, and no path
by which an agreement rate could ever appear. This is that missing half.

Why a separate tool rather than an extension of crosscheck.py: the two tasks are
different in kind. Values asks a human to apply a rubric to a model response.
Knowledge asks a human to answer a question and be compared to the dataset's key.
The knowledge one is easier to do badly - the risk is a human who simply agrees
with the key because the key is visible, or who reasons backwards from the source
quote until it matches. So this sheet is deliberately blind in a different way from
the values sheet: it withholds the key AND the model's answer, and it asks for the
judgement before the sources are shown.

What the sheet contains per item:
  * the question and its four options
  * a blank answer box
  * THEN, below a rule, the source quote and URL

What it never contains: `correct_answer`, and any model's prediction. A sheet that
showed either would measure compliance rather than agreement.

Scoring:
    python src/scripts/human_worksheet.py knowledge --build     # make the sheets
    python src/scripts/human_worksheet.py knowledge --score     # grade the sheets
    python src/scripts/human_worksheet.py values --status       # values progress

Why 18 knowledge items. The knowledge arm is a closed multiple-choice task scored
by exact letter match, so there is no judge to audit - the "agreement" here is
between the dataset key and a competent human. That is a check on the DATASET, not
on the model, and it is the check that would have caught K108, where the stored key
was C and the source plainly said D. 18 items is drawn to cover all six categories
and to straddle easy/medium/hard, because the failure this catches is
category-specific and difficulty-specific.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = 42

KNOWLEDGE_SHEET = ROOT / "results" / "human" / "knowledge_human_sheet.json"
KNOWLEDGE_SCORED = ROOT / "results" / "human" / "knowledge_human_scored.json"
VALUES_SHEET = ROOT / "results" / "parsed" / "values_8b_crosscheck.json"

LETTERS = ["A", "B", "C", "D"]
AGREEMENT_FLOOR = 0.75


# ----------------------------------------------------------------- knowledge
def _dev_items() -> list[dict]:
    p = ROOT / "data" / "knowledge" / "knowledge_dev.json"
    items = json.loads(p.read_text(encoding="utf-8"))
    return items if isinstance(items, list) else items["items"]


def build_knowledge(n: int = 18) -> Path:
    """
    Draw a stratified sample from the DEV split.

    Dev, not the sealed test set. A human answering 18 sealed items would be
    18 accesses to a set that is meant to be scored once, and the human's answers
    would themselves be an outcome measured on it. The dataset-key check does not
    need the sealed half: the same authoring process produced both halves.
    """
    items = _dev_items()
    if len(items) < n:
        raise SystemExit(f"dev split has {len(items)} items, need {n}")

    # Stratify by category, then spread across difficulty inside each category so
    # a single easy category cannot dominate the sheet.
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        by_cat[it.get("category", "?")].append(it)

    rng = random.Random(SEED)
    cats = sorted(by_cat)
    quota = {c: n // len(cats) for c in cats}
    for c in cats[: n % len(cats)]:
        quota[c] += 1

    picked: list[dict] = []
    for cat in cats:
        pool = sorted(by_cat[cat], key=lambda r: r["id"])
        want = quota[cat]
        # Round-robin ACROSS difficulties so a category contributes its spread
        # rather than its easiest items.
        #
        # The first version concatenated the difficulty lists - easy, then medium,
        # then hard - and took the first `want` of that order. With 3 per category
        # and 7-8 easy items available, every single drawn item was easy, and the
        # sheet printed "difficulty: {'easy': 18}" without that being obviously
        # wrong. A sheet of easy items cannot surface a difficulty-specific key
        # error, which is the main thing it exists to catch.
        by_diff: dict[str, list[dict]] = defaultdict(list)
        for r in pool:
            by_diff[r.get("difficulty", "?")].append(r)
        for lst in by_diff.values():
            rng.shuffle(lst)

        diffs = sorted(by_diff)
        order: list[dict] = []
        depth = 0
        while len(order) < want:
            added = False
            for d in diffs:
                if depth < len(by_diff[d]):
                    order.append(by_diff[d][depth])
                    added = True
                    if len(order) >= want:
                        break
            if not added:
                break
            depth += 1
        picked.extend(order[:want])

    rng.shuffle(picked)
    picked = picked[:n]
    picked.sort(key=lambda r: r["id"])

    rows = []
    for it in picked:
        # Everything the human needs, and nothing that hints at the key.
        rows.append({
            "item_id": it["id"],
            "category": it.get("category", ""),
            "difficulty": it.get("difficulty", ""),
            "question": it["question"],
            "options": it["options"],
            "human_answer": None,
            # Shown only after the answer box, as provenance for the second pass.
            "source_quote": it.get("source_quote", ""),
            "source_id": it.get("source_id", ""),
            "source_url": it.get("source_url", ""),
        })

    KNOWLEDGE_SHEET.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_SHEET.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")

    print(f"  knowledge sheet -> {KNOWLEDGE_SHEET.relative_to(ROOT)}")
    print(f"  {len(rows)} items, seeded ({SEED}), stratified by category then difficulty")
    print(f"  categories: {dict(sorted(Counter(r['category'] for r in rows).items()))}")
    print(f"  difficulty: {dict(sorted(Counter(r['difficulty'] for r in rows).items()))}")
    print()
    print("  The sheet contains no answer key and no model prediction. Score it with:")
    print("      python src/scripts/human_worksheet.py knowledge --score")
    return KNOWLEDGE_SHEET


def print_knowledge_sheet() -> None:
    rows = json.loads(KNOWLEDGE_SHEET.read_text(encoding="utf-8"))
    w = 78
    print("=" * w)
    print("  KNOWLEDGE — HUMAN VERIFICATION SHEET")
    print("=" * w)
    print()
    print("  Answer each question from your own knowledge FIRST. Only then read the")
    print("  source below the line and check yourself. Do not open the dataset.")
    print()
    for i, r in enumerate(rows, 1):
        print(f"  [{i:>2}] {r['item_id']}   {r['category']} / {r['difficulty']}")
        print(f"       {r['question']}")
        for L in LETTERS:
            print(f"          {L})  {r['options'].get(L, '')}")
        done = "done" if r.get("human_answer") else "____"
        print(f"       your answer: [{done}]   (A / B / C / D)")
        print("       " + "-" * (w - 8))
        q = r.get("source_quote", "")
        print(f"       source {r.get('source_id','')}: {q[:400]}")
        print(f"       {r.get('source_url','')}")
        print()

    scored = sum(1 for r in rows if r.get("human_answer"))
    print("=" * w)
    print(f"  {scored}/{len(rows)} answered. Save the file, then run:")
    print("      python src/scripts/human_worksheet.py knowledge --score")
    print("=" * w)


def score_knowledge() -> int:
    """Grade the sheet against the dataset key. Read-only on the key's own file."""
    rows = json.loads(KNOWLEDGE_SHEET.read_text(encoding="utf-8"))
    key = {q["id"]: q for q in _dev_items()}

    done = [r for r in rows if r.get("human_answer")]
    if not done:
        print("  no answers yet. Fill `human_answer` in the sheet and re-run.")
        return 1

    results = []
    for r in done:
        gold = key[r["item_id"]]["correct_answer"]
        results.append({
            "item_id": r["item_id"],
            "category": r["category"],
            "difficulty": r["difficulty"],
            "human": r["human_answer"],
            "key": gold,
            "agree": r["human_answer"] == gold,
        })

    agree = sum(1 for x in results if x["agree"])
    n = len(results)
    rate = agree / n

    lo = _wilson(agree, n)[0]
    print()
    print("=" * 72)
    print("  KNOWLEDGE — HUMAN vs DATASET KEY")
    print("=" * 72)
    print(f"  agreement : {agree}/{n} = {rate * 100:.1f}%   (floor {AGREEMENT_FLOOR * 100:.0f}%)")
    print(f"  95% CI   : [{lo * 100:.1f}, {_wilson(agree, n)[1] * 100:.1f}]")
    print()
    print("  Disagreements — each one is a possible defect in the DATASET:")
    for x in results:
        if not x["agree"]:
            row = next(r for r in rows if r["item_id"] == x["item_id"])
            print(f"    {x['item_id']}  human={x['human']}  key={x['key']}"
                  f"  [{x['category']}/{x['difficulty']}]")
            print(f"      Q: {row['question'][:100]}")
            print(f"      source says: {row['source_quote'][:200]}")
    if agree == n:
        print("    none — every answer matched the key.")
    print()
    print("  By category:")
    per = defaultdict(lambda: [0, 0])
    for x in results:
        per[x["category"]][1] += 1
        per[x["category"]][0] += x["agree"]
    for c in sorted(per):
        a, t = per[c]
        print(f"    {c:<12} {a}/{t}")
    print()

    out = {
        "n": n, "agreed": agree, "agreement": round(rate * 100, 1),
        "floor": AGREEMENT_FLOOR, "meets_floor": rate >= AGREEMENT_FLOOR,
        "by_category": {c: {"agreed": a, "n": t} for c, (a, t) in sorted(per.items())},
        "disagreements": [x for x in results if not x["agree"]],
        "seed": SEED,
    }
    KNOWLEDGE_SCORED.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
    # relative_to() raises for any path outside the repo, which would turn a
    # successful grading into a crash on the last line. Fall back to the raw path.
    try:
        shown = KNOWLEDGE_SCORED.relative_to(ROOT)
    except ValueError:
        shown = KNOWLEDGE_SCORED
    print(f"  written -> {shown}")
    return 0


# -------------------------------------------------------------------- values
def values_status() -> int:
    if not VALUES_SHEET.exists():
        print("  no values blind sample yet. Run:")
        print("      python src/eval/crosscheck.py select --model 8b")
        return 1
    rows = json.loads(VALUES_SHEET.read_text(encoding="utf-8"))
    done = [r for r in rows if r.get("manual_score") is not None]
    print(f"  values sheet : {VALUES_SHEET.relative_to(ROOT)}")
    print(f"  scored       : {len(done)}/{len(rows)}")
    if len(done) == len(rows) and rows:
        agree = sum(1 for r in done if r.get("manual_score") == r.get("judge_score"))
        print(f"  agreement    : {agree}/{len(done)} = {agree / len(done) * 100:.1f}%")
        print("  grade it with: python src/eval/crosscheck.py verify --model 8b")
    else:
        print()
        print("  Score it either in the JSON (`manual_score`) or interactively:")
        print("      python src/eval/crosscheck.py select --model 8b --interactive")
        print()
        print(f"  Precision note: at n={len(rows)} a realistic 80-90% agreement")
        print("  carries roughly +/-12 pp of interval. That is fine for the")
        print("  rubric's pass/fail against 0.75, too wide to quote as precise.")
    return 0


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(max(0.0, p * (1 - p) / n + z * z / (4 * n * n))) / d
    return max(0.0, c - h), min(1.0, c + h)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build and score the B5 human sheets.")
    ap.add_argument("task", choices=["knowledge", "values"])
    ap.add_argument("--build", action="store_true", help="(re)draw the sheet")
    ap.add_argument("--show", action="store_true", help="print the sheet to score")
    ap.add_argument("--score", action="store_true", help="grade the sheet")
    ap.add_argument("--n", type=int, default=18, help="items to draw (knowledge)")
    args = ap.parse_args()

    if args.task == "values":
        return values_status()

    if args.build or not KNOWLEDGE_SHEET.exists():
        build_knowledge(args.n)
        return 0
    if args.score:
        return score_knowledge()
    if args.show:
        print_knowledge_sheet()
        return 0

    print(f"  sheet exists: {KNOWLEDGE_SHEET.relative_to(ROOT)}")
    print("  next: --show to print it, --score to grade it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
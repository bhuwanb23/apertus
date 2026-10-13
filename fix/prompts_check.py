"""
prompts_check.py - Phase 3.3: the contamination gate.

WHY THIS EXISTS

docs/plans/phase_3.md §3.3 Option A proposes a system prompt that asserts Swiss
facts verbatim - 26 cantons, 100,000 signatures, suffrage in 1971, the Federal
Supreme Court in Lausanne, language percentages. It reads like a good prompt.

Measured against the dev set, that text answers **14 of 84 items (17%)**.

So a large part of any "improvement" Option A produces would be the answer key
inserted into the prompt, not a change in what the model knows. It would not
transfer either: the held-out test set is scored once in Phase 4.1, and a delta
bought this way does not reproduce on questions the prompt does not name.

A benchmark that hands the model the answers measures the prompt, not the model.

WHAT THIS MODULE DOES

  contamination_report(prompt_text, split)  -> which dev items the prompt answers
  assert_uncontaminated(prompt, split)     -> hard gate; raises on contamination
  adjusted_delta(...)                     -> headline delta with the contaminated
                                              items removed from the denominator

A prompt is allowed to be a good prompt. It is not allowed to know the answers.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from config import config          # noqa: E402

# Anything above this share of the split is answered by the prompt text, and the
# prompt is treated as contaminated. 5% is roughly one item's worth of slack -
# enough for incidental overlap, not enough to carry a headline number.
DEFAULT_THRESHOLD = 0.05

# Facts the Phase 1 corpus explicitly treats as load-bearing. A prompt that
# asserts any of these is being measured on them directly.
LOAD_BEARING = {
    "cantons":        r"\b(26|twenty-six)\s+can",
    "signature":      r"\b(100,?000|50,?000)\s+signature",
    "supreme court":  r"Federal Supreme Court[^\n]{0,60}Lausanne|Lausanne[^\n]{0,60}Federal Supreme Court",
    "suffrage":       r"suffrage[^\n]{0,40}1971|1971[^\n]{0,40}suffrage",
    "un":             r"United Nations[^\n]{0,40}2002|2002[^\n]{0,40}United Nations",
    "language share": r"\b(62|23|8)\s*(%|per ?cent)",
    "federal council": r"Federal Council[^\n]{0,40}(seven|7)\s+member|(seven|7)\s+member[^\n]{0,40}Federal Council",
    "bvg":            r"\bBVG\b|second pillar",
    "kvg":            r"\bKVG\b|\bLAMal\b",
    "schengen":       r"Schengen",
    "language count": r"four national languages",
}

# What it takes for an item to actually PROBE a fact. Without this the reason
# column is useless: the prompt mentions every fact, so every item appears to be
# about every fact, and a reviewer learns nothing about which line of the prompt
# to delete.
PROBED_BY = {
    "cantons":        r"how many canton|number of canton",
    "signature":      r"signature|initiative|referendum",
    "supreme court":  r"supreme court|court|lausanne",
    "suffrage":       r"suffrage|women",
    "un":             r"united nations|\bun\b",
    "language share": r"language|percent|%",
    "federal council": r"federal council|member",
    "bvg":            r"pension|retirement|occupational",
    "kvg":            r"health insurance|deductible|franchise|premium|co-pay",
    "schengen":       r"schengen|\beu\b|economic area",
    "language count": r"national language|language region|romansh",
}


@dataclass
class Report:
    split: str
    n_items: int
    contaminated_ids: list
    contaminated_fraction: float
    threshold: float
    reasons: dict

    @property
    def clean(self) -> bool:
        return self.contaminated_fraction <= self.threshold

    def summary(self) -> str:
        head = (f"{len(self.contaminated_ids)}/{self.n_items} "
                f"({self.contaminated_fraction * 100:.0f}%) of {self.split} items "
                f"are answered by the prompt")
        return head + (" — CLEAN" if self.clean else
                       f" — CONTAMINATED (threshold {self.threshold * 100:.0f}%)")


def contamination_report(prompt_text: str, split: str = "dev",
                         threshold: float = DEFAULT_THRESHOLD) -> Report:
    """
    Which items of `split` does this prompt text answer directly?

    A prompt is judged to "answer" an item when it asserts the item's fact. The
    test is deliberately conservative: the prompt must contain the specific
    figure or attribution, not merely the topic. A prompt that says "direct
    democracy matters in Switzerland" does not contaminate a question about
    signature thresholds.
    """
    questions = json.loads(
        config.data_path("knowledge", f"knowledge_{split}.json").read_text(encoding="utf-8"))
    text = prompt_text.casefold()
    text = re.sub(r"\s+", " ", text)

    contaminated, reasons = [], {}
    for q in questions:
        stem = q["question"].casefold()
        # Only a fact that is BOTH asserted by the prompt AND probed by this
        # item counts. Either alone is a coincidence worth ignoring.
        probed = [name for name, pat in LOAD_BEARING.items()
                  if re.search(pat, text, re.I)
                  and re.search(PROBED_BY.get(name, r"$^"), stem, re.I)]
        if not probed:
            continue
        contaminated.append(q["id"])
        reasons[q["id"]] = probed

    n = len(questions) or 1
    return Report(split=split, n_items=len(questions),
                  contaminated_ids=contaminated,
                  contaminated_fraction=len(contaminated) / n,
                  threshold=threshold, reasons=reasons)


def assert_uncontaminated(prompt_text: str, split: str = "dev",
                          threshold: float = DEFAULT_THRESHOLD) -> Report:
    """Hard gate. Raises rather than warns, because a contaminated prompt produces
    a number that looks like a result and is not one."""
    rep = contamination_report(prompt_text, split, threshold)
    if not rep.clean:
        detail = "; ".join(f"{i}: {'+'.join(rep.reasons.get(i, []))}"
                           for i in rep.contaminated_ids[:8])
        raise SystemExit(
            f"PROMPT IS CONTAMINATED - refusing to measure with it.\n\n"
            f"  {rep.summary()}\n\n"
            f"  {detail}\n\n"
            f"The prompt asserts facts the benchmark tests. Any improvement measured\n"
            f"this way is the answer key, not the model, and it will not reproduce on\n"
            f"the held-out set. Remove the factual content and keep the behavioural\n"
            f"rules - or accept that the result is not a benchmark result and say so\n"
            f"in the README.")
    return rep


# ------------------------------------------------------------------ reporting
def adjusted_delta(before: list, after: list, contaminated_ids: list) -> dict:
    """
    Headline delta with the contaminated items removed from both sides.

    A delta reported over a split where part of it was handed to the model in the
    prompt is not a delta. This recomputes the comparison on the clean subset, so
    the README can state the honest number and the raw one side by side.
    """
    clean = [i for i in {r["question_id"] for r in before}
             if i not in set(contaminated_ids)]
    b = {r["question_id"]: r for r in before}
    a = {r["question_id"]: r for r in after}

    def acc(rows):
        if not rows:
            return None, 0
        got = [b[i]["is_correct"] for i in rows if i in b]
        got += [a[i]["is_correct"] for i in rows if i in a]
        n = len(got)
        return (sum(got) / n * 100 if n else None), n

    raw_b, _ = acc(list(b))
    raw_a, _ = acc(list(a))
    clean_b, n_b = acc(clean)
    clean_a, n_a = acc(clean)

    def delta(x, y):
        return round(y - x, 1) if x is not None and y is not None else None

    return {
        "n_raw": len(b),
        "before_raw": round(raw_b, 1) if raw_b is not None else None,
        "after_raw": round(raw_a, 1) if raw_a is not None else None,
        "delta_raw": delta(raw_b, raw_a),
        "n_clean": n_b,
        "n_excluded": len(b) - n_b,
        "before_clean": round(clean_b, 1) if clean_b is not None else None,
        "after_clean": round(clean_a, 1) if clean_a is not None else None,
        "delta_clean": delta(clean_b, clean_a),
        "contaminated_ids": sorted(set(contaminated_ids)),
    }


def mcnemar(before: list, after: list, only: list | None = None) -> dict:
    """Paired before/after on the same items. See fix/select_target.py for why
    this is the only test that carries weight here."""
    from math import comb
    b = {r["question_id"]: r["is_correct"] for r in before}
    a = {r["question_id"]: r["is_correct"] for r in after}
    ids = only if only is not None else sorted(set(b) & set(a))
    improved = sum(1 for i in ids if not b[i] and a[i])
    regressed = sum(1 for i in ids if b[i] and not a[i])
    n = improved + regressed
    p = 1.0
    if n:
        k = min(improved, regressed)
        p = min(1.0, sum(comb(n, i) for i in range(k + 1)) / (2 ** n) * 2)
    return {"n": len(ids), "improved": improved, "regressed": regressed,
            "net": improved - regressed, "p": round(p, 4),
            "significant": p < 0.05 and improved > regressed}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Contamination gate for 3.3 prompts.")
    ap.add_argument("prompt", help="path to a prompt .txt, or '-' for stdin")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero when contaminated")
    args = ap.parse_args()

    text = sys.stdin.read() if args.prompt == "-" else Path(args.prompt).read_text(encoding="utf-8")
    rep = contamination_report(text, args.split, args.threshold)
    print(f"{args.prompt}")
    print(f"  {rep.summary()}")
    if rep.contaminated_ids:
        for qid in rep.contaminated_ids:
            print(f"    {qid}: {'+'.join(rep.reasons.get(qid, []))}")
    if args.gate and not rep.clean:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
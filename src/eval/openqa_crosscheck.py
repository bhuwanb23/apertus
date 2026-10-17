"""
openqa_crosscheck.py - the 20% human sample of openQA judge verdicts.

WHY THIS EXISTS SEPARATELY FROM crosscheck.py

crosscheck.py audits the VALUES judge. It cannot be reused here for a structural
reason: the openQA judge emits a THREE-WAY label, not a set of rated elements.
Agreement therefore has to be measured on a single categorical verdict per item,
and the interesting quantity is a different one:

    does the human agree with the judge on WHICH OF THREE LABELS applies?

A judge that collapses everything to CORRECT still produces a high raw agreement
rate when most answers are correct - agreement would be high and the judge would
still be useless. So this reports Cohen's kappa alongside raw agreement. Kappa
discounts agreement that is explained by the label distribution, which is the
number that actually says whether the judge carries information a coin could not.
Raw agreement is reported too, because the brief asks for agreement, and reporting
only kappa would overstate the sophistication of a hand-checked 18 items.

SAMPLE COMPOSITION

Sampling is stratified over the judge's two verdicts, because a uniform sample of
90 items would contain very few INCORRECT ones (11 in the sealed RAG arm) and the
agreement rate would be measured almost entirely on correct answers - i.e. it would
be measuring agreement on the easy case. The INCORRECT stratum is the one that
matters, so it is sampled proportionally and BOTH strata are reported.

Blinding: the human column is filled in by a person. The judge verdict is present
in the file because a reviewer must be able to check the grader afterwards, but it
is placed under a "judge_audit" key rather than beside the answer, and the scoring
script never reads it. Nothing is pre-filled.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))

import open_grade                                     # noqa: E402

SEED = 42                 # same seed as the split and the values audit
AUDIT_FRACTION = 0.20      # the brief's sampling rate
LABELS = (open_grade.CORRECT, open_grade.INCORRECT)


def select(parsed_path: Path, fraction: float = AUDIT_FRACTION,
           arm: str = "rag") -> Path:
    """
    Build the blind human sheet.

    Stratified over the two judged labels, seeded, so the sample is reproducible
    and re-running picks the same items.
    """
    payload = json.loads(parsed_path.read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in _load_items("test")}

    strata: dict = defaultdict(list)
    for r in payload["records"]:
        if not r.get("judged"):
            continue          # abstentions are decided by rule, not by the judge
        strata[r.get("judge_verdict")].append(r)

    total = sum(len(v) for v in strata.values())
    rng = random.Random(SEED)
    sheet: list[dict] = []
    for label in LABELS:
        pool = strata.get(label, [])
        if not pool:
            continue
        k = max(1, round(len(pool) * fraction))
        for r in rng.sample(pool, min(k, len(pool))):
            q = questions[r["question_id"]]
            sheet.append({
                "question_id": r["question_id"],
                "category": r.get("category", ""),
                "difficulty": r.get("difficulty", ""),
                "question": q["question"],
                "reference": (q.get("reference") or q.get("source_quote", ""))[:900],
                "accepted_answer_forms": r.get("answer", ""),
                "answer_variations": r.get("answer_variations", []),
                "model_answer": r.get("reply", ""),
                # THE COLUMN A HUMAN FILLS IN.
                "human_verdict": None,
                "human_notes": "",
            })
    # Recorded but kept out of the human's view: needed to score agreement, and a
    # reviewer must be able to audit the grader after the fact.
    for row in sheet:
        rec = next(r for r in payload["records"]
                   if r["question_id"] == row["question_id"])
        row["judge_audit"] = {"judge_verdict": rec.get("judge_verdict"),
                              "arm": arm, "model": payload.get("model", "")}

    out = ROOT / "results" / "human" / "openqa_human_sheet.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "sampling": {"fraction": fraction, "seed": SEED,
                     "stratified_over": list(LABELS),
                     "judged_pool": total},
        "counts": {k: len(v) for k, v in strata.items()},
        "sampled": len(sheet),
        "arm": arm,
        "instructions": (
            "Read the question and the reference passage, then label the MODEL "
            "ANSWER as one of: correct / incorrect / not_attempted.\n"
            "  correct        - it asserts what the reference states.\n"
            "  incorrect      - it asserts something the reference contradicts or "
            "does not support.\n"
            "  not_attempted  - it declines, or says it cannot know.\n"
            "Ignore wording, length and tone. Fill human_verdict, leave "
            "judge_audit alone."),
        "scored": False,
    }
    out.write_text(json.dumps({"meta": meta, "items": sheet}, indent=2,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def _load_items(split: str) -> list[dict]:
    p = ROOT / "data" / "knowledge" / f"knowledge_{split}.json"
    items = json.loads(p.read_text(encoding="utf-8"))
    return items if isinstance(items, list) else items["items"]


def agreement(sheet_path: Path) -> dict:
    """
    Judge-vs-human agreement on the three-way label.

    Returns raw agreement AND Cohen's kappa. Returns scored=False until a human
    has actually filled the sheet - an empty sheet reports "not started", never 0%
    or 100%.
    """
    d = json.loads(sheet_path.read_text(encoding="utf-8"))
    items = [it for it in d["items"] if it.get("human_verdict")]
    total = len(d["items"])

    out = {
        "sheet": sheet_path.name,
        "sampled": total,
        "human_scored": len(items),
        "scored": bool(items),
        "sampling": d["meta"].get("sampling", {}),
        "counts_in_pool": d["meta"].get("counts", {}),
    }
    if not items:
        out["agreement"] = None
        out["kappa"] = None
        out["note"] = "not started: no human verdicts recorded yet"
        return out

    agree = sum(1 for it in items
                if it["human_verdict"] == it["judge_audit"]["judge_verdict"])
    n = len(items)
    p_obs = agree / n

    # Kappa over the labels the judge can actually emit (it never sees abstentions).
    labels = LABELS
    human = [it["human_verdict"] for it in items]
    judge = [it["judge_audit"]["judge_verdict"] for it in items]
    p_e = sum((human.count(l) / n) * (judge.count(l) / n) for l in labels)
    kappa = (p_obs - p_e) / (1 - p_e) if p_e < 1 else None

    out["agreement"] = round(p_obs * 100, 1)
    out["agreements"] = agree
    out["kappa"] = round(kappa, 3) if kappa is not None else None
    out["label_counts"] = {
        "human": {l: human.count(l) for l in labels},
        "judge": {l: judge.count(l) for l in labels},
    }
    out["confusion"] = {
        f"human_{h}|judge_{j}": sum(
            1 for it in items
            if it["human_verdict"] == h
            and it["judge_audit"]["judge_verdict"] == j)
        for h in labels for j in labels
    }
    out["note"] = ("raw agreement alone is not sufficient: a judge that labels "
                   "everything CORRECT agrees with a human on most items whenever "
                   "most items are correct, so kappa is reported alongside it")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="openQA judge cross-check.")
    ap.add_argument("--build", action="store_true",
                    help="(re)build the blind human sheet")
    ap.add_argument("--arm", default="rag", choices=["rag", "baseline"])
    ap.add_argument("--fraction", type=float, default=AUDIT_FRACTION)
    ap.add_argument("--report", action="store_true",
                    help="print agreement for the existing sheet")
    args = ap.parse_args()

    parsed = ROOT / "results" / "parsed" / "openqa" / f"openqa_test_{args.arm}_8b.json"
    sheet = ROOT / "results" / "human" / "openqa_human_sheet.json"

    if args.build or not sheet.is_file():
        if not parsed.is_file():
            print(f"  no parsed result at {parsed}; run run_openqa.py first")
            return 1
        sheet = select(parsed, args.fraction, args.arm)
        print(f"  sheet -> {sheet.relative_to(ROOT)}")

    rep = agreement(sheet)
    print(f"\n  openQA judge cross-check ({rep['sheet']})")
    print(f"    sampled        {rep['sampled']}")
    print(f"    human scored   {rep['human_scored']}   "
          f"(scored={rep['scored']})")
    print(f"    pool counts    {rep.get('counts_in_pool')}")
    if rep["scored"]:
        print(f"    agreement      {rep['agreement']}%  ({rep['agreements']}/"
              f"{rep['human_scored']})")
        print(f"    kappa          {rep['kappa']}")
        print(f"    confusion      {rep['confusion']}")
    else:
        print("    agreement      not started - awaiting a human reviewer")
    print(f"\n    {rep['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
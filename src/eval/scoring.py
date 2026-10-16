"""
scoring.py - Accuracy calculation and breakdowns.

Kept free of any I/O to the model and of any knowledge of the dataset, so it can
be unit-tested against hand-built result lists. Phase 2.2 owns the parser
tests; this file only aggregates.

Provenance rule: every score dict carries `backend` and `is_mock` from the run
that produced it. A mock number is a pipeline self-test and must be visibly
distinguishable from a result at every point it is read.
"""

from __future__ import annotations

from collections import defaultdict


def calculate_knowledge_scores(results: list, backend: str = "unknown") -> dict:
    """
    Overall and per-category accuracy.

    `results` items are dicts with at least: category, predicted, correct,
    is_correct. A PARSE_ERROR counts as incorrect - that is the honest choice -
    but it is also counted separately so the parse-failure rate is never hidden
    inside the accuracy figure.
    """
    total = len(results)
    correct = sum(1 for r in results if r["is_correct"])
    parse_errors = sum(1 for r in results if r.get("predicted") == PARSE_ERROR)
    api_errors = sum(1 for r in results if r.get("api_failed"))

    by_category_counts = defaultdict(lambda: {"correct": 0, "total": 0})
    by_difficulty_counts = defaultdict(lambda: {"correct": 0, "total": 0})
    by_answer_counts = defaultdict(lambda: {"correct": 0, "total": 0})

    for r in results:
        for bucket, key in (
            (by_category_counts, r.get("category", "?")),
            (by_difficulty_counts, r.get("difficulty", "?")),
            (by_answer_counts, r.get("correct", "?")),
        ):
            bucket[key]["total"] += 1
            if r["is_correct"]:
                bucket[key]["correct"] += 1

    def pct(c: dict) -> dict:
        return {
            k: {"accuracy": round(v["correct"] / v["total"] * 100, 1),
                "correct": v["correct"], "total": v["total"]}
            for k, v in sorted(c.items())
        }

    return {
        "overall": round(correct / total * 100, 1) if total else 0.0,
        "total_questions": total,
        "correct": correct,
        "parse_errors": parse_errors,
        "parse_error_rate": round(parse_errors / total * 100, 1) if total else 0.0,
        "api_errors": api_errors,
        "chance_level": round(100 / 4, 1),
        "by_category": pct(by_category_counts),
        "by_difficulty": pct(by_difficulty_counts),
        "by_correct_answer": pct(by_answer_counts),
        "backend": backend,
        "is_mock": backend == "mock",
    }


PARSE_ERROR = "PARSE_ERROR"


def compare_models(scores_8b: dict, scores_70b: dict) -> dict:
    """8B vs 70B, overall and per category."""
    by_category = {}
    for cat in sorted(set(scores_8b.get("by_category", {})) | set(scores_70b.get("by_category", {}))):
        a = scores_8b.get("by_category", {}).get(cat, {}).get("accuracy", 0.0)
        b = scores_70b.get("by_category", {}).get(cat, {}).get("accuracy", 0.0)
        by_category[cat] = {"8b": a, "70b": b, "delta": round(b - a, 1)}
    return {
        "overall_8b": scores_8b.get("overall"),
        "overall_70b": scores_70b.get("overall"),
        "overall_delta": round(
            (scores_70b.get("overall") or 0.0) - (scores_8b.get("overall") or 0.0), 1),
        "by_category": by_category,
    }


def compare_before_after(scores_before: dict, scores_after: dict) -> dict:
    """
    Baseline vs improved. Both sides must come from the same backend and model,
    otherwise the delta confounds the intervention with the setup - so that is
    checked rather than assumed.
    """
    warns = []
    if scores_before.get("backend") != scores_after.get("backend"):
        warns.append("backend differs between before and after - the delta is not attributable to the fix")
    if scores_before.get("total_questions") != scores_after.get("total_questions"):
        warns.append("question count differs between before and after - sets are not comparable")

    by_cat = {}
    for cat in sorted(set(scores_before.get("by_category", {})) | set(scores_after.get("by_category", {}))):
        a = scores_before.get("by_category", {}).get(cat, {}).get("accuracy", 0.0)
        b = scores_after.get("by_category", {}).get(cat, {}).get("accuracy", 0.0)
        by_cat[cat] = {"before": a, "after": b, "delta": round(b - a, 1)}

    return {
        "before": scores_before.get("overall"),
        "after": scores_after.get("overall"),
        "delta": round((scores_after.get("overall") or 0.0) - (scores_before.get("overall") or 0.0), 1),
        "by_category": by_cat,
        "warnings": warns,
    }


def format_bar(accuracy: float, width: int = 20) -> str:
    filled = int(round(accuracy / 100 * width))
    return "#" * filled + "." * (width - filled)


def print_knowledge_summary(scores: dict, label: str = "") -> None:
    line = "-" * 62
    print(f"\n{line}\n  KNOWLEDGE RESULTS{(' - ' + label) if label else ''}\n{line}")
    if scores["total_questions"] == 0:
        print("  no questions evaluated")
        print(f"{line}\n")
        return
    print(f"  overall        : {scores['overall']}%  ({scores['correct']}/{scores['total_questions']})"
          f"   chance = {scores['chance_level']}%")
    print(f"  parse errors   : {scores['parse_errors']} ({scores['parse_error_rate']}%)")
    if scores["api_errors"]:
        print(f"  api errors     : {scores['api_errors']}  <-- these are infrastructure, not model failures")
    print("\n  by category")
    for cat, d in scores["by_category"].items():
        print(f"    {cat:<12} {format_bar(d['accuracy'])} {d['accuracy']:>5}%  "
              f"({d['correct']}/{d['total']})")
    if len(scores.get("by_difficulty", {})) > 1:
        print("\n  by difficulty")
        for diff, d in scores["by_difficulty"].items():
            print(f"    {diff:<12} {format_bar(d['accuracy'])} {d['accuracy']:>5}%  "
                  f"({d['correct']}/{d['total']})")
    if scores.get("is_mock"):
        print(f"\n  *** MOCK BACKEND - NOT A RESULT. Pipeline self-test only. ***")
    print(f"{line}\n")
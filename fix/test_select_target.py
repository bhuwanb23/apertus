"""
test_select_target.py - Phase 3.2 verification.

A target-selection tool that always names a target is a machine for confidently
doing the wrong thing. These tests assert the opposite behaviours:

  1. THE GATES FIRE. On a mock baseline, an unresolved taxonomy, or a single
     model, no target is selected - and the refusal says why.
  2. THE POWER ARITHMETIC IS RIGHT. This is the one part of 3.2 that is
     answerable without a model, so it has to be exactly right: the claim that a
     per-category result needs 6/14 flips with zero regressions is the single
     most consequential number in Phase 3, and nobody re-derives it by hand.
  3. THE MATRIX CANNOT REWARD AN UNFIXABLE CATEGORY. The plan's
     `impact x fixability` ranks a category at 0% with an unfixable dominant
     error above one at 30% that RAG would fix. That must not survive.
  4. Q3 IS ANSWERED FROM DATA, NOT ASSERTED.

Run:  python fix/test_select_target.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fix"))
sys.path.insert(0, str(ROOT / "eval"))

from select_target import (ALPHA, APPROACH, DEV_PER_CATEGORY,     # noqa: E402
                           build_decision, gates, mcnemar_exact,
                           power_table, source_material)

failures: list[str] = []
checks = 0


def check(label, got, expected):
    global checks
    checks += 1
    if got != expected:
        failures.append(f"{label}: got {got!r}, expected {expected!r}")


# ============================================== 1. STATISTICAL POWER IS EXACT
def test_power() -> int:
    n = 0
    # McNemar on the discordant pairs only; the 0/0 case is not significant
    check("mc/0-0 is null", mcnemar_exact(0, 0), 1.0)
    check("mc/1-0", round(mcnemar_exact(1, 0), 4), 1.0)
    check("mc/6-0", round(mcnemar_exact(6, 0), 4), 0.0312)
    check("mc/5-0", round(mcnemar_exact(5, 0), 4), 0.0625)
    check("mc/3-1", round(mcnemar_exact(3, 1), 4), 0.625)
    check("mc/5-2", round(mcnemar_exact(5, 2), 4), 0.4531)
    n += 6

    # symmetry: direction must not matter
    check("mc/symmetric 6-0 vs 0-6",
          round(mcnemar_exact(6, 0), 6), round(mcnemar_exact(0, 6), 6))
    n += 1

    # THE headline claim of 3.2, verified rather than asserted
    cat = power_table(DEV_PER_CATEGORY)
    zero = next(r for r in cat if r["regressed"] == 0)
    check("power/n=14 needs 6 with 0 regressions",
          zero["improvements_needed"], 6)
    check("power/n=14 delta", zero["accuracy_delta_pts"], 42.9)
    check("power/n=14 significant", zero["detectable"], True)
    n += 3

    # STRONGER and more alarming than "needs more": at n=14, once 2 items
    # regress, NOTHING is detectable at any achievable improvement count. A
    # fix that helps 6 and breaks 2 cannot be claimed at all.
    two = next(r for r in cat if r["regressed"] == 2)
    check("power/n=14 with 2 regressions: nothing detectable",
          two["improvements_needed"], None)
    check("power/n=14 with 2 regressions is undetectable", two["detectable"], False)
    n += 2

    # the whole dev set needs the same NET change as one category
    whole = power_table(84)
    w0 = next(r for r in whole if r["regressed"] == 0)
    check("power/n=84 needs 6 with 0 regressions", w0["improvements_needed"], 6)
    check("power/n=84 delta", w0["accuracy_delta_pts"], 7.1)
    n += 2

    # and a 5-up/2-down result is NOT significant, which is the whole point
    check("power/5 up 2 down at n=14 is null",
          mcnemar_exact(5, 2) < ALPHA, False)
    n += 1
    return n


# ==================================================== 2. GATES BLOCK A SELECTION
def _model(model_key="8b", is_mock=True, unclassified_pct=0.0, by_category=None):
    cats = by_category or {c: {"accuracy": 40.0, "correct": 6, "total": 14}
                           for c in ("politics", "law", "health",
                                     "geography", "services", "history")}
    return {
        "scores": {"by_category": cats, "overall": 40.0,
                   "run": {"is_mock": is_mock, "model_key": model_key}},
        "taxonomy": {
            "NUMERIC": {"count": 6, "pct_of_content_errors": 100 - unclassified_pct,
                        "categories": {c: 6 for c in cats}, "examples": [],
                        "n_deterministically_confirmed": 6, "classified": True,
                        "desc": "d", "example_of_kind": "e", "fixability": 6,
                        "by_difficulty": {}},
            "UNCLASSIFIED": {"count": 6 if unclassified_pct else 0,
                             "pct_of_content_errors": unclassified_pct,
                             "categories": {c: (6 if unclassified_pct else 0)
                                            for c in cats},
                             "examples": [], "n_deterministically_confirmed": 0,
                             "classified": False, "desc": "d",
                             "example_of_kind": "e", "fixability": None,
                             "by_difficulty": {}},
        },
        "parsed": {}, "qmap": {},
    }


def test_gates() -> int:
    n = 0

    # -- a mock baseline blocks selection
    g = gates({"8b": _model(is_mock=True)})
    fired = [x["id"] for x in g if x["fires"]]
    check("gate/mock fires", "G1-baseline-is-mock" in fired, True)
    n += 1

    # -- an unresolved taxonomy blocks selection
    g = gates({"8b": _model(is_mock=False, unclassified_pct=78.0)})
    fired = [x["id"] for x in g if x["fires"]]
    check("gate/unresolved taxonomy fires", "G2-error-taxonomy-unresolved" in fired, True)
    n += 1

    # -- a single live model blocks selection
    g = gates({"8b": _model(is_mock=False, unclassified_pct=0.0)})
    fired = [x["id"] for x in g if x["fires"]]
    check("gate/single model fires", "G3-single-model" in fired, True)
    n += 1

    # -- two live models with a clean taxonomy clears every data gate
    g = gates({"8b": _model("8b", False, 0.0), "70b": _model("70b", False, 0.0)})
    fired = [x["id"] for x in g if x["fires"]]
    check("gate/two live models clear the data gates",
          [f for f in fired if f != "G4-time-budget"], [])
    n += 1

    # every gate carries a reason, because a refusal nobody can act on is
    # just an obstacle
    for gate in gates({"8b": _model()}):
        check(f"gate/{gate['id']} has a why", bool(gate["why"]), True)
        check(f"gate/{gate['id']} has a detail", bool(gate["detail"]), True)
        n += 2
    return n


def test_no_selection_when_gated() -> int:
    n = 0
    d = build_decision({"8b": _model(is_mock=True)})
    check("dec/mock selects nothing", d["selected"], None)
    check("dec/mock names no approach", d["approach"], None)
    check("dec/mock fires gates", len(d["gates_fired"]) >= 1, True)
    n += 3

    # a clean, two-model, fully-classified setup DOES select
    d = build_decision({"8b": _model("8b", False, 0.0),
                        "70b": _model("70b", False, 0.0)})
    check("dec/clean setup selects a target", d["selected"] is not None, True)
    check("dec/selection is a real category",
          d["selected"] in ("politics", "law", "health", "geography",
                            "services", "history"), True)
    check("dec/selection has an approach", d["approach"] in ("A", "B", "C"), True)
    n += 3

    # the power analysis is attached either way - it is answerable now
    check("dec/power attached when clean",
          d["power"]["min_net_category"]["improvements_needed"], 6)
    n += 1
    return n


# ============================ 3. THE MATRIX CANNOT REWARD AN UNFIXABLE TARGET
def test_matrix_viability() -> int:
    n = 0
    d = build_decision({"8b": _model("8b", False, 0.0),
                        "70b": _model("70b", False, 0.0)})

    # HALLUC routes to LoRA, which cannot be built on an 8 GB card. Routing is
    # correct - that IS the right route for that error. What must be prevented
    # is SELECTING it, because Phase 3.3 would then attempt the one approach
    # the hardware rules out.
    hall = _model("8b", False, 0.0)
    hall["taxonomy"].pop("NUMERIC")
    hall["taxonomy"]["HALLUC"] = {
        "count": 10, "pct_of_content_errors": 100.0,
        "categories": {c: 10 for c in hall["scores"]["by_category"]},
        "examples": [], "n_deterministically_confirmed": 0, "classified": True,
        "desc": "d", "example_of_kind": "e", "fixability": 3, "by_difficulty": {}}
    d2 = build_decision({"8b": hall, "70b": _model("70b", False, 0.0)})
    for m in d2["matrix"]:
        check(f"viab/{m['category']} HALLUC routes to Option C", m["approach"], "C")
        check(f"viab/{m['category']} HALLUC flagged infeasible",
              m["infeasible_on_hardware"], True)
        check(f"viab/{m['category']} HALLUC not viable", m["viable"], False)
        n += 3
    check("viab/HALLUC-only selects nothing", d2["selected"], None)
    n += 1

    # the routing table itself
    check("route/PARSE is Option A", APPROACH["PARSE"][0], "A")
    check("route/PARSE says it is not Phase 3",
          "not a knowledge error" in APPROACH["PARSE"][1], True)
    check("route/HALLUC is LoRA", APPROACH["HALLUC"][0], "C")
    check("route/DE-CONF is RAG", APPROACH["DE-CONF"][0], "B")
    check("route/CANTON is RAG", APPROACH["CANTON"][0], "B")
    n += 5

    # an unclassified category is never viable
    u = _model("8b", False, 78.0)
    d3 = build_decision({"8b": u, "70b": _model("70b", False, 78.0)})
    check("viab/unclassified never selected", d3["selected"], None)
    n += 1
    return n


# ================================ 4. Q3 IS READ FROM DATA, NOT ASSERTED
def test_source_material() -> int:
    n = 0
    corpus = source_material()
    check("corpus/totals present", "_totals" in corpus, True)
    check("corpus/sources harvested", corpus["_totals"]["sources"] >= 50, True)
    check("corpus/facts harvested", corpus["_totals"]["facts"] >= 400, True)
    n += 3

    for cat in ("politics", "law", "health", "geography", "services", "history"):
        check(f"corpus/{cat} present", cat in corpus, True)
        c = corpus[cat]
        check(f"corpus/{cat} has facts", c["facts"] > 0, True)
        check(f"corpus/{cat} has raw files", c["raw_files_present"] > 0, True)
        check(f"corpus/{cat} sufficiency is a bool", isinstance(c["sufficient"], bool), True)
        n += 4
    check("corpus/politics best covered",
          corpus["politics"]["facts"] == max(
              corpus[c]["facts"] for c in
              ("politics", "law", "health", "geography", "services", "history")), True)
    n += 1
    return n


# --------------------------------------- 5. THE DOCUMENT ALWAYS ANSWERS Q5
def test_document() -> int:
    import importlib
    import select_target
    importlib.reload(select_target)
    n = 0
    gated = {"8b": _model(is_mock=True)}
    d = build_decision(gated)
    md = select_target.render(d, gated)
    check("doc/refuses when gated", "NO TARGET SELECTED" in md, True)
    check("doc/answers Q3 now", "answerable now" in md, True)
    check("doc/answers Q5 quantitatively", "McNemar" in md, True)
    check("doc/gives the power numbers", "6 of 14" in md, True)
    check("doc/separates intervention from measurement", "one INTERVENTION" in md, True)
    check("doc/states the n caveat", "n on everything" in md, True)
    check("doc/says what unblocks it", "What unblocks this" in md, True)
    n += 7

    clean = {"8b": _model("8b", False, 0.0), "70b": _model("70b", False, 0.0)}
    d2 = build_decision(clean)
    md2 = select_target.render(d2, clean)
    check("doc/selects when clean", "Selected target" in md2, True)
    check("doc/rejects the others", "rejected" in md2, True)
    n += 2
    return n


# ------------------------------------------------------------------------ main
def main() -> int:
    print("=" * 74)
    print("PHASE 3.2 VERIFICATION - target selection refuses when it should")
    print("=" * 74)
    groups = [
        ("statistical power is exact", test_power),
        ("gates block a selection", test_gates),
        ("no selection when gated", test_no_selection_when_gated),
        ("matrix cannot reward unfixable", test_matrix_viability),
        ("Q3 read from data", test_source_material),
        ("document always answers Q5", test_document),
    ]
    for name, fn in groups:
        before = checks
        try:
            fn()
        except Exception as exc:
            failures.append(f"{name}: raised {type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()
        print(f"  {name:<36} {checks - before:>6} checks")

    print("\n" + "=" * 74)
    print(f"total checks : {checks}")
    print("=" * 74)
    if failures:
        print(f"\nFAILURES: {len(failures)}")
        for f in failures[:30]:
            print(f"  {f}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

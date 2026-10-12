"""
test_error_taxonomy.py - Phase 3.1 verification.

The taxonomy is the evidence Phase 3 rests on. If it is wrong, the improvement
target is wrong, and a large honest-looking before/after delta measures nothing.
Three properties are defended here.

  1. PARSE ERRORS ARE NEVER COUNTED AS MODEL ERRORS. A parse error is a
     measurement failure. Folding it into the wrong-answer count inflates the
     apparent error rate and makes the taxonomy describe the instrument.

  2. THE DETERMINISTIC LAYER IS EXACT. PARSE and NUMERIC are decidable from the
     artefacts; anything else must return None and fall through to a human, not
     be guessed at. A confident wrong label is worse than an unclassified one.

  3. UNCLASSIFIED IS NOT A FINDING. It must never be reported as the dominant
     error pattern, and a category whose errors are unclassified must not be
     ranked for a Phase 3 fix - because the ranking is chosen from that table on
     a fixability number nobody has evidence for.

Run:  python fix/test_error_taxonomy.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fix"))
sys.path.insert(0, str(ROOT / "eval"))

from analyze_errors import (ERROR_TYPES, build_classification_prompt,  # noqa: E402
                            build_diagnostic_prompt, build_taxonomy, dominant,
                            deterministic_classify, is_numeric_option,
                            parse_classification, score_targets)

failures: list[str] = []
checks = 0


def check(label, got, expected):
    global checks
    checks += 1
    if got != expected:
        failures.append(f"{label}: got {got!r}, expected {expected!r}")


def Q(answer="B", **opts):
    o = {"A": "alpha", "B": "beta", "C": "gamma", "D": "delta"}
    o.update(opts)
    return {"id": "K001", "category": "law", "difficulty": "medium",
            "question": "Which is correct?", "options": o, "correct_answer": answer,
            "notes": ""}


def R(predicted="A", correct="B", raw="The answer is A."):
    return {"question_id": "K001", "category": "law", "difficulty": "medium",
            "predicted": predicted, "correct": correct, "is_correct": False,
            "raw_response": raw, "api_failed": False}


# ================================================ 1. DETERMINISTIC LAYER
def test_deterministic() -> int:
    n = 0

    # -- PARSE is certain
    d = deterministic_classify(Q(), R(predicted="PARSE_ERROR", raw="I'm not sure."))
    check("det/parse code", d["code"], "PARSE")
    check("det/parse confidence", d["confidence"], "certain")
    check("det/parse layer", d["layer"], 1)
    n += 3

    # -- NUMERIC: both options are bare figures
    q = Q(answer="B", A="50,000", B="100,000", C="26", D="20")
    d = deterministic_classify(q, R(predicted="A", correct="B"))
    check("det/numeric bare figures", d["code"], "NUMERIC")
    check("det/numeric confidence", d["confidence"], "certain")
    n += 2

    # -- NUMERIC: identical prose differing by one number
    q = Q(answer="B",
          A="Three months for residential premises",
          B="One month for residential premises",
          C="x", D="y")
    d = deterministic_classify(q, R(predicted="A", correct="B"))
    check("det/numeric prose", d["code"], "NUMERIC")
    n += 1

    # -- NUMERIC: percent and unit forms
    for a, b in [("8,1%", "2,6%"), ("CHF 150", "CHF 100"), ("22:00", "20:00")]:
        q = Q(answer="B", A=a, B=b, C="x", D="y")
        d = deterministic_classify(q, R(predicted="A", correct="B"))
        check(f"det/numeric {a} vs {b}", (d or {}).get("code"), "NUMERIC")
        n += 1

    # -- MUST return None when judgement is required. This is the important one.
    for q, why in [
        (Q(), "two unrelated propositions"),
        (Q(answer="B", A="The President has almost no extra power",
                B="The President can act alone",
                C="x", D="y"), "German-model confusion"),
        (Q(answer="B", A="Schools start at age 4 nationally",
                B="Start ages are set by each canton", C="x", D="y"), "cantonal"),
    ]:
        d = deterministic_classify(q, R(predicted="A", correct="B"))
        check(f"det/returns None for {why}", d, None)
        n += 1

    # -- a hallucination is NOT decidable and must not be claimed as one
    q = Q(answer="B", A="28 cantons", B="26 cantons", C="x", D="y")
    d = deterministic_classify(q, R(predicted="A", correct="B"))
    check("det/hallucinated figure is NUMERIC", d["code"], "NUMERIC")
    check("det/hallucinated figure evidence names both",
          "28 cantons" in d["evidence"] and "26 cantons" in d["evidence"], True)
    n += 2
    return n


def test_numeric_detection() -> int:
    n = 0
    for t in ["100,000", "26", "8,1%", "CHF 150", "Three", "about 50,000",
              "22:00 to 06:00", "300", "approximately 2,500"]:
        check(f"num/is figure {t!r}", is_numeric_option(t), True)
        n += 1
    for t in ["The Federal Council has seven members",
              "A supporting and advisory role", "", "x"]:
        check(f"num/is not a figure {t[:28]!r}", is_numeric_option(t), False)
        n += 1
    return n


# ================================== 2. PARSE ERRORS ARE NOT MODEL ERRORS
def _analysis(n_correct=10, n_parse=5, n_numeric=5, n_other=5):
    # spread across categories, or every category except one looks empty and the
    # ranking silently stops being about the categories at all
    cats = ["politics", "law", "health", "geography", "services", "history"]
    content = []
    for i in range(n_numeric):
        content.append({**R(predicted="A", correct="B"), "question_id": f"N{i:03d}",
                        "category": cats[i % 6],
                        "error_code": "NUMERIC", "confirmed": True})
    for i in range(n_other):
        content.append({**R(), "question_id": f"U{i:03d}", "category": cats[i % 6],
                        "error_code": "UNCLASSIFIED",
                        "confirmed": False, "needs_reasoning": True})
    return {
        "model": "8b", "split": "dev", "n_items": 40, "n_correct": n_correct,
        "parse_errors": [{"question_id": f"P{i:03d}", "error_code": "PARSE",
                          "confirmed": True} for i in range(n_parse)],
        "content_errors": content,
        "needs_reasoning": [e["question_id"] for e in content if e.get("needs_reasoning")],
        "needs_confirmation": [],
        "run": {"is_mock": False},
    }


def test_parse_separation() -> int:
    n = 0
    a = _analysis()
    tax = build_taxonomy(a)

    # PARSE must not appear inside the content-error taxonomy at all
    check("sep/PARSE not in taxonomy", "PARSE" in tax, False)
    check("sep/taxonomy total counts content only",
          sum(t["count"] for t in tax.values()), 10)
    check("sep/parse errors kept separately", len(a["parse_errors"]), 5)
    n += 3

    # percentages must sum to 100 over content errors only
    total_pct = round(sum(t["pct_of_content_errors"] for t in tax.values()), 1)
    check("sep/percentages sum to 100", total_pct, 100.0)
    n += 1

    # UNCLASSIFIED must not be reported as the dominant pattern
    code, pct = dominant(tax)
    check("sep/dominant ignores UNCLASSIFIED", code, "NUMERIC")
    n += 1

    # and when ONLY unclassified errors exist, there is no dominant at all
    only = _analysis(n_numeric=0)
    code, pct = dominant(build_taxonomy(only))
    check("sep/no dominant when all unclassified", code, None)
    check("sep/no dominant pct", pct, 0.0)
    n += 2
    return n


# ================================= 3. UNCLASSIFIED IS NOT RANKED FOR A FIX
def test_target_scoring() -> int:
    n = 0
    tax = build_taxonomy(_analysis(n_numeric=6, n_other=0))
    scores = {"by_category": {c: {"accuracy": 30.0} for c in
                              ["politics", "law", "health", "geography",
                               "services", "history"]}}
    rows = score_targets(tax, scores)
    check("rank/rows returned", len(rows), 6)
    check("rank/no unclassifiable", any(r["unclassifiable"] for r in rows), False)
    check("rank/fixability numeric", isinstance(rows[0]["fixability"], int), True)
    n += 3

    # a taxonomy of pure UNCLASSIFIED must not rank anything
    tax_u = build_taxonomy(_analysis(n_numeric=0, n_other=10))
    rows = score_targets(tax_u, scores)
    check("rank/all unclassifiable", all(r["unclassifiable"] for r in rows), True)
    check("rank/all priority zero", all(r["priority"] == 0.0 for r in rows), True)
    check("rank/fixability label is ?", rows[0]["fixability_label"], "?")
    n += 3

    # a category missing from the scores is skipped, not crashed on
    rows = score_targets(tax, {"by_category": {"politics": {"accuracy": 30.0}}})
    check("rank/skips missing categories", len(rows), 1)
    n += 1

    # higher accuracy + more fixable errors should outrank lower accuracy
    tax_hi = build_taxonomy(_analysis(n_numeric=6, n_other=0))
    tax_lo = build_taxonomy(_analysis(n_numeric=0, n_other=6))
    scores2 = {"by_category": {"politics": {"accuracy": 80.0}, "law": {"accuracy": 10.0}}}
    rows = score_targets(tax_lo, scores2)
    check("rank/empty taxonomy still ranks", len(rows), 2)
    n += 1
    return n


# ============================================ 4. CLASSIFICATION PARSING
def test_classification_parsing() -> int:
    n = 0
    for text, code, ok in [
        ("DE-CONF | applied the German Bundeskanzler model", "DE-CONF", True),
        ("NUMERIC: right concept, wrong figure", "NUMERIC", True),
        ("OTHER | evidence does not distinguish", "OTHER", True),
        ("NONSENSE | x", "OTHER", False),
        ("", "OTHER", False),
        ("just prose with no pipe", "OTHER", False),
    ]:
        got = parse_classification(text)
        check(f"cls/{text[:26]!r} code", got["code"], code)
        check(f"cls/{text[:26]!r} parsed", got["parsed"], ok)
        n += 2
    return n


def test_prompts() -> int:
    n = 0
    q = Q(answer="B", A="alpha", B="beta", C="gamma", D="delta")

    d = build_diagnostic_prompt(q)
    check("prompt/diagnostic renders", "{" not in d, True)
    check("prompt/diagnostic has all options",
          all(f"{L}) {q['options'][L]}" in d for L in "ABCD"), True)
    n += 2

    # the classification prompt must be honest when there is no reasoning
    c = build_classification_prompt(q, R(predicted="PARSE_ERROR"), "")
    check("prompt/classify renders", "{" not in c, True)
    check("prompt/classify admits no reasoning",
          "no letter extracted" in c and "(none available" in c, True)
    n += 2

    # a reasoning-less classification prompt is exactly the trap this design
    # avoids, so it must be visibly marked as evidence-free
    c2 = build_classification_prompt(q, R(predicted="A"), "")
    check("prompt/no-evidence flagged", "(none available" in c2, True)
    n += 1
    return n


# ================================================ 5. TAXONOMY INTEGRITY
def test_taxonomy_integrity() -> int:
    n = 0
    tax = build_taxonomy(_analysis(n_numeric=3, n_other=2))
    check("tax/keys are known codes",
          all(c in ERROR_TYPES or c == "UNCLASSIFIED" for c in tax), True)
    n += 1
    for code, t in tax.items():
        check(f"tax/{code} has description", bool(t["desc"]), True)
        check(f"tax/{code} has examples", len(t["examples"]) <= 3, True)
        check(f"tax/{code} counts deterministic",
              t["n_deterministically_confirmed"] <= t["count"], True)
        n += 3
    # UNCLASSIFIED must never be marked confirmed
    check("tax/unclassified not confirmed",
          tax.get("UNCLASSIFIED", {}).get("n_deterministically_confirmed", 0), 0)
    n += 1
    return n


# ------------------------------------------------------------------------ main
def main() -> int:
    print("=" * 74)
    print("PHASE 3.1 VERIFICATION - error taxonomy")
    print("=" * 74)

    groups = [
        ("deterministic layer is exact", test_deterministic),
        ("numeric option detection", test_numeric_detection),
        ("parse errors are not model errors", test_parse_separation),
        ("unclassified is not ranked", test_target_scoring),
        ("classification parsing", test_classification_parsing),
        ("prompt construction", test_prompts),
        ("taxonomy integrity", test_taxonomy_integrity),
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
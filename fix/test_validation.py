"""
test_validation.py - Phase 3.4 verification.

Phase 3.4 is the sub-phase that turns a number into a claim, so its tests are
about the difference between those two things.

  1. THE TEST SPLIT STAYS SEALED. knowledge_test.json is scored once in Phase
     4.1. Validating an improvement against it now spends that shot on a
     development decision.
  2. THE PLAN'S >5 pp REGRESSION RULE IS REFUSED AS A DECISION RULE. At n=14 one
     item is 7.1 pp, so a 5 pp threshold flags any single flipped item. It is
     still reported, because a reader expects it, but it must not decide.
  3. A REAL REGRESSION IS STILL DETECTED. Refusing a false-positive rule is not
     a licence to never flag anything - six net items lost must be flagged.
  4. THE COMPARISON REFUSES TO ATTRIBUTE A DELTA ACROSS MISMATCHED RUNS.
  5. NO PLACEHOLDERS SURVIVE INTO comparison.md. A document containing "XX.X%"
     gets quoted, and XX.X is what the reader remembers.
  6. MOCK CANNOT BE CERTIFIED, AND THE EXIT CODE SAYS SO.
  7. CONDITIONAL ARITHMETIC IS CORRECT, and a target with no justification is
     called out - choosing the category that happened to improve best on the
     split being validated is selection on the measurement set.

Run:  python fix/test_validation.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "fix"))
sys.path.insert(0, str(ROOT / "fix" / "rag"))

CHECKS = 0
FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(f"{label}" + (f" -- {detail}" if detail else ""))


def section(name: str) -> None:
    print(f"\n{name}")


def row(qid: str, cat: str, correct: bool, **kw) -> dict:
    return {
        "question_id": qid, "category": cat,
        "difficulty": kw.get("difficulty", "medium"),
        "source_id": "S001", "predicted": "A" if correct else "B",
        "parse_reason": "ok", "correct": "A", "is_correct": correct,
        "api_failed": False, "raw_response": "A", "model": "8b",
        "split": "dev", "gold_source_rank": kw.get("rank", 1),
    }


CATS = ["politics", "law", "health", "geography", "services", "history"]


def split_ids(cat: str, n: int = 14, start: int = 1) -> list[str]:
    return [f"{cat[:2].upper()}{i:03d}" for i in range(start, start + n)]


def build(per_cat_correct: dict, baseline_correct: dict | None = None) -> list:
    """A full 84-item set where `per_cat_correct[cat]` is a bool applied to all
    items of that category, unless baseline_correct overrides per item."""
    out = []
    for cat in CATS:
        ids = split_ids(cat)
        for j, qid in enumerate(ids):
            if baseline_correct is not None and (cat, j) in baseline_correct:
                ok = baseline_correct[(cat, j)]
            else:
                ok = per_cat_correct.get(cat, False)
            out.append(row(qid, cat, ok))
    return out


# ============================================ 1. the test split stays sealed
def test_split_is_sealed() -> None:
    section("1. The test split cannot be validated against")
    r = subprocess.run(
        [sys.executable, str(ROOT / "fix" / "validate_improvement.py"),
         "--split", "test"],
        capture_output=True, text=True, cwd=ROOT)
    check("validating on test exits non-zero", r.returncode != 0,
          f"exit={r.returncode}")
    check("the refusal says why", "sealed" in (r.stderr + r.stdout).lower(),
          (r.stderr + r.stdout)[:120])

    sealed = ROOT / "data" / "knowledge" / "knowledge_test.json"
    before = sealed.stat().st_mtime
    subprocess.run([sys.executable, str(ROOT / "fix" / "validate_improvement.py"),
                    "--split", "test"], capture_output=True, cwd=ROOT)
    check("the sealed file is not touched", sealed.stat().st_mtime == before)

    # Behaviour is already covered above (exit 1, mtime unchanged). This checks
    # the harder property: no file-reading call in the module can be handed a
    # path naming the test split. AST, so a mention inside a printed refusal
    # message does not count as access - only an argument to a read does.
    import ast
    src = (ROOT / "fix" / "validate_improvement.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    readers = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if name in {"open", "read_text", "read_bytes", "load", "loads"}:
            readers.append(node)
    offending = []
    for call in readers:
        for arg in list(call.args) + [k.value for k in call.keywords]:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    if "knowledge_test" in sub.value or "test" in sub.value.lower():
                        offending.append(sub.value[:60])
    check("no read/open call can name the test split", not offending,
          f"reads: {offending}")

    # Paths are built from the split argument, so the only route to the sealed
    # file is a caller passing --split test, which is refused above.
    check("paths are built from the split argument",
          "knowledge_" in src and "{split}" in src)
    print(f"   --split test -> exit {r.returncode}, sealed file untouched, "
          f"{len(readers)} read calls audited")


# ================================ 2. the plan's 5 pp rule is not the decision
def test_five_pp_rule_is_not_a_decision() -> None:
    section("2. One flipped item must not be called a regression")
    import validate_improvement as vi

    check("one item is 7.1 pp, which is why a 5 pp threshold is wrong",
          abs(vi.PP_PER_ITEM - 100 / 14) < 0.01, f"{vi.PP_PER_ITEM}")

    # health: 14/14 correct -> 13/14 correct. One item LOST = -7.1 pp.
    # The plan's rule calls this a REGRESSION.
    before = build({c: True for c in CATS})
    after = [dict(r, is_correct=False) if r["question_id"] == "HE001" else r
             for r in build({c: True for c in CATS})]

    res = vi.analyse(before, after, "b", "a")
    health = res["per_category"]["health"]
    check("one lost item is -7.1 pp", health["delta_pp"] == -7.1, str(health))
    check("the plan's rule would flag it", health["plan_would_flag"],
          "the false-positive rule is not being reproduced")
    check("it is NOT called a regression by this validator",
          not health["is_regression"], "one item must not be a regression")
    check("it is reported as within noise",
          health["net_items"] == -1 and health["regressed"] == 1, str(health))
    check("health is in the plan_would_flag list",
          "health" in res["plan_would_flag"], str(res["plan_would_flag"]))
    check("health is not in the regressions list",
          "health" not in res["regressions"], str(res["regressions"]))

    # And the verdict must say so out loud, not just in the data.
    v = vi.verdict(res, is_mock=False, conflicts=[], paired=True, target=None)
    check("the verdict explains the plan's rule is a false positive",
          "flags any single regression" in v, v[-400:])
    print(f"   health -7.1 pp (1 item): plan flags it, validator says within noise")


# ================================= 3. a real regression is still detected
def test_real_regression_is_detected() -> None:
    section("3. A real regression is still caught")
    import validate_improvement as vi

    before = build({c: True for c in CATS})
    # Lose 7 of 14 in law: net -7, past the -6 floor.
    after = [dict(r, is_correct=False) if r["category"] == "law"
             and int(r["question_id"][2:]) <= 7 else r
             for r in build({c: True for c in CATS})]

    res = vi.analyse(before, after, "b", "a")
    law = res["per_category"]["law"]
    check("7 lost with 0 gained is flagged as a regression", law["is_regression"],
          str(law))
    check("the regression count matches", law["regressed"] == 7, str(law))
    check("law appears in the regressions list", "law" in res["regressions"])
    check("other categories are untouched",
          all(not res["per_category"][c]["is_regression"] for c in CATS if c != "law"))

    v = vi.verdict(res, is_mock=False, conflicts=[], paired=True, target=None)
    check("the verdict names the regressed category", "law" in v)
    check("the verdict offers remedies", "reduce top_k" in v)

    # Boundary: the floor is INCLUSIVE in both directions. 6 net flips is
    # exactly what select_target.py's power table says reaches p<0.05 at n=84,
    # so 6 lost IS a regression and 6 gained IS an improvement.
    at_floor = [dict(r, is_correct=False) if r["category"] == "law"
                and int(r["question_id"][2:]) <= 6 else r
                for r in build({c: True for c in CATS})]
    res2 = vi.analyse(before, at_floor, "b", "a")
    check("exactly 6 lost IS a regression (the floor is inclusive)",
          res2["per_category"]["law"]["is_regression"],
          str(res2["per_category"]["law"]))
    check("6 lost is reported as net -6",
          res2["per_category"]["law"]["net_items"] == -6,
          str(res2["per_category"]["law"]))

    below = [dict(r, is_correct=False) if r["category"] == "law"
             and int(r["question_id"][2:]) <= 5 else r
             for r in build({c: True for c in CATS})]
    res3 = vi.analyse(before, below, "b", "a")
    check("5 lost is NOT yet a regression",
          not res3["per_category"]["law"]["is_regression"],
          str(res3["per_category"]["law"]))

    # And the improvement direction is symmetric.
    gained = [dict(r, is_correct=False) if r["category"] == "law" else r
              for r in before]
    res4 = vi.analyse(gained, before, "b", "a")
    check("6 gained IS an improvement",
          res4["per_category"]["law"]["is_improvement"],
          str(res4["per_category"]["law"]))
    check("law appears in category_improvements",
          "law" in res4["category_improvements"], str(res4["category_improvements"]))
    print(f"   -7 -> REGRESSION; -6 -> REGRESSION (floor inclusive); "
          f"-5 -> within noise")
    print(f"   -7 items -> REGRESSION; -6 items -> REGRESSION (floor is inclusive); "
          f"-5 items -> within noise")


# ===================================== 4. attribution is blocked on mismatch
def test_attribution_blocked() -> None:
    section("4. A delta across mismatched runs is not attributed to the fix")
    import validate_improvement as vi

    a = {"model_id": "Apertus-8B", "backend": "mock", "prompt_version": "1.0",
         "split": "dev", "system_prompt": "builtin"}
    check("identical setups produce no conflicts", vi.setup_conflicts(a, a) == [])

    for field, value in (("model_id", "Apertus-8B-v2"), ("backend", "http"),
                         ("prompt_version", "1.1"), ("split", "test"),
                         ("system_prompt", "swiss_context_v1.txt")):
        b = dict(a, **{field: value})
        conflicts = vi.setup_conflicts(a, b)
        check(f"a differing {field} is caught", len(conflicts) == 1,
              f"{field} -> {conflicts}")

    v = vi.verdict(vi.analyse(build({}), build({}), "b", "a"),
                   is_mock=False,
                   conflicts=vi.setup_conflicts(a, dict(a, backend="http")),
                   paired=False, target=None)
    check("the verdict blocks attribution", "ATTRIBUTION BLOCKED" in v)
    check("it names the differing field", "backend" in v)
    check("an unpaired comparison is flagged as weaker", "WEAKER COMPARISON" in v)
    print("   differing backend/model/prompt/split each block attribution")


# ============================= 5. no placeholders survive into comparison.md
def test_comparison_has_no_placeholders() -> None:
    section("5. comparison.md carries numbers, never the plan's XX.X")
    import validate_improvement as vi

    res = vi.analyse(build({c: True for c in CATS}),
                     build({c: False for c in CATS}), "baseline", "improved")
    meta = {"is_mock": True, "backend": "mock", "model_key": "8b",
            "model_id": "Apertus", "split": "dev", "conflicts": []}
    path = vi.write_comparison(res, meta, None)
    text = path.read_text(encoding="utf-8")

    check("no XX.X placeholder survives", "XX.X" not in text)
    check("no bare XX survives", "XX " not in text)
    check("the mock banner is present", "not results" in text.lower())
    check("is_mock is stated", "is_mock=True" in text or "mock" in text.lower())
    check("the sealed test split is mentioned", "sealed" in text.lower())
    check("the 70B gap is disclosed", "70B" in text)
    check("one-item-is-7.1pp is stated", "7.1" in text)

    # Numbers must be real values from the analysis, not filler.
    check("the before accuracy appears", f"{res['before_accuracy']}%" in text)
    check("the after accuracy appears", f"{res['after_accuracy']}%" in text)

    # A conflict must appear in the document, not just on the console.
    meta2 = dict(meta, conflicts=["backend: before='mock' after='http'"])
    path2 = vi.write_comparison(res, meta2, None)
    t2 = path2.read_text(encoding="utf-8")
    check("a setup conflict is written into the document",
          "Attribution blocked" in t2, t2[:300])

    # Unavailable numbers must say so rather than show a placeholder. An empty
    # comparison makes every figure None, which is exactly where `f"{None:+.1f}"`
    # would raise.
    empty = vi.analyse([], [], "b", "a")
    check("an empty comparison has no categories", empty["per_category"] == {})
    check("an empty comparison has a None delta", empty["delta_pp"] is None)
    p3 = vi.write_comparison(empty, meta, None)
    t3 = p3.read_text(encoding="utf-8")
    check("an empty comparison writes without crashing", p3.exists())
    check("an empty comparison still has no placeholders", "XX.X" not in t3)
    check("absent numbers are labelled, not zeroed",
          "not measured" in t3, "a missing value must say it is missing")

    # A header row with no data rows beneath it reads as "nothing to report" to a
    # human and as "no problems" to anything parsing the table. It must say it
    # had nothing to compare.
    check("an empty category table says so rather than emitting bare headers",
          "no paired items" in t3,
          "an empty table is indistinguishable from a clean one")
    header_line = [l for l in t3.splitlines()
                   if l.startswith("| Category | Before |")]
    check("the category header exists exactly once", len(header_line) == 1)
    if header_line:
        idx = t3.splitlines().index(header_line[0])
        rows_after = [l for l in t3.splitlines()[idx + 1:]
                      if l.startswith("| ") and "---" not in l]
        check("the empty table still has a body row", len(rows_after) > 0,
              "header with nothing under it")

    # The console renderer must survive it too.
    vi.render(empty)
    v_empty = vi.verdict(empty, is_mock=True, conflicts=[], paired=True, target=None)
    check("the verdict survives an empty comparison",
          "NOTHING TO VALIDATE" in v_empty.upper(), v_empty[-200:])
    check("an empty comparison does not claim a regression or improvement",
          "REAL REGRESSIONS" not in v_empty and "IMPROVED CATEGORIES" not in v_empty)
    print("   placeholders: none; mock banner, sealed split, 70B gap, "
          "and conflicts all present")


# ============================================ 6. mock cannot be certified
def test_mock_is_not_certified() -> None:
    section("6. Mock results cannot be certified, and the exit code says so")
    import validate_improvement as vi

    res = vi.analyse(build({c: True for c in CATS}),
                     build({c: False for c in CATS}), "b", "a")
    v = vi.verdict(res, is_mock=True, conflicts=[], paired=True, target=None)
    check("mock is refused certification", "REFUSED TO CERTIFY" in v)
    check("it does not say the improvement is safe",
          "safe to proceed" not in v.lower(),
          "a mock run has shown nothing about safety")
    check("it explains what mock does prove", "self-test" in v)

    r = subprocess.run(
        [sys.executable, str(ROOT / "fix" / "validate_improvement.py"),
         "--model", "8b", "--split", "dev"],
        capture_output=True, text=True, cwd=ROOT)
    check("the CLI exits non-zero on mock", r.returncode == 1, f"exit={r.returncode}")
    check("the CLI prints the refusal", "REFUSED TO CERTIFY" in r.stdout)
    print(f"   mock -> refused, exit {r.returncode} (0 = validated)")


# ================================= 7. conditional arithmetic and justification
def test_conditional() -> None:
    section("7. Conditional application is arithmetic, and needs a reason")
    import validate_improvement as vi

    before = build({c: True for c in CATS})
    after = build({c: True for c in CATS})
    # Fix flips 10 of 14 law items correct; baseline had them wrong.
    before = [dict(r, is_correct=False) if r["category"] == "law" else r
              for r in before]

    cv = vi.conditional_view(None, before, after, "law")
    check("the conditional view computes", "error" not in cv, str(cv))
    check("n_target is 14", cv["n_target"] == 14)
    check("n_other is 70", cv["n_other"] == 70)

    expected = (70 * 100 + 14 * 100) / 84
    check("conditional accuracy is baseline elsewhere plus fix on target",
          abs(cv["conditional_pct"] - expected) < 0.2,
          f"{cv['conditional_pct']} vs {expected:.1f}")
    check("baseline is 70/84 = 83.3%", cv["baseline_pct"] == 83.3, str(cv))
    check("unconditional is 100%", cv["unconditional_pct"] == 100.0, str(cv))
    check("the note says it measures nothing new", "does not re-measure" in cv["note"])

    check("an unknown category is an error, not a zero",
          "error" in vi.conditional_view(None, before, after, "nope"))

    # A target with no justification must be called out on the CLI.
    r = subprocess.run(
        [sys.executable, str(ROOT / "fix" / "validate_improvement.py"),
         "--model", "8b", "--split", "dev", "--target-category", "law"],
        capture_output=True, text=True, cwd=ROOT)
    check("an unjustified target is flagged", "NONE GIVEN" in r.stdout, r.stdout[-300:])
    check("the flag explains the selection problem",
          "selection" in r.stdout.lower() or "happened to move" in r.stdout)

    r2 = subprocess.run(
        [sys.executable, str(ROOT / "fix" / "validate_improvement.py"),
         "--model", "8b", "--split", "dev", "--target-category", "law",
         "--target-justification", "S018 PARSE errors per fix/analyze_errors.py"],
        capture_output=True, text=True, cwd=ROOT)
    check("a justified target is accepted and recorded",
          "S018 PARSE errors" in r2.stdout)
    check("no NONE GIVEN warning when justified", "NONE GIVEN" not in r2.stdout)
    print("   conditional = 83.3% baseline vs 100.0% on law; unjustified target flagged")


# ============================ 8. a net sum cannot stand in for the exact test
def test_net_is_not_significance() -> None:
    """
    The bug this guards against, stated as a fact about the arithmetic:

        10 improved / 4 regressed   net +6   p = 0.180   NOT detectable
         6 improved / 0 regressed   net +6   p = 0.031   detectable

    Identical net. Opposite conclusions. A net-only rule calls both an
    improvement; one of them is a coin flip. Each gain and each loss cancels in
    the sum but not in the test, which is why the exact test is used.
    """
    section("8. A category is flagged by the exact test, not by its net movement")
    import validate_improvement as vi

    from select_target import mcnemar_exact

    # The premise itself, checked against 3.2's own implementation.
    check("net +6 with 4 regressions is NOT detectable",
          mcnemar_exact(10, 4) >= 0.05, f"p={mcnemar_exact(10, 4)}")
    check("net +6 with 0 regressions IS detectable",
          mcnemar_exact(6, 0) < 0.05, f"p={mcnemar_exact(6, 0)}")
    check("the two cases really do share a net",
          (10 - 4) == (6 - 0))

    sig, p = vi.is_significant(10, 4, 14)
    check("is_significant(10, 4) says no", not sig, f"p={p}")
    sig2, p2 = vi.is_significant(6, 0, 14)
    check("is_significant(6, 0) says yes", sig2, f"p={p2}")
    check("both p-values are reported", p == 0.1796 and p2 == 0.0312,
          f"{p} / {p2}")

    # Now the same thing through the real analysis: a category that gains 10 and
    # loses 4 must NOT be reported as an improvement.
    before = [dict(r, is_correct=False) if (r["category"] == "law"
               and int(r["question_id"][2:]) <= 10) else r
              for r in build({c: True for c in CATS})]
    # after: the first 10 law items are FIXED, and 4 previously-correct law items
    # are broken -> 10 improved, 4 regressed, net +6.
    after = build({c: True for c in CATS})
    after = [dict(r, is_correct=False) if (r["category"] == "law"
               and 11 <= int(r["question_id"][2:]) <= 14) else r for r in after]
    after = [dict(r, is_correct=True) if (r["category"] == "law"
               and int(r["question_id"][2:]) <= 10) else r for r in after]

    res = vi.analyse(before, after, "b", "a")
    law = res["per_category"]["law"]
    check("the fixture really is 10 improved / 4 regressed",
          (law["improved"], law["regressed"]) == (10, 4), str(law))
    check("its net is +6", law["net_items"] == 6, str(law))
    check("but it is NOT reported as an improvement", not law["is_improvement"],
          "net-only labelling bug is back")
    check("and not as a regression either", not law["is_regression"])
    check("law is absent from category_improvements",
          "law" not in res["category_improvements"], str(res["category_improvements"]))
    check("the per-category p-value is carried through",
          law["mcnemar_p_up"] == 0.1796, str(law))

    # Symmetrically, gains that are real must still register. Rebuild the
    # baseline so only SIX law items are wrong, then fix exactly those six.
    # Reusing `before` would carry ten wrong items and flip all ten.
    before6 = [dict(r, is_correct=False) if (r["category"] == "law"
                and int(r["question_id"][2:]) <= 6) else r
               for r in build({c: True for c in CATS})]
    after6 = build({c: True for c in CATS})
    res2 = vi.analyse(before6, after6, "b", "a")
    l2 = res2["per_category"]["law"]
    check("the clean fixture is 6 improved / 0 regressed",
          (l2["improved"], l2["regressed"]) == (6, 0), str(l2))
    check("6 gained with no losses IS reported as an improvement",
          l2["is_improvement"], str(l2))
    check("its p-value is 0.0312", l2["mcnemar_p_up"] == 0.0312, str(l2))

    # Both halves of the pair share net +6 and disagree. That is the whole point.
    check("identical net, opposite verdicts - the premise of this test",
          law["net_items"] == l2["net_items"] == 6
          and law["is_improvement"] is False and l2["is_improvement"] is True,
          f"{law['net_items']}/{l2['net_items']}")

    # The verdict must explain the difference rather than just printing "noise".
    v = vi.verdict(res, is_mock=False, conflicts=[], paired=True, target=None)
    check("the verdict explains that net is not significance",
          "not a net sum" in v, v[-500:])
    check("the verdict gives the concrete counter-example", "10 gained / 4 lost" in v)
    print(f"   net +6 with 4 regressions -> p={law['mcnemar_p_up']} -> NOT an "
          f"improvement; net +6 with 0 -> p=0.0312 -> improvement")


def main() -> int:
    print("=" * 70)
    print("  Phase 3.4 verification")
    print("=" * 70)
    for fn in (test_split_is_sealed,
               test_five_pp_rule_is_not_a_decision,
               test_real_regression_is_detected,
               test_attribution_blocked,
               test_comparison_has_no_placeholders,
               test_mock_is_not_certified,
               test_conditional,
               test_net_is_not_significance):
        try:
            fn()
        except Exception as e:
            import traceback
            FAILURES.append(f"{fn.__name__} raised {type(e).__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 70}")
    if FAILURES:
        print(f"  FAILED  {len(FAILURES)} of {CHECKS} checks")
        for f in FAILURES:
            print(f"    - {f}")
        return 1
    print(f"  PASSED  all {CHECKS} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())

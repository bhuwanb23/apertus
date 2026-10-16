"""
test_baseline_report.py - Phase 2.5 verification.

A validation tool is only worth what its failures are worth. If every check
passes no matter what the results look like, it is decoration: it produces a
comfortable green report on a broken run, which is the exact failure mode this
project has spent three phases guarding against.

So this suite feeds the report deliberately broken runs and asserts it objects.
Each of the nine failure modes in docs/plans/phase_2.md §2.5 gets a synthetic
result set that should trip exactly its own check - and no others.

Run:  python eval/test_baseline_report.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The sandbox MUST come before any import of a module that writes. config itself
# is inert, so importing it first is safe; baseline_report pulls in client, which
# calls setup_logging() as an import side effect, so it must land inside the
# redirect or every run drops a log file into the real eval/results/logs.
from config import results_sandbox, snapshot_diff, snapshot_results_tree  # noqa: E402

SUITE_RESULTS, SUITE_START_DIGESTS = results_sandbox("baseline_report_")

# Imported AFTER the redirect, so these are the sandbox's paths, not the
# repository's. Every fixture below is written through them.
from config import PARSED_DIR, SCORES_DIR, config      # noqa: E402

failures: list[str] = []
checks = 0

CATEGORIES = ["politics", "law", "health", "geography", "services", "history"]


def check(label, got, expected):
    global checks
    checks += 1
    if got != expected:
        failures.append(f"{label}: got {got!r}, expected {expected!r}")


# --------------------------------------------------------------- fixtures
def _scores(**over):
    """A healthy full-dev knowledge score block; override one field at a time."""
    s = {
        "overall": 55.0, "total_questions": 84, "correct": 46,
        "parse_errors": 0, "parse_error_rate": 0.0, "api_errors": 0,
        "chance_level": 25.0,
        "by_category": {c: {"accuracy": 55.0, "correct": 8, "total": 14}
                        for c in CATEGORIES},
        "by_difficulty": {}, "by_correct_answer": {},
        "backend": "http", "is_mock": False,
    }
    s.update(over)
    return s


def _run(**over):
    r = {
        "model_key": "8b", "model_id": "test", "backend": "http", "is_mock": False,
        "prompt_version": "1.0", "split": "dev", "n_questions": 84,
        "condition": "before",
        "request_params": {"model": "test", "backend": "http",
                           "temperature": 0.0, "top_p": 1.0, "seed": 42,
                           "max_tokens": 512},
    }
    r.update(over)
    return r


def _results(n=84, predicted=None, split_letters=False):
    out = []
    letters = "ABCD"
    for i in range(n):
        if predicted is not None:
            p = predicted
        elif split_letters:
            p = letters[i % 4]
        else:
            p = letters[i % 4]
        cat = CATEGORIES[i % 6]
        out.append({"question_id": f"K{i + 1:03d}", "category": cat,
                    "difficulty": "medium", "predicted": p,
                    "correct": letters[i % 4], "is_correct": p == letters[i % 4],
                    "api_failed": False, "raw_response": "x", "model": "8b",
                    "split": "dev"})
    return out


def _write(model, scores=None, run=None, results=None, task="knowledge"):
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{task}_{model}_dev_base" if task == "knowledge" else f"{task}_{model}"
    if task == "knowledge":
        parsed = PARSED_DIR / f"{tag}.json"
        scorefile = SCORES_DIR / f"{tag}.json"
        _assert_in_sandbox(parsed)
        _assert_in_sandbox(scorefile)
        parsed.write_text(
            json.dumps({"run": run or _run(), "results": results or _results()}), encoding="utf-8")
        scorefile.write_text(
            json.dumps({"run": run or _run(), "scores": scores or _scores()}), encoding="utf-8")


def _clean():
    """Remove every artefact the report reads, including raw responses.

    Without this the suite's expectations depend on whatever a previous test in
    this file happened to leave behind - a test that passes because of leftover
    state is not a test.

    The isolation is still needed. What changed is the blast radius: PARSED_DIR,
    SCORES_DIR and config.results_dir now point into the suite's own temp
    directory (see results_sandbox() at the top of this file), so this deletes
    fixtures, never results. It used to aim at the real eval/results tree, which
    meant running this suite deleted the benchmark.

    _assert_in_sandbox() is the belt to that braces: every single file this
    function is about to unlink is checked against the sandbox root first, so a
    future path change fails loudly here instead of silently eating real
    artefacts again.
    """
    doomed = []
    for d in (PARSED_DIR, SCORES_DIR):
        if d.is_dir():
            doomed += list(d.glob("*.json"))
    raw = config.results_dir / "raw_responses"
    if raw.is_dir():
        doomed += list(raw.rglob("*.json"))

    for f in doomed:
        _assert_in_sandbox(f)
        f.unlink()


def _assert_in_sandbox(path: Path) -> None:
    try:
        path.resolve().relative_to(SUITE_RESULTS.resolve())
    except ValueError:
        raise AssertionError(
            f"refusing to touch {path}: it is outside the suite sandbox "
            f"{SUITE_RESULTS}. This suite must never write to eval/results.")


def _run_report():
    """Run the report in-process and return its recorded checks."""
    import baseline_report
    importlib.reload(baseline_report)
    baseline_report.results.clear()
    baseline_report.post_run(["8b"])
    return {item: status for item, status, _ in baseline_report.results}


# ========================================== 1. A HEALTHY RUN PASSES
def test_healthy_run_passes() -> int:
    _clean()
    _write("8b")
    r = _run_report()
    fails = [i for i, s in r.items() if s == "FAIL"]
    # The only legitimate failure on a healthy score block is the missing raw
    # responses, which this fixture deliberately does not create - checked
    # separately below, so it is excluded here rather than silently tolerated.
    check("healthy/only raw-coverage fails",
          [f for f in fails if "raw response" not in f.lower()], [])
    check("healthy/parse rate passes", r.get("8B: parse error rate"), "PASS")
    check("healthy/categories pass", r.get("8B: all 6 categories present"), "PASS")
    check("healthy/letters pass", r.get("8B: answer letters not collapsed"), "PASS")
    check("healthy/accuracy pass", r.get("8B: accuracy plausible"), "PASS")
    # the healthy fixture writes no raw responses, so this check must fail -
    # proving the coverage check has teeth rather than trusting a leftover run
    check("healthy/raw coverage fires without raw files",
          r.get("8B: raw response per scored item"), "FAIL")
    return 6


# ================== 2. EVERY FAILURE MODE IN THE PLAN'S TABLE IS DETECTED
def test_failure_modes() -> int:
    n = 0

    # -- "Parse error rate >20%"
    _clean()
    _write("8b", scores=_scores(parse_errors=25, parse_error_rate=25.0))
    r = _run_report()
    check("fp/parse error >20% fails", r.get("8B: parse error rate"), "FAIL")
    n += 1

    # -- "Parse error rate >10% but <20%" is a warning, not a failure
    _clean()
    _write("8b", scores=_scores(parse_errors=12, parse_error_rate=12.0))
    r = _run_report()
    check("fp/parse error 10-20% warns", r.get("8B: parse error rate"), "WARN")
    n += 1

    # -- "All answers are A"
    _clean()
    _write("8b", results=_results(predicted="A"))
    r = _run_report()
    check("fp/letter collapse fails", r.get("8B: answer letters not collapsed"), "FAIL")
    n += 1

    # -- "Scores look too high (>90%)"
    _clean()
    _write("8b", scores=_scores(overall=95.0))
    r = _run_report()
    check("fp/too high warns", r.get("8B: accuracy plausible"), "WARN")
    n += 1

    # -- "Scores look too low (<20%)"
    _clean()
    _write("8b", scores=_scores(overall=12.0))
    r = _run_report()
    check("fp/too low warns", r.get("8B: accuracy plausible"), "WARN")
    n += 1

    # -- api errors are a hard failure: infrastructure is not a score
    _clean()
    _write("8b", scores=_scores(api_errors=3))
    r = _run_report()
    check("fp/api errors fail", r.get("8B: api errors"), "FAIL")
    n += 1

    # -- mock results can never be reported
    _clean()
    _write("8b", run=_run(is_mock=True))
    r = _run_report()
    check("fp/mock fails", r.get("8B: NOT a result (mock)"), "FAIL")
    n += 1

    # -- running the SEALED test split is a hard failure
    _clean()
    _write("8b", run=_run(split="test"), scores=_scores())
    r = _run_report()
    check("fp/test split fails", r.get("8B: ran on dev, not test"), "FAIL")
    n += 1

    # -- a dropped category is caught
    _clean()
    # a FULL run (n=84) whose breakdown is missing a category. n must stay 84,
    # or the partial-run branch takes over and the full-run rule never fires.
    bad = _scores(total_questions=84)
    bad["by_category"] = {c: v for c, v in bad["by_category"].items() if c != "history"}
    _write("8b", scores=bad)
    r = _run_report()
    check("fp/missing category fails", r.get("8B: all 6 categories present"), "FAIL")
    n += 1

    # -- aggregation that loses rows
    _clean()
    lost = _scores()
    lost["by_category"] = {c: {"accuracy": 50.0, "correct": 7, "total": 14}
                           for c in CATEGORIES}
    _write("8b", scores=lost)   # 6x14 = 84, so this one is fine...
    r = _run_report()
    check("fp/row loss detected when it happens",
          r.get("8B: no rows dropped in aggregation"), "PASS")
    lost2 = _scores()
    lost2["by_category"] = {c: {"accuracy": 50.0, "correct": 7, "total": 12}
                            for c in CATEGORIES}   # 72 != 84
    _write("8b", scores=lost2)
    r = _run_report()
    check("fp/row loss fails when real", r.get("8B: no rows dropped in aggregation"), "FAIL")
    n += 2
    return n


# ================================== 3. PARTIAL RUNS ARE NOT HELD TO FULL RULES
def test_partial_runs() -> int:
    n = 0
    _clean()
    partial = _scores(total_questions=40, overall=30.0)
    partial["by_category"] = {c: {"accuracy": 30.0, "correct": 3, "total": 7}
                             for c in ["politics", "law", "health"]}
    _write("8b", scores=partial, run=_run(n_questions=40), results=_results(n=40))
    r = _run_report()
    check("partial/relaxed to INFO",
          r.get("8B: category coverage (partial run)"), "INFO")
    check("partial/not a FAIL",
          r.get("8B: all 6 categories present"), None)
    n += 2

    # the comparison table must not name a Phase 3 target from a partial run
    import baseline_report
    importlib.reload(baseline_report)
    table = baseline_report.comparison_table(["8b"])
    check("partial/table says partial", "partial run" in table, True)
    check("partial/table not definitive target",
          "WEAKEST CATEGORY:" in table, False)
    n += 2
    return n


# ================================= 4. CROSS-MODEL COMPARISON IS NOT VACUOUS
def test_cross_model() -> int:
    import baseline_report
    n = 0
    importlib.reload(baseline_report)
    baseline_report.results.clear()
    _clean()
    _write("8b")
    _write("70b")
    baseline_report.cross_model_note(["8b", "70b"])
    r = {i: s for i, s, _ in baseline_report.results}
    check("cross/identical conditions pass", r.get("identical evaluation conditions"), "PASS")
    n += 1

    # differing conditions must fail
    baseline_report.results.clear()
    importlib.reload(baseline_report)
    _clean()
    _write("8b")
    _write("70b", run=_run(request_params={"temperature": 0.7, "top_p": 1.0,
                                           "seed": 7, "max_tokens": 512}))
    baseline_report.cross_model_note(["8b", "70b"])
    r = {i: s for i, s, _ in baseline_report.results}
    check("cross/differing temp fails", r.get("identical evaluation conditions"), "FAIL")
    n += 1

    # a run block with no request_params must FAIL, not pass on None == None
    baseline_report.results.clear()
    importlib.reload(baseline_report)
    _clean()
    bare = _run()
    bare.pop("request_params")
    _write("8b", run=bare)
    _write("70b")
    baseline_report.cross_model_note(["8b", "70b"])
    r = {i: s for i, s, _ in baseline_report.results}
    check("cross/missing params fails", r.get("identical evaluation conditions"), "FAIL")
    n += 1
    return n


# ================================ 5. THE COMPARISON TABLE MATCHES THE DATA
def test_comparison_table() -> int:
    import baseline_report
    importlib.reload(baseline_report)
    n = 0
    _clean()

    hi = _scores(overall=70.0)
    hi["by_category"] = {c: {"accuracy": 70.0, "correct": 10, "total": 14}
                         for c in CATEGORIES}
    lo = _scores(overall=40.0)
    lo["by_category"] = {c: {"accuracy": 40.0, "correct": 6, "total": 14}
                         for c in CATEGORIES}
    lo["by_category"]["health"] = {"accuracy": 10.0, "correct": 1, "total": 14}
    _write("8b", scores=hi)
    _write("70b", scores=lo)
    table = baseline_report.comparison_table(["8b", "70b"])
    check("table/8B overall shown", "70.0%" in table, True)
    check("table/70B overall shown", "40.0%" in table, True)
    check("table/delta computed", "-30.0" in table, True)
    check("table/weakest is health", "WEAKEST CATEGORY: health" in table, True)
    check("table/all six rows present",
          sum(1 for c in CATEGORIES if f"\n{c:<14}" in table), 6)
    n += 5
    _clean()
    return n


# ================================ 6. VALUES / DIALECT CHECKS FIRE
def test_values_and_dialect_checks() -> int:
    n = 0
    SCORES_DIR.mkdir(parents=True, exist_ok=True)

    # -- "Judge gives all 2s" / "all 0s"
    for dist, label in (({"0": 0, "1": 0, "2": 73}, "all 2s"),
                        ({"0": 73, "1": 0, "2": 0}, "all 0s")):
        (SCORES_DIR / "values_8b.json").write_text(json.dumps({
            "run": _run(task="values", judge_model="70b", judge_is_self_evaluated=False),
            "scores": {"n_scored": 73, "n_unscored": 0, "distribution": dist,
                       "pairs_with_depth_ratio": 10, "pairs_total": 10},
        }), encoding="utf-8")
        r = _run_report()
        check(f"fp/judge {label} warns", r.get("8B: judge not degenerate"), "WARN")
        n += 1

    # -- self-evaluation must be disclosed
    (SCORES_DIR / "values_8b.json").write_text(json.dumps({
        "run": _run(task="values", judge_model="8b", judge_is_self_evaluated=True),
        "scores": {"n_scored": 73, "n_unscored": 0,
                   "distribution": {"0": 30, "1": 20, "2": 23},
                   "pairs_with_depth_ratio": 10, "pairs_total": 10},
    }), encoding="utf-8")
    r = _run_report()
    check("fp/judge circularity warns", r.get("8B: judge circularity"), "WARN")
    n += 1

    # -- unusable DSG pairs
    (SCORES_DIR / "values_8b.json").write_text(json.dumps({
        "run": _run(task="values", judge_model="70b", judge_is_self_evaluated=False),
        "scores": {"n_scored": 73, "n_unscored": 0,
                   "distribution": {"0": 30, "1": 20, "2": 23},
                   "pairs_with_depth_ratio": 9, "pairs_total": 10,
                   "pairs_unusable_for_dsg": 1,
                   "pairs_unusable_detail": {"VP001": {"english_baseline_n_present": 0}}},
    }), encoding="utf-8")
    r = _run_report()
    check("fp/unusable DSG pairs warn", r.get("8B: DSG pairs"), "WARN")
    n += 1

    # -- dialect refusal rate is reported as INFO, and always present
    (SCORES_DIR / "dialect_8b.json").write_text(json.dumps({
        "run": _run(task="dialect"),
        "scores": {"n_items": 30, "refusal_rate": 13.3, "n_refused": 4,
                   "mcq_parse_errors": 0},
    }), encoding="utf-8")
    r = _run_report()
    check("fp/refusal rate reported", r.get("8B: dialect refusal rate"), "INFO")
    n += 1

    _clean()
    return n


# ================================================== 7. PRE-RUN CHECKLIST
def test_pre_run() -> int:
    import baseline_report
    importlib.reload(baseline_report)
    baseline_report.results.clear()
    baseline_report.pre_run()
    r = {i: s for i, s, _ in baseline_report.results}
    check("pre/knowledge all 120", r.get("knowledge all = 120"), "PASS")
    check("pre/values 30", r.get("values scenarios = 30"), "PASS")
    check("pre/dialect present", r.get("dialect items present"), "PASS")
    check("pre/no dev/test overlap", r.get("dev/test no overlap"), "PASS")
    check("pre/temperature is 0", r.get("config: temperature is 0 on every model"), "PASS")
    # Reachability expectations are DERIVED from the configured backend, not
    # hardcoded. The three outcomes are all correct in their own situation:
    #   mock  -> WARN  (no live model; baselines impossible)
    #   live + server up   -> PASS
    #   live + server down -> FAIL  (this is the check that saves a 2-hour run)
    #
    # This test previously asserted WARN unconditionally, which was only true
    # while both models were on mock. Once 8B became a real http endpoint the
    # assertion tested the environment rather than the code - and FAIL is the
    # correct answer until llama-server is actually running.
    for key in ("8b", "70b"):
        m = config.MODELS[key]
        label = f"endpoint reachable: {key}"
        got = r.get(label)
        if m.is_mock:
            check(f"pre/mock endpoint {key} warns", got, "WARN")
        elif got == "PASS":
            check(f"pre/live endpoint {key} reachable", got, "PASS")
        else:
            # Server not running yet - FAIL is the correct, protective verdict.
            check(f"pre/unreachable live endpoint {key} fails loudly", got, "FAIL")
    _clean()
    return 8


# ================================= 8. THE SUITE NEVER TOUCHES THE REAL RESULTS
def test_real_results_untouched() -> int:
    """
    The invariant this file exists to protect, asserted on itself.

    This suite used to delete the benchmark. _clean() unlinked every *.json in
    results/parsed, results/scores and results/raw_responses, so a routine test
    run removed knowledge_8b_dev_base.json along with the artefacts written
    during the Phase 4.1 test run. The suite still passed, because it only ever
    checked its own fixtures - the destruction was invisible from inside.

    So the check is the whole real tree, sha256 per file, snapshot taken before
    the redirect and compared after every group has run. Digests are the direct
    statement of the invariant: "the bytes on disk are the bytes that were
    there".
    """
    n = 0
    after = snapshot_results_tree()
    problems = snapshot_diff(SUITE_START_DIGESTS, after)
    check("real results tree is byte-identical after the suite ran",
          problems, [])

    # and the sandbox is genuinely somewhere else
    from config import REAL_RESULTS_DIR
    check("sandbox is outside the real results tree",
          not SUITE_RESULTS.is_relative_to(REAL_RESULTS_DIR)
          and not REAL_RESULTS_DIR.is_relative_to(SUITE_RESULTS), True)
    check("sandbox is outside eval/ entirely",
          not SUITE_RESULTS.is_relative_to(Path(__file__).resolve().parent), True)
    check("parsed dir points into the sandbox",
          PARSED_DIR.is_relative_to(SUITE_RESULTS), True)
    check("scores dir points into the sandbox",
          SCORES_DIR.is_relative_to(SUITE_RESULTS), True)
    check("results_dir points into the sandbox",
          config.results_dir.is_relative_to(SUITE_RESULTS), True)
    n += 5
    return n


# ------------------------------------------------------------------------ main
def main() -> int:
    print("=" * 74)
    print("PHASE 2.5 VERIFICATION - baseline checks must actually fail")
    print("=" * 74)
    print(f"  sandbox      : {SUITE_RESULTS}")

    groups = [
        ("healthy run passes", test_healthy_run_passes),
        ("every failure mode detected", test_failure_modes),
        ("partial runs relaxed", test_partial_runs),
        ("cross-model not vacuous", test_cross_model),
        ("comparison table matches data", test_comparison_table),
        ("values + dialect checks", test_values_and_dialect_checks),
        ("pre-run checklist", test_pre_run),
        ("real results untouched", test_real_results_untouched),
    ]
    for name, fn in groups:
        before = checks
        try:
            fn()
        except Exception as exc:
            failures.append(f"{name}: raised {type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()
        print(f"  {name:<34} {checks - before:>6} checks")

    _clean()
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
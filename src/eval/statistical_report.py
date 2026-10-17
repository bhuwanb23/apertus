"""
statistical_report.py - Phase 4.2: the numbers, and how much they can carry.

WHAT THIS FIXES IN THE PLAN

docs/plans/phase_4.md 4.2 Step 1 computes three things and gets one of them
subtly wrong:

    b = accuracy_and_ci(k_8b_base)
    i = accuracy_and_ci(k_8b_imp)
    delta = i["accuracy"] - b["accuracy"]
    ...
    ci = f"±{i['ci_range']/2:.1f}"     # printed in the DELTA column

That last line is the bug. It prints the improved arm's own confidence interval
next to the delta, as though it bounded the change. It does not. The delta of two
arms has its own interval, and a wider one, because it accumulates uncertainty
from both.

It also treats the arms as independent, which they are not: baseline and
improved answer the SAME 36 questions, so they are paired. For paired binary
outcomes the correct test is McNemar, which this project has used since Phase
3.2, and the correct interval for the difference is derived from the discordant
pairs rather than from the two accuracies separately.

The plan's other two choices are kept: Wilson intervals for a single accuracy,
and the refusal to make per-category claims (see below - that refusal turns out
to be forced by arithmetic, not just good manners).

WHAT n=36 AND n=6 ACTUALLY SUPPORT

Computed by fix/select_target.py's power table, not asserted:

  OVERALL, n=36, paired
    0 regressions -> 6 improvements needed = +16.7 pp for p < 0.05
    1 regression  -> 8 improvements needed = +19.4 pp
  So a detectable result needs a large, clean swing. A +5 pp change is
  undetectable here no matter how real it is.

  PER CATEGORY, n=6
    6/0 -> p = 0.031   detectable, and only just
    5/1 -> p = 0.219   not detectable
    4/2 -> p = 0.688   not detectable
  **At n=6 the ONLY detectable category result is a perfect sweep with zero
  regressions.** Every other outcome is indistinguishable from chance.

That is a structural consequence of 36 questions across 6 categories, and it
should be stated before any number is read, so nobody reads a per-category table
as six findings. The report prints the power table itself, so the limit is
visible in the artefact rather than in a footnote.

WHAT IS DELIBERATELY NOT COMPUTED

  * A "best category". With 6 categories x 2 models x 2 methods, picking the
    maximum is selection on the measurement set. Per-category results are
    reported side by side and never ranked.
  * A cross-check agreement rate. It requires a human to score the 15 blind
    items (B5). Until that exists the field says so. It is not estimated, not
    guessed, and not left as an XX.X placeholder.
  * A dev-vs-test "consistency" score. The dev delta and the test delta are both
    reported. Whether the improvement transferred is a finding, not a metric to
    be optimised.

Run:
    python src/eval/statistical_report.py
    python src/eval/statistical_report.py --model 8b
    python src/eval/statistical_report.py --write   # statistical_report.md
Exit: 0 = report generated; 1 = refused (mock, or no test results).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "fix"))

import seal                                     # noqa: E402
from config import config                       # noqa: E402
from select_target import ALPHA, mcnemar_exact, power_table   # noqa: E402

TEST_RUN = config.results_dir / "test_run"
FINAL = config.results_dir / "final_scores"

MODELS = ("8b", "70b")


# ===================================================== binomial, exactly
def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p). Exact via integer coefficients.

    Used to invert for confidence bounds. n is 36 here, so float arithmetic on
    exact integer binomial coefficients is comfortably precise.
    """
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
               for i in range(k + 1))


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X > k)."""
    return max(0.0, 1.0 - binom_cdf(k, n, p))


def clopper_pearson(x: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """
    Exact (Clopper-Pearson) binomial interval.

    Chosen over the Wald interval because Wald is known to behave badly at small
    n and at proportions near 0 and 1 - exactly the regime of a 36-item
    benchmark. Obtained by inverting the exact binomial CDF, which needs no
    special functions: both bounds are monotone in p, so a bisection is exact to
    floating point rather than approximate in method.

    The two bounds solve, at level alpha/2:

        lower :  P(X >= x  | n, p) = alpha/2      (P(X > x-1), decreasing in p)
        upper :  P(X <= x  | n, p) = alpha/2      (P(X <= x), increasing in p)

    BOTH tails are alpha/2. The upper bound is not 1 - alpha/2; getting that
    backwards returns a lower bound in the upper slot and an interval that does
    not even contain the point estimate.
    """
    if n == 0:
        return (0.0, 1.0)
    half = alpha / 2

    # lower: P(X >= x | n, p) = half, i.e. P(X > x-1). This tail INCREASES with
    # p -- a larger success probability makes exceeding x-1 more likely -- so a
    # tail above the target means the current p is too high.
    lo, hi = 0.0, 1.0
    if x == 0:
        lower = 0.0
    else:
        for _ in range(100):
            mid = (lo + hi) / 2
            if binom_sf(x - 1, n, mid) > half:
                hi = mid
            else:
                lo = mid
        lower = (lo + hi) / 2

    # upper: P(X <= x | n, p) = half. Note the direction: for small p and
    # x < n/2 this tail DECREASES as p grows, so a tail above the target means
    # p is too low and the search moves right. (It is not monotone in p across
    # the whole unit interval - the binomial CDF is a degree-x polynomial and
    # turns over - but on the low-p branch where a 0.025 tail lives it is
    # strictly decreasing, which is the only branch the search ever visits.)
    lo, hi = 0.0, 1.0
    if x == n:
        upper = 1.0
    else:
        for _ in range(100):
            mid = (lo + hi) / 2
            if binom_cdf(x, n, mid) > half:
                lo = mid
            else:
                hi = mid
        upper = (lo + hi) / 2
    return lower, upper


# ========================================================= single accuracy
def wilson_ci(correct: int, n: int, confidence: float = 0.95) -> dict:
    """
    Wilson score interval for one accuracy.

    Right for a binomial proportion at small n: it stays inside [0, 1] and does
    not collapse to zero width at 0% or 100%, both of which a Wald interval does
    and both of which occur in practice on 36 items.
    """
    if n == 0:
        return {"accuracy": None, "correct": 0, "n": 0,
                "ci_lower": None, "ci_upper": None, "ci_half_width": None}
    p = correct / n
    z = {0.90: 1.6449, 0.95: 1.959964, 0.99: 2.575829}.get(confidence, 1.959964)
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    spread = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {
        "accuracy": round(p * 100, 1), "correct": correct, "n": n,
        "ci_lower": round(max(0.0, centre - spread) * 100, 1),
        "ci_upper": round(min(1.0, centre + spread) * 100, 1),
        "ci_half_width": round(spread * 100, 1),
        "confidence": confidence,
    }


# ======================================================== paired comparison
def paired_delta(before: list, after: list, alpha: float = ALPHA) -> dict:
    """
    Baseline -> improved on the same items. The correct analysis for paired
    binary outcomes.

    McNemar's test conditions on the DISCORDANT pairs: of the items that changed,
    how many moved the right way. Items both arms got right, or both got wrong,
    carry no information about the difference and are excluded. That is why the
    test can be significant at a much smaller delta than an unpaired comparison
    of the same two accuracies.

    The interval for the delta is exact and derived from the same quantity. If
    m items changed and b of them improved, then conditional on m the split is
    Binomial(m, p), and

        delta = (b - c) / n = (2p - 1) * m / n

    so an exact interval on p maps monotonically to an exact interval on delta.
    No bootstrap, no asymptotics, nothing that needs a seed.
    """
    b_map = {r["question_id"]: r for r in before}
    a_map = {r["question_id"]: r for r in after}
    ids = sorted(set(b_map) & set(a_map))

    improved = [i for i in ids
                if not b_map[i]["is_correct"] and a_map[i]["is_correct"]]
    regressed = [i for i in ids
                 if b_map[i]["is_correct"] and not a_map[i]["is_correct"]]
    bi, ri = len(improved), len(regressed)
    m = bi + ri
    n = len(ids)

    before_c = sum(1 for i in ids if b_map[i]["is_correct"])
    after_c = sum(1 for i in ids if a_map[i]["is_correct"])
    delta_pp = (after_c - before_c) / n * 100 if n else None

    p_value = 1.0 if m == 0 else mcnemar_exact(bi, ri)
    significant = bool(m and p_value < alpha and bi > ri)

    if n == 0:
        ci = (None, None)
    elif m == 0:
        # Nothing changed at all, so the difference is exactly zero. Reporting a
        # normal-looking interval here would imply we measured something.
        ci = (0.0, 0.0)
    else:
        lo, hi = clopper_pearson(bi, m, alpha)
        scale = m / n * 100
        ci = ((2 * lo - 1) * scale, (2 * hi - 1) * scale)

    return {
        "n_paired": n,
        "before_correct": before_c, "after_correct": after_c,
        "before_accuracy": round(before_c / n * 100, 1) if n else None,
        "after_accuracy": round(after_c / n * 100, 1) if n else None,
        "delta_pp": round(delta_pp, 1) if delta_pp is not None else None,
        "delta_ci_lower": round(ci[0], 1) if ci[0] is not None else None,
        "delta_ci_upper": round(ci[1], 1) if ci[1] is not None else None,
        "improved": bi, "regressed": ri, "discordant": m,
        "net_items": bi - ri,
        "mcnemar_p": round(p_value, 4),
        "significant": significant,
        "direction": ("improved" if significant else
                      "regressed" if (m and mcnemar_exact(ri, bi) < alpha and ri > bi)
                      else "no detectable change"),
        "improved_ids": improved, "regressed_ids": regressed,
    }


def by_category(before: list, after: list) -> dict:
    """Per-category paired comparison. Reported side by side, never ranked."""
    b_map = {r["question_id"]: r for r in before}
    a_map = {r["question_id"]: r for r in after}
    ids = sorted(set(b_map) & set(a_map))
    cats = sorted({b_map[i]["category"] for i in ids})
    out = {}
    for c in cats:
        sub = [i for i in ids if b_map[i]["category"] == c]
        bb = [b_map[i] for i in sub]
        aa = [a_map[i] for i in sub]
        out[c] = paired_delta(bb, aa)
    return out


# =================================================================== power
def detectable(n: int, alpha: float = ALPHA) -> dict:
    """
    What a paired test at this n can actually see.

    Printed into the report so the reader learns the limit from the artefact, not
    from a caveat paragraph they may skip.
    """
    rows = power_table(n, alpha)
    first = next((r for r in rows if r["improvements_needed"] is not None), None)
    any_regr = all(r["improvements_needed"] is None for r in rows[1:])
    return {
        "n": n,
        "alpha": alpha,
        "min_improvements_zero_regressions": first["improvements_needed"] if first else None,
        "min_delta_pp_zero_regressions": first["accuracy_delta_pts"] if first else None,
        "nothing_detectable_with_any_regression": any_regr,
        "table": [{k: r[k] for k in ("regressed", "improvements_needed", "net",
                                     "accuracy_delta_pts", "detectable")}
                  for r in rows[:8]],
    }


# ================================================================ loading
def _rows(payload) -> list:
    return payload["results"] if isinstance(payload, dict) and "results" in payload \
        else payload


def load_arm(task: str, model: str, method: str) -> tuple[list | None, dict]:
    """Load one arm. Returns (rows, meta) with rows=None when absent."""
    name = f"{task}_{model}_{method}.json"
    path = TEST_RUN / name
    if not path.exists():
        return None, {"present": False, "expected": name}
    payload = json.loads(path.read_text(encoding="utf-8"))
    meta = {k: v for k, v in payload.items() if k != "results"} \
        if isinstance(payload, dict) else {}
    meta["present"] = True
    return _rows(payload), meta


# ================================================================ values
def values_summary(rows: list | None) -> dict:
    """
    Values scores, with the invalid ones counted rather than dropped.

    The plan filters with `[r["score"] for r in rows if r["score"] >= 0]` and
    reports only the mean of what survives. If a third of the judgements failed,
    the mean is computed on a biased subset and nothing says so. Here the
    dropped count is part of the output.
    """
    if rows is None:
        return {"present": False}
    scores, missing = [], 0
    for r in rows:
        s = r.get("score")
        if s is None or s < 0:
            missing += 1
        else:
            scores.append(float(s))
    dist = {}
    for s in scores:
        dist[str(int(s))] = dist.get(str(int(s)), 0) + 1
    return {
        "present": True,
        "n": len(scores),
        "n_unscored": missing,
        "mean": round(sum(scores) / len(scores), 3) if scores else None,
        "distribution": dict(sorted(dist.items())),
        "scale_max": 2.0,
        "note": ("Scores with no valid judgement are counted as unscored, not "
                 "excluded from the denominator without saying so."),
    }


# ============================================================== the report
def compute(models=MODELS, n_expected: int | None = None) -> dict:
    knowledge: dict = {}
    n_cats: int | None = None
    for m in models:
        base, bm = load_arm("knowledge", m, "baseline")
        imp, im = load_arm("knowledge", m, "improved")
        entry = {
            "baseline_present": bm["present"], "improved_present": im["present"],
            "baseline_meta": bm, "improved_meta": im,
        }
        if base and imp:
            entry["baseline_ci"] = wilson_ci(
                sum(1 for r in base if r["is_correct"]), len(base))
            entry["improved_ci"] = wilson_ci(
                sum(1 for r in imp if r["is_correct"]), len(imp))
            entry["paired"] = paired_delta(base, imp)
            entry["by_category"] = by_category(base, imp)
            # The sealed-set size is whatever was actually measured, not a
            # constant this file remembers. At n=36 a hardcoded 36 was correct
            # and invisible; at any other n the power table would have
            # described a different experiment than the one in the report.
            if n_expected is None:
                n_expected = len(base)
            if n_cats is None and entry["by_category"]:
                n_cats = len(entry["by_category"])
        knowledge[m] = entry

    if n_expected is None:
        n_expected = seal.EXPECTED_N
    n_cats = n_cats or 1
    n_per_cat = max(1, n_expected // n_cats)

    # The dev half is reported alongside the sealed half so the limitation
    # section can state both sizes from the data rather than from memory.
    try:
        dev_n = len(json.loads(
            config.data_path("knowledge", "knowledge_dev.json").read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        dev_n = None

    cross = {}
    if all(knowledge.get(m, {}).get("baseline_present") for m in models):
        pairs = {m: load_arm("knowledge", m, "baseline")[0] for m in models}
        if len(models) == 2:
            a, b = models
            cross["8b_vs_70b_baseline"] = paired_delta(pairs[a], pairs[b])

    vals = {m: values_summary(load_arm("values", m, "baseline")[0]) for m in models}
    dial = {m: (load_arm("dialect", m, "baseline")[0] is not None) for m in models}

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_hash": seal.git_hash(),
        "alpha": ALPHA,
        "knowledge": knowledge,
        "cross_model": cross,
        "values": vals,
        "dialect_present": dial,
        "power": {
            # Size-agnostic keys. They used to be "overall_n36" and
            # "per_category_n6", which baked the old corpus size into the name of
            # every downstream lookup - the kind of constant that survives a
            # rescale and then quietly lies about the experiment.
            "overall": detectable(n_expected),
            "per_category": detectable(n_per_cat),
            "n_overall": n_expected,
            "n_per_category": n_per_cat,
        },
        "dev_n": dev_n,
        "judge_model": _judge_used(),
        "self_judged": _judge_used() in models,
    }


def _judge_used() -> str:
    """Which model actually judged the values arm.

    NOT config.judge_model. That is the configured default (70B), which is out
    of scope here and was never used - the one-shot pins the judge to the model
    under test. Reading the config made the report print "judge = 70b" beside a
    set of scores judged by 8B, and print "SELF-JUDGED" only by accident of the
    default landing outside the scope list. The run_metadata written by
    run_test_final.py records the judge that actually ran, so that is the
    source of truth; the config default is only a fallback for a report built
    without a one-shot run.
    """
    meta = TEST_RUN / "run_metadata.json"
    if meta.exists():
        try:
            recorded = json.loads(meta.read_text(encoding="utf-8")).get("judge_model")
            if recorded:
                return recorded
        except (json.JSONDecodeError, OSError):
            pass
    return config.judge_model


def _oq_summary() -> dict:
    """The open-ended arm's own summary. Never raises: a missing arm is a status."""
    try:
        from openqa_report import summary
        return summary()
    except (ImportError, OSError, json.JSONDecodeError, KeyError) as e:
        return {"status": "unavailable", "detail": str(e)}


def openqa_report_lines() -> list[str]:
    """Markdown section for the open-ended arm, rendered by openqa_report."""
    from openqa_report import markdown
    return markdown(_oq_summary())


def _oq_console() -> list[str]:
    """Console lines for the open-ended arm, indented to match this report."""
    try:
        from openqa_report import console
        return ["  " + line for line in console(_oq_summary())]
    except (ImportError, OSError, json.JSONDecodeError, KeyError) as e:
        return [f"  OPEN-ENDED FACTUALITY: unavailable - {e}"]


def knowledge_human_agreement() -> dict:
    """Human-vs-key agreement on the knowledge items, if it has been done.

    Absent means absent. An unrun check must never print a number someone could
    mistake for a result - the same rule the values cross-check follows.
    """
    scored_path = ROOT / "results" / "human" / "knowledge_human_scored.json"
    if not scored_path.is_file():
        return {"status": "not started",
                "detail": "no human has verified a sample of the knowledge items. "
                          "Run `python src/scripts/human_worksheet.py knowledge "
                          "--build`, answer the sheet, then `--score`."}
    try:
        d = json.loads(scored_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"status": "unreadable", "detail": str(e)}
    n = d.get("n", 0)
    if not n:
        return {"status": "incomplete", "detail": "sheet present but nothing scored"}
    return {
        "status": "complete",
        "n": n,
        "agreement": d.get("agreement"),
        "meets_floor": d.get("meets_floor"),
        "floor": d.get("floor", 0.75),
        "disagreements": len(d.get("disagreements", [])),
        "by_category": d.get("by_category", {}),
        "detail": (f"human matches the dataset key on {d.get('agreed')}/{n} = "
                   f"{d.get('agreement')}% ({len(d.get('disagreements', []))} "
                   f"disagreement(s) — each is a candidate dataset defect)"),
    }


def crosscheck_agreement() -> dict:
    """
    The human-judgement agreement rate. B5.

    Not computed, not estimated. If the blind sample has not been scored by a
    person, the answer is that it does not exist yet, and the report says so in
    the field rather than printing an XX.X that someone might fill in.
    """
    # Discover the sample rather than guessing one filename. crosscheck.py writes
    # <parsed>/values_<model>_crosscheck.json; an older layout used a single
    # results/crosscheck_blind.json. Both are accepted, and more than one is
    # reported rather than silently resolved - picking arbitrarily would let a
    # stale sample be presented as the current one.
    candidates = sorted(
        (ROOT / "results").rglob("values_*_crosscheck.json"),
        key=lambda q: q.stat().st_mtime,
        reverse=True,
    )
    legacy = ROOT / "results" / "crosscheck_blind.json"
    if legacy.is_file():
        candidates.append(legacy)

    if not candidates:
        return {"status": "not started",
                "detail": "B5: no blind sample exists yet. Run "
                          "`python src/eval/crosscheck.py select --model 8b`, then "
                          "score it by hand or with --interactive. This cannot be "
                          "delegated to a model."}
    if len(candidates) > 1:
        names = ", ".join(str(c.relative_to(ROOT)) for c in candidates)
        return {"status": "ambiguous",
                "detail": f"found {len(candidates)} blind samples ({names}); "
                          f"using the most recent. Delete the others so the "
                          f"reported rate is unambiguous."}

    blind = candidates[0]
    try:
        payload = json.loads(blind.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"status": "unreadable",
                "detail": f"{blind.relative_to(ROOT)} could not be read: {e}"}

    if not isinstance(payload, list):
        return {"status": "unreadable",
                "detail": f"{blind.relative_to(ROOT)} is not a list of items"}

    scored = [r for r in payload if r.get("manual_score") is not None]
    if not scored:
        return {"status": "incomplete",
                "detail": f"{len(payload)} items in the blind sample "
                          f"({blind.relative_to(ROOT)}), 0 scored by a human"}
    agreed = sum(1 for r in scored if r.get("manual_score") == r.get("judge_score"))
    return {"status": "complete", "n": len(scored),
            "source": str(blind.relative_to(ROOT)),
            "agreement": round(agreed / len(scored) * 100, 1),
            "floor": 0.75}


# ================================================================= rendering
def _f(v, suffix="", signed=False, none="not measured"):
    if v is None:
        return none
    return f"{v:+.1f}{suffix}" if signed else f"{v}{suffix}"


def render_console(s: dict) -> None:
    print("=" * 74)
    print("  STATISTICAL REPORT — Swiss Reality Check (held-out test set)")
    print("=" * 74)

    have = any(e.get("paired") for e in s["knowledge"].values())
    if not have:
        print("\n  No test results found. Nothing to report.")
        print(f"  looked in {TEST_RUN.relative_to(ROOT)}")
        print("  Phase 4.1 must run first, and it refuses on a mock backend.\n")
        return

    pw = s["power"]["overall"]
    pc = s["power"]["per_category"]
    print(f"\n  WHAT n={pw['n']} CAN SUPPORT (computed, not asserted)")
    print(f"    overall n={pw['n']}  : {pw['min_improvements_zero_regressions']} improvements "
          f"with 0 regressions = {_f(pw['min_delta_pp_zero_regressions'], ' pp')} "
          f"for p<{s['alpha']}")
    if pc["nothing_detectable_with_any_regression"]:
        print(f"    per-category  : n={pc['n']}. ONLY a clean sweep ({pc['n']}/0) is "
              f"detectable. Anything with a regression is not.")
    print()

    for m in MODELS:
        e = s["knowledge"].get(m, {})
        p = e.get("paired")
        if not p:
            continue
        b, i = e["baseline_ci"], e["improved_ci"]
        print(f"  {m.upper()} — knowledge, n={p['n_paired']}")
        print(f"    baseline  {_f(b['accuracy'])}%  ({b['correct']}/{b['n']})  "
              f"95% CI [{_f(b['ci_lower'])}, {_f(b['ci_upper'])}]")
        print(f"    improved  {_f(i['accuracy'])}%  ({i['correct']}/{i['n']})  "
              f"95% CI [{_f(i['ci_lower'])}, {_f(i['ci_upper'])}]")
        print(f"    delta     {_f(p['delta_pp'], ' pp', True)}  "
              f"exact 95% CI [{_f(p['delta_ci_lower'], signed=True)}, "
              f"{_f(p['delta_ci_upper'], signed=True)}]")
        print(f"    paired    {p['improved']} improved / {p['regressed']} regressed, "
              f"McNemar p={p['mcnemar_p']} -> {p['direction']}")
        print()

        cats = e.get("by_category") or {}
        if cats:
            print(f"    per category (reported, NOT ranked — n={next(iter(cats.values()))['n_paired']} each)")
            print(f"      {'category':<12} {'base':>7} {'impr':>7} {'delta':>8} "
                  f"{'imp':>4} {'reg':>4}  {'exact 95% CI':>22}  verdict")
            for c, d in sorted(cats.items()):
                print(f"      {c:<12} {_f(d['before_accuracy']):>6}% "
                      f"{_f(d['after_accuracy']):>6}% "
                      f"{_f(d['delta_pp'], signed=True):>8} {d['improved']:>4} "
                      f"{d['regressed']:>4}  "
                      f"[{_f(d['delta_ci_lower'], signed=True)}, "
                      f"{_f(d['delta_ci_upper'], signed=True)}]".ljust(76)
                      + f"  {d['direction']}")
            print()

    x = s["cross_model"].get("8b_vs_70b_baseline")
    if x:
        print(f"  8B vs 70B (baseline, same 36 items)")
        print(f"    {_f(x['before_accuracy'])}% -> {_f(x['after_accuracy'])}%  "
              f"delta {_f(x['delta_pp'], ' pp', True)}  "
              f"McNemar p={x['mcnemar_p']} -> {x['direction']}")
        print()

    for m in MODELS:
        v = s["values"].get(m, {})
        if v.get("present"):
            print(f"  VALUES {m.upper()}  mean {_f(v['mean'])}/2.0  "
                  f"n={v['n']}  unscored={v['n_unscored']}  dist={v['distribution']}")
    if any(v.get("present") for v in s["values"].values()):
        print(f"    judge = {s['judge_model']}"
              + ("  *** SELF-JUDGED ***" if s["self_judged"] else ""))
        print()

    cc = crosscheck_agreement()
    detail = cc.get("detail")
    if not detail:
        detail = f"agreement {cc.get('agreement')}% (n={cc.get('n')})"
    print(f"  HUMAN CROSS-CHECK (values judge): {cc['status']}")
    print(f"    {detail}")

    kh = knowledge_human_agreement()
    kdetail = kh.get("detail")
    if not kdetail:
        kdetail = f"agreement {kh.get('agreement')}% (n={kh.get('n')})"
    print(f"  HUMAN VERIFICATION  (knowledge key): {kh['status']}")
    print(f"    {kdetail}")
    print("=" * 74)


# ============================================================ the document
def write_report(s: dict, path: Path | None = None) -> Path:
    path = path or (FINAL / "statistical_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    L: list[str] = []
    A = L.append

    A("# Statistical report — Swiss Reality Check")
    A("")
    A(f"Generated {s['generated_utc']} by `eval/statistical_report.py`, "
      f"git `{s['git_hash'][:12]}`.")
    A("")
    A(f"Split: **held-out test set**. α = {s['alpha']}. Judge: `{s['judge_model']}`"
      + ("  — **self-judged**, disclosed per `values_rubric.md` §5."
         if s["self_judged"] else "."))
    A("")

    # ---- no data at all ---------------------------------------------------
    have = any(e.get("paired") for e in s["knowledge"].values())
    if not have:
        A("> ## ⚠️ No results yet")
        A(">")
        A("> Phase 4.1 has not been run. `results/test_run/` is empty, and")
        A("> `run_test_final.py` refuses to run on a mock backend — the sealed set")
        A("> is scored once, on a real model, and that has not happened.")
        A(">")
        A("> This file will be regenerated when the runs exist. Nothing below is")
        A("> a placeholder waiting to be filled in; there are no numbers to report.")
        A("")
        A(f"## What n={s['power']['n_overall']} supports, computed in advance")
        A("")
        _power_section(A, s)
        A("## What still has to happen before this report can mean anything")
        A("")
        A("- **B2** — Apertus-8B on a live backend")
        A("- **B3** — 70B route, for the second model and the judge")
        A("- **B5** — a human scores the 15 blind cross-check items")
        A("")
        path.write_text("\n".join(L) + "\n", encoding="utf-8")
        return path

    mocks = [m for m in MODELS
             if s["knowledge"].get(m, {}).get("baseline_meta", {}).get("is_mock")]
    if mocks:
        A("> ## ⚠️ MOCK BACKEND — these numbers describe the harness, not Apertus")
        A(">")
        A(f"> Arms produced under mock: {', '.join(mocks)}.")
        A("> Every accuracy, delta and interval below was computed from synthetic")
        A("> responses. None of it is a result about the model. The statistics are")
        A("> correct; the data is not.")
        A("")

    A("## Test set composition")
    A("")
    for m in MODELS:
        e = s["knowledge"].get(m, {})
        b = e.get("baseline_ci")
        if b:
            A(f"- Knowledge {m.upper()}: {b['n']} MCQs "
              f"({b['n'] // 6} per category), 4 options")
    v = next((s["values"].get(m) for m in MODELS
              if (s["values"].get(m) or {}).get("present")), None)
    if v:
        A(f"- Values: {v['n']} scenarios scored 0–2 by rubric")
    A("")

    A(f"## What n={s['power']['n_overall']} and n={s['power']['n_per_category']} can support")
    A("")
    _power_section(A, s)

    for m in MODELS:
        e = s["knowledge"].get(m, {})
        p = e.get("paired")
        if not p:
            continue
        b, i = e["baseline_ci"], e["improved_ci"]
        A(f"## Knowledge — {m.upper()} (n={p['n_paired']})")
        A("")
        A("| Arm | Accuracy | 95% CI (Wilson) |")
        A("|---|---|---|")
        A(f"| Baseline | {_f(b['accuracy'])}% ({b['correct']}/{b['n']}) | "
          f"[{_f(b['ci_lower'])}, {_f(b['ci_upper'])}] |")
        A(f"| Improved | {_f(i['accuracy'])}% ({i['correct']}/{i['n']}) | "
          f"[{_f(i['ci_lower'])}, {_f(i['ci_upper'])}] |")
        A("")
        A(f"**Delta: {_f(p['delta_pp'], ' pp', True)}** "
          f"(exact 95% CI [{_f(p['delta_ci_lower'], signed=True)}, "
          f"{_f(p['delta_ci_upper'], signed=True)}])")
        A("")
        A(f"Paired McNemar: **{p['improved']} improved, {p['regressed']} regressed**, "
          f"p = {p['mcnemar_p']} → **{p['direction']}**.")
        A("")
        A("The interval on the delta is not the improved arm's interval. It is an "
          "exact interval derived from the discordant pairs, and it is wider than "
          "either arm's.")
        A("")
        cats = e.get("by_category") or {}
        if cats:
            A("### Per category")
            A("")
            A("Reported side by side and **not ranked** — picking the best of six "
              "is selection on the measurement set.")
            A("")
            A("| Category | n | Baseline | Improved | Delta | Exact 95% CI | Verdict |")
            A("|---|---|---|---|---|---|---|")
            for c, d in sorted(cats.items()):
                A(f"| {c} | {d['n_paired']} | {_f(d['before_accuracy'])}% | "
                  f"{_f(d['after_accuracy'])}% | {_f(d['delta_pp'], ' pp', True)} | "
                  f"[{_f(d['delta_ci_lower'], signed=True)}, "
                  f"{_f(d['delta_ci_upper'], signed=True)}] | {d['direction']} |")
            A("")

    x = s["cross_model"].get("8b_vs_70b_baseline")
    if x:
        A("## 8B vs 70B (baseline, same items)")
        A("")
        A(f"Paired McNemar: **{x['improved']} / {x['regressed']}**, "
          f"p = {x['mcnemar_p']} → **{x['direction']}**.")
        A("")

    if any((s["values"].get(m) or {}).get("present") for m in MODELS):
        A("## Values")
        A("")
        A("| Model | n | Unscored | Mean / 2.0 | Distribution |")
        A("|---|---|---|---|---|")
        for m in MODELS:
            vv = s["values"].get(m) or {}
            if vv.get("present"):
                A(f"| {m.upper()} | {vv['n']} | {vv['n_unscored']} | "
                  f"{_f(vv['mean'])} | {vv['distribution']} |")
        A("")
        if s["self_judged"]:
            A(f"> **The `{s['judge_model']}` values arm is self-judged** — the "
              f"judge and the model under test are the same weights. Disclosed "
              f"per `values_rubric.md` §5.")
            A("")

    # The open-ended arm renders itself: different grading model (three-way judge,
    # not letter match), no shared code with the sections above. Keeping it out
    # here is what stops this file growing past a readable size.
    try:
        for _line in openqa_report_lines():
            A(_line)
        A("")
    except (ImportError, OSError, json.JSONDecodeError) as e:
        A("## Open-ended factuality (three-way grading)")
        A("")
        A(f"**unavailable** — {e}")
        A("")

    kh = knowledge_human_agreement()
    A("## Human verification of the knowledge key")
    if kh["status"] == "complete":
        A(f"A human independently answered **{kh['n']}** knowledge items drawn from the "
          f"dev split, stratified by category and difficulty, blind to the stored key. "
          f"The key matched on **{kh['agreement']}%**.")
        A("")
        A("This is a check on the DATASET, not on the model: the knowledge arm is scored "
          "by exact letter match, so no judge is involved and a wrong key silently marks "
          "a correct model answer wrong. Each disagreement is a candidate dataset "
          "defect, and one already found this way (K108, Appenzell Innerrhoden) is "
          "fixed and disclosed in the changelog.")
    else:
        A(f"**{kh['status']}** — {kh.get('detail', '')}")
        A("")
        A("Not yet performed. The knowledge items are graded by exact letter match "
          "against the dataset's own key, so an incorrect key is indistinguishable "
          "from model error in the headline number. This is a known open item, listed "
          "in technical_report.md §5.")

    cc = crosscheck_agreement()
    A("## Human cross-check agreement")
    A("")
    if cc["status"] == "complete":
        A(f"**{cc['agreement']}%** ({cc['n']} blind items scored by a human; "
          f"floor {cc['floor']:.0%}).")
    else:
        A(f"**Not available — {cc['status']}.** {cc['detail']}")
    A("")

    A("## Limitations")
    A("")
    pw = s["power"]["overall"]
    A(f"1. **n={pw['n']} is small.** A detectable paired change needs "
      f"{pw['min_improvements_zero_regressions']} improvements with zero "
      f"regressions ({_f(pw['min_delta_pp_zero_regressions'], ' pp')}). A smaller "
      f"real effect would not be distinguishable from noise here, and this report "
      f"does not claim one.")
    pc = s["power"]["per_category"]
    if pc["nothing_detectable_with_any_regression"]:
        A(f"2. **Per-category claims are not supportable at n={pc['n']}.** Only a "
          f"clean sweep with no regressions reaches p<{s['alpha']}. Every other "
          f"category outcome is indistinguishable from chance. The per-category "
          f"table is descriptive, not inferential.")
    dev_note = f" (n={s['dev_n']})" if s.get("dev_n") else ""
    A(f"3. **The improvement was designed on dev{dev_note}** and evaluated once "
      f"on test (n={pw['n']}). A dev-set delta that fails to transfer is a finding "
      f"about overfitting to dev, and is reported as one.")
    if s["self_judged"]:
        A("4. **LLM-as-judge scoring is subjective**, and the arm where judge and "
          "model are the same weights is self-judged.")
    A(f"{5 if s['self_judged'] else 4}. **Dialect scoring is automated word-overlap** "
      "(`dialect_scoring_protocol.md`), an approximation of translation quality, "
      "and all 30 items carry `validated_by: null` pending a native speaker (B1).")
    A("")

    A("## Reproducibility")
    A("")
    A(f"- Git commit: `{s['git_hash']}`")
    A("- Seed: 42 · Temperature: 0.0 · Prompt version: 1.0")
    A(f"- Sealed test set SHA-256: `{seal.file_hash()[:32]}…`")
    A(f"- Raw responses and per-arm metadata: `results/test_run/`")
    A(f"- Machine-readable statistics: `results/final_scores/test_scores.json`")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def _power_section(A, s: dict) -> None:
    pw, pc = s["power"]["overall"], s["power"]["per_category"]
    A(f"**Overall (n={pw['n']}, paired)** — computed from the same exact test used "
      f"for the results above:")
    A("")
    A("| Regressions | Improvements needed | Net | Delta |")
    A("|---|---|---|---|")
    for r in pw["table"][:6]:
        if r["improvements_needed"] is None:
            A(f"| {r['regressed']} | *not detectable* | — | — |")
        else:
            A(f"| {r['regressed']} | {r['improvements_needed']} | {r['net']:+d} | "
              f"{_f(r['accuracy_delta_pts'], ' pp', True)} |")
    A("")
    A(f"**Per category (n={pc['n']})** — " +
      ("**nothing is detectable except a clean sweep with zero regressions** "
       "(6/0, p=0.031). With one regression, no achievable improvement count "
       "reaches significance at this n."
       if pc["nothing_detectable_with_any_regression"]
       else "see the table below."))
    A("")
    A("This is why the per-category tables are labelled descriptive. It is a "
      "property of 36 questions across 6 categories, not a caveat added afterwards.")
    A("")


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 4.2 statistical report.")
    ap.add_argument("--model", action="append", choices=list(MODELS), default=None)
    # Writing is the default. Both files are derived from the archived arms in
    # results/test_run/, so regenerating is idempotent and always in scope.
    # Gating it behind a flag meant the obvious invocation refreshed the console
    # and left the SHIPPED report untouched on disk - so statistical_report.md
    # could be arbitrarily stale while the terminal output looked perfect. That
    # is the failure this project keeps having: the artefact a judge reads
    # diverging from the one that was just computed.
    ap.add_argument("--no-write", dest="write", action="store_false", default=True,
                    help="console only; do not refresh the report files")
    args = ap.parse_args()
    models = tuple(args.model) if args.model else MODELS

    s = compute(models)
    render_console(s)

    if args.write:
        FINAL.mkdir(parents=True, exist_ok=True)
        (FINAL / "test_scores.json").write_text(
            json.dumps(s, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8")
        p = write_report(s)
        print(f"\n  report  -> {p.relative_to(ROOT)}")
        print(f"  scores  -> {(FINAL / 'test_scores.json').relative_to(ROOT)}")
        cc = crosscheck_agreement()
        if cc["status"] != "complete":
            print(f"\n  NOTE: the values human cross-check is {cc['status']}. The "
                  f"report says so rather than carrying a placeholder for it.")
            kh = knowledge_human_agreement()
            if kh["status"] != "complete":
                print(f"  NOTE: human verification of the knowledge key is "
                      f"{kh['status']}. The report says so rather than "
                      f"carrying a placeholder for it.")
            for line in _oq_console():
                print(line)
        mocks = [m for m in models
                 if s["knowledge"].get(m, {}).get("baseline_meta", {}).get("is_mock")]
        if mocks:
            print(f"  *** written from MOCK arms ({', '.join(mocks)}). "
                  f"Regenerate after the real run. ***")
            return 1

    have = any(s["knowledge"].get(m, {}).get("paired") for m in models)
    return 0 if have else 1


if __name__ == "__main__":
    sys.exit(main())

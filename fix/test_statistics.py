"""
test_statistics.py - Phase 4.2 verification.

These numbers go into a submission to a jury that includes statisticians. A
confidence interval that is wrong in a way nobody notices is worse than no
interval, because it lends false precision to a number.

And this suite is not hypothetical: the first version of `clopper_pearson`
inverted the upper bound against 1 - alpha/2 instead of alpha/2, and then had
the lower bound's monotonicity backwards. Both bugs produced an interval that
did not contain its own point estimate. Nothing crashed. The report would have
been written and published.

So the tests here are mostly against KNOWN VALUES, not against the
implementation's own behaviour - a test that computes the expected value with
the same function it is testing proves nothing.

  1. CLOPPER-PEARSON MATCHES TEXTBOOK VALUES.
  2. AND SATISFIES ITS DEFINING PROPERTY: both bounds reproduce P = alpha/2.
  3. AND IS SYMMETRIC, CONTAINS ITS ESTIMATE, AND STAYS IN [0, 1].
  4. WILSON BEHAVES WHERE WALD FAILS: at 0% and 100% it keeps width.
  5. THE DELTA INTERVAL IS NOT THE IMPROVED ARM'S INTERVAL. The bug the plan
     ships is printing one arm's CI next to the delta.
  6. THE PAIRED CI EXCLUDES ZERO EXACTLY WHEN McNEMAR IS SIGNIFICANT.
  7. NET MOVEMENT IS NOT SIGNIFICANCE - carried forward from 3.4, because it is
     the same trap in a new place.
  8. NOTHING IS REPORTED THAT WAS NOT MEASURED.
  9. THE POWER CLAIMS ARE COMPUTED, NOT ASSERTED, AND n=6 IS CALLED IMPOSSIBLE.

Run:  python fix/test_statistics.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "fix"))

CHECKS = 0
FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(f"{label}" + (f" -- {detail}" if detail else ""))


def section(name: str) -> None:
    print(f"\n{name}")


# ================================================= 1-3. Clopper-Pearson
# Textbook 95% Clopper-Pearson bounds.
TEXTBOOK = [
    (2, 10, 0.0252, 0.5561),
    (0, 10, 0.0000, 0.3085),
    (10, 10, 0.6915, 1.0000),
    (5, 10, 0.1871, 0.8129),
    (1, 10, 0.0025, 0.4450),
    (8, 10, 0.4439, 0.9748),
    (0, 36, 0.0000, 0.0974),
]


def test_clopper_pearson_known_values() -> None:
    section("1. Clopper-Pearson matches published values")
    from statistical_report import clopper_pearson

    for x, n, el, eu in TEXTBOOK:
        lo, hi = clopper_pearson(x, n)
        check(f"{x}/{n} lower bound", abs(lo - el) < 0.0012, f"{lo:.4f} != {el}")
        check(f"{x}/{n} upper bound", abs(hi - eu) < 0.0012, f"{hi:.4f} != {eu}")

    # An empty sample must not divide by zero or produce NaN.
    lo, hi = clopper_pearson(0, 0)
    check("n=0 returns the full range", (lo, hi) == (0.0, 1.0), f"{lo},{hi}")
    print(f"   {len(TEXTBOOK)} published intervals reproduced to <0.0012")


def test_clopper_pearson_defining_property() -> None:
    section("2. Each bound reproduces its own tail probability")
    from statistical_report import binom_cdf, binom_sf, clopper_pearson

    # The property, not the number: lower solves P(X >= x) = alpha/2 and upper
    # solves P(X <= x) = alpha/2. Both tails are alpha/2 - using 1 - alpha/2 for
    # the upper bound is the bug this suite was written after.
    for x, n in [(5, 10), (2, 10), (18, 36), (24, 36), (1, 10), (12, 36), (3, 36)]:
        lo, hi = clopper_pearson(x, n)
        check(f"{x}/{n} lower reproduces P(X>={x})=0.025",
              abs(binom_sf(x - 1, n, lo) - 0.025) < 1e-9,
              f"{binom_sf(x - 1, n, lo)}")
        check(f"{x}/{n} upper reproduces P(X<={x})=0.025",
              abs(binom_cdf(x, n, hi) - 0.025) < 1e-9,
              f"{binom_cdf(x, n, hi)}")

    # Monotonicity on the branch the bisection actually visits. P(X <= k | n, p)
    # is NOT monotone in p across [0,1] -- it is a degree-k polynomial that turns
    # over -- so a blanket claim would be false. On the low-p branch where a
    # 0.025 tail lives it is strictly decreasing, and that is the only branch the
    # upper-bound search reaches.
    sf_inc = all(binom_sf(4, 10, 0.1 + 0.01 * i) <= binom_sf(4, 10, 0.1 + 0.01 * (i + 1))
                 for i in range(80))
    check("P(X > k) increases with p (the lower bound's branch)", sf_inc)
    cdf_dec = all(binom_cdf(2, 10, 0.01 * i) >= binom_cdf(2, 10, 0.01 * (i + 1))
                  for i in range(1, 80))
    check("P(X <= k) decreases with p on the low-p branch (the upper bound's branch)",
          cdf_dec)

    check("sf(k) == 1 - cdf(k)",
          all(abs(binom_sf(k, 20, 0.3) - (1 - binom_cdf(k, 20, 0.3))) < 1e-12
              for k in range(21)))
    print("   both bounds reproduce P=0.025 to 1e-9 at every n tested")


def test_clopper_pearson_invariants() -> None:
    section("3. The interval contains its estimate and is symmetric")
    from statistical_report import clopper_pearson

    grid = [(x, 36) for x in range(0, 37, 3)] + [(x, 10) for x in range(0, 11, 2)]
    for x, n in grid:
        lo, hi = clopper_pearson(x, n)
        check(f"{x}/{n} contains its point estimate", lo <= x / n <= hi,
              f"[{lo:.4f},{hi:.4f}] vs {x/n:.4f}")
        check(f"{x}/{n} is within [0,1]", 0.0 <= lo <= hi <= 1.0)
        check(f"{x}/{n} is symmetric",
              abs(lo - (1 - clopper_pearson(n - x, n)[1])) < 1e-9)

    # A larger n must give a narrower interval at the same proportion.
    w10 = clopper_pearson(5, 10)
    w100 = clopper_pearson(50, 100)
    check("the interval narrows as n grows",
          (w100[1] - w100[0]) < (w10[1] - w10[0]),
          f"{w10[1]-w10[0]:.3f} vs {w100[1]-w100[0]:.3f}")
    print(f"   {len(grid)} intervals contain their estimate; "
          f"width 5/10={w10[1]-w10[0]:.3f} -> 50/100={w100[1]-w100[0]:.3f}")


# ================================================= 4. Wilson
def test_wilson() -> None:
    section("4. Wilson keeps width where Wald collapses")
    from statistical_report import wilson_ci

    w = wilson_ci(18, 36)
    check("18/36 is centred on 50%", w["ci_lower"] < 50 < w["ci_upper"],
          f"[{w['ci_lower']},{w['ci_upper']}]")
    # Wilson 95% for 18/36 is about [34.5, 65.5].
    check("18/36 matches the published Wilson interval",
          abs(w["ci_lower"] - 34.5) < 0.3 and abs(w["ci_upper"] - 65.5) < 0.3,
          f"[{w['ci_lower']},{w['ci_upper']}]")

    # Wald's two classic failures: zero-width at 0% and at 100%.
    w0 = wilson_ci(0, 36)
    w100 = wilson_ci(36, 36)
    check("0/36 has a non-zero upper bound", w0["ci_upper"] > 0, str(w0))
    check("36/36 has a lower bound below 100", w100["ci_lower"] < 100, str(w100))
    check("0/36 and 36/36 are mirror images",
          abs(w0["ci_upper"] - (100 - w100["ci_lower"])) < 0.1)

    empty = wilson_ci(0, 0)
    check("n=0 returns None, not zero", empty["accuracy"] is None, str(empty))
    check("n=0 returns no interval", empty["ci_lower"] is None)

    # A larger confidence level must widen it.
    check("99% is wider than 95%",
          wilson_ci(18, 36, 0.99)["ci_upper"]
          > wilson_ci(18, 36, 0.95)["ci_upper"])
    print(f"   0/36 -> [{w0['ci_lower']}, {w0['ci_upper']}]  "
          f"36/36 -> [{w100['ci_lower']}, {w100['ci_upper']}]  (Wald: [0,0] and [100,100])")


# ================================================= 5-7. the paired delta
def mk_arm(n, n_up, n_down, cat="law"):
    """Two arms over the same n items: n_up flip wrong->right, n_down flip
    right->wrong, the rest unchanged."""
    before, after = [], []
    for i in range(n):
        if i < n_up:
            b, a = False, True
        elif i < n_up + n_down:
            b, a = True, False
        else:
            b, a = True, True
        base = {"question_id": f"K{i:03d}", "category": cat, "correct": "A",
                "predicted": "A", "parse_reason": "ok", "api_failed": False}
        before.append({**base, "is_correct": b})
        after.append({**base, "is_correct": a, "predicted": "A" if a else "B"})
    return before, after


def test_delta_interval_is_not_an_arm_interval() -> None:
    section("5. The delta's interval is its own, not an arm's")
    from statistical_report import paired_delta, wilson_ci

    # The exact bug in the plan: `ci = f"+/-{improved['ci_range']/2}"` printed
    # in the delta column.
    before, after = mk_arm(36, 8, 1)
    d = paired_delta(before, after)
    arm = wilson_ci(sum(1 for r in after if r["is_correct"]), 36)

    check("the delta CI is present", d["delta_ci_lower"] is not None)
    check("the delta CI is WIDER than the improved arm's",
          (d["delta_ci_upper"] - d["delta_ci_lower"])
          > (arm["ci_upper"] - arm["ci_lower"]),
          f"delta {d['delta_ci_upper']-d['delta_ci_lower']:.1f} vs "
          f"arm {arm['ci_upper']-arm['ci_lower']:.1f}")
    check("the delta CI is not the arm CI",
          (d["delta_ci_lower"], d["delta_ci_upper"])
          != (arm["ci_lower"], arm["ci_upper"]))
    check("the delta equals improved minus baseline",
          abs(d["delta_pp"] - (d["after_accuracy"] - d["before_accuracy"])) < 0.05)
    print(f"   delta [{d['delta_ci_lower']}, {d['delta_ci_upper']}] "
          f"vs improved arm [{arm['ci_lower']}, {arm['ci_upper']}]")


def test_paired_ci_tracks_mcnemar() -> None:
    section("6. The paired interval excludes zero exactly when the test is significant")
    from statistical_report import paired_delta
    from select_target import mcnemar_exact

    cases = [(36, 0, 0), (36, 6, 0), (36, 8, 1), (36, 10, 4), (36, 4, 2),
             (36, 0, 6), (36, 3, 3), (36, 12, 2), (36, 7, 1), (36, 1, 1)]
    for n, up, dn in cases:
        before, after = mk_arm(n, up, dn)
        d = paired_delta(before, after)
        lo, hi = d["delta_ci_lower"], d["delta_ci_upper"]
        excludes0 = not (lo <= 0 <= hi)
        # Significant in EITHER direction. Checking only the improvement side
        # would miss every regression, which is the half that matters most.
        expected_sig = d["mcnemar_p"] < 0.05 and up != dn
        check(f"{up}/{dn}: CI-excludes-0 agrees with McNemar",
              excludes0 == expected_sig,
              f"p={d['mcnemar_p']}, CI [{lo},{hi}]")
        check(f"{up}/{dn}: p matches select_target's independent implementation",
              abs(d["mcnemar_p"] - round(mcnemar_exact(up, dn), 4)) < 1e-9)
        # Direction reflects SIGNIFICANCE, not just the sign of the net. 10 up /
        # 4 down has a positive net but is not a detectable improvement, and
        # calling it one is the exact error the net-only rule made.
        expected = ("improved" if d["significant"] else
                    "regressed" if (d["discordant"]
                                    and mcnemar_exact(dn, up) < 0.05 and dn > up)
                    else "no detectable change")
        check(f"{up}/{dn}: direction reflects significance, not just sign",
              d["direction"] == expected, f"{d['direction']} != {expected}")
        check(f"{up}/{dn}: a positive net with p>=0.05 is not called improved",
              not (up > dn and d["mcnemar_p"] >= 0.05 and d["direction"] == "improved"))

    # No change at all: the difference is exactly zero, and saying so with a
    # normal-looking interval would imply we measured something.
    before, after = mk_arm(36, 0, 0)
    d = paired_delta(before, after)
    check("no change gives an exactly degenerate interval",
          (d["delta_ci_lower"], d["delta_ci_upper"]) == (0.0, 0.0), str(d))
    check("no change gives p=1", d["mcnemar_p"] == 1.0)
    check("no change is not called an improvement", not d["significant"])

    # Direction is detected both ways.
    _, after = mk_arm(36, 0, 6)
    before, _ = mk_arm(36, 0, 0)
    d = paired_delta(before, after)
    check("a regression is reported as a regression", d["direction"] == "regressed",
          d["direction"])
    print(f"   {len(cases)} cases: the interval and the test never disagree")


def test_net_is_not_significance() -> None:
    section("7. Net movement is still not significance (the 3.4 trap, again)")
    from statistical_report import paired_delta

    # Same net +6, opposite conclusions.
    b1, a1 = mk_arm(36, 6, 0)
    b2, a2 = mk_arm(36, 10, 4)
    d1, d2 = paired_delta(b1, a1), paired_delta(b2, a2)

    check("both have net +6", d1["net_items"] == d2["net_items"] == 6,
          f"{d1['net_items']} / {d2['net_items']}")
    check("6/0 is significant", d1["significant"])
    check("10/4 is NOT", not d2["significant"], f"p={d2['mcnemar_p']}")
    check("their directions differ",
          d1["direction"] != d2["direction"],
          f"{d1['direction']} vs {d2['direction']}")
    check("only the first CI excludes zero",
          (not (d1["delta_ci_lower"] <= 0 <= d1["delta_ci_upper"]))
          and (d2["delta_ci_lower"] <= 0 <= d2["delta_ci_upper"]))
    print(f"   net +6: 6/0 -> p={d1['mcnemar_p']} significant; "
          f"10/4 -> p={d2['mcnemar_p']} not")


# ================================================= 8. nothing unmeasured
def test_nothing_unmeasured_is_reported() -> None:
    section("8. Absent numbers are labelled, never zeroed or filled in")
    import statistical_report as sr

    check("_f(None) says so", sr._f(None) == "not measured", sr._f(None))
    check("_f renders a real number", sr._f(12.3) == "12.3", sr._f(12.3))
    check("_f signs when asked", sr._f(5.0, " pp", True) == "+5.0 pp",
          sr._f(5.0, " pp", True))
    check("_f signs a negative", sr._f(-3.0, " pp", True) == "-3.0 pp")

    # The document must never carry the plan's placeholders.
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        empty = sr.compute(models=())
        p = sr.write_report(empty, Path(td) / "r.md")
        text = p.read_text(encoding="utf-8")
        check("an empty report writes", p.exists())
        check("no XX.X placeholder survives", "XX.X" not in text)
        check("no bare XX survives", "XX " not in text and "X/36" not in text)
        check("it says the results do not exist yet",
              "not been run" in text.lower())
        check("it still states the power limits", "6" in text and "16.7" in text)
        check("it lists the blockers", all(b in text for b in ("B2", "B3", "B5")))

    # The cross-check agreement must not be invented.
    cc = sr.crosscheck_agreement()
    check("the cross-check is reported as not available",
          cc["status"] != "complete", str(cc))
    check("it explains who has to do it", "human" in cc["detail"].lower(),
          cc["detail"])
    check("no agreement number is invented", "agreement" not in cc
          or cc.get("agreement") is None, str(cc))

    # Values: unscored items must be counted, not silently dropped.
    vs = sr.values_summary([
        {"score": 2.0}, {"score": 1.0}, {"score": None}, {"score": -1},
        {"score": 0.0}])
    check("unscored values are counted", vs["n_unscored"] == 2, str(vs))
    check("the mean uses only scored items", vs["n"] == 3, str(vs))
    check("the mean is computed correctly", abs(vs["mean"] - 1.0) < 1e-9, str(vs))
    check("the distribution is reported", vs["distribution"] == {"0": 1, "1": 1, "2": 1},
          str(vs))
    check("an absent values arm reports present=False",
          sr.values_summary(None)["present"] is False)
    print("   absent -> 'not measured'; unscored counted; cross-check not invented")


# ================================================= 9. the power claims
def test_power_claims() -> None:
    section("9. The power claims are computed, and n=6 is called impossible")
    import statistical_report as sr
    from select_target import mcnemar_exact

    d36 = sr.detectable(36)
    check("at n=36, 6 improvements with 0 regressions is the threshold",
          d36["min_improvements_zero_regressions"] == 6, str(d36))
    check("that is +16.7 pp", abs(d36["min_delta_pp_zero_regressions"] - 16.7) < 0.1,
          str(d36["min_delta_pp_zero_regressions"]))
    check("it agrees with the independent implementation",
          mcnemar_exact(6, 0) < 0.05 and mcnemar_exact(5, 0) >= 0.05)

    d6 = sr.detectable(6)
    check("at n=6, only a clean sweep is detectable",
          d6["nothing_detectable_with_any_regression"],
          str(d6["table"]))
    check("6/0 at n=6 is significant", mcnemar_exact(6, 0) < 0.05)
    check("5/1 at n=6 is not", mcnemar_exact(5, 1) >= 0.05)
    check("4/2 at n=6 is not", mcnemar_exact(4, 2) >= 0.05)
    check("3/3 at n=6 is not", mcnemar_exact(3, 3) >= 0.05)

    # The table must be monotonic: needing more improvements as regressions grow.
    needs = [r["improvements_needed"] for r in d36["table"]
             if r["improvements_needed"] is not None]
    check("the requirement grows with regressions",
          all(needs[i] <= needs[i + 1] for i in range(len(needs) - 1)), str(needs))
    print(f"   n=36: {d36['min_improvements_zero_regressions']} gains needed "
          f"= +{d36['min_delta_pp_zero_regressions']} pp; "
          f"n=6: only 6/0 detectable")


def main() -> int:
    print("=" * 72)
    print("  Phase 4.2 verification")
    print("=" * 72)
    for fn in (test_clopper_pearson_known_values,
               test_clopper_pearson_defining_property,
               test_clopper_pearson_invariants,
               test_wilson,
               test_delta_interval_is_not_an_arm_interval,
               test_paired_ci_tracks_mcnemar,
               test_net_is_not_significance,
               test_nothing_unmeasured_is_reported,
               test_power_claims):
        try:
            fn()
        except Exception as e:
            import traceback
            FAILURES.append(f"{fn.__name__} raised {type(e).__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 72}")
    if FAILURES:
        print(f"  FAILED  {len(FAILURES)} of {CHECKS} checks")
        for f in FAILURES:
            print(f"    - {f}")
        return 1
    print(f"  PASSED  all {CHECKS} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())

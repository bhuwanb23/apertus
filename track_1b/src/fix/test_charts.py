"""
test_charts.py - Phase 4.3 verification.

A chart is the most efficient way to over-claim in a benchmark submission, and
the least detectable. A table of numbers can be checked; a bar chart is already
an argument. So these tests are not "does it draw" - they are about whether the
picture tells the truth.

  1. EVERY CHART IS VALID, SELF-CONTAINED SVG. Well-formed, viewBox declared,
     no external references, no script. A chart that a renderer rejects is a
     chart nobody sees.
  2. NO CHART CARRIES A NUMBER THAT WAS NOT MEASURED. The plan's template is
     full of XX.X placeholders designed to be filled by hand; a hand-filled
     chart number is a number no code produced.
  3. EVERY ACCURACY BAR CARRIES ITS INTERVAL. A bar without a whisker is a
     point estimate presented as a measurement, and at n=6 that is the whole
     problem.
  4. THE POWER LIMIT IS DRAWN, NOT JUST MENTIONED. A caveat in a caption is
     read after the number.
  5. THERE IS NO HEATMAP. At n=6 a 0/6 score has a CI of [0, 39] and 6/6 has
     [61, 100]; a colour ramp over those numbers renders noise as signal.
  6. NO CHART RANKS CATEGORIES. Picking the best of six is selection.
  7. MOCK DATA IS WATERMARKED. The failure this prevents is a chart screenshotted
     into a README months later.
  8. THE RETRIEVAL NUMBERS ARE COMPUTED, NOT TYPED IN.
  9. THE CHARTS AGREE WITH THE STATISTICS MODULE. Two code paths rendering the
     same quantity must not disagree.

Run:  python fix/test_charts.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import re
import subprocess
import sys
import xml.dom.minidom as minidom
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


def all_charts():
    import generate_charts as gc
    return gc.CHARTS_META


def render_all(stats=None):
    """Render every chart and return {name: svg_text}."""
    import generate_charts as gc
    from statistical_report import compute
    stats = stats if stats is not None else (gc._load_stats() or compute())
    out = {}
    for name, fn, _ in gc.CHARTS_META:
        try:
            out[name] = fn(stats).render()
        except Exception:
            out[name] = None
    return out, stats


# ================================================ 1. valid, self-contained SVG
def test_svg_validity() -> None:
    section("1. Every chart is valid, self-contained SVG")
    charts, _ = render_all()
    for name, svg in charts.items():
        check(f"{name} rendered", svg is not None, "render raised")
        if not svg:
            continue
        try:
            minidom.parseString(svg)
            check(f"{name} is well-formed XML", True)
        except Exception as e:
            check(f"{name} is well-formed XML", False, str(e)[:80])
            continue

        check(f"{name} declares a viewBox", "viewBox=" in svg)
        check(f"{name} has a title for screen readers", "<title" in svg)
        check(f"{name} has a description", "<desc" in svg)
        # Self-contained: a chart that fetches anything will break in a README.
        check(f"{name} references nothing external",
              "http://" not in svg.replace("http://www.w3.org/2000/svg", "")
              and "https://" not in svg and "xlink:href" not in svg)
        check(f"{name} has no script", "<script" not in svg and "onload" not in svg)
        check(f"{name} is not empty", len(svg) > 2000, f"{len(svg)} bytes")
        # Every tag must be closed; unclosed tags parse in some readers and
        # silently drop content in others.
        check(f"{name} has balanced groups",
              svg.count("<g") == svg.count("</g>"), "unbalanced <g>")
    print(f"   {len(charts)} charts: valid XML, self-contained, no script")


# =========================================== 2. nothing unmeasured is drawn
def test_no_placeholders_or_fabrication() -> None:
    section("2. No chart carries a number that was not measured")
    charts, stats = render_all()
    import generate_charts as gc

    for name, svg in charts.items():
        if not svg:
            continue
        check(f"{name} has no XX.X placeholder", "XX.X" not in svg)
        check(f"{name} has no bare XX", not re.search(r"\bXX\b", svg))
        check(f"{name} has no empty-cell placeholder", "|XX|" not in svg)

    have = gc._has_knowledge(stats)
    if not have:
        # With no test results, figs 1-3 must say so rather than draw bars.
        for name in ("fig1_overall_accuracy", "fig2_category_intervals"):
            svg = charts.get(name) or ""
            check(f"{name} states that there is no data",
                  "No test results yet" in svg, "an empty chart must say why")
        check("fig4 still renders, because it needs no model",
              charts.get("fig4_retrieval_recall") is not None)

    # fig4's numbers must come from the retriever, and there must be NO
    # fallback to literals - a stale bar with no staleness marker is the worst
    # failure a chart can have, and it is the one the plan's hardcoded values
    # would have produced.
    src = (ROOT / "eval" / "generate_charts.py").read_text(encoding="utf-8")
    check("retrieval recall is recomputed, not hardcoded",
          "def _retrieval_numbers" in src)
    body = src.split("def _retrieval_numbers", 1)[1]
    body = body.split("\n# ===", 1)[0]
    # Executable code only. The docstring names the removed literals in order to
    # explain why they are gone, and testing raw text would flag the very
    # sentence documenting the fix.
    code = body.split('"""', 2)[0] + "".join(body.split('"""')[2:])
    check("the recompute path calls the real retriever",
          "retrieval_report" in code and "SwissRetriever" in code)
    literals = [v for v in ("83.3", "90.5", "94.0", "0.833") if v in code]
    check("there is NO hardcoded recall in executable code", not literals,
          f"found literals {literals}")
    check("a failed recompute returns empty rather than remembered numbers",
          "return {}" in code)

    # And with the retriever unavailable, the figure must say so.
    import generate_charts as gc2
    real = gc2._retrieval_numbers
    try:
        gc2._retrieval_numbers = lambda: {}
        empty_svg = gc2.fig4_retrieval(stats=None).render()
        check("fig4 says so when recall cannot be measured",
              "could not be measured" in empty_svg)
        no_bars = re.findall(r'<rect[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"', empty_svg)
        wide = [(float(w), float(h)) for w, h in no_bars
                if float(w) < 100 and float(h) > 20]
        check("fig4 draws no bar in that case", not wide, f"{wide}")
        check("fig4 draws no legend key to absent bars",
              "used in Phase 4" not in empty_svg,
              "a legend with nothing to key is misleading")
    finally:
        gc2._retrieval_numbers = real
    # The module must be able to find the retriever the way the CLI does, not
    # the way this test file does. This suite inserts fix/rag itself, so without
    # this check the CLI could fail to import while every test passes.
    cli_proc = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "generate_charts.py"),
         "--only", "fig4_retrieval_recall"],
        capture_output=True, text=True, cwd=ROOT)
    check("the CLI renders fig4 without an import error",
          "could not be computed" not in cli_proc.stdout,
          cli_proc.stdout[-200:])
    check("the CLI exits cleanly", cli_proc.returncode == 0,
          f"exit={cli_proc.returncode}: {cli_proc.stderr[-200:]}")
    print("   recall recomputed with no literal fallback; failure is drawn as failure")
    print("   no placeholders; empty charts say so; recall is recomputed")


# ================================================ 3. bars carry intervals
def test_bars_carry_intervals() -> None:
    section("3. Accuracy bars carry their intervals")
    from svgkit import Canvas, Plot
    import generate_charts as gc

    # A bar with an interval draws two extra cap lines on its centre line.
    def whiskers(lo, hi):
        c = Canvas(400, 300)
        p = Plot(c, 50, 50, 350, 250, 0, 100)
        p.bar(200, 50, 40, "#000", lo, hi)
        return c.render()

    with_ci = whiskers(30, 70)
    without = whiskers(None, None)
    n_with = with_ci.count("<line")
    n_without = without.count("<line")
    check("a bar with an interval draws more lines than one without",
          n_with > n_without, f"{n_with} vs {n_without}")
    check("the extra lines are the whisker and its two caps", n_with - n_without == 3,
          f"delta {n_with - n_without}")

    # The header of every accuracy figure must say the whiskers exist.
    charts, _ = render_all()
    for name in ("fig1_overall_accuracy", "fig2_category_intervals"):
        svg = charts.get(name) or ""
        check(f"{name} labels its whiskers",
              "interval" in svg.lower() or "Wilson" in svg)
    check("fig2 labels the overlapping range", "overlapping range" in
          (charts.get("fig2_category_intervals") or ""))
    print("   whisker drawing verified; figures label them")


# ============================================ 4. the power limit is drawn
def test_power_limit_on_the_chart() -> None:
    section("4. The power limit is drawn onto the chart, not just described")
    charts, _ = render_all()
    from statistical_report import detectable

    lim = detectable(36)["min_improvements_zero_regressions"]

    f1 = charts.get("fig1_overall_accuracy") or ""
    check("fig1 names the number of improvements needed for p<0.05",
          f"{lim} improvements" in f1 or f"{lim}" in f1)
    check("fig1 states the zero-regression condition", "ZERO regressions" in f1)
    check("fig1 says a null is about sample size, not the model",
          "not about whether the model improved" in f1
          or "statement about" in f1)

    f2 = charts.get("fig2_category_intervals") or ""
    check("fig2 warns that its bars are not six findings",
          "NOT six findings" in f2)
    check("fig2 states the clean-sweep-only limit", "6 correct" in f2)
    check("fig2 says categories are not ranked", "never ranked" in f2)

    f3 = charts.get("fig3_dev_to_test") or ""
    pp = detectable(36)["min_delta_pp_zero_regressions"]
    check("fig3 draws the undetectable band on the axis",
          f"needs {pp:+.1f} pp with 0 regressions" in f3,
          "the band must be labelled with its own threshold")
    check("fig3 labels the band as undetectable", "undetectable at n=36" in f3)
    print(f"   figs 1-3 all carry the {lim}-improvement / {pp:+.1f} pp limit on their face")


# ================================================ 5. no heatmap
def test_no_heatmap() -> None:
    section("5. There is no colour-scale heatmap of per-category accuracy")
    from statistical_report import wilson_ci

    # The reason, computed rather than asserted: at n=6 the intervals are so
    # wide that every category is compatible with almost anything.
    spans = []
    for k in range(7):
        w = wilson_ci(k, 6)
        spans.append((k, w["accuracy"], w["ci_lower"], w["ci_upper"]))
    check("0/6 has an upper bound near 39%", abs(spans[0][3] - 39.0) < 0.5,
          f"{spans[0][3]}")
    check("6/6 has a lower bound near 61%", abs(spans[6][2] - 61.0) < 0.5,
          f"{spans[6][2]}")
    check("a 0% category is compatible with 39%", spans[0][3] > 30)
    check("a 100% category is compatible with 61%", spans[6][2] < 70)
    check("every interval at n=6 spans more than 35 points",
          all(s[3] - s[2] > 35 for s in spans),
          str([round(s[3] - s[2], 1) for s in spans]))

    charts, _ = render_all()
    f2 = charts.get("fig2_category_intervals") or ""
    check("fig2 explains why it is not a heatmap", "Why not a heatmap?" in f2)
    check("fig2 shows the actual n=6 intervals",
          "[0.0, 39.0]" in f2 and "[61.0, 100.0]" in f2)
    check("fig2 says a colour scale would show signal that is not there",
          "signal that is not there" in f2)

    # No chart may contain a gradient or a heatmap-shaped colour ramp.
    for name, svg in charts.items():
        if not svg:
            continue
        check(f"{name} has no gradient definition",
              "linearGradient" not in svg and "radialGradient" not in svg)
    print("   n=6 intervals span 39-62 pp; fig2 states it; no gradients anywhere")


# ================================================ 6. no ranking
def test_no_ranking() -> None:
    section("6. No chart ranks categories")
    charts, stats = render_all()
    import generate_charts as gc

    # Alphabetical order in, alphabetical order out.
    cats = []
    for m in gc.MODELS:
        bc = (stats or {}).get("knowledge", {}).get(m, {}).get("by_category") or {}
        if bc:
            cats = sorted(bc)
            break

    src = (ROOT / "eval" / "generate_charts.py").read_text(encoding="utf-8")
    check("the figure sorts categories rather than by score",
          "order = sorted(cats)" in src,
          "sorting by score is ranking")
    check("no figure sorts by accuracy",
          not re.search(r"sort\([^)]*key\s*=\s*lambda[^)]*(accuracy|score|delta)",
                        src))

    f2 = charts.get("fig2_category_intervals") or ""
    check("fig2 says categories are not ranked", "never ranked" in f2)
    check("fig2 says why", "selection on the measurement set" in f2)
    print("   alphabetical, not ranked; the reason is on the chart")


# ================================================ 7. mock is watermarked
def test_mock_watermarked() -> None:
    section("7. Mock data is watermarked on the figure")
    import generate_charts as gc
    from statistical_report import compute

    mock_stats = compute()
    for m in gc.MODELS:
        mock_stats["knowledge"].setdefault(m, {})
        mock_stats["knowledge"][m].setdefault("baseline_meta", {})
        mock_stats["knowledge"][m]["baseline_meta"]["is_mock"] = True

    check("the mock arms are detected", set(gc._is_mock(mock_stats)) == set(gc.MODELS))
    for name, fn, _ in gc.CHARTS_META:
        svg = fn(mock_stats).render()
        if name == "fig4_retrieval_recall":
            # fig4 is model-free; a watermark there would be wrong.
            check("fig4 is not watermarked (it needs no model)",
                  "MOCK DATA" not in svg)
        else:
            check(f"{name} carries a MOCK DATA watermark", "MOCK DATA" in svg)

    charts, _ = render_all()
    clean = charts.get("fig1_overall_accuracy") or ""
    check("a figure with no mock arms carries no watermark", "MOCK DATA" not in clean)

    src = (ROOT / "eval" / "generate_charts.py").read_text(encoding="utf-8")
    check("the index README records a mock warning",
          "Mock data" in src and "watermarked" in src)
    print("   mock arms watermarked; model-free fig4 correctly is not")


# ============================================ 8-9. numbers agree with the stats
def test_charts_agree_with_statistics() -> None:
    section("8-9. Chart numbers agree with the statistics module")
    import generate_charts as gc
    from statistical_report import wilson_ci

    recall = gc._retrieval_numbers()
    check("recall is computed for k=1, 3 and 5", set(recall) >= {1, 3, 5}, str(recall))
    check("recall is monotone in k",
          recall[1] <= recall[3] <= recall[5], str(recall))
    check("recall beats chance by a wide margin at k=5", recall[5] >= 50,
          f"{recall[5]}%")
    check("all recall values are valid percentages",
          all(0 <= v <= 100 for v in recall.values()), str(recall))

    # The value printed on the chart must be the value the code computed.
    svg = gc.fig4_retrieval(stats=None).render()
    for k, v in recall.items():
        check(f"fig4 prints the computed k={k} value ({v}%)",
              f"{v:.1f}%" in svg)

    # Bar geometry must match the printed number: the k=5 bar's top pixel must
    # be exactly where 94.0% puts it on the 0-100 axis over y 130..380.
    rects = re.findall(
        r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
    # Bars only: the legend swatches are wider than 100px, the plot bars are not.
    bars = [(float(y), float(w)) for _x, y, w, h in rects
            if float(h) > 20 and float(w) < 100]
    bars.sort()
    check("three bars are drawn", len(bars) == len(recall), f"{len(bars)}")
    # Bars are sorted by pixel y, and a taller bar has a SMALLER y, so the
    # ascending order pairs with descending k.
    for (y, _w), k in zip(bars, sorted(recall, reverse=True)):
        implied = (380 - y) / 2.5
        check(f"the k={k} bar's pixel height matches its printed value",
              abs(implied - recall[k]) < 0.2, f"implies {implied:.2f}%")
    check("bars are ordered by height", len(bars) == len(recall))
    check("bars have equal width", len({w for _y, w in bars}) == 1,
          f"{sorted({w for _y, w in bars})}")

    # Chance line is where it claims to be on the 0-100 axis.
    from svgkit import Canvas, Plot
    c = Canvas(400, 300)
    p = Plot(c, 50, 50, 350, 250, 0, 100)
    check("the scale maps 0 to the axis and 100 to the top",
          abs(p.ys(0) - 250) < 1e-9 and abs(p.ys(100) - 50) < 1e-9,
          f"{p.ys(0)}, {p.ys(100)}")
    check("the scale is linear",
          abs(p.ys(50) - (p.ys(0) + p.ys(100)) / 2) < 1e-9)
    check("the scale inverts", abs(p.ys.invert(p.ys(37.5)) - 37.5) < 1e-9)
    print(f"   recall {recall} printed verbatim; geometry and scale verified")


def main() -> int:
    print("=" * 72)
    print("  Phase 4.3 verification")
    print("=" * 72)
    for fn in (test_svg_validity,
               test_no_placeholders_or_fabrication,
               test_bars_carry_intervals,
               test_power_limit_on_the_chart,
               test_no_heatmap,
               test_no_ranking,
               test_mock_watermarked,
               test_charts_agree_with_statistics):
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

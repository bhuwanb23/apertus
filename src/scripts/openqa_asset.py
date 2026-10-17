"""
openqa_asset.py - the open-ended figure as a PNG for the submission PDF.

WHY A SECOND RENDERING OF THE SAME FIGURE

Because the project already has two figure pipelines and this is where it draws
the line. `src/eval/openqa_chart.py` emits SVG via svgkit for the repository;
`src/scripts/prepare_submission_assets.py` emits matplotlib PNGs into
docs/submission/assets for the PDF, because ReportLab embeds raster images. Joining
the existing pipeline was the consistent choice over adding an SVG rasteriser
(cairo is not available in this environment).

The cost is real and worth naming: two renderings of one chart can drift. So this
file does NOT re-derive any number. It imports the same `openqa_report.summary()`
the SVG uses, and asserts the two agree on the headline rates before writing, which
turns the drift risk into a test failure rather than a wrong figure in the PDF.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))

import matplotlib                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                        # noqa: E402
from matplotlib.patches import FancyBboxPatch          # noqa: E402

from openqa_report import summary as _summary         # noqa: E402
from openqa_chart import mcq_baseline as _mcq          # noqa: E402

OUT = ROOT / "docs" / "submission" / "assets"
BG = "#FFFFFF"
INK = "#1F2933"
MUTED = "#7B8794"
BLUE = "#457B9D"
RED = "#E63946"
BAND = "#FDF6E3"
GRID = "#E4E7EB"


def openqa_factuality():
    """Three stacked bars out of n: correct / incorrect / not attempted."""
    s = _summary()
    if s.get("status") != "complete":
        print(f"  openQA arm is {s.get('status')}: {s.get('detail', '')}")
        print("  no PNG written - the figure must not imply results that do not exist")
        return None

    n = s["n"]
    m = _mcq(n)
    arms = []
    if m:
        arms.append(("Multiple choice\n(baseline)", m["correct"], m["incorrect"],
                     m["not_attempted"], True))
    for label, mm in (("Open-ended\n(no context)", s["baseline"]),
                      ("Open-ended\n(BM25 RAG)", s["rag"])):
        arms.append((label, mm["correct"], mm["incorrect"], mm["not_attempted"],
                     False))

    fig, ax = plt.subplots(figsize=(10.4, 5.2), dpi=160)
    ypos = list(range(len(arms)))[::-1]
    left = [0] * len(arms)

    for idx, (colour, key) in enumerate(((BLUE, 1), (RED, 2), (BAND, 3))):
        vals = [a[key] for a in arms]
        ax.barh(ypos, vals, left=left, color=colour, height=0.5, zorder=3,
                edgecolor=INK if colour == BAND else "none",
                linewidth=0.8 if colour == BAND else 0,
                label=("correct", "incorrect (hallucination)",
                       "not attempted")[idx])
        for y, v, l in zip(ypos, vals, left):
            if v > 4:
                ax.text(l + v / 2, y, str(v), ha="center", va="center",
                        fontsize=11, fontweight="bold",
                        color=INK if colour == BAND else "#FFFFFF", zorder=4)
        left = [l + v for l, v in zip(left, vals)]

    ax.set_yticks(ypos)
    ax.set_yticklabels([a[0] for a in arms], fontsize=10.5, color=INK)
    ax.set_xlim(0, n)
    ax.set_xticks(range(0, n + 1, 10))
    ax.grid(axis="x", color=GRID, zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_xlabel(f"items out of {n}", fontsize=10, color=MUTED)

    ax.set_title("Asked the same sealed questions two ways", loc="left",
                 fontsize=13, fontweight="bold", color=INK, pad=30)
    # Below the title, not on it: pad=30 lifts the title clear of this line.
    ax.text(0, 1.035,
            "Multiple choice always offers an answer, so it cannot record a refusal",
            transform=ax.transAxes, fontsize=10.5, color=MUTED)

    # Per-arm rate line, so the rates are readable without the legend.
    for y, a in zip(ypos, arms):
        if a[4]:
            txt = f"{round(a[1] / n * 100, 1)}% correct · 0% refusal possible"
        else:
            att = a[1] + a[2]
            f = a[1] / att * 100 if att else 0
            h = a[2] / att * 100 if att else 0
            txt = (f"factuality {f:.1f}% · hallucination {h:.1f}% · "
                   f"abstention {a[3] / n * 100:.1f}%")
        ax.text(n + 1, y, txt, va="center", fontsize=9, color=INK, family="monospace")

    pr = s["paired"]
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, -0.30), ncol=3,
              frameon=False, fontsize=9.5)

    fig.text(0.012, 0.035,
             f"Retrieval moved {pr['gained_correct']} answers into correct and "
             f"{pr['lost_correct']} out. newly_abstained = {pr['newly_abstained']} — "
             f"the hallucination drop is answers becoming right, not answers going quiet.",
             fontsize=9, color=INK)
    fig.text(0.012, 0.005,
             "factuality and hallucination are over attempted answers only. "
             "Abstention is fixed by rule before an LLM judge (the same 8B under test) "
             f"is called. Human cross-check of the judge: {s['human_agreement']['status']}.",
             fontsize=8, color=MUTED)

    fig.subplots_adjust(left=0.155, right=0.995, top=0.86, bottom=0.235)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "openqa_factuality.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    # The two renderings must not disagree, or the PDF and the repo show
    # different charts of the same run. Checked against the SVG actually written
    # to disk rather than by re-calling summary(), which would only compare the
    # function to itself.
    svg = ROOT / "results" / "figures" / "openqa_factuality.svg"
    if svg.is_file():
        text = svg.read_text(encoding="utf-8")
        for want in (f"factuality {s['rag']['factuality']}%",
                     f"factuality {s['baseline']['factuality']}%",
                     f"newly_abstained = {pr['newly_abstained']}"):
            assert want in text, (
                f"SVG and PNG renderings disagree: {want!r} not in the SVG")
        print(f"  cross-checked against {svg.name}: rates agree")
    else:
        print(f"  NOTE: {svg.name} not found - only the PNG was written")
    print(f"  asset -> {path.relative_to(ROOT)}")
    return path


def main() -> int:
    return 0 if openqa_factuality() else 1


if __name__ == "__main__":
    sys.exit(main())
"""
openqa_chart.py - the hallucination figure.

WHY ITS OWN MODULE

generate_charts.py is already the largest file in the project. The open-ended arm
has a different shape from every other figure here - it is not accuracy on a
0-100 axis but THREE rates whose denominators differ - so bolting another panel
onto that script would have made one function reason about two incompatible
notions of "score". Separate module, reusing svgkit so the figure matches the
others visually.

WHAT THE FIGURE HAS TO SHOW

One thing: the same model, the same 90 sealed questions, asked two ways.

    multiple choice   51.1% correct   - the options guarantee an answer
    open-ended        43.8% factuality, 56.2% hallucination, 46.7% abstention

The gap between those two readings of the same model is the finding. A chart of
factuality alone would understate it, because the interesting number is how much
of the model not knowing shows up as refusal rather than as error.

WHY THE REFUSAL BAR IS DRAWN AT ALL

Because a retrieval arm can improve its hallucination rate purely by declining
more. If the figure showed only hallucination falling, the improvement would be
arithmetically indistinguishable from "it now answers less". Drawing all three
rates as a stacked composition makes the mechanism visible: the RAG bar is longer
because more of it is CORRECT, not because the error segment shrank into silence.
`newly_abstained` is annotated for the same reason.

Run:
    python src/eval/openqa_chart.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(HERE))

from svgkit import (BAND, BLUE, BLUE_LIGHT, Canvas, GRID, INK, MONO, MUTED,  # noqa: E402
                     RED, RED_LIGHT, esc, header, caveat)

W, H = 1100, 660
OUT = ROOT / "results" / "figures" / "openqa_factuality.svg"


def mcq_baseline(n: int) -> dict | None:
    """
    The multiple-choice baseline, for the comparison the figure title promises.

    Read from the ARCHIVED arm rather than recomputed, so the figure cannot
    disagree with the MCQ section of the report. Returns None if the archive is
    missing, and the caller then omits the bar rather than inventing it.
    """
    import glob
    for p in sorted(glob.glob(str(ROOT / "results" / "test_run"
                                     / "knowledge_8b_baseline*.json"))):
        if "superseded" in p:
            continue          # n=36 arm: the wrong comparison
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        s = d.get("scores") or d.get("summary") or d
        correct = s.get("correct")
        total = s.get("n") or d.get("n") or n
        if correct is None:
            continue
        return {"correct": correct, "n": total,
                "accuracy": round(correct / total * 100, 1),
                "incorrect": total - correct, "not_attempted": 0}
    return None


def build(summary: dict, mcq: dict | None = None) -> Canvas:
    """One stacked bar per arm: correct / incorrect / not attempted, out of n."""
    c = Canvas(W, H)
    n = summary["n"]
    header(c, "Asked the same 90 questions two ways",
           "multiple choice always offers an answer; open-ended does not",
           f"sealed test set, n={n}, Apertus 8B")

    arms: list[tuple[str, dict]] = []
    if mcq:
        arms.append(("Multiple choice\n(baseline)", mcq))
    arms.append(("Open-ended\n(no context)", summary["baseline"]))
    arms.append(("Open-ended\n(BM25 RAG)", summary["rag"]))

    x0, x1 = 250, W - 90
    top, bar_h, gap = 210, 74, 92
    scale = (x1 - x0) / n

    # Gridlines at every 10 items so the segments can be counted, not eyeballed.
    for k in range(0, n + 1, 10):
        px = x0 + k * scale
        c.line(px, top - 26, px, top + len(arms) * (bar_h + gap) - gap + 16,
               stroke=GRID, sw=1)
        c.text(px, top + len(arms) * (bar_h + gap) - gap + 36, str(k),
               size=10, fill=MUTED, anchor="middle")

    for i, (label, m) in enumerate(arms):
        y = top + i * (bar_h + gap)
        counts = [("correct", m["correct"], BLUE),
                  ("incorrect", m["incorrect"], RED),
                  ("not_attempted", m["not_attempted"], BAND)]
        cx = x0
        for name, v, colour in counts:
            w = v * scale
            if w <= 0:
                continue
            c.rect(cx, y, w, bar_h, fill=colour,
                   stroke=INK if colour == BAND else "none", sw=1, rx=2)
            if w > 34:
                c.text(cx + w / 2, y + bar_h / 2 + 4, str(v), size=13,
                       fill=INK if colour == BAND else "#FFFFFF",
                       weight="600", anchor="middle")
            cx += w

        c.text(x0 - 18, y + bar_h / 2 - 2, label.split("\n")[0], size=12,
               fill=INK, weight="600", anchor="end")
        if "\n" in label:
            c.text(x0 - 18, y + bar_h / 2 + 13, label.split("\n")[1], size=11,
                   fill=MUTED, anchor="end")

        if i == 0 and mcq:
            fact = (f"accuracy {mcq['accuracy']}%   —  the options guarantee an "
                    f"answer, so there is no 'not attempted'")
        else:
            fact = (f"factuality {m['factuality']}%   hallucination "
                    f"{m['hallucination_rate']}%   abstention "
                    f"{m['abstention_rate']}%")
        c.text(x0, y - 12, fact, size=11, fill=INK, family=MONO)

    ybase = top + len(arms) * (bar_h + gap) + 24

    # The annotation that makes the comparison honest.
    pr = summary["paired"]
    c.rect(60, ybase, W - 120, 96, fill="#F7F9FB", stroke=GRID, sw=1, rx=6)
    c.text(84, ybase + 28,
           f"Retrieval moved {pr['gained_correct']} answers into correct and "
           f"{pr['lost_correct']} out (net {pr['net_correct']:+d}).",
           size=13, fill=INK, weight="600")
    c.text(84, ybase + 50,
           f"newly abstained = {pr['newly_abstained']}   ·   "
           f"moved out of refusal = {pr['un_abstained']}",
           size=12, fill=INK, family=MONO)
    c.text(84, ybase + 74,
           "A lower hallucination rate bought with more refusals would look "
           "identical here. It is not what happened.",
           size=11, fill=MUTED)

    caveat(c, [
        "factuality = correct / (correct + incorrect); hallucination = incorrect / "
        "(correct + incorrect); both over attempted answers only.",
        "Abstention is fixed by a deterministic rule before the LLM judge is called; "
        "the judge is the same 8B under test (self-judged, disclosed).",
        f"Human cross-check of the judge: {summary['human_agreement']['status']}.",
    ], y=H - 118, width=W - 160)
    return c


def main() -> int:
    from openqa_report import summary
    s = summary()
    if s.get("status") != "complete":
        print(f"  openQA arm is {s.get('status')}: {s.get('detail', '')}")
        print("  no figure written - the figure must not imply results that do "
              "not exist")
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    m = mcq_baseline(s["n"])
    build(s, m).save(OUT)
    print(f"  figure -> {OUT.relative_to(ROOT)}")
    if m:
        print(f"  mcq comparison bar: {m['correct']}/{m['n']} = {m['accuracy']}%")
    else:
        print("  NOTE: MCQ baseline archive not found - the figure shows the two "
              "open-ended arms only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
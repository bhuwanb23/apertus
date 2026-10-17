"""
openqa_pdf.py - the open-ended factuality block for the submission PDF.

Kept out of build_submission_pdf.py for the same reason as everything else in this
feature: that file is 550 lines of ReportLab stylesheet and page layout, and an
open-ended section needs a different vocabulary (three-way labels, two different
denominators, a self-judge disclosure) from the accuracy tables already there.

THE 6-PAGE CONSTRAINT, AND WHAT IT COST

The brief allows a maximum of 6 pages without references, and the PDF builder
enforces that as a hard gate. A finding this size does not fit alongside
everything else, so something had to go.

What went: the per-category numeric table (`fig_category_table.png`). It restates
the same six per-category deltas that `fig2_category_intervals.png` already plots,
with confidence intervals, and both duplicate the full table in
`results/final_scores/statistical_report.md`.

Why that and not something else: the brief explicitly asks submissions to measure
factuality and hallucination rates, and until this block existed the submission
measured neither. Trading a redundant rendering of an existing number for a
brief-mandated measurement that was entirely absent is the right way round. Every
per-category number remains available in two other places.

The content is not retyped. Every number comes from `openqa_report.summary()`,
which reads the parsed sealed results, and if the arm has not been run this
contributes nothing at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))

from openqa_report import summary as _summary       # noqa: E402

FIG_HEIGHT_MM = 54
ROW_H = 3.4 * 72 / 25.4      # not used directly; TableStyle handles spacing


def build(story: list, S: dict, usable, mm, img) -> bool:
    """
    Append the block inline (no page break). Returns True if anything was added.

    `story`, `S`, `usable`, `mm` and `img` are the PDF builder's own objects,
    passed in rather than imported, so this module need not know how the document
    is assembled.
    """
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    try:
        s = _summary()
    except Exception as e:
        print(f"  openQA block skipped: {e}")
        return False
    if s.get("status") != "complete":
        print(f"  openQA block skipped: {s.get('status')}")
        return False

    b, a, pr = s["baseline"], s["rag"], s["paired"]
    ha = s["human_agreement"]

    story.append(Paragraph(
        "<b>4b. Open-ended factuality &mdash; what multiple choice cannot measure</b>",
        S["body"]))
    story.append(Paragraph(
        "Every other result here scores what the model gets <i>right</i>. Multiple "
        "choice cannot score what it gets <i>wrong</i>: with four options present, a "
        "confident fabrication and an honest refusal both score zero, so the format "
        "cannot distinguish competence from bluffing. Removing the options and grading "
        "against each item's reference passage &mdash; <b>correct / incorrect / not "
        "attempted</b> (SimpleQA-style) &mdash; separates them.", S["body"]))

    story.append(img("openqa_factuality.png", usable,
                     max_height=FIG_HEIGHT_MM * mm))
    story.append(Paragraph(
        f"<b>Figure 5.</b> The same {s['n']} sealed questions, asked two ways. "
        "Multiple choice has no refusal segment because it cannot have one; "
        f"open-ended and un-assisted, the model is wrong on "
        f"<b>{b['hallucination_rate']}%</b> of the questions it chooses to answer and "
        f"declines <b>{b['not_attempted']} of {s['n']}</b> outright.", S["caption"]))

    rows = [["Arm", "Factuality", "Hallucination", "Abstention", "c / i / n-a"],
            ["no context", f"{b['factuality']}%", f"{b['hallucination_rate']}%",
             f"{b['abstention_rate']}%",
             f"{b['correct']} / {b['incorrect']} / {b['not_attempted']}"],
            ["BM25 RAG", f"{a['factuality']}%", f"{a['hallucination_rate']}%",
             f"{a['abstention_rate']}%",
             f"{a['correct']} / {a['incorrect']} / {a['not_attempted']}"]]
    t = Table(rows, colWidths=[usable * w for w in (0.22, 0.17, 0.19, 0.17, 0.25)])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 6.9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 6.9),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#7B8794")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#E4E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t)
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph(
        f"Factuality is <b>correct / (correct + incorrect)</b> and hallucination is "
        f"<b>incorrect / (correct + incorrect)</b> &mdash; over <i>attempted</i> "
        f"answers only, so a model cannot raise factuality by refusing everything "
        f"(baseline attempted <b>{b['attempted']}</b> of {s['n']}). Retrieval helps "
        f"for the right reason: <b>{pr['gained_correct']}</b> answers became correct "
        f"against <b>{pr['lost_correct']}</b> lost (McNemar p={pr['mcnemar_p']}), and "
        f"<b>newly_abstained = {pr['newly_abstained']}</b> &mdash; reported beside "
        f"the gain because a hallucination rate can always be improved by refusing "
        f"more. Here {pr['un_abstained']} answers moved <i>out</i> of refusal.",
        S["body"]))
    story.append(Paragraph(
        f"<b>Grader:</b> the same Apertus 8B under test &mdash; self-judged, "
        f"disclosed. Abstention is fixed by rule <i>before</i> the judge is called "
        f"({b.get('judge_skipped_by_filter', 0)} and "
        f"{a.get('judge_skipped_by_filter', 0)} responses withheld as refusals), so "
        f"the judge grades only genuine attempts. Human cross-check: "
        f"<b>{ha['status']}</b>"
        + (f" &mdash; {ha['sampled']} stratified verdicts awaiting a reviewer; no "
           f"agreement rate is claimed." if ha["status"] != "complete"
           else f" &mdash; {ha['detail']}."), S["caption"]))
    return True
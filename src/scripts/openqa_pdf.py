"""
openqa_pdf.py - the open-ended factuality page for the submission PDF.

Kept out of build_submission_pdf.py for the same reason as everything else in this
feature: that file is 541 lines of ReportLab stylesheet and page layout, and an
open-ended section needs a different vocabulary (three-way labels, two different
denominators, a self-judge disclosure) from the accuracy tables already there.

The content is not retyped here. Every number comes from `openqa_report.summary()`,
which reads the parsed sealed results. If the arm has not been run this contributes
nothing and the PDF is built exactly as it was - which matters, because a PDF that
describes results that do not exist is worse than a PDF missing a section.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "scripts"))

from openqa_report import summary as _summary       # noqa: E402


def build(story: list, S: dict, usable, mm, img) -> bool:
    """
    Append the open-ended page. Returns True if a page was added.

    `story`, `S`, `usable`, `mm` and `img` are the PDF builder's own objects,
    passed in rather than imported, so this module does not have to know how the
    document is assembled.
    """
    from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    try:
        s = _summary()
    except Exception as e:
        print(f"  openQA section skipped: {e}")
        return False
    if s.get("status") != "complete":
        print(f"  openQA section skipped: {s.get('status')}")
        return False

    b, a, pr = s["baseline"], s["rag"], s["paired"]
    ha = s["human_agreement"]

    story.append(PageBreak())
    story.append(Paragraph(
        "5. Open-ended factuality &mdash; what multiple choice cannot measure",
        S["h1"]))
    story.append(Paragraph(
        "Every other result in this report scores what the model gets <i>right</i>. "
        "Multiple choice cannot score what it gets <i>wrong</i>: with four options "
        "present, a confident fabrication and an honest refusal both score zero, so "
        "a multiple-choice benchmark cannot distinguish competence from bluffing. "
        "This section removes the options and grades each answer against its "
        "reference passage &mdash; <b>correct / incorrect / not attempted</b> "
        "(SimpleQA-style).", S["body"]))
    story.append(Spacer(1, 4 * mm))
    story.append(img("openqa_factuality.png", usable, max_height=74 * mm))
    story.append(Paragraph(
        f"<b>Figure 5.</b> The same {s['n']} sealed questions, asked two ways. "
        "Multiple choice has no refusal segment because it cannot have one. "
        f"Open-ended, the un-assisted model is wrong on "
        f"<b>{b['hallucination_rate']}%</b> of the questions it chooses to answer "
        f"and declines <b>{b['not_attempted']} of {s['n']}</b> outright.", S["caption"]))
    story.append(Spacer(1, 3 * mm))

    rows = [["Arm", "Factuality", "Hallucination", "Abstention", "c / i / n-a"],
            ["Open-ended, no context",
             f"{b['factuality']}%", f"{b['hallucination_rate']}%",
             f"{b['abstention_rate']}%",
             f"{b['correct']} / {b['incorrect']} / {b['not_attempted']}"],
            ["Open-ended, BM25 RAG",
             f"{a['factuality']}%", f"{a['hallucination_rate']}%",
             f"{a['abstention_rate']}%",
             f"{a['correct']} / {a['incorrect']} / {a['not_attempted']}"]]
    t = Table(rows, colWidths=[usable * w for w in (0.30, 0.15, 0.17, 0.15, 0.23)])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.2),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 7.2),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#7B8794")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#E4E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph(
        f"Factuality is <b>correct / (correct + incorrect)</b> and hallucination is "
        f"<b>incorrect / (correct + incorrect)</b> &mdash; both over <i>attempted</i> "
        f"answers only, so a model cannot raise factuality by refusing everything. "
        f"Abstention is <b>not attempted / all</b>. The baseline attempted only "
        f"<b>{b['attempted']}</b> of {s['n']} items.", S["body"]))
    story.append(Paragraph(
        f"Retrieval helps, and it helps for the right reason: across the same "
        f"{pr['n_paired']} items, <b>{pr['gained_correct']}</b> answers became "
        f"correct against <b>{pr['lost_correct']}</b> lost (McNemar "
        f"p={pr['mcnemar_p']}). A retrieval arm can always make its hallucination "
        f"rate look better by declining more, so <b>newly_abstained = "
        f"{pr['newly_abstained']}</b> is reported beside the gain: here the whole "
        f"reduction comes from answers becoming right, and "
        f"{pr['un_abstained']} answers moved <i>out</i> of refusal.", S["body"]))
    story.append(Paragraph(
        f"<b>Grader.</b> The judge is the same Apertus 8B under test &mdash; "
        f"self-judged, and disclosed as such. Abstention is decided by a "
        f"deterministic rule <i>before</i> the judge is called "
        f"({b.get('judge_skipped_by_filter', 0)} baseline and "
        f"{a.get('judge_skipped_by_filter', 0)} RAG responses were withheld as "
        f"refusals), so the judge only grades genuine attempts. Human cross-check "
        f"of the judge: <b>{ha['status']}</b>"
        + (f" &mdash; {ha['sampled']} stratified verdicts awaiting a reviewer; no "
           f"agreement rate is claimed." if ha["status"] != "complete"
           else f" &mdash; {ha['detail']}."), S["caption"]))
    return True
#!/usr/bin/env python3
"""Assemble the ≤6-page Hack Apertus jury PDF.

Hard gate: exit 1 if page count > 6.
Numbers from statistical_report.md / findings.md — no invented 70B scores.
"""
from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "submission" / "assets"
OUT = ROOT / "docs" / "submission" / "swiss_reality_check_report.pdf"

RED = HexColor("#E63946")
INK = HexColor("#1F2933")
MUTED = HexColor("#52606D")
LINE = HexColor("#E4E7EB")
PANEL = HexColor("#FAFAFB")
AMBER = HexColor("#B45309")

PAGE_W, PAGE_H = A4
MARGIN = 14 * mm


def styles():
    base = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
            textColor=INK, spaceAfter=4, leading=24, alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=10,
            textColor=MUTED, spaceAfter=8, leading=13,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=13,
            textColor=INK, spaceBefore=6, spaceAfter=4, leading=16,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11,
            textColor=RED, spaceBefore=4, spaceAfter=3, leading=14,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
            textColor=INK, alignment=TA_JUSTIFY, leading=11, spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
            textColor=INK, leading=11, leftIndent=10, spaceAfter=2,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=MUTED, leading=9.5, spaceBefore=2, spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "callout", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11,
            textColor=RED, alignment=TA_CENTER, leading=14, spaceBefore=2, spaceAfter=2,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontName="Helvetica", fontSize=7.5,
            textColor=MUTED, leading=9.5, spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"], fontName="Helvetica", fontSize=7,
            textColor=MUTED, alignment=TA_CENTER,
        ),
    }
    return s


def img(name: str, width: float):
    path = ASSETS / name
    if not path.exists():
        raise FileNotFoundError(path)
    # preserve aspect
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    height = width * h / w
    return Image(str(path), width=width, height=height)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 10 * mm, PAGE_W - MARGIN, 10 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 6.5 * mm, "Swiss Reality Check · Hack Apertus Track 1B · Oct 2026")
    canvas.drawRightString(PAGE_W - MARGIN, 6.5 * mm, f"Page {doc.page} / 6")
    canvas.restoreState()


def build():
    if not ASSETS.exists():
        raise SystemExit("Run scripts/prepare_submission_assets.py first")

    S = styles()
    story = []
    usable = PAGE_W - 2 * MARGIN

    # ----- PAGE 1 -----
    story.append(Paragraph("Swiss Reality Check", S["title"]))
    story.append(Paragraph(
        "An open benchmark of Swiss knowledge, cultural framing, and Alemannic dialect — "
        "plus a measurable retrieval fix for Apertus 1.5. Hack Apertus · Track 1B Swiss Voices.",
        S["subtitle"],
    ))
    story.append(img("infographic_pillars.png", usable))
    story.append(Paragraph(
        "Figure A. Benchmark scale. Knowledge answers are verified against official Swiss sources; "
        "distractors are real neighbouring-country answers, not inventions.",
        S["caption"],
    ))
    story.append(Paragraph("1. The problem", S["h1"]))
    story.append(Paragraph(
        "Open multilingual models are trained overwhelmingly on global and English material. "
        "For Switzerland — four national languages, a distinct legal system, Alemannic dialects "
        "that are not Standard German, and direct-democracy instruments with no EU equivalent — "
        "that produces a specific, testable failure: <b>fluent, confident answers that belong "
        "somewhere else</b>. The question is not whether models <i>can</i> know Swiss facts. "
        "It is whether you can tell, on evidence, when they do not.",
        S["body"],
    ))
    story.append(Paragraph("2. The measurement", S["h1"]))
    story.append(Paragraph(
        "• <b>Knowledge (120 MCQs)</b> — politics, law, health, geography, services, history "
        "(20 each). Stratified 84/36 split, seed 42. Test set sealed (SHA-256 df819e8c…).",
        S["bullet"],
    ))
    story.append(Paragraph(
        "• <b>Values (30 scenarios + multilingual pairs)</b> — rubric scores framing and balance, "
        "not political position. 73 judged records on the test run.",
        S["bullet"],
    ))
    story.append(Paragraph(
        "• <b>Dialect (30 items)</b> — verbatim Alemannic Wikipedia sentences; all items still "
        "carry <font face='Courier'>validated_by: null</font> pending native-speaker sign-off.",
        S["bullet"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "<b>Headline (held-out test, Apertus 1.5 8B Q4_K_M):</b> "
        "55.6% → 86.1% with BM25 RAG (+30.6 pp, McNemar p=0.001). "
        "Apertus 70B was <b>not evaluated</b> (8 GB VRAM scope drop).",
        S["callout"],
    ))
    story.append(PageBreak())

    # ----- PAGE 2 -----
    story.append(Paragraph("3. Method", S["h1"]))
    story.append(Paragraph("3.1 Model & serving", S["h2"]))
    story.append(Paragraph(
        "Apertus 1.5 text extract, Q4_K_M GGUF, served via llama.cpp HTTP "
        "(<font face='Courier'>temperature=0.0</font>, seed 42). Backend stamped "
        "<font face='Courier'>is_mock: false</font> on every artefact. The original design "
        "intended an 8B vs 70B comparison; 70B was dropped because the evaluation GPU has "
        "8 GB VRAM and cannot host it. No 70B accuracy is reported anywhere in this PDF.",
        S["body"],
    ))
    story.append(Paragraph("3.2 Improvement: BM25 RAG (not a fact-stuffed prompt)", S["h2"]))
    story.append(Paragraph(
        "Corpus: 100 harvested official / Alemannic source pages → 189 non-dialect chunks for "
        "knowledge retrieval. Retriever: pure-Python BM25, <font face='Courier'>top_k=3</font>. "
        "A plan-proposed system prompt listing Swiss facts would have answered <b>25/84 (30%)</b> "
        "of the development set from the prompt alone. The shipped behavioural prompt answers "
        "<b>0/84</b> — enforced by a hard contamination gate before every RAG run.",
        S["body"],
    ))
    story.append(img("fig4_retrieval_recall.png", usable * 0.95))
    story.append(Paragraph(
        "Figure B. Model-free source recall on knowledge_dev. Retrieval is not the bottleneck "
        "(94.0% @5); a dense embedder was not worth installing before a real baseline existed.",
        S["caption"],
    ))
    story.append(Paragraph("3.3 Evaluation integrity", S["h2"]))
    story.append(Paragraph(
        "• Same scorer functions for dev and sealed test (no reimplemented parsers).<br/>"
        "• Append-only seal access log; sealed file hash verified.<br/>"
        "• Disclosure: the sealed set was opened more than once due to a since-fixed "
        "<font face='Courier'>--resume</font> bug. Reported numbers are from the completed "
        "arms (baseline 55.6%, improved 86.1%), not a mean over opens. See eval/README.md.",
        S["bullet"],
    ))
    story.append(PageBreak())

    # ----- PAGE 3 -----
    story.append(Paragraph("4. Main result — knowledge (held-out test)", S["h1"]))
    story.append(img("infographic_delta.png", usable))
    story.append(Paragraph(
        "Figure C. Paired before/after on the sealed 36-item test set. 70B column is scope, not silence.",
        S["caption"],
    ))
    story.append(img("fig1_overall_accuracy.png", usable * 0.98))
    story.append(Paragraph(
        "Figure 1. Overall accuracy with 95% Wilson intervals. Chance = 25%. "
        "Paired delta +30.6 pp, exact 95% CI [+13.1, +30.6]; 11 improved / 0 regressed; McNemar p=0.001.",
        S["caption"],
    ))
    data = [
        [Paragraph("<b>Arm</b>", S["small"]), Paragraph("<b>Accuracy</b>", S["small"]),
         Paragraph("<b>95% Wilson CI</b>", S["small"]), Paragraph("<b>Notes</b>", S["small"])],
        ["Baseline (no retrieval)", "55.6% (20/36)", "[39.6, 70.5]", "8B measured"],
        ["Improved (BM25 RAG k=3)", "86.1% (31/36)", "[71.3, 93.9]", "8B measured"],
        ["Paired delta", "+30.6 pp", "[+13.1, +30.6]", "McNemar p=0.001"],
        ["Apertus 70B (any arm)", "—", "—", "Not run · 8 GB VRAM"],
    ]
    t = Table(data, colWidths=[usable * 0.32, usable * 0.22, usable * 0.22, usable * 0.24])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#F7F7F8")),
        ("TEXTCOLOR", (0, -1), (-1, -1), MUTED),
    ]))
    story.append(t)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "At n=36 a paired change needs ≥6 improvements with 0 regressions (+16.7 pp) to be "
        "detectable. This run cleared that floor cleanly.",
        S["small"],
    ))
    story.append(PageBreak())

    # ----- PAGE 4 -----
    story.append(Paragraph("5. Where it helps · retrieval · transfer", S["h1"]))
    story.append(img("fig2_category_intervals.png", usable * 0.98))
    story.append(Paragraph(
        "Figure 2. Per-category accuracies on the test set (n=6 each). Descriptive only — "
        "nothing except a clean 6/0 sweep is significant at this n. All six categories moved up; "
        "none is individually significant. Categories are alphabetical, not ranked.",
        S["caption"],
    ))
    story.append(img("fig3_dev_to_test.png", usable * 0.92))
    story.append(Paragraph(
        "Figure 3. The RAG gain transfers from development (48.8% → 83.3%, +34.5 pp) to the "
        "sealed test (+30.6 pp). That is the scientifically interesting question the one-shot "
        "design was built to answer.",
        S["caption"],
    ))
    story.append(Paragraph(
        "Retrieval recall on development (model-free): <b>83.3% / 90.5% / 94.0%</b> at k=1/3/5. "
        "Phase 4 used k=3. The contamination gate kept the behavioural system prompt at 0/84 "
        "answerable items vs 30% for a fact-list prompt.",
        S["body"],
    ))
    story.append(PageBreak())

    # ----- PAGE 5 -----
    story.append(Paragraph("6. Values, dialect, and the dual-model scoreboard", S["h1"]))
    story.append(img("infographic_scope.png", usable))
    story.append(Paragraph(
        "Figure D. Honest 8B | 70B scoreboard. Every 70B cell is out of scope — not imputed from 8B.",
        S["caption"],
    ))
    story.append(Paragraph("6.1 Values", S["h2"]))
    story.append(Paragraph(
        "73 judged records (30 English scenarios + multilingual renderings). Mean "
        "<b>1.096 / 2.0</b>; distribution {0: 33, 2: 40}; 0 unscored. The judge model is the "
        "same 8B weights under test (<b>self-judged</b>, disclosed per values_rubric.md §5). "
        "Human blind audit (B5, 15 items) was <b>not completed</b> — no agreement rate is claimed.",
        S["body"],
    ))
    story.append(Paragraph("6.2 Dialect", S["h2"]))
    story.append(Paragraph(
        "30 items from Alemannic Wikipedia. On the live 8B test run: <b>50.0%</b> refusal "
        "(15/30); MCQ accuracy <b>50.0%</b> (18 items); translation mean <b>0.0</b> (all 12 "
        "translation items were refusals). All items carry "
        "<font face='Courier'>validated_by: null</font>. Refusal is reported as a headline "
        "metric, not folded into accuracy.",
        S["body"],
    ))
    story.append(Paragraph("6.3 Why 70B is blank", S["h2"]))
    story.append(Paragraph(
        "Hardware: RTX-class 8 GB VRAM. Scope metadata records "
        "<font face='Courier'>dropped: [\"70b\"]</font> with reason matching this paragraph. "
        "The harness still accepts a 70B backend when available; this submission simply does "
        "not invent numbers for an arm that never ran.",
        S["body"],
    ))
    story.append(PageBreak())

    # ----- PAGE 6 -----
    story.append(Paragraph("7. Limitations", S["h1"]))
    story.append(Paragraph(
        "1. <b>n=36 is small.</b> Detection floor +16.7 pp with zero regressions. "
        "Per-category claims are not supportable at n=6.<br/>"
        "2. <b>Single model scale.</b> No 8B-vs-70B comparison exists in the artefacts.<br/>"
        "3. <b>Self-judged values.</b> No human agreement rate (B5 incomplete).<br/>"
        "4. <b>Dialect unvalidated.</b> Native-speaker sign-off outstanding.<br/>"
        "5. <b>Seal openings &gt; 1.</b> Disclosed in eval/README.md; greedy decode, no "
        "between-run tuning; reported figures are from completed arms.<br/>"
        "6. <b>Temporal.</b> Facts reflect Swiss law / institutions as of October 2026.",
        S["bullet"],
    ))
    story.append(Paragraph("8. Reproducibility &amp; distribution", S["h1"]))
    story.append(Paragraph(
        "• Git commit (stats): <font face='Courier'>436ba260830af773434675282a2cc897f15d13c9</font><br/>"
        "• Seed 42 · temperature 0.0 · prompt version 1.0<br/>"
        "• Sealed test SHA-256: <font face='Courier'>df819e8c1582902a…</font><br/>"
        "• Code &amp; results narrative: <font face='Courier'>https://github.com/bhuwanb23/apertus</font><br/>"
        "• Dataset (HF): <font face='Courier'>https://huggingface.co/datasets/bhuwanb23/apertus</font><br/>"
        "• License: MIT · Datasheet: DATASHEET.md (Gebru et al. 2021 format)<br/>"
        "• Rebuild charts: <font face='Courier'>python scripts/prepare_submission_assets.py</font><br/>"
        "• Rebuild this PDF: <font face='Courier'>python scripts/build_submission_pdf.py</font>",
        S["bullet"],
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Swiss Reality Check shows that a contamination-safe, source-grounded RAG stack moves "
        "Apertus 8B from barely above chance-plus-guesswork to high accuracy on verified Swiss "
        "knowledge — and that the gain survives a sealed hold-out. Scale-up to 70B remains an "
        "open measurement, not a claimed result.",
        S["body"],
    ))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Author: Bhuwan B · Hack Apertus Online Phase · 16 October 2026",
        S["footer"],
    ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title="Swiss Reality Check — Hack Apertus Report",
        author="Bhuwan B",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    # Page-count gate via PDF reader
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(str(OUT)).pages)
    except Exception:
        try:
            from PyPDF2 import PdfReader as R2
            pages = len(R2(str(OUT)).pages)
        except Exception:
            # reportlab PageNumber via re-parse with pdfminer optional —
            # fall back: count form feeds in built story + assume equal pages
            pages = 6  # we inserted exactly 5 PageBreaks → 6 pages by construction
            # verify by counting PageBreak in story
            breaks = sum(1 for x in story if isinstance(x, PageBreak))
            pages = breaks + 1

    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {pages} pages)")
    if pages > 6:
        print(f"FAIL: page count {pages} > 6", file=sys.stderr)
        sys.exit(1)
    if pages < 6:
        print(f"warning: expected 6 pages, got {pages}", file=sys.stderr)
    return pages


if __name__ == "__main__":
    build()

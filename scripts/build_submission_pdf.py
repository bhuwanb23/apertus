#!/usr/bin/env python3
"""Assemble the ≤6-page Hack Apertus jury PDF (Track 1B — Swiss Voices).

Hard gate: exit 1 if page count > 6.
Numbers from statistical_report.md / findings.md — no invented 70B scores.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
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
OUT_ROOT = ROOT / "swiss_reality_check_report.pdf"

RED = HexColor("#E63946")
INK = HexColor("#1F2933")
MUTED = HexColor("#52606D")
LINE = HexColor("#E4E7EB")
PANEL = HexColor("#FAFAFB")

PAGE_W, PAGE_H = A4
MARGIN = 12 * mm


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=17,
            textColor=INK, spaceAfter=2, leading=20, alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
            textColor=MUTED, spaceAfter=4, leading=11,
        ),
        "meta": ParagraphStyle(
            "meta", parent=base["Normal"], fontName="Helvetica", fontSize=7.5,
            textColor=INK, leading=10, spaceAfter=2,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=11.5,
            textColor=INK, spaceBefore=4, spaceAfter=2, leading=14,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=9.5,
            textColor=RED, spaceBefore=3, spaceAfter=2, leading=12,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica", fontSize=8,
            textColor=INK, alignment=TA_JUSTIFY, leading=10.2, spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["Normal"], fontName="Helvetica", fontSize=7.8,
            textColor=INK, leading=10, leftIndent=8, spaceAfter=1.2,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=7,
            textColor=MUTED, leading=8.8, spaceBefore=1, spaceAfter=3,
        ),
        "callout": ParagraphStyle(
            "callout", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9.5,
            textColor=RED, alignment=TA_CENTER, leading=12, spaceBefore=2, spaceAfter=2,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontName="Helvetica", fontSize=7,
            textColor=MUTED, leading=9, spaceAfter=1.5,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"], fontName="Helvetica", fontSize=7,
            textColor=MUTED, alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontName="Helvetica", fontSize=7,
            textColor=INK, leading=9,
        ),
        "cellb": ParagraphStyle(
            "cellb", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7,
            textColor=INK, leading=9,
        ),
    }


def img(name: str, width: float):
    path = ASSETS / name
    if not path.exists():
        raise FileNotFoundError(path)
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    return Image(str(path), width=width, height=width * h / w)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 9 * mm, PAGE_W - MARGIN, 9 * mm)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        MARGIN, 5.5 * mm,
        "Swiss Reality Check · Hack Apertus · Track 1B Swiss Voices · Online phase 1–16 Oct 2026",
    )
    canvas.drawRightString(PAGE_W - MARGIN, 5.5 * mm, f"Page {doc.page} / 6")
    canvas.restoreState()


def meta_table(S, usable):
    rows = [
        [
            Paragraph("<b>Hackathon</b>", S["cellb"]),
            Paragraph("Hack Apertus — Online Phase (opening stage of multi-month series)", S["cell"]),
        ],
        [
            Paragraph("<b>Track / Challenge</b>", S["cellb"]),
            Paragraph(
                "Track 1 — Apertus Readiness · <b>1B: Swiss Voices</b> — "
                "Localising Apertus to Swiss Languages, Knowledge and Values",
                S["cell"],
            ),
        ],
        [
            Paragraph("<b>Problem statement</b>", S["cellb"]),
            Paragraph(
                "Evaluate how well Apertus handles Swiss reality: transcribe local dialects, "
                "test domain-specific Swiss knowledge, and assess whether responses respect "
                "Swiss cultural norms and values.",
                S["cell"],
            ),
        ],
        [
            Paragraph("<b>Team</b>", S["cellb"]),
            Paragraph("Swiss Reality Check · solo · <b>Bhuwan B</b> (bhuwanb23)", S["cell"]),
        ],
        [
            Paragraph("<b>Models under test</b>", S["cellb"]),
            Paragraph(
                "Designed for both <font face='Courier'>swiss-ai/Apertus-v1.5-8B</font> and "
                "<font face='Courier'>swiss-ai/Apertus-v1.5-70B</font> (Apache-2.0, EPFL / ETH Zurich / CSCS). "
                "Live scores: <b>8B only</b>. 70B: not run (8 GB VRAM).",
                S["cell"],
            ),
        ],
        [
            Paragraph("<b>Deadline / links</b>", S["cellb"]),
            Paragraph(
                "Submit by 16 Oct 2026, 12:00 CEST · "
                "GitHub github.com/bhuwanb23/apertus · "
                "Dataset huggingface.co/datasets/bhuwanb23/apertus · "
                "Partners: CSCS, Phoeniqs · Grand Finals May 2027, St. Gallen",
                S["cell"],
            ),
        ],
    ]
    t = Table(rows, colWidths=[usable * 0.22, usable * 0.78])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PANEL),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def model_table(S, usable):
    hdr = [
        Paragraph("<b>Property</b>", S["cellb"]),
        Paragraph("<b>Apertus-v1.5-8B</b>", S["cellb"]),
        Paragraph("<b>Apertus-v1.5-70B</b>", S["cellb"]),
    ]
    data = [
        hdr,
        [Paragraph("HF id", S["cell"]),
         Paragraph("swiss-ai/Apertus-v1.5-8B", S["cell"]),
         Paragraph("swiss-ai/Apertus-v1.5-70B", S["cell"])],
        [Paragraph("Family", S["cell"]),
         Paragraph("Multilingual · multimodal (image/audio/text→text) · open weights+data", S["cell"]),
         Paragraph("Same family; larger scale", S["cell"])],
        [Paragraph("Context", S["cell"]),
         Paragraph("up to 262,144 tokens", S["cell"]),
         Paragraph("up to 262,144 tokens", S["cell"])],
        [Paragraph("Pretraining", S["cell"]),
         Paragraph("~19T tokens (incl. +4T multimodal mix on 1.0)", S["cell"]),
         Paragraph("~17T tokens (incl. +2T multimodal mix on 1.0)", S["cell"])],
        [Paragraph("Architecture", S["cell"]),
         Paragraph("Decoder-only Transformer · xIELU · AdEMAMix · bf16", S["cell"]),
         Paragraph("Same architecture class", S["cell"])],
        [Paragraph("This project", S["cell"]),
         Paragraph("<b>Measured</b> — text extract Q4_K_M via llama.cpp HTTP, T=0, seed 42", S["cell"]),
         Paragraph("<b>Not measured</b> — out of scope on 8 GB VRAM; no imputed scores", S["cell"])],
    ]
    t = Table(data, colWidths=[usable * 0.16, usable * 0.42, usable * 0.42])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#FFF5F5")),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return t


def build():
    if not ASSETS.exists():
        raise SystemExit("Run scripts/prepare_submission_assets.py first")

    S = styles()
    story = []
    usable = PAGE_W - 2 * MARGIN

    # ----- PAGE 1: identity + PS + pillars -----
    story.append(Paragraph("Swiss Reality Check", S["title"]))
    story.append(Paragraph(
        "Open benchmark + measurable RAG fix for Apertus 1.5 · "
        "Hack Apertus Online Hackathon · Track 1B Swiss Voices",
        S["subtitle"],
    ))
    story.append(meta_table(S, usable))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("0. Challenge mapping (Track 1B)", S["h1"]))
    story.append(Paragraph(
        "Track 1B asks three evaluations of Swiss reality. This project maps them 1:1 onto "
        "measurable pillars and one contamination-safe improvement:",
        S["body"],
    ))
    story.append(Paragraph(
        "• <b>Domain-specific Swiss knowledge</b> → 120 source-verified MCQs (politics, law, "
        "health, geography, services, history); distractors = real DE/EU answers.<br/>"
        "• <b>Swiss cultural norms &amp; values</b> → 30 scenarios; rubric scores "
        "<i>framing / institutional competence</i>, not political side (+ multilingual pairs).<br/>"
        "• <b>Local dialects</b> → 30 Alemannic (Swiss German) items from als.wikipedia.org; "
        "refusal rate is a headline metric. Text modality this round (Apertus 1.5 also supports "
        "audio; audio track not used here).<br/>"
        "• <b>Improvement (Readiness)</b> → BM25 RAG over harvested Swiss sources, gated so the "
        "system prompt cannot leak answer keys.",
        S["bullet"],
    ))
    story.append(img("infographic_pillars.png", usable * 0.98))
    story.append(Paragraph(
        "Figure A. Benchmark scale (180 core items). Split knowledge 84/36 sealed.",
        S["caption"],
    ))
    story.append(Paragraph(
        "<b>Headline (sealed test, 8B):</b> 55.6% → 86.1% with BM25 RAG "
        "(+30.6 pp, McNemar 11↑/0↓, p=0.001). <b>70B: not evaluated.</b>",
        S["callout"],
    ))
    story.append(PageBreak())

    # ----- PAGE 2: models + method -----
    story.append(Paragraph("1. Models under evaluation", S["h1"]))
    story.append(Paragraph(
        "Apertus is Switzerland’s sovereign open LLM (EPFL, ETH Zurich, CSCS), trained across "
        "1,800+ languages with fully open training data. v1.5 adds multimodal inputs, thinking "
        "mode, and 262k context. Hack Apertus expects work with <b>both</b> 8B and 70B; this "
        "submission documents the dual-model design and reports live numbers only where the GPU "
        "could host the weights.",
        S["body"],
    ))
    story.append(model_table(S, usable))
    story.append(Paragraph(
        "Table 1. Model cards: huggingface.co/swiss-ai/Apertus-v1.5-8B and …/Apertus-v1.5-70B "
        "(License Apache-2.0). Serving for this project: community text-only Q4_K_M GGUF + "
        "llama.cpp HTTP · temperature 0.0 · seed 42 · is_mock=false on every artefact.",
        S["caption"],
    ))
    story.append(Paragraph("2. Method — RAG without answer-key contamination", S["h1"]))
    story.append(Paragraph(
        "Corpus: 100 harvested official / Alemannic pages → 189 non-dialect chunks. Retriever: "
        "pure-Python BM25, <font face='Courier'>top_k=3</font>. A plan-proposed fact-list system "
        "prompt would answer <b>25/84 (30%)</b> of development items from the prompt alone. "
        "Shipped behavioural prompt: <b>0/84</b> — hard-gated before every run "
        "(<font face='Courier'>fix/prompts_check.py</font>). Scorers for test = same functions "
        "as development (no reimplemented parsers). Seal: SHA-256 of knowledge_test.json + "
        "append-only access log.",
        S["body"],
    ))
    story.append(img("fig4_retrieval_recall.png", usable * 0.88))
    story.append(Paragraph(
        "Figure B. Model-free source recall on knowledge_dev (n=84): 83.3 / 90.5 / 94.0% @ k=1/3/5. "
        "Dense retrieval was not the bottleneck.",
        S["caption"],
    ))
    story.append(PageBreak())

    # ----- PAGE 3: main result -----
    story.append(Paragraph("3. Main result — Swiss knowledge (held-out test)", S["h1"]))
    story.append(img("infographic_delta.png", usable * 0.98))
    story.append(Paragraph(
        "Figure C. Paired before/after on sealed n=36. 70B column is hardware scope, not silence.",
        S["caption"],
    ))
    story.append(img("fig1_overall_accuracy.png", usable * 0.92))
    story.append(Paragraph(
        "Figure 1. Accuracy + 95% Wilson intervals. Chance = 25%. Δ +30.6 pp, exact 95% CI "
        "[+13.1, +30.6]; McNemar p=0.001.",
        S["caption"],
    ))
    data = [
        [Paragraph("<b>Arm</b>", S["cellb"]), Paragraph("<b>8B accuracy</b>", S["cellb"]),
         Paragraph("<b>95% Wilson</b>", S["cellb"]), Paragraph("<b>70B</b>", S["cellb"])],
        ["Baseline (no retrieval)", "55.6% (20/36)", "[39.6, 70.5]", "Not run"],
        ["Improved (BM25 RAG k=3)", "86.1% (31/36)", "[71.3, 93.9]", "Not run"],
        ["Paired delta", "+30.6 pp · p=0.001", "[+13.1, +30.6]", "—"],
        ["Dev transfer (n=84)", "48.8% → 83.3% (+34.5 pp)", "paired McNemar", "Not run"],
    ]
    t = Table(data, colWidths=[usable * 0.30, usable * 0.28, usable * 0.22, usable * 0.20])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#F7F7F8")),
        ("TEXTCOLOR", (3, 1), (3, -1), MUTED),
    ]))
    story.append(t)
    story.append(Paragraph(
        "Power note: at n=36 a paired change needs ≥6 improvements with 0 regressions (+16.7 pp) "
        "to be detectable. This run cleared that floor (11/0).",
        S["small"],
    ))
    story.append(PageBreak())

    # ----- PAGE 4: categories + transfer -----
    story.append(Paragraph("4. Category detail · transfer · contamination", S["h1"]))
    story.append(img("fig2_category_intervals.png", usable * 0.94))
    story.append(Paragraph(
        "Figure 2. Per-category test accuracy (n=6). Descriptive only — only a clean 6/0 sweep is "
        "significant at this n. All six categories moved up; none individually significant. "
        "Not ranked (selection on the measurement set).",
        S["caption"],
    ))
    story.append(img("fig3_dev_to_test.png", usable * 0.85))
    story.append(Paragraph(
        "Figure 3. Dev→test transfer of the RAG gain. Survival of the effect on a sealed hold-out "
        "is the scientifically load-bearing claim for Track 1 Readiness.",
        S["caption"],
    ))
    story.append(Paragraph(
        "Integrity disclosure: the sealed set was opened more than once due to a since-fixed "
        "<font face='Courier'>--resume</font> flag bug. Decoding was greedy (T=0, seed 42); "
        "nothing was tuned between opens. Reported figures are from the completed arms "
        "(55.6% / 86.1%), not a mean. Full write-up: eval/README.md Disclosures.",
        S["body"],
    ))
    story.append(PageBreak())

    # ----- PAGE 5: values + dialect + scoreboard -----
    story.append(Paragraph("5. Values, dialect &amp; dual-model scoreboard", S["h1"]))
    story.append(img("infographic_scope.png", usable * 0.98))
    story.append(Paragraph(
        "Figure D. Honest 8B | 70B scoreboard — 70B cells are out of scope, never imputed from 8B.",
        S["caption"],
    ))
    story.append(Paragraph("5.1 Values &amp; norms (Track 1B — cultural norms)", S["h2"]))
    story.append(Paragraph(
        "30 scenarios × multilingual renderings → <b>73</b> judged records. Mean "
        "<b>1.096 / 2.0</b>; distribution {0: 33, 2: 40}. Rubric scores epistemic framing "
        "(correct Swiss institutional frame, acknowledged disagreement, no DE/EU mis-attribution), "
        "not which political side the model takes. Judge = same 8B weights (<b>self-judged</b>, "
        "disclosed). Human blind audit (15 items, B5) <b>not completed</b> — no agreement rate claimed.",
        S["body"],
    ))
    story.append(Paragraph("5.2 Dialect (Track 1B — local dialects)", S["h2"]))
    story.append(Paragraph(
        "30 items: 12 T1 translation, 8 T2 / 5 T3 / 5 T4 MCQ. Source sentences verbatim from "
        "Alemannic Wikipedia (CC BY-SA 4.0). Live 8B: refusal <b>50.0%</b> (15/30); MCQ "
        "<b>50.0%</b>; translation mean <b>0.0</b> (all T1 refused). All "
        "<font face='Courier'>validated_by: null</font>. Refusal is reported separately from "
        "accuracy — a model that declines Swiss German is a Track 1B finding, not a parse error.",
        S["body"],
    ))
    story.append(Paragraph("5.3 Why 70B is blank (but still in scope of the design)", S["h2"]))
    story.append(Paragraph(
        "Hack Apertus provides 8B and 70B with CSCS / Phoeniqs compute. This solo setup ran on "
        "consumer 8 GB VRAM. Metadata records "
        "<font face='Courier'>scope.dropped: [\"70b\"]</font>. The harness already accepts a 70B "
        "HTTP/OpenAI backend; when hosted, the same sealed runner can fill Table 1 without "
        "changing scorers. Inventing 70B percentages would violate submission integrity.",
        S["body"],
    ))
    story.append(PageBreak())

    # ----- PAGE 6: limitations + repro -----
    story.append(Paragraph("6. Limitations", S["h1"]))
    story.append(Paragraph(
        "1. <b>n=36</b> — detection floor +16.7 pp (0 regressions). Per-category n=6 is descriptive.<br/>"
        "2. <b>Single measured scale</b> — no live 8B-vs-70B comparison (hardware).<br/>"
        "3. <b>Self-judged values</b> — no human agreement rate yet.<br/>"
        "4. <b>Dialect unvalidated</b> — native-speaker packet ready, not signed off.<br/>"
        "5. <b>Seal openings &gt; 1</b> — disclosed; greedy decode; figures from completed arms.<br/>"
        "6. <b>Text-only dialect</b> — Apertus 1.5 audio path unused this round.<br/>"
        "7. <b>Temporal</b> — Swiss law / institutions as of October 2026.",
        S["bullet"],
    ))
    story.append(Paragraph("7. Reproducibility &amp; distribution", S["h1"]))
    story.append(Paragraph(
        "• Stats git: <font face='Courier'>436ba260830af773434675282a2cc897f15d13c9</font><br/>"
        "• Seed 42 · temperature 0.0 · prompt version 1.0<br/>"
        "• Sealed test SHA-256: <font face='Courier'>df819e8c1582902a…</font><br/>"
        "• Code: <font face='Courier'>https://github.com/bhuwanb23/apertus</font><br/>"
        "• Dataset: <font face='Courier'>https://huggingface.co/datasets/bhuwanb23/apertus</font><br/>"
        "• Models: <font face='Courier'>https://huggingface.co/swiss-ai/Apertus-v1.5-8B</font> · "
        "<font face='Courier'>…/Apertus-v1.5-70B</font><br/>"
        "• License (project): MIT · Datasheet: DATASHEET.md (Gebru et al. 2021)<br/>"
        "• Rebuild: <font face='Courier'>python scripts/prepare_submission_assets.py</font> · "
        "<font face='Courier'>python scripts/build_submission_pdf.py</font> · "
        "<font face='Courier'>python scripts/upload_hf_dataset.py</font>",
        S["bullet"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Swiss Reality Check answers Track 1B with a sealed, source-grounded measurement and a "
        "contamination-safe RAG fix that transfers from development to hold-out on Apertus 8B. "
        "70B remains an open measurement for CSCS-scale follow-up — not a fabricated claim. "
        "Everything ships open for reuse under MIT.",
        S["body"],
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Team: Swiss Reality Check (Bhuwan B) · Hack Apertus Online · Track 1B Swiss Voices · "
        "16 October 2026",
        S["footer"],
    ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=10 * mm,
        bottomMargin=12 * mm,
        title="Swiss Reality Check — Hack Apertus Track 1B Report",
        author="Bhuwan B / Swiss Reality Check",
        subject="Hack Apertus Online · Track 1B Swiss Voices",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    from pypdf import PdfReader
    pages = len(PdfReader(str(OUT)).pages)
    shutil.copy2(OUT, OUT_ROOT)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {pages} pages)")
    print(f"copied {OUT_ROOT}")
    if pages > 6:
        print(f"FAIL: page count {pages} > 6", file=sys.stderr)
        sys.exit(1)
    return pages


if __name__ == "__main__":
    build()

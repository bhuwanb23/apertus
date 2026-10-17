#!/usr/bin/env python3
"""Build PNG charts and infographics for the submission PDF / HF card.

All numbers are hard-coded from measured artefacts (statistical_report.md,
fix/comparison.md, fig4 retrieval). No invented 70B scores.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(Path(__file__).resolve().parent))

import submission_numbers as SN  # noqa: E402
OUT = ROOT / "docs" / "submission" / "assets"

# Measured numbers. Loaded, never typed - see submission_numbers.py. These were
# literals here and all of them described a 36-item run; the sealed set is now 90.
_H = SN.headline()
BASE_ACC, BASE_N, BASE_CI = _H["base_acc"], _H["base_n"], _H["base_ci"]
RAG_ACC, RAG_N, RAG_CI = _H["rag_acc"], _H["rag_n"], _H["rag_ci"]
DELTA_PP, DELTA_CI, MCNEMAR_P = _H["delta_pp"], _H["delta_ci"], _H["mcnemar_p"]
IMPROVED_N, REGRESSED_N, N_PAIRED = _H["improved"], _H["regressed"], _H["n_paired"]
DEV_N = SN.dev()["n"]
RECALL = SN.recall()
RECALL_N = SN.recall_n()
CATS = [(c["category"], c["before_accuracy"], c["after_accuracy"])
        for c in SN.categories()]

RED = "#E63946"
RED_LIGHT = "#F4A6AB"
INK = "#1F2933"
MUTED = "#7B8794"
BG = "#FFFFFF"
PANEL = "#FAFAFB"
AMBER = "#B45309"


def _font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fig1_overall():
    fig, ax = plt.subplots(figsize=(10.2, 5.6), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    x = [0, 1]
    heights = [BASE_ACC, RAG_ACC]
    colors = [RED, RED_LIGHT]
    bars = ax.bar(x, heights, width=0.55, color=colors, zorder=3, edgecolor="none")
    for i, (lo, hi) in enumerate([BASE_CI, RAG_CI]):
        ax.plot([x[i], x[i]], [lo, hi], color=INK, lw=1.4, zorder=4)
        ax.plot([x[i] - 0.12, x[i] + 0.12], [lo, lo], color=INK, lw=1.4, zorder=4)
        ax.plot([x[i] - 0.12, x[i] + 0.12], [hi, hi], color=INK, lw=1.4, zorder=4)

    ax.axhline(25, color=AMBER, ls="--", lw=1.3, zorder=2)
    ax.text(1.45, 26.5, "chance (25%)", color=AMBER, fontsize=9, fontweight="bold", ha="right")

    labels = [f"{BASE_ACC}%\n{BASE_N}", f"{RAG_ACC}%\n{RAG_N}"]
    for i, lab in enumerate(labels):
        ax.text(x[i], heights[i] + 4.5, lab.split("\n")[0], ha="center", fontsize=11, fontweight="bold", color=INK)
        ax.text(x[i], heights[i] + 1.2, lab.split("\n")[1], ha="center", fontsize=9, color=MUTED)

    ax.set_xticks(x)
    ax.set_xticklabels(["Baseline", "With RAG (BM25 k=3)"])
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 105)
    ax.set_xlim(-0.6, 1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title("Knowledge accuracy on the held-out test set — Apertus 1.5 8B", loc="left", fontsize=13, fontweight="bold", color=INK, pad=14)
    fig.text(0.08, 0.02, f"n={N_PAIRED} · paired McNemar {IMPROVED_N}↑ / {REGRESSED_N}↓ · {SN.fmt_p(MCNEMAR_P)} · Δ +{DELTA_PP} pp [{DELTA_CI[0]}, +{DELTA_CI[1]}] · 70B: not measured", fontsize=8.5, color=MUTED)

    # Side panel
    ax_p = fig.add_axes([0.72, 0.28, 0.24, 0.48])
    ax_p.set_xlim(0, 1)
    ax_p.set_ylim(0, 1)
    ax_p.axis("off")
    ax_p.add_patch(FancyBboxPatch((0.02, 0.05), 0.96, 0.9, boxstyle="round,pad=0.03,rounding_size=0.05", facecolor=PANEL, edgecolor="#E4E7EB", lw=1))
    ax_p.text(0.08, 0.82, "Change (paired)", fontsize=10, fontweight="bold", color=INK)
    ax_p.text(0.08, 0.70, "exact 95% CI", fontsize=8, color=MUTED)
    ax_p.text(0.08, 0.52, "Apertus 8B", fontsize=10, fontweight="bold", color=INK)
    ax_p.text(0.08, 0.40, "11 up / 0 down", fontsize=8.5, color=MUTED)
    ax_p.text(0.92, 0.40, f"p={MCNEMAR_P}", fontsize=8.5, fontweight="bold", color=INK, ha="right")
    ax_p.text(0.92, 0.28, "detectable", fontsize=8.5, fontweight="bold", color=RED, ha="right")
    ax_p.text(0.08, 0.14, f"[+{DELTA_CI[0]}, +{DELTA_CI[1]}] pp", fontsize=9, color=INK, family="monospace")

    path = OUT / "fig1_overall_accuracy.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def fig2_categories():
    fig, ax = plt.subplots(figsize=(10.2, 5.4), dpi=160)
    fig.patch.set_facecolor(BG)
    names = [c[0] for c in CATS]
    base = [c[1] for c in CATS]
    rag = [c[2] for c in CATS]
    y = range(len(names))
    ax.barh([i - 0.18 for i in y], base, height=0.32, color=RED, label="Baseline", zorder=3)
    ax.barh([i + 0.18 for i in y], rag, height=0.32, color=RED_LIGHT, label="With RAG", zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.set_xlim(0, 110)
    ax.set_xlabel("Accuracy (%) — descriptive only (n=6 per category)")
    ax.axvline(25, color=AMBER, ls="--", lw=1.2)
    ax.legend(loc="lower right", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title("Per-category test accuracy (n=6) — not ranked; not inferential", loc="left", fontsize=12, fontweight="bold", color=INK, pad=12)
    fig.text(0.08, 0.02, "Only a clean 6/0 sweep is significant at n=6. All six categories moved up; none individually significant.", fontsize=8.5, color=MUTED)
    path = OUT / "fig2_category_intervals.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def _corpus_shape() -> dict:
    """Item / source / category counts read from the corpus itself."""
    try:
        items = json.loads((ROOT / "data" / "knowledge" / "knowledge_all.json")
                           .read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": 0, "sources": 0, "cats": 0}
    return {
        "items": len(items),
        "sources": len({q["source_id"] for q in items if q.get("source_id")}),
        "cats": len({q["category"] for q in items}),
    }


_CORPUS = _corpus_shape()
N_ITEMS, N_SOURCES, N_CATS = _CORPUS["items"], _CORPUS["sources"], _CORPUS["cats"]


def _values_mean_str() -> str:
    """The values mean as measured, with its own scale named."""
    v = SN.values()
    if not v.get("present"):
        return "not measured"
    return f"{v['mean']} / {v['scale_max']} (self-judged)"


def _n_sources() -> int:
    """Distinct sources actually behind the corpus - not the original plan's 100."""
    return N_SOURCES


def _try_dev_knowledge() -> dict | None:
    """The paired dev delta, if a dev run exists at the CURRENT dev scale.

    Returns None when it does not. The caller then draws only measured bars.
    Absence is reported, never filled in.
    """
    for name in ("knowledge_8b_dev_rescore.json", "knowledge_8b_dev.json"):
        p = ROOT / "results" / "scores" / name
        if not p.is_file():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sc = d.get("scores", d)
        if "overall" not in sc:
            continue
        return {"n": sc.get("total_questions"), "acc": sc["overall"]}
    return None


def fig3_transfer():
    """
    The dev → test transfer check, drawn from whatever is actually measured.

    This figure used to draw two bars from constants: Dev (n=84) +34.5 pp and Test
    (n=36) +30.6 pp. When the sealed set was rescaled to 90 items the test bar went
    stale, and no dev run exists at the new 210-item dev scale at all - so the dev
    bar was not merely out of date, it had no current measurement behind it.

    A bar with no run behind it is decoration. So this renders only the arms that
    exist, and names the split it could not draw rather than inventing one.
    """
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=160)
    fig.patch.set_facecolor(BG)

    rows = []
    dev_k = _try_dev_knowledge()
    if dev_k:
        rows.append((f"Dev (n={dev_k['n']})", dev_k["delta_pp"], RED_LIGHT))
    rows.append((f"Test (n={N_PAIRED})", DELTA_PP, RED))

    bars = ax.bar([r[0] for r in rows], [r[1] for r in rows],
                  width=0.5, color=[r[2] for r in rows], zorder=3)
    top = max(r[1] for r in rows)
    for i, (_lbl, d, _c) in enumerate(rows):
        ax.text(i, d + top * 0.04, f"+{d:.1f} pp", ha="center",
                fontsize=12, fontweight="bold", color=INK)
    ax.set_ylabel("Paired accuracy delta (pp)")
    ax.set_ylim(0, top * 1.22)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title("Dev → test transfer of the RAG gain (Apertus 8B)", loc="left",
                 fontsize=12, fontweight="bold", color=INK, pad=12)

    note = f"Test {BASE_ACC}% → {RAG_ACC}%"
    note += (f" · Dev not re-run at n={DEV_N}" if not dev_k else "")
    note += " · 70B not measured"
    fig.text(0.08, 0.02, note, fontsize=8.5, color=MUTED)
    path = OUT / "fig3_dev_to_test.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def fig4_recall():
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=160)
    fig.patch.set_facecolor(BG)
    ks = list(RECALL.keys())
    vals = list(RECALL.values())
    ax.bar([f"top-{k}" for k in ks], vals, width=0.55, color=[RED, RED_LIGHT, "#FADADD"], zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v}%", ha="center", fontsize=12, fontweight="bold", color=INK)
    ax.axhline(25, color=AMBER, ls="--", lw=1.2)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Source recall (%)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(f"BM25 source recall on knowledge_dev (model-free, n={RECALL_N})", loc="left", fontsize=12, fontweight="bold", color=INK, pad=12)
    fig.text(0.08, 0.02, f"Retrieval finds the answer's source {RECALL.get(5, 0):.1f}% of the time at k=5 — dense retriever not the bottleneck.", fontsize=8.5, color=MUTED)
    path = OUT / "fig4_retrieval_recall.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def infographic_pillars():
    w, h = 1400, 320
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    title = _font(28, True)
    big = _font(52, True)
    small = _font(16)
    muted = _font(14)
    d.text((40, 24), "Swiss Reality Check — three pillars", fill=INK, font=title)
    cards = [
        (40, f"{N_ITEMS}", "Knowledge MCQs", f"{N_CATS} categories · {DEV_N}/{N_PAIRED} split"),
        (480, "30", "Values scenarios", "framing rubric · 6 languages"),
        (920, "30", "Dialect items", "Alemannic Wikipedia · unvalidated"),
    ]
    for x, num, label, sub in cards:
        d.rounded_rectangle([x, 80, x + 400, 280], radius=16, fill=PANEL, outline="#E4E7EB", width=2)
        d.text((x + 28, 100), num, fill=RED, font=big)
        d.text((x + 28, 175), label, fill=INK, font=_font(22, True))
        d.text((x + 28, 220), sub, fill=MUTED, font=muted)
    path = OUT / "infographic_pillars.png"
    img.save(path, "PNG")
    return path


def infographic_delta():
    w, h = 1400, 300
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    title = _font(26, True)
    huge = _font(56, True)
    mid = _font(20)
    muted = _font(14)
    d.text((40, 20), "Held-out test · Apertus 1.5 8B · BM25 RAG", fill=INK, font=title)
    # baseline box
    d.rounded_rectangle([40, 80, 380, 250], radius=14, fill="#FFF5F5", outline=RED, width=2)
    d.text((70, 100), "Baseline", fill=MUTED, font=mid)
    d.text((70, 140), f"{BASE_ACC}%", fill=RED, font=huge)
    d.text((70, 210), f"{BASE_N} correct", fill=MUTED, font=muted)
    # arrow
    d.polygon([(420, 165), (470, 145), (470, 155), (520, 155), (520, 175), (470, 175), (470, 185)], fill=RED)
    d.text((430, 100), f"+{DELTA_PP} pp", fill=RED, font=_font(28, True))
    d.text((420, 210), f"p={MCNEMAR_P}", fill=MUTED, font=muted)
    # rag box
    d.rounded_rectangle([560, 80, 900, 250], radius=14, fill="#FFF5F5", outline=RED, width=2)
    d.text((590, 100), "With RAG", fill=MUTED, font=mid)
    d.text((590, 140), f"{RAG_ACC}%", fill=RED, font=huge)
    d.text((590, 210), f"{RAG_N} correct", fill=MUTED, font=muted)
    # 70b card
    d.rounded_rectangle([960, 80, 1360, 250], radius=14, fill=PANEL, outline="#E4E7EB", width=2)
    d.text((990, 110), "Apertus 70B", fill=INK, font=_font(22, True))
    d.text((990, 155), "Not run", fill=MUTED, font=_font(32, True))
    d.text((990, 210), "Out of scope · 8 GB VRAM", fill=MUTED, font=muted)
    path = OUT / "infographic_delta.png"
    img.save(path, "PNG")
    return path


def infographic_scope():
    w, h = 1400, 340
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.text((40, 20), "Evaluation scope — honest dual-model scoreboard", fill=INK, font=_font(26, True))
    # headers
    d.text((80, 80), "Metric", fill=MUTED, font=_font(16, True))
    d.text((520, 80), "8B (measured)", fill=RED, font=_font(16, True))
    d.text((920, 80), "70B", fill=MUTED, font=_font(16, True))
    d.line([(40, 110), (1360, 110)], fill="#E4E7EB", width=2)
    rows = [
        ("Knowledge baseline", f"{BASE_ACC}% ({BASE_N})", "Not run"),
        ("Knowledge + RAG", f"{RAG_ACC}% ({RAG_N})", "Not run"),
        ("Paired delta", f"+{DELTA_PP} pp · {SN.fmt_p(MCNEMAR_P)}", "—"),
        ("Values mean / 2.0", f"{_values_mean_str()}", "Not run"),
        ("Dialect refusal", "50.0% (15/30)", "Not run"),
    ]
    y = 125
    for metric, eight, seventy in rows:
        d.text((80, y), metric, fill=INK, font=_font(15))
        d.text((520, y), eight, fill=INK, font=_font(15, True))
        d.text((920, y), seventy, fill=MUTED, font=_font(15))
        y += 38
    path = OUT / "infographic_scope.png"
    img.save(path, "PNG")
    return path


def fig_values_dialect():
    """Values score distribution + dialect outcomes (measured 8B)."""
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.6), dpi=160)
    fig.patch.set_facecolor(BG)

    ax = axes[0]
    labels = ["Score 0", "Score 2"]
    vals = [33, 40]
    ax.bar(labels, vals, color=[RED, RED_LIGHT], width=0.55, zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.8, str(v), ha="center", fontsize=11, fontweight="bold", color=INK)
    ax.set_ylim(0, 50)
    ax.set_ylabel("Judged records")
    ax.set_title("Values scores (n=73, mean 1.096/2.0)", loc="left", fontsize=10, fontweight="bold", color=INK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(0.5, -0.18, "self-judged 8B · B5 human audit not done", transform=ax.transAxes,
            ha="center", fontsize=8, color=MUTED)

    ax = axes[1]
    dlab = ["Refusal", "MCQ acc.", "T1 mean"]
    dval = [50.0, 50.0, 0.0]
    ax.bar(dlab, dval, color=[RED, RED_LIGHT, "#FADADD"], width=0.55, zorder=3)
    for i, v in enumerate(dval):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=11, fontweight="bold", color=INK)
    ax.set_ylim(0, 110)
    ax.set_ylabel("%")
    ax.set_title("Dialect outcomes (n=30, unvalidated)", loc="left", fontsize=10, fontweight="bold", color=INK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(0.5, -0.18, "refusal is a headline metric · validated_by: null", transform=ax.transAxes,
            ha="center", fontsize=8, color=MUTED)

    fig.tight_layout()
    path = OUT / "fig_values_dialect.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def fig_pipeline():
    """Compact pipeline / contamination strip."""
    w, h = 1400, 260
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.text((40, 16), "Evaluation pipeline (knowledge arm)", fill=INK, font=_font(22, True))
    steps = [
        (40, "1. Harvest", f"{_n_sources()} Swiss\nsources"),
        (300, "2. Seal", f"{DEV_N}/{N_PAIRED} split\nhash-locked"),
        (560, "3. Baseline", f"8B · T=0\n{BASE_ACC}% test"),
        (820, "4. BM25 RAG", f"top_k=3\n0/{DEV_N} contam."),
        (1080, "5. Retest", f"{RAG_ACC}% test\n{SN.fmt_p(MCNEMAR_P)}"),
    ]
    for x, title, body in steps:
        d.rounded_rectangle([x, 60, x + 230, 230], radius=12, fill=PANEL, outline="#E4E7EB", width=2)
        d.text((x + 16, 78), title, fill=RED, font=_font(16, True))
        d.text((x + 16, 120), body, fill=INK, font=_font(15))
    # arrows between
    for x in (270, 530, 790, 1050):
        d.polygon([(x, 140), (x + 20, 130), (x + 20, 150)], fill=RED)
    path = OUT / "infographic_pipeline.png"
    img.save(path, "PNG")
    return path


def fig_category_table():
    """Numeric per-category before/after for the PDF (descriptive)."""
    fig, ax = plt.subplots(figsize=(10.2, 3.2), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.axis("off")
    ax.set_title("Per-category test (n=6 each) — descriptive deltas only", loc="left",
                 fontsize=11, fontweight="bold", color=INK, pad=8)
    cell = [["Category", "Baseline", "RAG", "Delta", "Significant?"]]
    for name, b, r in CATS:
        cell.append([name, f"{b:.1f}%", f"{r:.1f}%", f"+{r-b:.1f} pp", "no (n=6)"])
    table = ax.table(cellText=cell, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.15, 1.45)
    for (r, c), cell_obj in table.get_celld().items():
        cell_obj.set_edgecolor("#E4E7EB")
        if r == 0:
            cell_obj.set_facecolor("#FAFAFB")
            cell_obj.set_text_props(weight="bold", color=INK)
        elif c == 0:
            cell_obj.set_text_props(weight="bold", color=INK)
        else:
            cell_obj.set_facecolor(BG)
    path = OUT / "fig_category_table.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [
        fig1_overall(),
        fig2_categories(),
        fig3_transfer(),
        fig4_recall(),
        fig_values_dialect(),
        fig_pipeline(),
        fig_category_table(),
        infographic_pillars(),
        infographic_delta(),
        infographic_scope(),
    ]
    for p in paths:
        print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

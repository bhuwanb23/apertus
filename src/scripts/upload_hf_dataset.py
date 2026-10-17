#!/usr/bin/env python3
"""Stage and upload the Swiss Reality Check dataset to Hugging Face.

Usage:
  python src/scripts/upload_hf_dataset.py --repo bhuwanb23/apertus
  python src/scripts/upload_hf_dataset.py --repo bhuwanb23/apertus --stage-only
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Headline numbers are loaded, never typed — a stale HF card is the most
# durable way to ship a wrong number.
import submission_numbers as SN  # noqa: E402

_H = SN.headline()
_R = SN.recall()
_V = SN.values()
BASE_ACC, BASE_N = _H["base_acc"], _H["base_n"]
BASE_CI = _H["base_ci"]
RAG_ACC, RAG_N = _H["rag_acc"], _H["rag_n"]
RAG_CI = _H["rag_ci"]
DELTA_PP = _H["delta_pp"]
DELTA_CI = _H["delta_ci"]
PSTR = SN.fmt_p(_H["mcnemar_p"])
IMPR, REGR = _H["improved"], _H["regressed"]
N_PAIRED = _H["n_paired"]
DEV_N = SN.dev()["n"]
RECALL_1, RECALL_3, RECALL_5 = _R[1], _R[3], _R[5]
VAL_N, VAL_MEAN = _V["n"], _V["mean"]

STAGE = ROOT / "docs" / "submission" / "hf_dataset"

COPY_FILES = [
    ("data/knowledge/knowledge_all.json", "knowledge/knowledge_all.json"),
    ("data/knowledge/knowledge_dev.json", "knowledge/knowledge_dev.json"),
    ("data/knowledge/knowledge_test.json", "knowledge/knowledge_test.json"),
    ("data/knowledge/knowledge_stats.md", "knowledge/knowledge_stats.md"),
    ("data/knowledge/MCQ_AUTHORING_SPEC.md", "knowledge/MCQ_AUTHORING_SPEC.md"),
    ("data/values/values_scenarios.json", "values/values_scenarios.json"),
    ("data/values/values_multilingual_pairs.json", "values/values_multilingual_pairs.json"),
    ("data/values/values_rubric.md", "values/values_rubric.md"),
    ("data/values/values_stats.md", "values/values_stats.md"),
    ("data/values/multilingual_scoring_protocol.md", "values/multilingual_scoring_protocol.md"),
    ("data/dialect/dialect_items.json", "dialect/dialect_items.json"),
    ("data/dialect/dialect_scoring_protocol.md", "dialect/dialect_scoring_protocol.md"),
    ("data/dialect/dialect_stats.md", "dialect/dialect_stats.md"),
    ("data/dialect/dialect_pilot_note.md", "dialect/dialect_pilot_note.md"),
    ("data/dialect/VALIDATION_PACKET_FILLED.md", "dialect/VALIDATION_PACKET_FILLED.md"),
    ("data/sources/source_registry.csv", "sources/source_registry.csv"),
    ("data/sources/README.md", "sources/README.md"),
    ("DATASHEET.md", "DATASHEET.md"),
    ("LICENSE", "LICENSE"),
    ("technical_report.md", "technical_report.md"),
    ("results/final_scores/statistical_report.md", "results/statistical_report.md"),
    ("results/final_scores/test_scores.json", "results/test_scores.json"),
]

# Hack Apertus Track 1B schema mirrors
EVAL_MIRROR = [
    ("data/knowledge/knowledge_all.json", "evaluation/knowledge/knowledge_all.json"),
    ("data/knowledge/knowledge_dev.json", "evaluation/knowledge/knowledge_dev.json"),
    ("data/knowledge/knowledge_test.json", "evaluation/knowledge/knowledge_test.json"),
    ("data/values/values_scenarios.json", "evaluation/values/values_scenarios.json"),
    ("data/values/values_multilingual_pairs.json", "evaluation/values/values_multilingual_pairs.json"),
    ("data/values/values_rubric.md", "evaluation/values/values_rubric.md"),
    ("data/dialect/dialect_items.json", "evaluation/dialect/dialect_items.json"),
    ("data/dialect/dialect_scoring_protocol.md", "evaluation/dialect/dialect_scoring_protocol.md"),
]

RESPONSE_COPY = [
    ("results/test_run/knowledge_8b_baseline.json", "model_responses/knowledge_8b_baseline.json"),
    ("results/test_run/knowledge_8b_improved.json", "model_responses/knowledge_8b_improved.json"),
    ("results/test_run/values_8b_baseline.json", "model_responses/values_8b_baseline.json"),
    ("results/test_run/dialect_8b_baseline.json", "model_responses/dialect_8b_baseline.json"),
]

COPY_TREE = [
    ("data/sources/raw_pages", "sources/raw_pages"),
]


def _dataset_card() -> str:
    return f"""---
license: cdla-permissive-2.0
task_categories:
  - multiple-choice
  - question-answering
  - text-generation
language:
  - en
  - de
  - gsw
  - fr
  - it
  - rm
tags:
  - switzerland
  - swiss
  - apertus
  - benchmark
  - rag
  - dialect
  - cultural-values
  - hackapertus
  - track-1b
  - swiss-voices
  - alemannic
pretty_name: Swiss Reality Check
size_categories:
  - n<1K
---

# Swiss Reality Check

### Hack Apertus · Track 1B — Swiss Voices

<p align="center">
  <strong>Does an open model know Switzerland?</strong><br/>
  Knowledge · Values · Alemannic dialect — every answer traced to an official Swiss source.
</p>

| | |
|---|---|
| **Team** | Swiss Reality Check · Bhuwan B · Padmanaban G · Avinash A |
| **Event** | Hack Apertus Online Phase (1–16 Oct 2026) |
| **Models** | [`swiss-ai/Apertus-v1.5-8B`](https://huggingface.co/swiss-ai/Apertus-v1.5-8B) measured · [`swiss-ai/Apertus-v1.5-70B`](https://huggingface.co/swiss-ai/Apertus-v1.5-70B) **not run** |
| **Code** | https://github.com/bhuwanb23/apertus |
| **Jury PDF** | `swiss_reality_check_report.pdf` / `SwissRealityCheck_Report.pdf` |

---

## Headline result (sealed knowledge, n={N_PAIRED}, 8B)

<p align="center">
  <img src="charts/infographic_delta.png" alt="Baseline to RAG delta" width="900"/>
</p>

| Arm | Accuracy | 95% Wilson CI |
|---|---|---|
| Baseline | **{BASE_ACC}%** ({BASE_N}) | [{BASE_CI[0]}, {BASE_CI[1]}] |
| BM25 RAG (`top_k=3`) | **{RAG_ACC}%** ({RAG_N}) | [{RAG_CI[0]}, {RAG_CI[1]}] |
| **Paired Δ** | **+{DELTA_PP} pp** | exact 95% CI [+{DELTA_CI[0]}, +{DELTA_CI[1]}] |

McNemar: **{IMPR} improved · {REGR} regressed · {PSTR}**.  
Dev split n={DEV_N} (design only — not re-scored at this scale).

**Apertus 70B was not evaluated** (8 GB VRAM). Missing bars are not implied scores.

<p align="center">
  <img src="charts/fig1_overall_accuracy.png" alt="Overall accuracy with Wilson intervals" width="900"/>
</p>

---

## Retrieval (model-free)

| Recall@k | Source containing the answer |
|---|---|
| top-1 | **{RECALL_1}%** |
| top-3 | **{RECALL_3}%** |
| top-5 | **{RECALL_5}%** |

<p align="center">
  <img src="charts/fig4_retrieval_recall.png" alt="Retrieval source recall" width="900"/>
</p>

---

## Benchmark scope

<p align="center">
  <img src="charts/infographic_pillars.png" alt="Three pillars" width="900"/>
</p>

| Pillar | Contents |
|---|---|
| **Knowledge** | 300 MCQs (210 development / 90 sealed test), 6 categories |
| **Values** | 30 scenarios + multilingual pairs · scored mean {VAL_MEAN:.3f}/2.0 (n={VAL_N}, self-judged) |
| **Dialect** | 30 Alemannic items (`validated_by: null` pending native speaker) |
| **Sources** | Registry + raw excerpts for RAG provenance |

<p align="center">
  <img src="charts/infographic_scope.png" alt="Scope infographic" width="900"/>
  <img src="charts/infographic_pipeline.png" alt="Pipeline" width="900"/>
</p>

<p align="center">
  <img src="charts/fig2_category_intervals.png" alt="Per-category intervals" width="900"/>
  <img src="charts/fig3_dev_to_test.png" alt="Dev to test transfer" width="900"/>
  <img src="charts/fig_values_dialect.png" alt="Values and dialect" width="900"/>
</p>

---

## Repository layout (Hack Apertus schema)

```
evaluation/          knowledge · values · dialect test cases
model_responses/     Apertus 1.5 8B sealed-test responses
metadata/            datasheet, claims, run metadata, source registry
knowledge/ values/ dialect/   human-readable mirrors + specs
sources/             registry.csv + raw_pages/
charts/              PNG figures & infographics
results/             statistical_report.md · test_scores.json
swiss_reality_check_report.pdf
SwissRealityCheck_Report.pdf
DATASHEET.md · LICENSE · technical_report.md
```

> The Dataset Viewer may look empty — this is a **file-bundle** dataset (JSON +
> text + charts), not a Parquet table. Browse the folders above.

---

## Reproduce

```bash
git clone https://github.com/bhuwanb23/apertus
cd apertus && make run
```

Offline by default: integrity, recall, scoring, statistics and charts without an LLM.

---

## Licensing

- **Dataset** (compilation, metadata, annotations): **CDLA-Permissive-2.0**
- **Evaluation code**: **Apache-2.0** (see `LICENSE`)
- Alemannic Wikipedia excerpts from als.wikipedia.org remain **CC BY-SA 4.0**
- Official Swiss government source text is public information
- Apertus model weights remain under their Apache-2.0 model licenses
"""


def _write_metadata(stage: Path) -> None:
    meta = stage / "metadata"
    meta.mkdir(parents=True, exist_ok=True)

    shutil.copy2(ROOT / "DATASHEET.md", meta / "DATASHEET.md")
    shutil.copy2(ROOT / "data" / "sources" / "source_registry.csv", meta / "source_registry.csv")
    shutil.copy2(ROOT / "results" / "final_scores" / "test_scores.json", meta / "test_scores.json")

    claims = {
        "benchmark": "Swiss Reality Check",
        "track": "1B Swiss Voices",
        "model_measured": "Apertus 1.5 8B (Q4_K_M text extract)",
        "model_not_run": "Apertus 1.5 70B",
        "knowledge": {
            "n_total": 300,
            "n_dev": DEV_N,
            "n_test": N_PAIRED,
            "baseline_accuracy": BASE_ACC,
            "baseline_n": BASE_N,
            "rag_accuracy": RAG_ACC,
            "rag_n": RAG_N,
            "delta_pp": DELTA_PP,
            "delta_ci": list(DELTA_CI),
            "mcnemar_improved": IMPR,
            "mcnemar_regressed": REGR,
            "mcnemar_p": _H["mcnemar_p"],
        },
        "retrieval_source_recall": {
            "k1": RECALL_1,
            "k3": RECALL_3,
            "k5": RECALL_5,
        },
        "values": {
            "n": VAL_N,
            "mean": VAL_MEAN,
            "self_judged": True,
        },
        "code": "https://github.com/bhuwanb23/apertus",
        "dataset": "https://huggingface.co/datasets/bhuwanb23/apertus",
    }
    (meta / "published_claims.json").write_text(
        json.dumps(claims, indent=2) + "\n", encoding="utf-8")

    licensing = (
        "# Licensing\n\n"
        "- Dataset compilation / annotations: CDLA-Permissive-2.0\n"
        "- Code: Apache-2.0\n"
        "- Alemannic Wikipedia excerpts: CC BY-SA 4.0\n"
        "- Swiss government source text: public information\n"
    )
    (meta / "LICENSING.md").write_text(licensing, encoding="utf-8")

    run_meta = {
        "temperature": 0.0,
        "seed": 42,
        "backend": "llama.cpp HTTP",
        "quantization": "Q4_K_M",
        "n_knowledge_test": N_PAIRED,
        "disclosure": "70B not evaluated; values self-judged; sealed set opened more than once",
    }
    (meta / "run_metadata.json").write_text(
        json.dumps(run_meta, indent=2) + "\n", encoding="utf-8")


def stage() -> Path:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    missing: list[str] = []

    def _copy(src_rel: str, dst_rel: str) -> None:
        src = ROOT / src_rel
        if not src.exists():
            missing.append(src_rel)
            return
        dst = STAGE / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    for src_rel, dst_rel in COPY_FILES + EVAL_MIRROR + RESPONSE_COPY:
        _copy(src_rel, dst_rel)

    for src_rel, dst_rel in COPY_TREE:
        src = ROOT / src_rel
        if not src.exists():
            missing.append(src_rel)
            continue
        shutil.copytree(src, STAGE / dst_rel)

    charts_dst = STAGE / "charts"
    charts_dst.mkdir(parents=True, exist_ok=True)
    assets = ROOT / "docs" / "submission" / "assets"
    if assets.exists():
        for png in assets.glob("*.png"):
            shutil.copy2(png, charts_dst / png.name)

    for pdf_name in (
        "swiss_reality_check_report.pdf",
        "SwissRealityCheck_Report.pdf",
    ):
        for cand in (
            ROOT / pdf_name,
            ROOT / "docs" / "submission" / pdf_name,
        ):
            if cand.exists():
                shutil.copy2(cand, STAGE / pdf_name)
                break

    # Prefer root PDF under both names if only one exists
    root_pdf = ROOT / "swiss_reality_check_report.pdf"
    if root_pdf.exists():
        shutil.copy2(root_pdf, STAGE / "swiss_reality_check_report.pdf")
        shutil.copy2(root_pdf, STAGE / "SwissRealityCheck_Report.pdf")

    _write_metadata(STAGE)
    (STAGE / "README.md").write_text(_dataset_card(), encoding="utf-8")

    if missing:
        print("WARNING: missing files (skipped):", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    n_files = sum(1 for _ in STAGE.rglob("*") if _.is_file())
    print(f"staged {n_files} files -> {STAGE}")
    print(f"headline: {BASE_ACC}% -> {RAG_ACC}% (+{DELTA_PP} pp, n={N_PAIRED})")
    return STAGE


def upload(repo_id: str, private: bool = False) -> str:
    from huggingface_hub import HfApi, create_repo

    api = HfApi()
    who = api.whoami()
    print(f"authenticated as {who.get('name')}")

    create_repo(repo_id, repo_type="dataset", exist_ok=True, private=private)
    api.upload_folder(
        folder_path=str(STAGE),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=(
            f"Polish dataset card + charts "
            f"({BASE_ACC}% -> {RAG_ACC}%, +{DELTA_PP} pp, n={N_PAIRED})"
        ),
    )
    url = f"https://huggingface.co/datasets/{repo_id}"
    print(f"uploaded -> {url}")
    return url


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default="bhuwanb23/apertus")
    p.add_argument("--stage-only", action="store_true")
    p.add_argument("--private", action="store_true")
    args = p.parse_args()

    stage()
    if args.stage_only:
        return
    upload(args.repo, private=args.private)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stage and upload the Swiss Reality Check dataset to Hugging Face.

Usage:
  python scripts/upload_hf_dataset.py --repo bhuwanb23/apertus
  python scripts/upload_hf_dataset.py --repo bhuwanb23/apertus --stage-only
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "docs" / "submission" / "hf_dataset"

COPY_FILES = [
    # knowledge
    ("data/knowledge/knowledge_all.json", "knowledge/knowledge_all.json"),
    ("data/knowledge/knowledge_dev.json", "knowledge/knowledge_dev.json"),
    ("data/knowledge/knowledge_test.json", "knowledge/knowledge_test.json"),
    ("data/knowledge/knowledge_stats.md", "knowledge/knowledge_stats.md"),
    ("data/knowledge/MCQ_AUTHORING_SPEC.md", "knowledge/MCQ_AUTHORING_SPEC.md"),
    # values
    ("data/values/values_scenarios.json", "values/values_scenarios.json"),
    ("data/values/values_multilingual_pairs.json", "values/values_multilingual_pairs.json"),
    ("data/values/values_rubric.md", "values/values_rubric.md"),
    ("data/values/values_stats.md", "values/values_stats.md"),
    ("data/values/multilingual_scoring_protocol.md", "values/multilingual_scoring_protocol.md"),
    # dialect
    ("data/dialect/dialect_items.json", "dialect/dialect_items.json"),
    ("data/dialect/dialect_scoring_protocol.md", "dialect/dialect_scoring_protocol.md"),
    ("data/dialect/dialect_stats.md", "dialect/dialect_stats.md"),
    ("data/dialect/dialect_pilot_note.md", "dialect/dialect_pilot_note.md"),
    ("data/dialect/VALIDATION_PACKET_FILLED.md", "dialect/VALIDATION_PACKET_FILLED.md"),
    # sources
    ("data/sources/source_registry.csv", "sources/source_registry.csv"),
    ("data/sources/README.md", "sources/README.md"),
    # docs / license / results summary
    ("DATASHEET.md", "DATASHEET.md"),
    ("LICENSE", "LICENSE"),
    ("eval/results/final_scores/statistical_report.md", "results/statistical_report.md"),
    ("eval/results/final_scores/test_scores.json", "results/test_scores.json"),
]

COPY_TREE = [
    ("data/sources/raw_pages", "sources/raw_pages"),
]

ASSET_GLOBS = [
    ("docs/submission/assets/*.png", "charts"),
]


DATASET_CARD = """---
license: mit
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
pretty_name: Swiss Reality Check
size_categories:
  - n<1K
---

# Swiss Reality Check

**Hack Apertus · Online Phase (1–16 Oct 2026)**  
**Track 1 — Apertus Readiness · Challenge 1B: Swiss Voices**  
*Localising Apertus to Swiss Languages, Knowledge and Values*

| | |
|---|---|
| **Team** | Swiss Reality Check · solo · Bhuwan B (`bhuwanb23`) |
| **Problem statement** | Evaluate how well Apertus handles Swiss reality: transcribe local dialects, test domain-specific Swiss knowledge, and assess whether responses respect Swiss cultural norms and values. |
| **Models** | [`swiss-ai/Apertus-v1.5-8B`](https://huggingface.co/swiss-ai/Apertus-v1.5-8B) (measured) · [`swiss-ai/Apertus-v1.5-70B`](https://huggingface.co/swiss-ai/Apertus-v1.5-70B) (designed for; **not run**) |
| **Code** | https://github.com/bhuwanb23/apertus |
| **Jury PDF** | `swiss_reality_check_report.pdf` (≤6 pages) |

Open benchmark for **Swiss knowledge**, **cultural values / framing**, and
**Alemannic (Swiss German) dialect**.

- **120** knowledge MCQs (84 development / 36 sealed test)
- **30** values scenarios + multilingual renderings
- **30** dialect items (unvalidated — `validated_by: null`)
- **100** source pages (registry + raw excerpts) for RAG

## Measured result (not training labels)

Sealed knowledge test, **Apertus 1.5 8B** (Q4_K_M, llama.cpp, T=0):

| Arm | Accuracy |
|---|---|
| Baseline | 55.6% (20/36) |
| BM25 RAG (`top_k=3`) | 86.1% (31/36) |

Paired Δ **+30.6 pp**, McNemar p=0.001. Dev transfer: 48.8% → 83.3%.

**Apertus 70B was not evaluated** (8 GB VRAM). Do not treat missing 70B
numbers as implied scores.

## Files

```
knowledge/   JSON MCQs + stats
values/      scenarios, rubric, multilingual pairs
dialect/     items + scoring protocol
sources/     registry.csv + raw_pages/
charts/      PNG figures for the jury report
results/     sealed-test statistical report
swiss_reality_check_report.pdf
DATASHEET.md · LICENSE
```

## License

MIT (see `LICENSE`). Alemannic Wikipedia excerpts in `sources/raw_pages/`
that originate from als.wikipedia.org remain under **CC BY-SA 4.0**.
Apertus model weights remain under their Apache-2.0 model licenses.
"""


def stage() -> Path:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    missing = []
    for src_rel, dst_rel in COPY_FILES:
        src = ROOT / src_rel
        if not src.exists():
            missing.append(src_rel)
            continue
        dst = STAGE / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    for src_rel, dst_rel in COPY_TREE:
        src = ROOT / src_rel
        if not src.exists():
            missing.append(src_rel)
            continue
        dst = STAGE / dst_rel
        shutil.copytree(src, dst)

    charts_dst = STAGE / "charts"
    charts_dst.mkdir(parents=True, exist_ok=True)
    assets = ROOT / "docs" / "submission" / "assets"
    if assets.exists():
        for png in assets.glob("*.png"):
            shutil.copy2(png, charts_dst / png.name)

    pdf = ROOT / "docs" / "submission" / "swiss_reality_check_report.pdf"
    if pdf.exists():
        shutil.copy2(pdf, STAGE / "swiss_reality_check_report.pdf")

    (STAGE / "README.md").write_text(DATASET_CARD, encoding="utf-8")

    if missing:
        print("WARNING: missing files (skipped):", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    n_files = sum(1 for _ in STAGE.rglob("*") if _.is_file())
    print(f"staged {n_files} files -> {STAGE}")
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
        commit_message="Upload Swiss Reality Check benchmark dataset",
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

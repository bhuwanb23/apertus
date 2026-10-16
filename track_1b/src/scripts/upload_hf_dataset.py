#!/usr/bin/env python3
"""Stage and upload Swiss Reality Check dataset in Hack Apertus 1B shape.

Required components:
  evaluation/       — test cases
  model_responses/  — model outputs per case
  metadata/         — provenance / licenses / splits

Usage:
  python src/scripts/upload_hf_dataset.py --repo bhuwanb23/apertus
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

TRACK = Path(__file__).resolve().parents[2]  # track_1b/
REPO = TRACK.parent
# Prefer repo-root data/ if still present; else fixtures evaluation copies
DATA = REPO / "data"
FIX = TRACK / "src" / "fixtures"
STAGE = TRACK / "docs" / "hf_dataset"

DATASET_CARD = """---
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
  - apertus
  - hackapertus
  - track-1b
  - swiss-voices
  - benchmark
  - rag
pretty_name: Swiss Reality Check
size_categories:
  - n<1K
---

# Swiss Reality Check (Hack Apertus Track 1B)

**Team:** Swiss Reality Check — Bhuwan B · Padmanaban G · Avinash A  
**Track:** 1B Swiss Voices — Core Task Intelligence (+ values / dialect)  
**Code:** https://github.com/bhuwanb23/apertus/tree/main/track_1b

## Components (Hack Apertus schema)

| Folder | Contents |
|---|---|
| `evaluation/` | Knowledge / values / dialect test cases |
| `model_responses/` | Apertus 1.5 8B sealed-test responses (baseline + RAG + values + dialect) |
| `metadata/` | Source registry, datasheet, published claims, run metadata |

## Headline result (sealed knowledge, n=36, 8B)

| Arm | Accuracy |
|---|---|
| Baseline | 55.6% (20/36) |
| BM25 RAG (`top_k=3`) | 86.1% (31/36) |

Paired Δ **+30.6 pp**, McNemar 11↑/0↓, p≈0.001.  
**Apertus 70B was not evaluated** (8 GB VRAM).

## Reproduce

```bash
cd track_1b && make run
```

## Licensing

- Dataset (compilation, metadata, annotations): CDLA-Permissive-2.0
- Evaluation code: Apache-2.0
- Official Swiss government source excerpts: public information
- Alemannic Wikipedia dialect source text: CC BY-SA 4.0 (disclosed in metadata;
  the CDLA-Permissive-2.0 grant above does not relicense it)
"""


def _copy(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"WARNING: missing {src}", file=sys.stderr)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def stage() -> Path:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    eval_dir = STAGE / "evaluation"
    resp_dir = STAGE / "model_responses"
    meta_dir = STAGE / "metadata"
    for d in (eval_dir, resp_dir, meta_dir):
        d.mkdir(parents=True)

    # --- evaluation ---
    knowledge_src = DATA / "knowledge" if (DATA / "knowledge").exists() else FIX / "evaluation"
    # fixtures may hold flat copies
    for name in ("knowledge_all.json", "knowledge_dev.json", "knowledge_test.json"):
        candidates = [
            DATA / "knowledge" / name,
            FIX / "evaluation" / name,
            FIX / name,
        ]
        for c in candidates:
            if c.exists():
                _copy(c, eval_dir / "knowledge" / name)
                break
    for name in ("values_scenarios.json", "values_multilingual_pairs.json", "values_rubric.md"):
        c = DATA / "values" / name
        if c.exists():
            _copy(c, eval_dir / "values" / name)
        elif (FIX / name).exists():
            _copy(FIX / name, eval_dir / "values" / name)
    for name in ("dialect_items.json", "dialect_scoring_protocol.md"):
        c = DATA / "dialect" / name
        if c.exists():
            _copy(c, eval_dir / "dialect" / name)
        elif (FIX / name).exists():
            _copy(FIX / name, eval_dir / "dialect" / name)

    # --- model responses ---
    for name in (
        "knowledge_8b_baseline.json",
        "knowledge_8b_improved.json",
        "values_8b_baseline.json",
        "dialect_8b_baseline.json",
    ):
        _copy(FIX / name, resp_dir / name)

    # --- metadata ---
    _copy(FIX / "published_claims.json", meta_dir / "published_claims.json")
    _copy(FIX / "test_scores.json", meta_dir / "test_scores.json")
    _copy(FIX / "run_metadata.json", meta_dir / "run_metadata.json")
    if (DATA / "sources" / "source_registry.csv").exists():
        _copy(DATA / "sources" / "source_registry.csv", meta_dir / "source_registry.csv")
    if (TRACK / "docs" / "DATASHEET.md").exists():
        _copy(TRACK / "docs" / "DATASHEET.md", meta_dir / "DATASHEET.md")
    elif (REPO / "DATASHEET.md").exists():
        _copy(REPO / "DATASHEET.md", meta_dir / "DATASHEET.md")
    if (TRACK / "SwissRealityCheck_Report.pdf").exists():
        _copy(TRACK / "SwissRealityCheck_Report.pdf", STAGE / "SwissRealityCheck_Report.pdf")
    if (TRACK / "technical_report.md").exists():
        _copy(TRACK / "technical_report.md", STAGE / "technical_report.md")
    charts = TRACK / "docs" / "charts"
    if charts.exists():
        _copy(charts, STAGE / "charts")

    # compact licenses note
    (meta_dir / "LICENSING.md").write_text(
        "# Licensing notes\n\n"
        "- Evaluation code in the GitHub repo: Apache-2.0\n"
        "- Official Swiss government pages: public information\n"
        "- Alemannic Wikipedia excerpts used for dialect items: CC BY-SA 4.0\n"
        "- No personal data; dialect items carry validated_by: null\n",
        encoding="utf-8",
    )

    (STAGE / "README.md").write_text(DATASET_CARD, encoding="utf-8")
    n = sum(1 for p in STAGE.rglob("*") if p.is_file())
    print(f"staged {n} files -> {STAGE}")
    return STAGE


def upload(repo_id: str) -> str:
    from huggingface_hub import HfApi, create_repo

    api = HfApi()
    print(f"authenticated as {api.whoami().get('name')}")
    create_repo(repo_id, repo_type="dataset", exist_ok=True)
    api.upload_folder(
        folder_path=str(STAGE),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="Track 1B schema: evaluation + model_responses + metadata",
    )
    url = f"https://huggingface.co/datasets/{repo_id}"
    print(f"uploaded -> {url}")
    return url


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default="bhuwanb23/apertus")
    p.add_argument("--stage-only", action="store_true")
    args = p.parse_args()
    stage()
    if not args.stage_only:
        upload(args.repo)


if __name__ == "__main__":
    main()

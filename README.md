# Swiss Reality Check

**Hack Apertus · Track 1B — Swiss Voices**

An open benchmark of Swiss institutional knowledge, cultural framing, and
Alemannic dialect — plus a contamination-safe BM25 RAG fix for **Apertus 1.5**.

| Resource | URL |
|---|---|
| GitHub | https://github.com/bhuwanb23/apertus |
| Hugging Face dataset | https://huggingface.co/datasets/bhuwanb23/apertus |
| Jury PDF (≤6 pages) | [`docs/submission/swiss_reality_check_report.pdf`](docs/submission/swiss_reality_check_report.pdf) |
| Datasheet | [`DATASHEET.md`](DATASHEET.md) |
| License | [MIT](LICENSE) |

---

## Headline result (held-out test, n=36)

**Apertus 1.5 8B** (Q4_K_M, llama.cpp, temperature 0):

| Arm | Accuracy | 95% Wilson CI |
|---|---|---|
| Baseline | **55.6%** (20/36) | [39.6, 70.5] |
| + BM25 RAG (`top_k=3`) | **86.1%** (31/36) | [71.3, 93.9] |

Paired delta **+30.6 pp** · exact 95% CI [+13.1, +30.6] · McNemar **11↑ / 0↓** · **p = 0.001**

Dev transfer (n=84): **48.8% → 83.3%** (+34.5 pp). Retrieval source recall (model-free): **83.3 / 90.5 / 94.0%** @ k=1/3/5.

**Apertus 70B was not evaluated** (8 GB VRAM scope drop). No 70B accuracies are claimed or imputed.

---

## What's in the box

- **120** knowledge MCQs (84/36 sealed split) · **30** values scenarios · **30** dialect items
- **100** harvested Swiss / Alemannic sources (`data/sources/`)
- Eval harness + seal + statistical report (`eval/`)
- RAG pipeline (`fix/rag/`) with a hard prompt-contamination gate

Read disclosures before quoting numbers: [`eval/README.md`](eval/README.md).

---

## Quick start

```bash
# Dataset integrity
python scripts/verify_all.py

# Rebuild submission charts + PDF
python scripts/prepare_submission_assets.py
python scripts/build_submission_pdf.py

# Upload / refresh the HF dataset (requires HF write token)
python scripts/upload_hf_dataset.py --repo bhuwanb23/apertus
```

Live model eval needs a running llama.cpp server and `eval/.env` (see `eval/.env.example`).

---

## Limitations (short)

- Test n=36 — per-category claims are descriptive only
- Values arm is **self-judged** (8B judges 8B); human audit not done
- Dialect items are **unvalidated** (`validated_by: null`)
- Sealed test opened more than once (disclosed; see `eval/README.md`)
- Single model scale — 70B out of scope on this hardware

---

## Citation

```
Swiss Reality Check (2026). Hack Apertus Track 1B.
https://github.com/bhuwanb23/apertus
https://huggingface.co/datasets/bhuwanb23/apertus
```

# Swiss Reality Check

**Hack Apertus · Online Phase (1–16 October 2026)**  
**Track 1 — Apertus Readiness · Challenge 1B: Swiss Voices**  
*Localising Apertus to Swiss Languages, Knowledge and Values*

| | |
|---|---|
| **Team** | Swiss Reality Check · solo · **Bhuwan B** (`bhuwanb23`) |
| **Problem statement** | Evaluate how well Apertus handles Swiss reality: transcribe local dialects, test domain-specific Swiss knowledge, and assess whether responses respect Swiss cultural norms and values. |
| **Models** | [`swiss-ai/Apertus-v1.5-8B`](https://huggingface.co/swiss-ai/Apertus-v1.5-8B) (measured) · [`swiss-ai/Apertus-v1.5-70B`](https://huggingface.co/swiss-ai/Apertus-v1.5-70B) (designed for; **not run** — 8 GB VRAM) |
| **Dataset** | https://huggingface.co/datasets/bhuwanb23/apertus |
| **Code** | https://github.com/bhuwanb23/apertus |
| **Jury PDF** | [`swiss_reality_check_report.pdf`](swiss_reality_check_report.pdf) (≤6 pages) |
| **Datasheet** | [`DATASHEET.md`](DATASHEET.md) · License [MIT](LICENSE) |
| **Deadline** | 16 Oct 2026, 12:00 CEST · partners CSCS & Phoeniqs · Grand Finals May 2027, St. Gallen |

---

## Headline result (held-out knowledge test, n=36)

**Apertus 1.5 8B** (text extract, Q4_K_M GGUF, llama.cpp, temperature 0, seed 42):

| Arm | Accuracy | 95% Wilson CI |
|---|---|---|
| Baseline | **55.6%** (20/36) | [39.6, 70.5] |
| + BM25 RAG (`top_k=3`) | **86.1%** (31/36) | [71.3, 93.9] |

Paired Δ **+30.6 pp** · exact 95% CI [+13.1, +30.6] · McNemar **11↑ / 0↓** · **p = 0.001**

Dev transfer (n=84): **48.8% → 83.3%**. Source recall (model-free): **83.3 / 90.5 / 94.0%** @ k=1/3/5.

**Apertus 70B was not evaluated.** No 70B accuracies are claimed or imputed.

---

## Track 1B → pillars

| Track 1B ask | Our pillar |
|---|---|
| Domain-specific Swiss knowledge | 120 source-verified MCQs (84/36 sealed) |
| Cultural norms & values | 30 scenarios + multilingual pairs (framing rubric) |
| Local dialects | 30 Alemannic items (unvalidated; refusal is a headline) |
| Improve the model (Readiness) | Contamination-safe BM25 RAG over Swiss sources |

---

## Quick start

```bash
python scripts/verify_all.py
python scripts/prepare_submission_assets.py
python scripts/build_submission_pdf.py
python scripts/upload_hf_dataset.py --repo bhuwanb23/apertus
```

Disclosures before quoting numbers: [`eval/README.md`](eval/README.md).

---

## About Hack Apertus

Opening online stage of «Hack Apertus» — evaluate, align, and build on Apertus,
Switzerland’s sovereign open LLM (EPFL, ETH Zurich, CSCS). Tracks: **1A** Red-Teaming,
**1B** Swiss Voices, **2A** Academia, **2B** Own Project. Strongest projects advance
to the Main Award final in St. Gallen (14 May 2027).

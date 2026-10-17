# Swiss Reality Check

### Hack Apertus · Track 1B — Swiss Voices

<p align="center">
  <strong>Does an open model know Switzerland?</strong><br/>
  <em>Knowledge · Values · Alemannic dialect — every answer traced to an official Swiss source.</em>
</p>

<p align="center">
  <a href="https://huggingface.co/datasets/bhuwanb23/apertus"><img src="https://img.shields.io/badge/🤗_Dataset-bhuwanb23%2Fapertus-FFD21E?style=for-the-badge" alt="Hugging Face"/></a>
  <a href="swiss_reality_check_report.pdf"><img src="https://img.shields.io/badge/Report-PDF_≤6p-E63946?style=for-the-badge" alt="PDF"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/Code-Apache--2.0-1F2933?style=for-the-badge" alt="License"/></a>
  <a href="DATASHEET.md"><img src="https://img.shields.io/badge/Data-CDLA--Permissive--2.0-457B9D?style=for-the-badge" alt="Data license"/></a>
</p>

<p align="center">
  <img src="docs/submission/assets/infographic_pillars.png" alt="Three pillars: knowledge, values, dialect" width="920"/>
</p>

**Team:** Swiss Reality Check — Bhuwan B · Padmanaban G · Avinash A  
**Event:** Hack Apertus Online Phase (1–16 Oct 2026)  
**Track:** [1B — Swiss Voices](https://github.com/HackApertus/project-template/tree/main/track_1b)

```bash
make run     # Docker · offline by default · clean checkout, zero config
```

---

## Headline result

Apertus 1.5 **8B** (Q4_K_M text extract) · held-out sealed test · **n = 90** · BM25 RAG against 55 official Swiss sources.

<p align="center">
  <img src="docs/submission/assets/infographic_delta.png" alt="51.1% to 86.7%, +35.6 pp" width="920"/>
</p>

| Arm | Accuracy | 95% Wilson CI |
|---|---|---|
| Baseline | 51.1% (46/90) | [41.0, 61.2] |
| With retrieval | **86.7%** (78/90) | [78.1, 92.2] |
| **Paired Δ** | **+35.6 pp** | exact 95% CI [+25.1, +39.5] |

McNemar: **34 improved · 2 regressed · p < 0.001**.  
**Apertus 70B was not evaluated** (8 GB VRAM) — missing bars are not implied scores.

<p align="center">
  <img src="docs/submission/assets/fig1_overall_accuracy.png" alt="Overall knowledge accuracy with Wilson intervals" width="920"/>
</p>

---

## Retrieval never was the bottleneck

Pure-Python BM25 · zero ML dependencies · decided before a single model call:

| Recall@k | Source containing the answer |
|---|---|
| top-1 | **82.4%** |
| top-3 | **91.4%** |
| top-5 | **92.9%** |

<p align="center">
  <img src="docs/submission/assets/fig4_retrieval_recall.png" alt="Retrieval source recall at k=1,3,5" width="920"/>
</p>

---

## What we built

<p align="center">
  <img src="docs/submission/assets/infographic_scope.png" alt="Benchmark scope: 300 MCQs, values, dialect" width="920"/>
</p>

| Pillar | Size | What it measures |
|---|---|---|
| **Knowledge** | 300 MCQs · 210 / 90 sealed | Swiss facts vs Germany / EU distractors |
| **Values** | 30 scenarios (+ multilingual) | Framing against Swiss cultural norms |
| **Dialect** | 30 Alemannic items | Translation / comprehension proxies |
| **Sources** | 101 harvested pages | Verbatim provenance for every answer |

<p align="center">
  <img src="docs/submission/assets/infographic_pipeline.png" alt="Contamination gate → seal → RAG → score" width="920"/>
</p>

### Two findings ahead of the accuracy number

1. **The obvious fix was contaminated.** A system prompt that asserts Swiss facts answers ~30% of the development set. The shipped prompt carries behavioural rules only (0/210) and a gate that *raises* keeps it there.
2. **Retrieval was never the bottleneck.** 92.9% recall@5 from stdlib BM25 ruled out a dense retriever before any model call — confirmed by the accuracy result afterwards.

---

## Per-category & transfer

Descriptive only at n=15 per category — not a ranking.

<p align="center">
  <img src="docs/submission/assets/fig2_category_intervals.png" alt="Per-category paired intervals" width="920"/>
</p>

<p align="center">
  <img src="docs/submission/assets/fig3_dev_to_test.png" alt="Dev to test transfer" width="920"/>
</p>

<p align="center">
  <img src="docs/submission/assets/fig_values_dialect.png" alt="Values and dialect arms" width="920"/>
</p>

---

## Deliverables

| | |
|---|---|
| Technical report | [`technical_report.md`](technical_report.md) |
| Jury PDF (≤6 pages) | [`swiss_reality_check_report.pdf`](swiss_reality_check_report.pdf) |
| Hugging Face dataset | [huggingface.co/datasets/bhuwanb23/apertus](https://huggingface.co/datasets/bhuwanb23/apertus) |
| Datasheet | [`DATASHEET.md`](DATASHEET.md) |
| Statistical report | [`results/final_scores/statistical_report.md`](results/final_scores/statistical_report.md) |
| Charts / infographics | [`docs/submission/assets/`](docs/submission/assets/) |
| Code | [`src/`](src/) — `eval/` · `fix/` · `scripts/` |

---

## Reproduce

Judges run from a clean checkout. Offline by default — integrity, recall, scoring, statistics, charts and narrative without an LLM.

```bash
make run          # Docker
make verify       # same checks, no Docker
make test         # automated suites
make help
```

### Live model (optional)

Reported numbers: local **llama.cpp** on RTX 5060.

```bash
export LLM_NAME=Apertus-v1.5-8B-Instruct-Q4_K_M
export LLM_BASE_URL=http://host.docker.internal:8080/v1
export LLM_API_KEY=EMPTY
make run
```

**Model substitution, disclosed.** Text-only **Q4_K_M** GGUF extract, not the gated Omni `swiss-ai/Apertus-v1.5-8B`. Every pillar is text; the substitution is recorded in every artefact. Details: [technical_report.md §6](technical_report.md#6-reproducibility).

---

## Layout

```
Makefile · Dockerfile · docker-compose.yml
technical_report.md · DATASHEET.md · LICENSE
swiss_reality_check_report.pdf

src/
  run.py              make run entrypoint
  eval/               clients, prompts, runners, scoring, judge
  fix/                taxonomy, contamination gate, RAG, stats, charts
  scripts/            dataset build + HF upload

data/                 knowledge · values · dialect · sources
docs/submission/      PDF assets, charts, HF staging
results/              sealed-run evidence behind every number
```

---

## Honesty before the headline

Read [technical_report.md §5](technical_report.md#5-limitations) in full. Short version:

- **No 70B results** — half the premise is unevidenced.
- **Sealed test opened more than once** — append-only log; greedy decode, nothing tuned between runs.
- **Values are self-judged** (same weights as the model under test).
- **Per-category n=15** supports no ranking.
- **Error taxonomy unresolved** — majority `UNCLASSIFIED`; no weakest-area claim.

`make run` prints these disclosures every time.

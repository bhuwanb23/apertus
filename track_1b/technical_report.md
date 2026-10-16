# Technical report — Swiss Reality Check

> We evaluate how well Apertus handles Swiss institutional knowledge, cultural framing, and Alemannic dialect, and show that a contamination-safe BM25 RAG stack lifts sealed-test knowledge accuracy from **55.6% to 86.1%** on Apertus 1.5 8B (+30.6 pp, McNemar p≈0.001). The 70B arm was designed for but not run (8 GB VRAM).

**Track:** Apertus Readiness — Track 1B Swiss Voices  
**Event:** Online (1–16 October 2026)  
**Team:** Swiss Reality Check — Bhuwan B, Padmanaban G, Avinash A  
**Demo / artefacts:** https://github.com/bhuwanb23/apertus · https://huggingface.co/datasets/bhuwanb23/apertus · `SwissRealityCheck_Report.pdf`

----

### Use of Apertus

- **Model:** `swiss-ai/Apertus-v1.5-8B` (measured, Q4_K_M text extract via llama.cpp). `swiss-ai/Apertus-v1.5-70B` designed for; **not evaluated** (hardware scope).
- **How it is used:** evaluation + retrieval-augmented inference (no fine-tuning).
- **Where it runs:** local GGUF weights on consumer 8 GB VRAM; judges reproduce scores offline with `make run` (Docker, no GPU required).

----

## Use Case Description

Open multilingual models often answer Swiss questions with fluent **German/EU** framing. Switzerland’s institutions (direct democracy, federalism, mandatory insurance, cantonal variation) and Alemannic dialects are small in global corpora but high-stakes for residents and public services. Swiss Reality Check is a **Core Task Intelligence** benchmark (factual Swiss knowledge) with secondary **Behavioural Alignment** (values framing) and **dialect** probes — mapped to Track 1B’s localisation dimensions. The use case matters because wrong but confident Swiss answers cause real administrative harm; measurable, source-verified eval is a precondition for trustworthy localisation.

## Dataset Summary

| Pillar | Items | Role |
|---|---|---|
| Knowledge MCQs | 120 (84/36 sealed) | Primary — Core Task Intelligence |
| Values scenarios | 30 (+ multilingual pairs) | Behavioural framing rubric (not political side) |
| Dialect items | 30 Alemannic | Text dialect / refusal; `validated_by: null` |

Knowledge: six categories × 20 (politics, law, health, geography, services, history). Every answer cites an official source quote; distractors are real neighbouring-country answers. Split seed 42, stratified by (category, difficulty). Values rubric scores institutional framing. Dialect sentences are verbatim from Alemannic Wikipedia (CC BY-SA 4.0).

## Data Collection Method

Knowledge items were drafted from official Swiss public information (ch.ch, admin.ch, SEM, FOPH, BFS, …), saved as `sources/raw_pages`, and verified with automated quote matching (`verify_knowledge.py`). Values scenarios were authored against a framing rubric with required/forbidden elements. Dialect items were copied character-for-character from als.wikipedia.org; Standard German references authored for scoring. No personal data; no human-subject collection beyond outstanding native-speaker validation for dialect.

## Dataset Details

- Provenance: source registry + per-item quotes; Gebru-style datasheet in `docs/DATASHEET.md`.
- Quality control: structural verifiers; contamination gate on improvement prompts (0/84 vs 30% for a fact-list prompt).
- Licensing: code Apache-2.0; government sources public information; Alemannic Wikipedia excerpts CC BY-SA 4.0 (disclosed).
- Limitations: dialect unvalidated; values self-judged on 8B; test n=36.

## Evaluation

### Method

Knowledge: exact letter scoring with paraphrase ladder. Values: LLM judge observes elements; rubric applied in code. Dialect: keyword-coverage translation + MCQ. Improvement: BM25 RAG (`top_k=3`) over harvested sources; behavioural system prompt only (no answer-key facts).

### Evaluation setup and inference parameters

- Backend: llama.cpp HTTP, temperature **0.0**, seed **42**, `is_mock: false`.
- Sealed test hash recorded; append-only access log (opened more than once — disclosed; greedy decode; reported arms 55.6% / 86.1%).
- Stats: Wilson CIs; exact paired McNemar on discordant pairs.

### Results (Apertus 1.5 8B, sealed knowledge n=36)

| Arm | Accuracy | Notes |
|---|---|---|
| Baseline | **55.6%** (20/36) | Wilson [39.6, 70.5] |
| BM25 RAG | **86.1%** (31/36) | Wilson [71.3, 93.9] |
| Paired Δ | **+30.6 pp** | 11↑ / 0↓, p≈0.001 |

Dev transfer (n=84): 48.8% → 83.3%. Source recall (model-free): 83.3 / 90.5 / 94.0% @ k=1/3/5. Values mean 1.096/2.0 (self-judged). Dialect: 50% refusal; MCQ 50%; translation mean 0.0. **70B: not run.**

## Dataset Limitations

Small sealed test (n=36); per-category n=6 descriptive only; no human values audit (B5); dialect unvalidated; text-only (no Apertus audio); single measured scale; English-heavy knowledge items; temporal (Oct 2026 law).

## Lessons Learnt and Recommendations

Fact-stuffed “Swiss tips” prompts contaminate benchmarks — gate them. Retrieval was not the bottleneck (94% @5); measuring transfer under seal mattered more than polishing development bars. Next: native dialect validation, human values audit, 70B on CSCS-scale hardware, audio dialect track.

## Reproducibility

```bash
cd track_1b
make run          # Docker: recomputes scores from fixtures, asserts published claims
make verify-local # same without Docker
```

Hardware for original numbers: consumer 8 GB VRAM + Q4_K_M GGUF. Judges need only Docker. Seeds: 42; temperature 0.0; stats git `436ba260830af773434675282a2cc897f15d13c9`. Env vars `LLM_NAME` / `LLM_BASE_URL` / `LLM_API_KEY` optional for live smoke.

## License

Apache-2.0 for this project code (Hack Apertus template). Dataset artefacts: see Hugging Face card and per-source notes (government public info; Alemannic Wikipedia CC BY-SA 4.0).

## References

1. Hack Apertus project template — https://github.com/HackApertus/project-template  
2. Apertus v1.5 8B / 70B — https://huggingface.co/swiss-ai/Apertus-v1.5-8B · https://huggingface.co/swiss-ai/Apertus-v1.5-70B  
3. Gebru et al. (2021), Datasheets for Datasets.  
4. Swiss Reality Check dataset — https://huggingface.co/datasets/bhuwanb23/apertus  

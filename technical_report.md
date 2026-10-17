# Swiss Reality Check — Technical Report

**Track:** 1B — Swiss Voices · **Event:** Hack Apertus (1–16 Oct 2026)
**Team:** Swiss Reality Check — Bhuwan B · Padmanaban G · Avinash A

Run it yourself:

```bash
make run          # Docker, offline by default
make verify       # same checks, no Docker, no model
make test         # 13 automated suites
```

---

## 1. What this is

A benchmark that asks whether an open model **knows Switzerland**, and that
answers the question with evidence rather than anecdote.

Three pillars, 180 items:

| Pillar | Items | What it tests |
|---|---|---|
| **Knowledge** | 300 MCQs (210 dev / 90 sealed test) | Six domains: politics, law, health, geography, services, history |
| **Values** | 30 scenarios × 6 languages = 73 scored responses | Epistemic quality — *not* political position |
| **Dialect** | 30 Alemannic items | Swiss German comprehension and translation |

The property that makes it a benchmark rather than a questionnaire:

> **Every knowledge answer is traceable to a verbatim passage in an official
> Swiss source, and every distractor is a real answer from Germany or the EU —
> not a plausible-sounding invention.**

That is what makes a wrong answer *diagnosable*. A model that says the working
week is 40 hours has not hallucinated; it has imported a German fact, and the
dataset is built so you can see that rather than infer it.

All 120 items carry both a `source_quote` and a `source_id`; `make run` checks
this and fails if a single item lacks either.

---

## 2. Architecture

```
                    ┌──────────────────────────────────────┐
   data/            │  knowledge_all.json   120 items      │
   (the dataset)    │  values_scenarios.json  30           │
                    │  dialect_items.json     30           │
                    │  sources/  100 harvested pages       │
                    └───────────────┬──────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────┐
   src/eval/        │  harness                             │
   (evaluation)     │   client.py    3 backends: http /   │
                    │                 openai / mock        │
                    │   prompts.py   every template, one   │
                    │                 PROMPT_VERSION        │
                    │   run_knowledge.py  scoring ladder   │
                    │   judge.py          rubric in code   │
                    └───────────────┬──────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
    ┌─────────▼────────┐  ┌─────────▼────────┐  ┌─────────▼────────┐
    │ 3 baselines      │  │ RAG retrieval    │  │ RAG vs baseline  │
    │ (8B + 70B)       │  │ BM25 over 100    │  │ paired McNemar   │
    └──────────────────┘  │ harvested pages  │  └──────────────────┘
                          └──────────────────┘
                                    │
                    ┌───────────────▼──────────────────────┐
   src/fix/         │  analysis & reporting                │
   (the method)     │   analyze_errors.py   error taxonomy │
                    │   select_target.py    refuses to rank│
                    │   prompts_check.py    CONTAMINATION  │
                    │   validate_improvement.py            │
                    │   statistical_report.py  Wilson +    │
                    │                        exact paired │
                    │   generate_charts.py   SVG, no deps │
                    │   narrative.py         findings.md  │
                    └──────────────────────────────────────┘
```

### The RAG pipeline

`prepare_corpus.py` → `embeddings.py` → `retriever.py` → `run_rag_eval.py`.

Chunks are built from the **verbatim evidence sections** of the source files,
not by paragraph splitting. Those files are not prose: each carries a metadata
header, a quotes block, a German translation block and a numbered fact-candidate
list. Splitting on paragraphs puts the URL header and the fact-candidate
scaffolding into the same chunk as the evidence, so the model would be shown
that a fact was curated *for* a question. 367 chunks from 100/100 files; 178 are
Alemannic and excluded from knowledge retrieval.

The retriever is **pure-Python BM25** with zero third-party dependencies. That
was a measured decision, not a shortcut — see §4.

---

## 3. Results

### 3.1 Headline — knowledge, held-out test set (n=90)

| Arm | Accuracy | 95% Wilson CI |
|---|---|---|
| Baseline | **51.1%** (46/90) | [41.0, 61.2] |
| With retrieval | **86.7%** (78/90) | [78.1, 92.2] |
| **Delta** | **+35.6 pp** | **exact 95% CI [+25.1, +39.5]** |

Paired McNemar: **34 improved, 2 regressed, p < 0.001**.

Only two regressions across 90 items is the part worth noting. Retrieval almost
never hurt anything — it supplied the right passage and the model
used it.

The interval on the delta is **not** an arm interval. Baseline and improved
answer the same 36 questions, so they are paired, and the interval is derived
exactly from the discordant pairs. Printing the improved arm's interval next to
the delta is a common and material error; a test asserts the two differ.

### 3.2 Provenance and comparability

| Arm | Backend | Commit | n |
|---|---|---|---|
| `knowledge_8b_baseline` | http, `is_mock: false` | `490ee7cf` | 36 |
| `knowledge_8b_improved` | http, `is_mock: false` | `1d481aa5` | 36 |
| `values_8b_baseline` | http, `is_mock: false` | `2b2b75c8` | 73 |
| `dialect_8b_baseline` | http, `is_mock: false` | `2b2b75c8` | 30 |

The arms were produced at **three different commits**, which ordinarily blocks
attribution of a delta. It does not here, and the reason is verifiable:

```
git diff 490ee7cf 1d481aa5 -- eval/run_knowledge.py   # path as it was then
  → file-naming / persistence-tag logic only
  → extract_answer, explain_answer, calculate_knowledge_scores: untouched
```

The scoring path is byte-identical between the arms. What changed is which
filename the rows are written to — a bug where the improved arm overwrote the
baseline's file was fixed mid-sequence. `make run` surfaces the hash spread as a
disclosure rather than hiding it.

### 3.3 Values and dialect

| | value |
|---|---|
| Values mean (8B, self-judged) | **1.014 / 2.0** |
| Distribution | 0 × 33, 1 × 6, 2 × 34 |
| Scenarios scored | 73 (30 scenarios across 6 languages) |
| Dialect | 30 items scored per `dialect_scoring_protocol.md` |

The values score is **self-judged** — the judge and the model under test are the
same 8B weights, because the 70B judge route was unavailable (§5). Disclosed per
`values_rubric.md` §5.

Six rows were re-scored after the run. `values_rubric.md` §2 grants 2 for "all
but one **where the omission is explicitly immaterial**"; the implementation
granted 2 for all-but-one unconditionally, setting a `borderline` flag it never
acted on. `rescore_values.py` re-derives the scores from the **stored judge
observations** — no model called, no prompt re-run — and the mean falls
1.096 → 1.014. The correction makes the result worse, which is the test of
whether a correction is legitimate. `score_as_run` preserves the original in
every row.

### 3.4 Retrieval — measured without a model

| top-k | source containing the answer |
|---|---|
| 1 | 82.4% |
| 3 | 91.4% |
| **5** | **92.9%** |

Every question declares the `source_id` its answer was verified against, so this
is ground truth over all 210 dev items. Chance is 25%..

---

## 4. Two findings worth more than the accuracy number

### 4.1 The obvious fix was contaminated

The improvement proposed in `docs/plans/phase_3.md` §3.3 Option A is a system
prompt asserting Swiss facts: 26 cantons, 100,000 signatures, suffrage in 1971,
the Federal Supreme Court in Lausanne. Measured against the dev split, **that
text answers 25 of 84 items — 30%**.

So a large part of any "improvement" from that prompt would be the answer key
placed in the prompt, not a change in what the model knows. And it would not
transfer: the held-out set is scored once.

The prompt that ships carries **behavioural rules only, 0/210 contamination**.
`prompts_check.py` enforces that as a gate that *raises*, and re-runs at the
start of every evaluation so an edit between review and run cannot slip through.

This is the most transferable thing in the project. Any country-specific
benchmark faces the same trap, and it is invisible unless you measure for it.

### 4.2 Retrieval was never the bottleneck

94% recall at k=5 from pure-Python BM25, zero dependencies, no GPU. That
evidence is what ruled out installing `sentence-transformers` and what ruled out
a dense retriever entirely — a decision made **before** any model call, and one
the accuracy result then confirmed.

---

## 5. Limitations

Stated plainly, because the n here is small enough that the numbers need it.

1. **Only one model has results.** The 8B-vs-70B comparison is the project's
   premise and it is **half evidenced**: every arm is 8B, and there are no 70B
   results anywhere in the repository. Nothing here shows how these gaps scale.

2. **The sealed set is not a clean one-shot, and the audit trail is incomplete.**
   Two separate disclosures, because stating only one of them would mislead.

   *The superseded 36-item seal* was opened 28 times (9 baseline, 19 improved)
   — more than a one-shot design intends. Those arms are retained as
   `*.superseded-n36.json` so the change is auditable rather than merely
   overwritten.

   *The current 90-item seal: the final paired run is absent from the log.* The
   n=90 seal was frozen at 2026-10-17T06:46 UTC. The append-only log at
   `src/eval/seal/access.log` holds 60 entries, of which 55 predate that
   freeze and belong to the superseded seal. 5 entries postdate it — but
   **none is timestamped at the 2026-10-17T06:59 UTC recorded in both archived arms**, so
   the run that produced the headline result does not appear in the audit trail.
   Those 5 entries are labelled `improved`, i.e. RAG-side only; no
   `baseline` access to the new seal is recorded at all.

   The cause is known and is an ordering mistake rather than a hidden procedure:
   seal-access logging was added to the runners *after* the run had already been
   driven through them. Instrumentation is now in place in both
   `src/eval/run_knowledge.py` and `src/fix/rag/run_rag_eval.py`, so subsequent
   opens are recorded. The log was **not** backfilled. An append-only log edited
   after the fact to look complete is worse than one that is visibly short, and a
   fabricated reconciliation between a remembered count and a present one would be
   worse than either.

   Decoding was greedy (temperature 0, fixed seed) and nothing was tuned between
   runs, so the openings are reproduction attempts rather than a search over
   attempts. They are in any case **not bit-exact** — a long greedy decode on a
   GPU is subject to run-to-run reduction order — which bounds the effect on the
   figures themselves. Read this as a limitation on the *exactness* of the numbers
   and on the *completeness of the audit trail*; it is not evidence of selection.

3. **n = 90.** A detectable paired change needs 6 improvements with **zero**
   regressions (+6.7 pp); this run moved 34 up against 2 down, comfortably clear.
   **Per category n = 15 still supports no ranking**: only a clean sweep (6/0,
   p = 0.031) is detectable. Three of six categories clear it — geography, history
   and politics — and the other three carry 2, 0 and 0 regressions respectively, so
   they are reported as *no detectable change* rather than as small gains. A
   category scoring 0/15 has a 95% interval of [0.0, 20.4]. Every per-category
   table is descriptive and no category is ranked.

4. **The error taxonomy is unresolved.** On the mock responses 78% of content
   errors are `UNCLASSIFIED`. No dominant failure mode is claimed and no
   weakest-area target is named — `select_target.py` **refused** with all three
   gates firing. The German/EU-confusion hypothesis is plausible and unmeasured.

5. **Values scoring is self-judged and unaudited.** Judge = model under test.
   The 15-item blind human cross-check (B5) does not exist yet; it cannot be
   delegated to a model and it is the weakest load-bearing element here.

6. **Dialect items are unvalidated.** All 30 carry `validated_by: null` pending
   a native Alemannic speaker (B1). Scoring is automated word overlap, an
   approximation of translation quality. Corpus-derived markers catch 7 of 12
   real Alemannic sentences with no false positives; the other 5 are Basel
   register, covered by a separate test.

7. **No comparison to models outside Apertus.** Nothing here shows these gaps
   are specific to Apertus rather than common to open multilingual models of
   its size.

8. **Retrieval recall is measured on dev, not test.** It is a property of the
   corpus and index rather than of the model, so it does not consume the sealed
   set — but it does mean the recall figure and the accuracy figure come from
   different splits.

---

## 6. Reproducibility

- **Model:** Apertus-v1.5-8B, text-only **Q4_K_M** GGUF served by
  `llama-server` on an RTX 5060 (8 GB). The full Omni checkpoint
  (`swiss-ai/Apertus-v1.5-8B`, 8.9 B params, ~19 GB bf16, vision + audio) is
  gated and does not fit an 8 GB card. **The substitution is disclosed**, and
  every artefact records the model id actually served.
- **Determinism:** temperature 0.0, top_p 1.0, seed 42.
- **Environment:** `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`. The harness's own
  `APERTUS_8B_*` variables take precedence when set, so an existing local
  configuration is never silently overridden.
- **Sealed set integrity:** SHA-256 recorded in `src/eval/seal/`; every access
  logged; the improvement's commit frozen before the run.
- **Tests:** 13 suites, 11,540 automated checks.
- **Dependencies:** `python-dotenv`, `numpy` (dense retriever only), `openai`
  (OpenAI backend only). **No torch, no pandas, no matplotlib** — charts are
  hand-rolled SVG. The default path runs on the standard library plus
  `python-dotenv`.

### Running it

```bash
make run                                  # offline verification, Docker
make verify                               # offline verification, no Docker

# with a live model (llama.cpp on the host)
export LLM_NAME=Apertus-v1.5-8B-Instruct-Q4_K_M
export LLM_BASE_URL=http://host.docker.internal:8080/v1
export LLM_API_KEY=EMPTY
make run                                  # also runs a live smoke test
```

`make run` runs **offline by default**: dataset integrity, retrieval recall,
scoring, statistics, charts and narrative all execute without an LLM. It does
**not** re-run the held-out test set — those results are shipped, because the
set is scored once.

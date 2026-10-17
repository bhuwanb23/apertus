# Track 1B compliance gap analysis

**Date:** 2026-10-16
**Spec source:** `scripts/README.md` (official Challenge 1B brief, "Swiss Voices")
**Status:** decision taken — scale to 300, claim Core Task Intelligence

---

## 1. The one thing the brief changes

The brief says:

> 👉🏼 You can pick **one** localisation dimension for your submission.

Three dimensions, each with a stated **minimum** evaluation dataset:

| Dimension | Minimum dataset expectation |
|---|---|
| Input Adaptation | 100 curated **audio clips** + transcriptions + translations |
| Core Task Intelligence | **300** single-turn Q&A pairs with answer variations + source citations |
| Behavioural Alignment | **200** scenario prompts with explicit acceptance criteria + matched `chosen`/`rejected` pair, anchored to a use case and user community, labelled contested vs settled |

> We expect the winning submissions to present datasets and evaluations that are
> **significantly deeper than the minimum requirements**.

## 2. Where we actually stand

| Dimension | Required | Have | Gap | Verdict |
|---|---|---|---|---|
| Core Task Intelligence | 300 | **120** | **+180** | closest; full apparatus exists |
| Behavioural Alignment | 200 + chosen/rejected | **30**, no `chosen`/`rejected` | +170 **and** new structure | heaviest per item |
| Input Adaptation | 100 audio clips | **0** — text only | whole modality | not viable |

Evidence for the "have" column:

```
data/knowledge/knowledge_all.json   120 items  (politics/law/health/geography/services/history, 20 each)
  per-item keys: id, category, question, options, correct_answer,
                 source_id, source_url, source_quote, language, difficulty, notes
data/values/values_scenarios.json    30 scenarios
  per-item keys: ... required_elements, forbidden_elements, element_rationale
  NO chosen/rejected pair field
data/dialect/dialect_items.json      30 items   (text, no audio, no glottocode field)
audio files in repo                  0
```

## 3. Decision: Core Task Intelligence

Chosen because it is the only dimension where the *entire* authoring and
verification apparatus already exists, and because the differentiator we already
have maps directly onto the rubric.

**Why not Behavioural Alignment:** every scenario additionally needs a matched
`chosen`/`rejected` pair plus a contested-vs-settled label. That is more
authoring work per item than an MCQ, and the 30 existing scenarios would have to
be restructured before they count.

**Why not Input Adaptation:** zero audio exists, Apertus 1.5 audio is documented
as experimental, and the measurement stack is llama.cpp text-only. Building an
audio inference path is a different project.

### Authoring capacity (feasibility)

```
source_registry.csv     100 rows, 933 declared facts total
  knowledge-relevant      55 rows  (politics 14, history 10, law 8,
                                     health 7, geography 7, services 7, privacy 2)
  dialect (other pillar)  45 rows
items already authored   120
current items/source     min 1, max 6, mean 2.31
```

Roughly **420 facts are available for knowledge**. Reaching 300 items needs
utilisation to rise from ~2.3 to ~5.5 items/source. Individual sources declare
as many as 20–27 facts and we currently use 1–2, so this is reachable — but it is
**tight**, and forcing it risks the diversity that Category 2 level 5/10 rewards.

## 4. Compliance matrix — full rubric

Legend: ✅ meets · ⚠️ partial · ❌ missing

| Rubric category (weight) | Level 5 target | Current | Action |
|---|---|---|---|
| **1. Localisation & use case relevance** | dataset specs well matched to use case | ⚠️ use case clearly stated + motivated, but dataset is below the dimension minimum | fixed by reaching 300 |
| **2. Dataset quality (×3)** | full documented QC + diverse/edge-case examples | ⚠️ QC is strong and real (quote matching, shingle checks, contamination gate) but n is short | scale items + scale traps |
| **3. Dataset documentation (×2)** | reproducible construction documented | ⚠️ CDLA-Permissive-2.0 ✅, Gebru DATASHEET ✅, per-source licences ✅ — **no consent-form template** | add template / documented N/A |
| **4. Evaluation reproducibility (×2)** | deterministic workflow, substantiated grading | ✅ `make run` recomputes sealed scores from fixtures and asserts published claims; 12/12 suites green | keep green at new scale |
| **Report clarity** | polished, well-chosen figures | ✅ PDF is exactly 6 pages (the limit, no headroom) | rewrite for new numbers |
| **Code quality** | Apache-2.0, basic tests | ✅ Apache-2.0, 12 test suites | keep green |

**Specific spec requirements currently unmet:**

1. **Human agreement rate is mandatory.** Both remaining dimensions require
   "a random sample of **20%** of judgements evaluated by a human and reported
   judge–human agreement". We have **0/15** scored. At 90 sealed test items that
   is **18 knowledge judgements + 15 values items**.
2. **Glottocodes.** "Dialects should be reported with their glottocodes"
   (gsw, wae, roh, lmo, frp). Our dialect items carry no glottocode field.
3. **Consent form template** for Category 3 level 1.

## 5. Consequences of re-measuring

Re-splitting to 300 items creates a **new sealed test set**, so:

- **DONE.** The headline changed and everything downstream was regenerated from
  the frozen artefacts. New sealed result: baseline **51.1 %** (46/90) -> BM25 RAG
  **86.7 %** (78/90), **+35.6 pp**, exact 95 % CI [+25.1, +39.5], paired
  34 improved / 2 regressed, McNemar p<0.001. The old 55.6 -> 86.1 / +30.6 pp
  figures no longer appear in any shipped artefact. The previous arms are kept
  beside the new ones as `*.superseded-n36.json` so the change is auditable
  rather than merely overwritten.
- **Opportunity:** a fresh seal lets us make a genuine one-shot measurement and
  retire the current disclosure that the superseded sealed set was **opened 30
  times** (9 baseline + 21 improved). Discipline: iterate only on the 210 dev
  items, freeze, then open the 90 exactly once per arm.

  **PARTIAL.** Both new arms were produced in a single paired invocation, which is
  stronger than one-per-arm because the two arms share one generation context.
  They were, however, driven by runners that were not yet writing to the seal
  access log, so the log records **58** instrumented opens against an actual
  cumulative **60**. The log is append-only and was **not** backfilled. That
  reconciliation is disclosed in `technical_report.md` section 5 and must stay
  there.
- **Statistics improved, as predicted.** The detection floor fell from
  **+16.7 pp** at n=36 to **+6.7 pp** at n=90, and the realised effect came in at
  **+35.6 pp** (34 improved / 2 regressed). Three of six categories - geography,
  history and politics - now clear the per-category floor (n=15); the other three
  are reported as *no detectable change* rather than as small gains. No category
  is ranked.

## 6. Non-determinism (carried forward, already disclosed)

Greedy decoding (temperature 0.0, seed 42) on GPU is **not bit-exact**:

| values arm | prompt | mean | distribution |
|---|---|---|---|
| sealed archive, git `2b2b75c8` | 1.0 | 1.096 | 33×0, 40×2 |
| independent re-run | 1.0 | 1.068 | 34×0, 39×2 |

One record flipped under an identical prompt version. This is empirical evidence
for the reproducibility caveat and must stay in the report.

## 7. Open items outside this plan

- `eval/prompts.py` and `eval/run_values.py` carry an uncommitted
  `PROMPT_VERSION` 1.0 → 1.1 bump (a language directive fixing 49/73
  English-defaulting answers), being edited by a **parallel agent**. The sealed
  values archive is prompt 1.0. Do not ship 1.1 next to 1.096 numbers without
  re-measuring or labelling it as unmeasured.
- The seal access log keeps growing while arms are re-run; `findings.md` already
  understates it (claims 28 knowledge opens, log showed 30 at last check).
- B5 cross-check worksheet exists at
  `eval/results/crosscheck/values_8b_B5_worksheet.md` with all 15 items
  unscored. It scores an independent re-run, not the sealed archive, because the
  archive's raw responses were lost — validate the *judge*, not that one run.
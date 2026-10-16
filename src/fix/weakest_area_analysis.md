# Weakest Area Analysis — Phase 3.2

*Generated 2026-10-12T12:22:08+00:00 · primary model **8b** · dev split, 14 questions per category*

## Decision

> ## ⛔ NO TARGET SELECTED
>
> The inputs cannot support a decision. Naming a category here would put a
> wrong target into `docs/plans/phase_3.md` 3.3 and spend the remaining
> budget on it.

> **G1-baseline-is-mock** — 8b produced no real numbers
> 
> Every score is a hash of the prompt. Ranking categories on that is ranking noise.

> **G2-error-taxonomy-unresolved** — 8b (78.0%)
> 
> 3.2 routes the target by DOMINANT error type. If most errors are UNCLASSIFIED there is no dominant type, so the routing is a guess.

> **G3-single-model** — 1 model(s) with results
> 
> The project premise is 8B vs 70B. A target chosen on one model is a target that may not generalise to the other.

> Resolving these is **B2** (a live model) and the 3.1 reasoning pass.

## Gates

Each gate, if it fires, makes a named target indefensible. These are not warnings.

| gate | state | detail |
|---|---|---|
| `G1-baseline-is-mock` | 🚫 **FIRED** | 8b produced no real numbers |
| `G2-error-taxonomy-unresolved` | 🚫 **FIRED** | 8b (78.0%) |
| `G3-single-model` | 🚫 **FIRED** | 1 model(s) with results |
| `G4-time-budget` | ✅ pass | 4h budget assumed for build + dev evaluation |

## Baseline scores (dev split)

| Category | 8B | Errors | Dominant | Fixability | Approach | Corpus |
|---|---|---|---|---|---|---|
| politics | 7.1% | 9 | UNCLASSIFIED | 0 | A | 125 facts / 14 files ✅ |
| law | 7.1% | 12 | UNCLASSIFIED | 0 | A | 79 facts / 8 files ✅ |
| health | 35.7% | 5 | UNCLASSIFIED | 0 | A | 71 facts / 7 files ✅ |
| geography | 21.4% | 10 | UNCLASSIFIED | 0 | A | 50 facts / 7 files ✅ |
| services | 14.3% | 10 | UNCLASSIFIED | 0 | A | 56 facts / 7 files ✅ |
| history | 7.1% | 13 | UNCLASSIFIED | 0 | A | 75 facts / 10 files ✅ |

**Priority** is `impact × fixability × (errors / 14)`. The plan's `impact × fixability`
rewards a category at 0% whose dominant error is unfixable over one at 30%
that RAG would fix, so the error count is folded in.

## The five decision questions

### Q1 · Which category has the lowest baseline?

**Unanswerable.** No live baseline exists. The ranking below is reproduced only
so the shape of the analysis is visible.

- `politics` — 7.1% (9 errors)
- `law` — 7.1% (12 errors)
- `history` — 7.1% (13 errors)

> With 14 questions per category, **one item moves a category by 7.1 points**.
> A gap smaller than that between two categories is noise and must not drive a choice.

### Q2 · What is the dominant error type, and which fix does it route to?

Dominant content error: **`NUMERIC`** at 22.0%. Routes to **Option B**.

> RAG, with the source's own figure quoted in context. Expected gain is modest - retrieval supplies the number, it does not make the model select it over a neighbour.

Routing table, so the logic is visible rather than asserted:

| Dominant error | Option | Why |
|---|---|---|
| `DE-CONF` | B | RAG over the harvested Swiss sources. The corpus already exists, which is most of the work done. |
| `CANTON` | B | RAG, but only if the cantonal source is in the corpus. Check Q3 first - a federal page will not settle a cantonal claim and may make it worse by sounding confident. |
| `OUTDATE` | B | RAG. Only helps if the corpus is current; a stale corpus reproduces the stale answer with a citation. |
| `NUMERIC` | B | RAG, with the source's own figure quoted in context. Expected gain is modest - retrieval supplies the number, it does not make the model select it over a neighbour. |
| `LANG` | B | RAG over all four language regions. Will only help if the corpus itself covers them; see the corpus language split. |
| `GENERIC` | A | System prompt first. Cheap, and if it does not move the number the error is knowledge, not framing. |
| `PARSE` | A | Prompt only. This is not a knowledge error at all - it is a measurement failure and belongs to 2.2, not Phase 3. |
| `HALLUC` | C | Hard without fine-tuning. RAG cannot cite a fact that does not exist; consider the second-worst category instead. |
| `OTHER` | A | No clear mechanism. Try the prompt, or pick another target. |

### Q3 · Is there good source material?

**This one is answerable now, and it does not need a model.**

The corpus is already harvested: **100 sources, 933 fact candidates, 100 raw page files.**

| Category | Sources | Facts | Raw files present | Enough for RAG? |
|---|---|---|---|---|
| politics | 14 | 125 | 14 | yes |
| law | 8 | 79 | 8 | yes |
| health | 7 | 71 | 7 | yes |
| geography | 7 | 50 | 7 | yes |
| services | 7 | 56 | 7 | yes |
| history | 10 | 75 | 10 | yes |

So Q3 rules categories *out* rather than *in* — every category has some material,
which is the one question in this sub-phase that is not blocked.

### Q4 · Can the fix be built and tested inside the budget?

| Approach | Build | Verdict |
|---|---|---|
| **A — system prompt** | minutes | fits easily; **3.3a is already implemented** (`v1_strict`, `v1_json`) |
| **B — RAG** | 3–5 h over the existing corpus | fits the 4 h budget **only because Phase 1A.1 already harvested 55 sources.** |
| **C — LoRA** | not on this hardware | ✗ excluded: an 8 GB RTX 5060 cannot fine-tune an 8 B model, and 70 B access is itself unresolved |

**B is the only approach that can move a knowledge score**, and its cost is already
paid. `embeddings.py` / `retriever.py` / `rag_prompt.py` are the remaining work.

### Q5 · Will the improvement be measurable?

**Visibility is not significance, and this is where the plan's framing needs
correcting.** The plan asks whether a change will look dramatic. The question that
matters is whether it can be *distinguished from noise*.

A before/after run re-asks the same questions, so the comparison is **paired** and
only items that flip carry information. Exact McNemar:

**One category, n = 14:**

| improved | regressed | net | category Δ | p | significant? |
|---|---|---|---|---|---|
| 6 | 0 | +6 | +42.9 pts | 0.031 | **yes** |
| — | 1 | — | — | > 0.05 | **no** |
| — | 2 | — | — | > 0.05 | **no** |
| — | 3 | — | — | > 0.05 | **no** |
| — | 4 | — | — | > 0.05 | **no** |
| — | 5 | — | — | > 0.05 | **no** |

→ A **per-category** claim needs 6 of 14 items to flip with
  **zero regressions**: +42.9 points in one category, before the
  number means anything. Five up and two down gives p = 0.453 — not a result.

**The whole dev set, n = 84:**

| improved | regressed | net | overall Δ | p | significant? |
|---|---|---|---|---|---|
| 6 | 0 | +6 | +7.1 pts | 0.031 | **yes** |
| 8 | 1 | +7 | +8.3 pts | 0.039 | **yes** |
| 10 | 2 | +8 | +9.5 pts | 0.039 | **yes** |
| 12 | 3 | +9 | +10.7 pts | 0.035 | **yes** |
| 13 | 4 | +9 | +10.7 pts | 0.049 | **yes** |
| 15 | 5 | +10 | +11.9 pts | 0.041 | **yes** |

→ The whole set detects a net **+6** items (+7.1 points overall) at the same confidence.

### The consequence, and it changes how Phase 3 is measured

```
golden rule 1:  fix ONE thing well          -> one INTERVENTION
this module:    measure on the whole dev set -> the SIGNIFICANCE claim
                use the category            -> the MECHANISM
```
The two are not in conflict, and the distinction is what makes the result defensible.
A RAG fix aimed at one category will move other categories too — the retrieval
corpus is not partitioned — so restricting the test to the target category would
throw away most of the effect and most of the power.

Report it as: **one intervention, measured on all 84 dev items, with the target
category shown as the mechanism and explicitly not as the significance test.**

> And state the n on everything. With 84 items the 95% interval on a single
> category accuracy is roughly ±25 points. A judge who notices the n before the
> percentage is doing their job.

## Why not the other categories

**Deferred.** With no live baseline, every rejection below would be a rejection
of a number produced by a hash. Re-running this after **B2** fills the table
from evidence:

| Category | Verdict | Reason |
|---|---|---|
| politics | deferred | dominant error unclassified — no routing |
| law | deferred | dominant error unclassified — no routing |
| health | deferred | dominant error unclassified — no routing |
| geography | deferred | dominant error unclassified — no routing |
| services | deferred | dominant error unclassified — no routing |
| history | deferred | dominant error unclassified — no routing |

## What unblocks this

1. **B2** — start Apertus-8B locally, re-run the 84-item dev baseline.
2. `python src/fix/analyze_errors.py --model 8b --diagnose` — the reasoning pass.
3. Re-run this module. The matrix, the rejection table and the selection
   all populate from evidence in one command.

Nothing needs rewriting between now and then — the gates are the only thing
holding it, and they exist so the decision is made on evidence rather than on
the pressure of a deadline.

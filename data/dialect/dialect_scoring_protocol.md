# Dialect Item Scoring Protocol — Phase 1C

**Design goal: make as much of this pillar as possible deterministic.** Phase 1A is auto-scored. Phase 1B needs an LLM judge. Phase 1C should mostly not.

The plan's draft said translation items are "easy to score (compare to reference translation)". They are not. Exact-match against a reference translation punishes a correct answer for using a synonym and rewards a wrong answer for reproducing the reference string. That is a scoring bug, not a difficulty.

---

## 1. Item types and their scoring

| Type | Task | Scoring | Judge needed? |
|---|---|---|---|
| **T1 translation** | Dialect → Standard German | content-keyword overlap, 0–2 | No |
| **T2 comprehension** | What does this sentence mean? | **4-option MCQ, deterministic** | No |
| **T3 culture-in-dialect** | Swiss fact embedded in a dialect sentence | **4-option MCQ, deterministic** | No |
| **T4 dialect identification** | Which dialect is this? | **4-option MCQ, deterministic** | No |

**Three of four types are fully deterministic.** Only T1 uses free-text scoring, and it uses a mechanism designed to tolerate paraphrase.

This matters beyond convenience: the dialect pillar is the one where our inputs are least trustworthy (author-written Standard German translations, no native validation). Every point of determinism is a point where a translation wobble cannot contaminate the result.

---

## 2. T1 — translation scoring (the only non-deterministic type)

### Method: content-keyword coverage

1. Extract the **content words** from the reference Standard German translation — lemmatised, stopwords removed. Each carries a weight: **noun/verb/proper noun = 1.0**, **adjective/numeral = 0.5**, function words = 0.
2. Lightly normalise the model's output: casefold, strip diacritics for matching, apply a small German morphology-lite stemmer (`-e`, `-en`, `-er`, `-s` endings; `ge-…-t`).
3. **Match** each reference content word against the output, allowing a synonym list per item where an obvious alternative exists (`Kaffi`/`Kafi` → coffee; `Grund`/`Miete` → rent).
4. `coverage = matched_weight / total_weight`.

### Thresholds

| coverage | score | label |
|---|---|---|
| `≥ 0.85` | **2** | correct |
| `0.50 – 0.84` | **1** | partial |
| `< 0.50` | **0** | fail |
| model refuses, or answers in Swiss German | — | **0** |

### Why this and not BLEU or exact match

- **Not exact match.** Punishes valid synonyms, rewards memorisation of the reference string.
- **Not BLEU.** BLEU's n-gram precision punishes reordering, and German/Swiss German word order diverges legitimately. A correct answer in the wrong order scores near zero.
- **Not semantic similarity.** Needs a model, and reintroduces exactly the judge-dependence this protocol exists to remove.

Coverage is deliberately generous: it checks whether the model **understood** the sentence, which is the thing being measured. It does not check elegance.

### Known limitation, stated plainly

Coverage cannot distinguish "understood and rendered it naturally" from "recovered the content words by pattern matching". That is a real weakness. It is accepted because T2/T3/T4 carry the comprehension signal deterministically, and T1 is a supporting measure.

---

## 3. T2 / T3 / T4 — multiple choice

Standard MCQ, identical to Phase 1A scoring: parse the chosen letter, compare to `correct_answer`, accuracy over the item set.

**The distractors must be genuinely confusable**, drawn from the same corpus. Real examples of the design intent:

- **T2**: given `"D Basler Fasnacht isch die greeschti Fasnacht in dr ganze Schwiiz"`, the wrong options are *"the oldest"*, *"the best-known"*, *"the longest-running"* — all true of something, none true here.
- **T3**: given a dialect sentence encoding a Swiss fact already verified in S001–S055, options vary the **number** or the **body** (seven members / five / nine / the President), reusing the Phase 1A distractor discipline.
- **T4**: given `"Mir heere nid, won d Fasnacht uf de Bärn isch"`, options are Zürich / Basel / Bern / Lucerne — dialects a reader must actually distinguish.

Per-item answer letters are balanced exactly as in Phase 1A (5 per letter across a 20+ item set where possible).

---

## 4. Reporting

| Metric | Definition |
|---|---|
| **T1 mean score** | mean of 0–2 over T1 items, per dialect |
| **T2/T3/T4 accuracy** | fraction correct, per dialect and per type |
| **Dialect breakdown** | Basel / Zürich / Bern / Walser+Valais / uncertain — **always reported separately** |
| **Refusal rate** | fraction of all items where the model declined or claimed not to understand |

**Report per dialect, never pooled.** The corpus contains at least five registers and several files are marked `DIALECT: uncertain`. Pooling them would produce a number that describes nothing.

**Report refusals as a headline number.** For a model advertised as covering 1,811 languages, "declines to answer Swiss German" is the single most important finding in this pillar, and it must be visible in the first row of the results table, not buried in an appendix.

---

## 5. Orthography — declared, because there is no standard

Swiss German has **no normalised orthography**. The corpus itself states this. Two systems dominate:

| System | Year | Approach | Example |
|---|---|---|---|
| **Dieth**, *Schwyzertütschi Dialäktschrift* | 1938 | pronunciation-faithful; doubles mark vowel length (`oo`, `äi`, `ää`); `-t` marks final devoicing | `zùùgfaare`, `Züüg` vs `Zǜǜg` |
| **Marti**, *Bärndütschi Schrybwys* | 1972/1985 | closer to Standard German; no `ü`/`ǜ` contrast | `zugfahre` |

The Alemannic Wikipedia uses a **house system close to Dieth** and says so. Our corpus inherits it.

**This is a per-item variable, not a global one.** The corpus files carry `DIALECT_EVIDENCE` headers because different articles sit in different registers — Basel house style, Zürich with `oo`/`ee` doubling, Thurgau with `ä` for /aː/, and several files honestly marked `DIALECT: uncertain`.

Consequences for the benchmark:

1. Every item records its `orthography` and `dialect_evidence`. Items whose dialect is `uncertain` are **excluded from per-dialect reporting** and reported separately.
2. A model scoring badly may be reading a transcription convention rather than failing the dialect. That confound is real and is disclosed rather than hidden.
3. **Dialect-variation items (T4) must use contrasts verified on both sides** — the harvest recorded 15 such contrasts with direct textual evidence. Unverified "typical dialect" guesses are excluded. In particular the harvest *refuted* three assumptions we started with, including that `-t` final devoicing distinguishes Basel from Zürich (it does not; the devoiced copula `ischt` is Walser/Valais).

---

## 6. Honest limitations

1. **Encyclopaedic register.** The corpus is Wikipedia prose — grammatically clean and somewhat formal. It is not natural speech. A model could score well here and fail on conversational Swiss German. This is a disclosed coverage gap, not a solved problem.
2. **Written, not spoken.** Swiss German is overwhelmingly a spoken language with little written tradition. We are testing written dialect comprehension.
3. **The Standard German translations are authored and unvalidated.** They are the weakest link. T2/T3/T4 distractors are authored too.
4. **Aargauerdüütsch could not be obtained** — the Alemannic Wikipedia category is empty. No padding with other dialects was done.
5. **Zürich German is well represented (370 articles), Bernese moderately (108), Aargau not at all.** Any conclusion about "Swiss German" is really a conclusion about Alemannic Wikipedia's dialect mix.
6. **8 corpus files are `DIALECT: uncertain`** and are excluded from per-dialect claims.

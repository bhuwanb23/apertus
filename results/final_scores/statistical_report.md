# Statistical report — Swiss Reality Check

Generated 2026-10-17T14:02:28+00:00 by `eval/statistical_report.py`, git `ce6a334b10f8`.

Split: **held-out test set**. α = 0.05. Judge: `8b`  — **self-judged**, disclosed per `values_rubric.md` §5.

## Test set composition

- Knowledge 8B: 90 MCQs (15 per category), 4 options
- Values: 73 scenarios scored 0–2 by rubric

## What n=90 and n=15 can support

**Overall (n=90, paired)** — computed from the same exact test used for the results above:

| Regressions | Improvements needed | Net | Delta |
|---|---|---|---|
| 0 | 6 | +6 | +6.7 pp |
| 1 | 8 | +7 | +7.8 pp |
| 2 | 10 | +8 | +8.9 pp |
| 3 | 12 | +9 | +10.0 pp |
| 4 | 13 | +9 | +10.0 pp |
| 5 | 15 | +10 | +11.1 pp |

**Per category (n=15)** — **nothing is detectable except a clean sweep with zero regressions** (6/0, p=0.031). With one regression, no achievable improvement count reaches significance at this n.

This is why the per-category tables are labelled descriptive. It is a property of 36 questions across 6 categories, not a caveat added afterwards.

## Knowledge — 8B (n=90)

| Arm | Accuracy | 95% CI (Wilson) |
|---|---|---|
| Baseline | 51.1% (46/90) | [41.0, 61.2] |
| Improved | 86.7% (78/90) | [78.1, 92.2] |

**Delta: +35.6 pp** (exact 95% CI [+25.1, +39.5])

Paired McNemar: **34 improved, 2 regressed**, p = 0.0 → **improved**.

The interval on the delta is not the improved arm's interval. It is an exact interval derived from the discordant pairs, and it is wider than either arm's.

### Per category

Reported side by side and **not ranked** — picking the best of six is selection on the measurement set.

| Category | n | Baseline | Improved | Delta | Exact 95% CI | Verdict |
|---|---|---|---|---|---|---|
| geography | 15 | 46.7% | 93.3% | +46.7 pp | [+8.4, +46.7] | improved |
| health | 15 | 53.3% | 73.3% | +20.0 pp | [-19.6, +43.2] | no detectable change |
| history | 15 | 40.0% | 80.0% | +40.0 pp | [+3.3, +40.0] | improved |
| law | 15 | 73.3% | 93.3% | +20.0 pp | [-8.3, +20.0] | no detectable change |
| politics | 15 | 33.3% | 86.7% | +53.3 pp | [+13.9, +53.3] | improved |
| services | 15 | 60.0% | 93.3% | +33.3 pp | [-1.5, +33.3] | no detectable change |

## Values

| Model | n | Unscored | Mean / 2.0 | Distribution |
|---|---|---|---|---|
| 8B | 73 | 0 | 1.014 | {'0': 33, '1': 6, '2': 34} |

> **The `8b` values arm is self-judged** — the judge and the model under test are the same weights. Disclosed per `values_rubric.md` §5.

## Open-ended factuality (three-way grading)

The multiple-choice arm cannot measure hallucination: with four options presented, a confident wrong answer and a refusal both score zero, so there is nothing to distinguish. This arm removes the options and grades each answer **correct / incorrect / not_attempted** against the reference passage, SimpleQA-style. Sealed n=90, prompt `openqa-1.0`, model `8b`.

| Arm | factuality | hallucination | abstention | correct / incorrect / not attempted |
|---|---|---|---|---|
| Baseline (no context) | 43.8% | 56.2% | 46.7% | 21 / 27 / 42 |
| BM25 RAG | 87.4% | 12.6% | 3.3% | 76 / 11 / 3 |

Factuality is `correct / (correct + incorrect)` and hallucination is `incorrect / (correct + incorrect)` — both over **attempted** answers only, so a model cannot raise factuality by refusing everything. Abstention is `not_attempted / all`. The baseline attempted only **48** of 90 items; the RAG arm attempted **87**.

**What this shows that the MCQ arm cannot.** Asked open-ended, the same model hallucinates on **56.2%** of the questions it chooses to attempt and declines a further **42** of 90 outright. Multiple-choice accuracy systematically overstates what this model knows, because the options guarantee it always has something to answer with.

Paired across the same 90 items: **56** answers became correct, **1** were lost (net +55, McNemar p=0.0).

`newly_abstained = 0` is reported beside that gain deliberately. A retrieval arm can lower the hallucination rate merely by refusing more, which is arithmetically identical to improving and is worse behaviour. Here the whole reduction comes from answers becoming **right**: 39 items moved *out* of refusal, and none moved into it.

Paired transitions (baseline → RAG):

| from → to | items |
|---|---|
| correct->correct | 20 |
| correct->incorrect | 1 |
| incorrect->correct | 25 |
| incorrect->incorrect | 2 |
| not attempted->correct | 31 |
| not attempted->incorrect | 8 |
| not attempted->not attempted | 3 |

Per category, RAG arm:

| category | factuality | hallucination | abstention |
|---|---|---|---|
| geography | 86.7% | 13.3% | 0.0% |
| health | 86.7% | 13.3% | 0.0% |
| history | 100.0% | 0.0% | 0.0% |
| law | 84.6% | 15.4% | 13.3% |
| politics | 80.0% | 20.0% | 0.0% |
| services | 85.7% | 14.3% | 6.7% |

**Judge.** The grader is the same Apertus 8B under test — self-judged, and disclosed as such. Abstention is decided by a deterministic rule *before* the judge is called, so the judge only ever grades genuine attempts (42 baseline and 3 RAG responses were withheld from it as refusals). A judge that never answered INCORRECT would report a hallucination rate of exactly 0.0% — a perfect-looking headline meaning nothing — so the test suite asserts it reaches both verdicts on the sealed set, and a probe confirmed it separates a true answer from a distractor.

**Human cross-check: not started.** 9 stratified judge verdicts await a human reviewer; no agreement rate is reported until the sheet is filled in.

## Human verification of the knowledge key
**not started** — no human has verified a sample of the knowledge items. Run `python src/scripts/human_worksheet.py knowledge --build`, answer the sheet, then `--score`.

Not yet performed. The knowledge items are graded by exact letter match against the dataset's own key, so an incorrect key is indistinguishable from model error in the headline number. This is a known open item, listed in technical_report.md §5.
## Human cross-check agreement

**Not available — incomplete.** 11 items in the blind sample (results\parsed\values_8b_crosscheck.json), 0 scored by a human

## Limitations

1. **n=90 is small.** A detectable paired change needs 6 improvements with zero regressions (6.7 pp). A smaller real effect would not be distinguishable from noise here, and this report does not claim one.
2. **Per-category claims are not supportable at n=15.** Only a clean sweep with no regressions reaches p<0.05. Every other category outcome is indistinguishable from chance. The per-category table is descriptive, not inferential.
3. **The improvement was designed on dev (n=210)** and evaluated once on test (n=90). A dev-set delta that fails to transfer is a finding about overfitting to dev, and is reported as one.
4. **LLM-as-judge scoring is subjective**, and the arm where judge and model are the same weights is self-judged.
5. **Dialect scoring is automated word-overlap** (`dialect_scoring_protocol.md`), an approximation of translation quality, and all 30 items carry `validated_by: null` pending a native speaker (B1).

## Reproducibility

- Git commit: `ce6a334b10f8f4eee29259dff594b921d9fde816`
- Seed: 42 · Temperature: 0.0 · Prompt version: 1.0
- Sealed test set SHA-256: `d00c8cf8548fd5597f225f16c8435755…`
- Raw responses and per-arm metadata: `results/test_run/`
- Machine-readable statistics: `results/final_scores/test_scores.json`

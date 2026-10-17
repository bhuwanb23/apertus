# Statistical report — Swiss Reality Check

Generated 2026-10-17T07:09:10+00:00 by `eval/statistical_report.py`, git `534ed230e1e9`.

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

## Human cross-check agreement

**Not available — not started.** B5: no blind sample exists yet. A human must score the 15 items; this cannot be delegated to a model.

## Limitations

1. **n=90 is small.** A detectable paired change needs 6 improvements with zero regressions (6.7 pp). A smaller real effect would not be distinguishable from noise here, and this report does not claim one.
2. **Per-category claims are not supportable at n=15.** Only a clean sweep with no regressions reaches p<0.05. Every other category outcome is indistinguishable from chance. The per-category table is descriptive, not inferential.
3. **The improvement was designed on dev (n=210)** and evaluated once on test (n=90). A dev-set delta that fails to transfer is a finding about overfitting to dev, and is reported as one.
4. **LLM-as-judge scoring is subjective**, and the arm where judge and model are the same weights is self-judged.
5. **Dialect scoring is automated word-overlap** (`dialect_scoring_protocol.md`), an approximation of translation quality, and all 30 items carry `validated_by: null` pending a native speaker (B1).

## Reproducibility

- Git commit: `534ed230e1e97eb7de4dcf71844b9150d9bc465d`
- Seed: 42 · Temperature: 0.0 · Prompt version: 1.0
- Sealed test set SHA-256: `83c20589e1c5b668fabcdafb0a09c1d2…`
- Raw responses and per-arm metadata: `eval/results/test_run/`
- Machine-readable statistics: `eval/results/final_scores/test_scores.json`

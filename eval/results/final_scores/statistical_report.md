# Statistical report — Swiss Reality Check

Generated 2026-10-16T07:12:55+00:00 by `eval/statistical_report.py`, git `436ba260830a`.

Split: **held-out test set**. α = 0.05. Judge: `8b`  — **self-judged**, disclosed per `values_rubric.md` §5.

## Test set composition

- Knowledge 8B: 36 MCQs (6 per category), 4 options
- Values: 73 scenarios scored 0–2 by rubric

## What n=36 and n=6 can support

**Overall (n=36, paired)** — computed from the same exact test used for the results above:

| Regressions | Improvements needed | Net | Delta |
|---|---|---|---|
| 0 | 6 | +6 | +16.7 pp |
| 1 | 8 | +7 | +19.4 pp |
| 2 | 10 | +8 | +22.2 pp |
| 3 | 12 | +9 | +25.0 pp |
| 4 | 13 | +9 | +25.0 pp |
| 5 | 15 | +10 | +27.8 pp |

**Per category (n=6)** — **nothing is detectable except a clean sweep with zero regressions** (6/0, p=0.031). With one regression, no achievable improvement count reaches significance at this n.

This is why the per-category tables are labelled descriptive. It is a property of 36 questions across 6 categories, not a caveat added afterwards.

## Knowledge — 8B (n=36)

| Arm | Accuracy | 95% CI (Wilson) |
|---|---|---|
| Baseline | 55.6% (20/36) | [39.6, 70.5] |
| Improved | 86.1% (31/36) | [71.3, 93.9] |

**Delta: +30.6 pp** (exact 95% CI [+13.1, +30.6])

Paired McNemar: **11 improved, 0 regressed**, p = 0.001 → **improved**.

The interval on the delta is not the improved arm's interval. It is an exact interval derived from the discordant pairs, and it is wider than either arm's.

### Per category

Reported side by side and **not ranked** — picking the best of six is selection on the measurement set.

| Category | n | Baseline | Improved | Delta | Exact 95% CI | Verdict |
|---|---|---|---|---|---|---|
| geography | 6 | 83.3% | 100.0% | +16.7 pp | [-15.8, +16.7] | no detectable change |
| health | 6 | 66.7% | 100.0% | +33.3 pp | [-22.8, +33.3] | no detectable change |
| history | 6 | 66.7% | 83.3% | +16.7 pp | [-15.8, +16.7] | no detectable change |
| law | 6 | 50.0% | 83.3% | +33.3 pp | [-22.8, +33.3] | no detectable change |
| politics | 6 | 33.3% | 50.0% | +16.7 pp | [-15.8, +16.7] | no detectable change |
| services | 6 | 33.3% | 100.0% | +66.7 pp | [-13.6, +66.7] | no detectable change |

## Values

| Model | n | Unscored | Mean / 2.0 | Distribution |
|---|---|---|---|---|
| 8B | 73 | 0 | 1.096 | {'0': 33, '2': 40} |

> **The `8b` values arm is self-judged** — the judge and the model under test are the same weights. Disclosed per `values_rubric.md` §5.

## Human cross-check agreement

**Not available — not started.** B5: no blind sample exists yet. A human must score the 15 items; this cannot be delegated to a model.

## Limitations

1. **n=36 is small.** A detectable paired change needs 6 improvements with zero regressions (16.7 pp). A smaller real effect would not be distinguishable from noise here, and this report does not claim one.
2. **Per-category claims are not supportable at n=6.** Only a clean sweep with no regressions reaches p<0.05. Every other category outcome is indistinguishable from chance. The per-category table is descriptive, not inferential.
3. **The improvement was designed on dev (n=84)** and evaluated once on test (n=36). A dev-set delta that fails to transfer is a finding about overfitting to dev, and is reported as one.
4. **LLM-as-judge scoring is subjective**, and the arm where judge and model are the same weights is self-judged.
5. **Dialect scoring is automated word-overlap** (`dialect_scoring_protocol.md`), an approximation of translation quality, and all 30 items carry `validated_by: null` pending a native speaker (B1).

## Reproducibility

- Git commit: `436ba260830af773434675282a2cc897f15d13c9`
- Seed: 42 · Temperature: 0.0 · Prompt version: 1.0
- Sealed test set SHA-256: `df819e8c1582902a23197ed2aa4ab2e9…`
- Raw responses and per-arm metadata: `eval/results/test_run/`
- Machine-readable statistics: `eval/results/final_scores/test_scores.json`

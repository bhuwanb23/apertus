# Improvement comparison

Generated 2026-10-16T05:33:01+00:00 by `fix/validate_improvement.py`.

> ## ⚠️ These are not results
>
> Backend: **mock**, `is_mock=True`.
> Every number in this file comes from the mock backend and is a
> self-test of the harness. Nothing here says anything about Apertus.
> This file exists to be regenerated once a real model is running (B2).

- Model: `8b` (`Apertus`)
- Split: `dev` — **dev only. The 36-item test set is sealed for Phase 4.1 and was not read.**
- Comparison: b → a
- Paired items: 0

## Overall

| | value |
|---|---|
| Baseline accuracy | not measured |
| Improved accuracy | not measured |
| Delta | not measured |
| Items improved | 0 |
| Items regressed | 0 |
| Net item movement | +0 |
| McNemar p | 1.0 |
| Distinguishable from noise | no |

At n=0 a detectable effect needs about 6 net item flips. This run moved +0.

## By category

One item in a 14-item category is **7.1 pp**, so every value below moves in steps of 7.1.

| Category | Before | After | Delta | Improved | Regressed | Net | p | Status |
|---|---|---|---|---|---|---|---|---|
| _no paired items - nothing was compared_ | | | | | | | | |

Status is the exact paired McNemar test on that category's discordant
pairs, not a comparison of percentages and not a net sum. A category can
move a long way and still be indistinguishable from chance, because every
gain and every loss cancels in the net.

## By difficulty

| Difficulty | n | Before | After | Net items |
|---|---|---|---|---|

## Limitations

- Dev split only (84 items). The 36-item test set is sealed for Phase 4.1 and was not read by anything in this sub-phase.
- 70B was not measured (B3), so there is no claim that the effect holds across model sizes.
- **All figures are mock-backend self-tests and describe the harness, not the model.**
- Per-category n is 14, so one item is 7.1 pp. Category-level claims are not supportable at this sample size.
- The overall delta of +0 net items is below the 6-item floor for n=0, so this comparison separates neither a real effect from noise nor the reverse.
- Retrieval recall for the RAG arm is reported in `fix/rag/RESULTS.md` and is model-free ground truth; it is not affected by the mock backend.


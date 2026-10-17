> **Record of the dev split at n=84 — superseded as a current measurement.**
> The dev split has since been rebuilt at **210 items** (stratified 70/30,
> 15 sealed items per category) and has **not** been re-run. Every number
> below therefore describes the previous corpus and must not be quoted as a
> current result. The current evidence is the sealed n=90 pair in
> `results/test_run/` and `results/final_scores/statistical_report.md`:
> baseline **51.1%** (46/90) → RAG **86.7%** (78/90), **+35.6 pp**,
> 34 improved / 2 regressed, p<0.001.

# Improvement comparison

Generated 2026-10-16T07:55:33+00:00 by `fix/validate_improvement.py`.

- Model: `8b` (`apertus-v1.5-8b-text-q4_k_m`)
- Split: `dev` — **dev only. The 36-item test set is sealed for Phase 4.1 and was not read.**
- Comparison: paired control (no context) → paired treatment (rag, top_k=3)
- Paired items: 84

## Overall

| | value |
|---|---|
| Baseline accuracy | 48.8% |
| Improved accuracy | 83.3% |
| Delta | +34.5 pp |
| Items improved | 34 |
| Items regressed | 5 |
| Net item movement | +29 |
| McNemar p | 0.0 |
| Distinguishable from noise | yes |

At n=84 a detectable effect needs about 6 net item flips. This run moved +29.

## By category

One item in a 14-item category is **7.1 pp**, so every value below moves in steps of 7.1.

| Category | Before | After | Delta | Improved | Regressed | Net | p | Status |
|---|---|---|---|---|---|---|---|---|
| geography | 57.1% | 92.9% | +35.8 pp | 5 | 0 | +5 | 0.0625 | within noise |
| health | 50.0% | 85.7% | +35.7 pp | 6 | 1 | +5 | 0.125 | within noise |
| history | 42.9% | 92.9% | +50.0 pp | 8 | 1 | +7 | 0.0391 | improved |
| law | 21.4% | 64.3% | +42.9 pp | 8 | 2 | +6 | 0.1094 | within noise |
| politics | 64.3% | 78.6% | +14.3 pp | 3 | 1 | +2 | 0.625 | within noise |
| services | 57.1% | 85.7% | +28.6 pp | 4 | 0 | +4 | 0.125 | within noise |

Status is the exact paired McNemar test on that category's discordant
pairs, not a comparison of percentages and not a net sum. A category can
move a long way and still be indistinguishable from chance, because every
gain and every loss cancels in the net.

## By difficulty

| Difficulty | n | Before | After | Net items |
|---|---|---|---|---|
| easy | 18 | 50.0% | 88.9% | +7 |
| hard | 24 | 54.2% | 83.3% | +7 |
| medium | 42 | 45.2% | 81.0% | +15 |

Net movement by difficulty ranges from **easy (+7)** to **medium (+15)**. A flat profile means the effect is not
concentrated in one band of question difficulty; a profile that only
moves easy questions would suggest the context is restating what the
model already had rather than supplying something it lacked.

## Limitations

- Dev split only (84 items). The 36-item test set is sealed for Phase 4.1 and was not read by anything in this sub-phase.
- 70B was not measured (B3), so there is no claim that the effect holds across model sizes.
- Per-category n is 14, so one item is 7.1 pp. Category-level claims are not supportable at this sample size.
- The overall delta of +29 net items is at or above the 6-item floor for n=84, which is detectable at this n, so the effect is separated from noise.
- Retrieval recall for the RAG arm is reported in `fix/rag/RESULTS.md` and is model-free ground truth; it is not affected by the mock backend.


# Phase 2 — Baseline State

**Generated:** 2026-10-12 · **Backend:** `mock` · **Status: pipeline complete, no real
numbers yet.**

> ## ⚠️ Nothing in this document is a result
>
> Every figure below was produced by the **mock backend** — a deterministic
> offline stand-in whose answers are a hash of the prompt. It exists to prove
> the harness end to end, and every artefact it touches is stamped
> `is_mock: true` and printed with a `*** MOCK ***` banner.
>
> `python src/eval/baseline_report.py` **refuses to certify these** — it exits
> non-zero with `NOT a result (mock)` for both models. That refusal is the
> intended behaviour, not a bug.
>
> Real baselines require **B2** (local Apertus-8B) and **B3** (a 70B route).

---

## What exists and works

| Sub-phase | Code | Tests | Live numbers |
|---|---|---|---|
| 2.1 Eval architecture | ✅ | 9 checks + wire-format proof | — |
| 2.2 Knowledge scoring | ✅ | 9,928 checks | 🔒 B2, B3 |
| 2.3 Values judge | ✅ | 225 checks | 🔒 B2, B3, **B5** |
| 2.4 Dialect scoring | ✅ | 515 checks | 🔒 B2, B3 |
| 2.5 Baseline runs | ✅ | 41 checks | 🔒 B2, B3 |

**10,709 automated checks** across four suites, plus the Phase 1 dataset
verifiers and a byte-identical rebuild of `knowledge_all/dev/test.json`.

---

## The Phase 3 starting point

Produced by `python src/eval/baseline_report.py --models 8b 70b`. The structure is
what matters here; the numbers are hash-derived noise.

```
category                8B         70B     delta
politics               7.1%       14.3%      +7.2
law                    7.1%       28.6%     +21.5
health                35.7%       21.4%     -14.3
geography             21.4%       14.3%      -7.1
services              14.3%       42.9%     +28.6
history                7.1%       28.6%     +21.5
OVERALL               15.5%       25.0%      +9.5
```

Chance is 25%. A real run should be checked against the sanity band in
`eval/baseline_report.py`: **below 20% suggests broken parsing; above 90%
suggests the distractors are no longer plausible.** The table below is in the
correct place — above chance on both — which is the only claim it supports.

Cross-model: `19%` identical answers across 84 items, at
`temp=0.0 top_p=1.0 seed=42 max_tokens=512` and prompt `v1.0` on both.

---

## The nine failure modes from `docs/plans/phase_2.md` §2.5

All nine are mechanised in `eval/baseline_report.py`, and
`eval/test_baseline_report.py` asserts each one **actually fires** on a
synthetic broken run. A validation tool that cannot fail is decoration.

| # | Failure mode | Detection | Status |
|---|---|---|---|
| 1 | All answers are "A" | >70% of predictions on one letter | ✅ verified to fail |
| 2 | Parse error rate >20% | `FAIL` above 20%, `WARN` above 10% | ✅ verified |
| 3 | 70B times out | `api_errors` counter, hard `FAIL` | ✅ verified |
| 4 | Scores too high (>90%) | `WARN` | ✅ verified |
| 5 | Scores too low (<20%) | `WARN` | ✅ verified |
| 6 | 8B and 70B identical | agreement %, reported not hidden | ✅ verified |
| 7 | Judge gives all 2s | >85% on one score | ✅ verified |
| 8 | Judge gives all 0s | >85% on one score | ✅ verified |
| 9 | *(not in the plan)* mock contamination | `is_mock` stamp, hard `FAIL` | ✅ verified |

Checks added beyond the plan, because the project's own failure modes needed
them: **mock contamination**, **the sealed test split being touched**,
**divergent evaluation conditions between models**, **rows lost in
aggregation**, **a missing category in the breakdown**, and **judge
circularity**.

---

## What the run flagged on the current mock baseline

| Warning | Meaning |
|---|---|
| parse error rate 13–14% | mock noise — the mock emits refusals on purpose |
| accuracy 15.5% < 20% | mock noise |
| DSG pairs 9/10 | **real** — VP001's English baseline scored zero coverage, so `depth_ratio` is undefined. Phase 4 must report `DSG_mean` over n=9 |
| judge circularity on 70B | **real** — the 70B run judges itself. Must be disclosed with the audit rate |
| dialect MCQ parse errors 1–2 | mock noise |

Two of these survive into the real run and need handling, not fixing.

---

## To produce a real baseline

```bash
# 1. one-time: get the model running (see eval/README.md)
#    HF gate -> Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF -> llama-server on :8080
#    then edit eval/.env: APERTUS_8B_BACKEND=http

# 2. pre-flight
python src/eval/baseline_report.py --pre        # exits non-zero if anything is wrong

# 3. baseline, both models, all three tasks
rm -rf eval/results
python src/eval/run_all.py  --model 8b  --task knowledge
python eval/run_values.py --model 8b
python eval/run_dialect.py --model 8b
python src/eval/run_all.py  --model 70b --task knowledge
python eval/run_values.py --model 70b
python eval/run_dialect.py --model 70b

# 4. read the first responses BEFORE trusting anything
python src/eval/baseline_report.py --models 8b 70b --inspect 10

# 5. if the parse rate is high, diagnose then escalate
python eval/analyse_parses.py
EVAL_KNOWLEDGE_VARIANT=v1_strict python src/eval/run_all.py --model 8b --task knowledge

# 6. the one step only a human can do
python eval/crosscheck.py select --model 8b --interactive
python eval/crosscheck.py verify  --model 8b

# 7. final check - must exit 0
python src/eval/baseline_report.py --models 8b 70b
```

---

## Integrity rules this baseline must keep

- 🔒 `knowledge_test.json` sealed until Phase 4.1. One run. The report hard-fails
  on `split=test`.
- 🔒 Identical `temperature`, `top_p`, `seed`, `max_tokens` and prompt version
  across 8B and 70B. Verified on every report.
- 🔒 `temperature = 0.0` everywhere. Verified on every report.
- 🔒 Prompt changes are made by **variant name**, never by editing a template,
  so a run is never incomparable with an earlier one.
- 🔒 A mock number may never appear in the README, charts or submission. The
  report enforces it.

---

## Known limitations to carry into the datasheet

1. **Judge circularity.** The 70B values run is self-judged. Requires the 20%
   manual audit and a disclosed agreement rate.
2. **DSG over n=9, not n=10.** VP001 is excluded because its English baseline
   achieved zero required-element coverage.
3. **Swiss German detection is partial.** Function-word markers detect 7 of 12
   real Alemannic sentences; the rest are Basel register, caught instead by the
   echo check. See `eval/run_dialect.py`.
4. **Dialect inputs are unvalidated.** All 30 items carry `validated_by: null`.
5. **T1 translation is an automated approximation.** Content-keyword coverage
   cannot distinguish genuine understanding from pattern-matched content words.
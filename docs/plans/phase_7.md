# Phase 7 — Scale to 300 and re-measure

**Goal:** take the knowledge pillar from 120 to 300 items to meet the Track 1B
Core Task Intelligence minimum, then re-measure once and regenerate every
downstream artefact from the frozen results.

**Why:** see [`track_1b_gap_analysis.md`](track_1b_gap_analysis.md).

**Started:** 2026-10-16

---

## Ground rules

1. **Dev-only until frozen.** No work on the sealed half until W1–W3 are done.
   The seal is the one thing we currently have to apologise for; do not give the
   judges a bigger version of that disclosure.
2. **Freeze before prose.** Once W3b lands, every number is fixed. Only then
   rewrite the report (W5c). Never hand-edit a number into a document.
3. **Suites stay green.** Each suite runs as its **own process**:
   `python track_1b/src/eval/test_x.py`. They monkeypatch `config.results_dir`
   at import time, so `pytest eval fix` in one process produces false failures.
4. **Never commit another agent's in-flight files.** `eval/prompts.py`,
   `eval/run_values.py` and `track_1b/src/eval/{prompts,run_values}.py` are
   dirty from a parallel agent (prompt 1.1 language directive).

---

## W1 — Derive the split constants · **blocks everything**

Hardcoded `120`/`84`/`36` will fail the moment the count changes. Make them
derived from `len(questions)` so the next scale-up is free.

| File | Line | Currently |
|---|---|---|
| `src/scripts/build_knowledge.py` | 33 | `assert len(questions) == 120` |
| `src/scripts/build_knowledge.py` | 34 | ids must be `K001..K120` |
| `src/scripts/build_knowledge.py` | 83 | `assert len(dev) == 84 and len(test) == 36` |
| `src/scripts/verify_knowledge.py` | 134 | `expected 120 questions` |
| `src/eval/seal.py` | 69 | `EXPECTED_N = 36` |
| `src/eval/statistical_report.py` | 361 | `n_expected: int = 36` |
| `src/eval/statistical_report.py` | 475 | prints "WHAT n=36 CAN SUPPORT" |
| `src/eval/baseline_report.py` | 92 | `"dev+test = all 120"` |
| `src/eval/baseline_report.py` | 212 | `n={total}/84, expected` |
| `src/run.py` | 44 | `expected 36 results` ← **judge-facing Docker gate** |
| `src/fixtures/published_claims.json` | — | `knowledge_test_n: 36` and friends |
| `src/fix/test_improvement.py` | 85,154,217 | `n_items == 84`, `* 84` |
| `src/fix/test_phase4.py` | 152,182,721 | `n_questions == 36`, `EXPECTED_N == 36`, `len(sealed) == 36` |
| `src/fix/test_validation.py` | 457,461 | 84-based CV arithmetic |
| `src/eval/test_baseline_report.py` | 70 | `"n_questions": 84` |

**Done when** `python src/scripts/build_knowledge.py` still reproduces an 84/36
split from the current 120 items, and all 12 suites pass unchanged.

```bash
for s in eval/test_baseline_report eval/test_dialect eval/test_judge \
         eval/test_knowledge_scoring fix/test_charts fix/test_error_taxonomy \
         fix/test_narrative fix/test_select_target fix/test_improvement \
         fix/test_phase4 fix/test_statistics fix/test_validation; do
  python track_1b/src/$s.py 2>&1 | tail -1
done
```

## W1b — Prove the scale works before authoring · **do not skip**

Temporarily point the derived constants at 300 with the current 120 items
expected to fail the count gate, and confirm the **only** failures are count
assertions — not logic errors. Then revert the data.

**Done when** every failure is a count mismatch, never a scoring or I/O error.

## W2 — Author +180 items · **longest pole, start first**

30 more per category, drawn from the ~420 declared-but-unused facts in
`data/sources/source_registry.csv`.

Rules:
- Every item must carry a real `source_quote` that `verify_knowledge.py` matches
  against `data/sources/raw_pages/`. No quote → no item.
- Distractors must be plausible and **wrong**, preferring real
  neighbouring-jurisdiction answers.
- Cap items per source; require ≥2 distinct question types per source so the
  set does not go formulaic.
- Prefer sources with high declared `fact_count` that we barely touched.

**Done when** `verify_knowledge.py` reports 0 errors and
`build_knowledge.py` asserts 300 with a 210/90 split.

## W2b — Scale the contamination traps

The known-bad-fact traps are our most defensible Category 2 level-10 signal
(contaminated prompt scored 0/84 vs 30% for a fact-list prompt). They currently
cover only a handful of items. Extend them across the new items and categories.

## W3 — Re-split, re-seal, re-gate

1. `build_knowledge.py` → 210 dev / 90 test
2. Re-freeze `src/eval/seal/knowledge_test.sha256`
3. Re-run the contamination gate
4. Update `seal.EXPECTED_N`

## W3b — One-shot sealed measurement

Iterate on **dev only** until satisfied. Then open the 90 test items exactly
once per arm:

- baseline
- BM25 RAG, `top_k=3`

Target: **2 seal opens total**, against the current 30.

## W4 — Human agreement worksheets · **user task**

Mandated by the brief: 20% of judgements, human-scored, agreement reported.

- [ ] **18** sealed-test knowledge judgements
- [ ] **15** values items — worksheet already exists:
      `eval/results/crosscheck/values_8b_B5_worksheet.md` (all `manual_score`
      currently `null`, judge scores hidden)

`python eval/crosscheck.py verify --model 8b` computes the agreement rate.

## W5 — Regenerate everything from the frozen result

- [ ] `statistical_report.py` → new CIs, McNemar, power at n=90
- [ ] `test_scores.json`
- [ ] 4 charts
- [ ] narrative `findings.md` — **and reconcile the seal-open count against
      `eval/seal/access.log`, which has drifted repeatedly**
- [ ] `fixtures/*` + `published_claims.json`
- [ ] `DATASHEET.md`
- [ ] 6-page PDF (rebuild — currently exactly at the limit)
- [ ] HF dataset

## W5b — Close the remaining spec gaps

- [ ] Add ISO-639-3 **glottocodes** to dialect items (gsw/wae/roh/lmo/frp)
- [ ] Consent-form template, or a documented N/A justification, for Category 3

## W5c — Rewrite the report around the new number

`technical_report.md` must state: the use case and why it matters, dataset
design and its match to the use case, construction method, results, limitations,
and the non-determinism caveat. **The 86.1% figure must not survive anywhere
unless it is still what the measurement says.**

## W6 — Verify the judge-facing path

```bash
cd track_1b
docker compose build
make run          # must recompute the NEW published claims and exit 0
```

## W7 — Final freeze

- [ ] Seal count in `findings.md` matches the log exactly
- [ ] 12/12 suites green, each in its own process
- [ ] `git status` shows no unintended files
- [ ] Commit, then tag the freeze

---

## Status log

| Date | W | Outcome |
|---|---|---|
| 2026-10-16 | W0 | Plan + gap analysis written |
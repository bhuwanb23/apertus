# Phase 4.1 — the sealed run: machinery, and what it cost

**Status: built and tested. NOT RUN. The one-shot rule has not been spent.**

Built 2026-10-13. `python fix/test_phase4.py` — **99 checks, all passing.**

---

## ⛔ Why nothing has been run

`eval/.env` still has `APERTUS_8B_BACKEND=mock` and `APERTUS_70B_BACKEND=mock`.
No model has ever run against this harness.

Phase 4.1 evaluates the sealed 36-item test set **once**. Running it against a
mock backend would spend the single unrepeatable evaluation of the whole project
on synthetic responses. `run_test_final.py` refuses on that ground and the
refusal is a named check, not a warning.

Model access is being arranged manually. Everything else is ready.

```bash
# when the 8B is live:
#   1. eval/.env:  APERTUS_8B_BACKEND=http
#   2. git add -A && git commit -m "Phase 4: final test run"
#   3. python eval/seal.py freeze          # freeze the improvement (Golden Rule 4)
#   4. python eval/run_test_final.py --preflight     # must be all PASS
#   5. python eval/run_test_final.py
```

The 70B arm (B3) can be added later with `--only`; the knowledge arms are the
ones the plan requires in pairs.

---

## ⚠️ Seven recorded accesses to the sealed set — all from this project's own tests

`eval/seal.py audit` is reproduced exactly as it stands:

```
2026-10-13T16:47:04+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
2026-10-13T16:48:43+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
2026-10-13T16:48:43+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
2026-10-13T16:48:48+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
2026-10-13T16:48:48+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
2026-10-13T16:59:22+00:00  user  git=076f3f74      test-run knowledge/8b/baseline
2026-10-13T16:59:22+00:00  user  git=076f3f74      test-run knowledge/8b/baseline
```

Seven, not one — and not the five first reported. The count grew while the bug
was being fixed, which is exactly what a hand-maintained note gets wrong and a
log cannot.

| entries | cause | read the sealed set? |
|---|---|---|
| 1 (16:47) | **the bug** — `run_one()` called directly, unguarded | **yes**, all 36, against mock |
| 4 (16:48) | my follow-up test runs, before the guard was stubbed out of the path | **yes**, all 36, against mock |
| 2 (16:59) | the resume test with a stubbed dispatcher | **no** — fake dispatch, temp dir |

**Root cause of the first five.** `run_test_final.run_one()` had **no gate of its
own** — the pre-flight lived in `main()`. Any caller that did not go through
`main()` was unguarded, and the test suite was exactly such a caller.

**Aftermath:**

- The mock artefacts are deleted. `eval/results/parsed/` holds only
  `knowledge_8b_dev_base.json`; `eval/results/test_run/` does not exist. No
  derived file from any of the five survives anywhere.
- The sealed file was never modified. Its SHA-256 is unchanged and
  `seal.py verify` passes.
- **All seven audit entries were kept.** Removing them would defeat the only
  mechanism that caught this. A log that can be tidied is not an audit.
- `run_one` now calls `guard()` itself, putting the refusal at the point of use.
  `fix/test_phase4.py` §6b asserts a direct call is refused, makes zero model
  calls, writes zero files, and **logs no access**.
- The test suite now redirects `seal.AUDIT_PATH` to a temp file. The last two
  entries are exactly that problem: a test access indistinguishable from a real
  one. A log that fills with noise stops answering the question it exists to
  answer.

**The real shot is unspent.** The first five produced synthetic responses nobody
can cite, and nothing from them exists. But the accesses happened and they are on
the record.

This is the argument for the audit log. Without it the first run would have
succeeded, produced a plausible-looking table at 27.8%, and been quoted. The log
turned a silent contamination into a two-line fix — and it is also what made it
impossible for this document to quietly under-report the count.

**Before the real run, the log should be reset** — `mv eval/seal/access.log
eval/seal/access.log.preflight-incident` — so the record of the actual evaluation
is clean. The incident log is kept alongside it, not instead of it.

---

## What was built

### `eval/seal.py` — makes "one shot" enforceable

A rule in a checklist is broken by accident, at 2am, the day before a deadline.
So it is mechanical in three parts:

1. **A hash.** SHA-256 of `knowledge_test.json`, recorded. A single changed
   character invalidates every number produced from the old file.
2. **An audit log.** Every read appends a line: timestamp, pid, actor, git hash,
   reason. Append-only, survives corruption, and attributable. This is what
   caught the accident above.
3. **A freeze.** The git hash of the improvement is recorded and checked before
   every run — **Golden Rule 4**, the rule that forbids changing the fix after
   seeing the numbers, which in practice means changing it between reading them
   and re-running.

It does not pretend to stop anyone running `cat`. No local mechanism can, and
one that claimed to would be false assurance. It makes the access *recorded*.

### `eval/run_test_final.py` — 8 runs, resumable

`knowledge_{8b,70b}_{baseline,improved}`, `values_{8b,70b}`,
`dialect_{8b,70b}`.

**Pre-flight: 13 checks, all reported at once.** Blocking: mock backend, seal
mismatch, wrong question count, improvement not frozen, moved HEAD, dirty tree,
non-zero temperature, missing corpus, no disk space. Non-blocking: an already
recorded run (so interrupted runs stay resumable).

**Resume.** A crashed arm restarts alone; completed arms are never redone.
`--resume` continues, `--accept-rerun` deliberately redoes and is recorded.

---

## Four corrections to `docs/plans/phase_4.md`

### 1. The plan's runner would have broken Golden Rule 3 by construction

Golden Rule 3 is "identical conditions to Phase 2 — same parsing code". The
plan's `run_test_final.py` reimplements everything, and each reimplementation
silently diverges:

| Plan's runner | What breaks |
|---|---|
| `extract_answer(text)` with no `options=` | Exact option-phrase matching and the paraphrase ladder never run. Phase 2 scored dev with `explain_answer(text, options=...)`. Test numbers computed differently are **not comparable to dev numbers** — which is the entire point of a held-out set. |
| `predicted != "PARSE_ERROR"` compared inline | The parse-failure rate is invisible, though Phase 2 tracks it separately and `baseline_report.py` hard-fails above 10%. |
| bare `judge_response(...)` | Bypasses `score_from_observations`, which is where `values_rubric.md` §2/§5 are actually applied. |
| dialect branch saves `model_response`, unscored | Discards `data/dialect/dialect_scoring_protocol.md` entirely — a module built over Phase 2.4. |
| `"improvement_method": "RAG over 30 official Swiss sources"` | The corpus is **100 sources / 189 non-dialect chunks**. A wrong provenance string in the definitive metadata is worse than none. |

So this runner calls `evaluate_knowledge`, `evaluate_values` and
`evaluate_dialect` — the functions that produced every Phase 2 number — and adds
only what Phase 4 needs. `fix/test_phase4.py` §5 asserts the Phase 2 functions
are imported and that the runner never calls `extract_answer` or
`judge_response` itself.

### 2. The sanity check needed two more failure modes

The plan flags 0% and 100%. Two were added, both because this project has
already hit what they catch:

- **A score at chance.** A broken parse path still returns `ok=True` for every
  request, so "the API worked" is not evidence the run worked. A four-option
  benchmark answered at chance means the answers are not being parsed. The
  chance level is **computed from the data** — an earlier hardcoded 35%
  threshold flagged a healthy 26.7% run as broken.
- **A constant prediction.** A model answering "A" to all 36 questions scores
  25%, looks entirely plausible in a table, and is wrong.

Ten cases verified: three healthy runs pass unflagged, seven failure modes are
caught.

### 3. The "improved" arm is retrieval only

The Phase 4.1 improved arm applies RAG. It does **not** apply the 3.3a system
prompt — that prompt is behavioural-rules-only, and `fix/rag/RESULTS.md`
documents that choice. `IMPROVEMENT` records which, so a reader of
`run_metadata.json` cannot mistake one for the other.

### 4. The expected result is "no change"

Phase 3.4 found **no detectable effect** on dev (15 improved / 10 regressed,
p = 0.42). So the improved arm is expected to **match** baseline on test.

That is a legitimate, reportable outcome and Golden Rule 4 forbids reacting to
it. It is also not a reason to skip the arm: "RAG did not help this model on
this benchmark, and here is the paired test showing why" is a stronger finding
than a favourable number with no uncertainty attached.

---

## Still open before 4.1 can run

| # | Blocker | Owner |
|---|---|---|
| **B2** | Apertus-8B on a live backend | **You** — `APERTUS_8B_BACKEND=http` |
| **B3** | 70B route (values/dialect arms, and the 70B-vs-8B comparison) | **You** |
| **B5** | Human scores the 15 blind cross-check items | **You** — not delegable |

B5 matters here: the values arm's judge is the 70B, and for the 70B arm the judge
**is the model under test**. That is self-judging, it is disclosed per
`values_rubric.md` §5, and the agreement rate against the human sample goes in
the writeup.

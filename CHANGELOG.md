# Changelog — Swiss Reality Check, Track 1B

Every entry is a change that altered the submission's evidence, not its wording.
The governing rule: **a number that is stated anywhere must be derived from the
artefacts it describes.** Most of the work below exists because that rule was
violated and the violation was found by a scan rather than by reading.

---

## The headline change

| | Before (superseded) | After (current) |
|---|---|---|
| Corpus | 120 MCQs | **300 MCQs** (50 per category) |
| Distinct sources | 55 (of a 100-source harvest) | 55 |
| Split | 84 dev / 36 sealed | **210 dev / 90 sealed** |
| Answer letters | 30/30/30/30 | **75/75/75/75** |
| Detection floor (overall) | +16.7 pp | **+6.7 pp** |
| Detection floor (per category) | +16.7 pp at n=6 | **+40.0 pp at n=15** |
| Sealed baseline | 55.6 % (20/36) | **51.1 % (46/90)** |
| Sealed BM25 RAG k=3 | 86.1 % (31/36) | **86.7 % (78/90)** |
| Delta | +30.6 pp, CI [+13.1, +30.6] | **+35.6 pp, CI [+25.1, +39.5]** |

---

## Open-ended factuality arm (new)

The brief asks submissions to *"measure factuality and hallucination rates"* and to
use *"SimpleQA-style three-way grading (correct/incorrect/not attempted) against
ground-truth references using LLM-as-a-judge"*. None of that existed: every arm
scored only what the model got **right**, and multiple choice cannot score what it
gets wrong, because with four options a confident fabrication and an honest refusal
both score zero. The new arm removes the options and grades against each item's
verified source sentence.

**Sealed n=90, same weights, same seed:**

| Arm | factuality | hallucination | abstention | c / i / n-a |
|---|---|---|---|---|
| Open-ended, no context | 43.8% | **56.2%** | 46.7% | 21 / 27 / 42 |
| Open-ended, BM25 RAG | **87.4%** | **12.6%** | 3.3% | 76 / 11 / 3 |

Paired: 56 answers became correct against 1 lost (net +55, McNemar p<0.001),
`newly_abstained = 0`, 39 answers moved *out* of refusal.

**What this changes about the headline.** The 51.1% multiple-choice score is real
and also incomplete: asked to answer unaided, this model invents an answer on
56.2% of the questions it attempts and declines 42 of 90. Multiple-choice accuracy
overstates what it knows, because the options guarantee it always has something to
answer with.

**`newly_abstained` is reported beside the gain on purpose.** A retrieval arm can
lower its hallucination rate simply by declining more — arithmetically identical
to improving, behaviourally worse. Here the entire reduction comes from answers
becoming *right*, with nothing new abstained.

### Dataset changes
- Added four derived fields to all 300 knowledge items: `answer`,
  `answer_variations`, `answer_type`, `reference`.
- **`answer` is derived, not authored**: it is `options[correct_answer]`, so it
  cannot drift from the key. The suite asserts equality across all 300 items.
- `answer_variations` is present on 297/300; the three without are bare numbers
  (`58`, `67%`, `7`) where a paraphrase would be ambiguous.
- `reference` is identical to `source_quote` by construction, kept under its own
  name so the grader has an explicit reference.
- **The 90-item seal was re-recorded** after a field-level equivalence check proved
  all 90 ids and all 10 pre-existing scored fields byte-identical, with the four new
  fields purely additive. Reason recorded in the seal's own audit entry.

### Bugs the arm surfaced and fixed
- **Abstention misclassified a real answer as a refusal.** A real reply asserts an
  answer and *then* hedges ("…I don't know if there is a specific official role
  beyond that"). The original regex matched the trailing hedge, which would have
  deleted genuine attempts from both the factuality and hallucination denominators
  — making hallucination look better with no change in model behaviour. Now a
  refusal counts only when it opens the reply or the reply is short. The offending
  reply is a regression test.
- **`parse_judgement` crashed** on a judge reply containing neither `CORRECT` nor
  `INCORRECT`, aborting the run instead of degrading one item. Now falls back to
  INCORRECT one-directionally, so a judge failure can never manufacture a good
  result.
- **The option-leak guard rejected legitimate retrieved context** containing the
  correct answer. Retrieval surfacing the answer is the point of the arm, and the
  MCQ arm does the same. The guard now checks only the prompt scaffolding outside
  the context.
- **Regex missed `I'm not sure`** (contraction has no space before the
  apostrophe), silently missing every contraction-form refusal.
- Replies were truncated mid-sentence at `max_tokens=64`, so the judge graded
  fragments. Raised to 128.

### Honest limits, disclosed on every artefact
- The judge is the same Apertus 8B under test — **self-judged**.
- Mitigations: abstention fixed by rule before the judge is called; the suite
  asserts the judge reaches both verdicts on the sealed set (a judge stuck on
  CORRECT would report a hallucination rate of exactly 0.0%); a probe confirmed it
  separates a true answer from a distractor 12/12.
- **20% human cross-check sheet prepared and unscored** (17 RAG / 9 baseline
  stratified verdicts). No agreement rate is claimed.
- Baseline factuality rests on the 48 questions it attempted, not all 90.
- `answer_variations` captures acceptable phrasings of a *known* answer, not
  answers the dataset never anticipated.
- The arm reuses the MCQ items, which were selected for a world where distractors
  existed.

### Process incident, disclosed

While wiring this arm in, `src/eval/statistical_report.py` was destroyed by a
PowerShell negative-index bug in a recovery command of mine (`$lines[-1..]` wraps
around instead of erroring), and commit `19308af` captured the resulting 14-line
corrupt file. It was restored from `HEAD~1` and the feature re-applied cleanly;
the suite passes and the report regenerates. No generated artefact had been
written from the corrupt version, and no number in any shipped artefact came from
it. Recorded here because the same class of silent truncation is exactly what the
rest of this changelog exists to catch — it was caught here only because the file
failed to parse.

Two PDF-integrity failures were also caught by existing gates rather than by
inspection, and are worth recording for the same reason:
- Adding the open-ended block as a 7th page tripped the **max-6-pages** gate from
  the brief. The block was folded into page 4 and the redundant per-category
  numeric table (which duplicated Figure 4 and the statistical report) was removed
  to make room. All per-category numbers remain available in two other places.
- The chart and the PDF asset disagreed on `newly abstained` vs
  `newly_abstained`; the asset builder now cross-checks both renderings against the
  SVG on disk and fails if they diverge.
| Paired | 11 improved / 0 regressed, p=0.001 | **34 improved / 2 regressed, p<0.001** |
| Retrieval recall @1/3/5 | 83.3 / 90.5 / 94.0 % | **82.4 / 91.4 / 92.9 %** |
| Categories clearing their own floor | 0 of 6 | **3 of 6** (geography, history, politics) |
| Sealed SHA-256 | `df819e8c…` | **`83c20589e1c5b668…`** |

The previous arms are **kept** at `results/test_run/*.superseded-n36.json` rather
than deleted, so the supersession is auditable. `src/scripts/promote_arm.py`
refuses to promote an arm containing parse errors rather than silently scoring them
as wrong.

---

## 1. Corpus scaled 120 → 300

300 MCQs, exactly 50 per category, all six categories balanced. Every item carries
a verbatim quote traceable to one of 55 distinct official sources; 300/300 verified.
Difficulty 60 easy / 148 medium / 92 hard. Answer letters balanced 75/75/75/75 across
the whole corpus.

*Fixed along the way:* **K108** was marked C (Obwalden) while its own source and notes
said D (Appenzell Innerrhoden). The old baseline had predicted D and was therefore
scored as *wrong* on a correct answer — a false negative that flattered the RAG delta.
**K264** was reframed so its undated 2,110-commune snapshot cannot be confused with
K070's dated 2,121 figure.

`verify_knowledge.py` emits one informational near-duplicate warning (K117/K282).

## 2. Re-split and re-sealed at 210/90

Stratified 70/30 with exactly 15 sealed items per category, which is what makes the
per-category paired comparison possible at all. New seal hash `83c20589…`.

Corpus sizes are now **derived** from the split files throughout the codebase
(`build_knowledge.py`, `seal.py`, `statistical_report.py`, `baseline_report.py`,
`run.py`, `published_claims.json`), which is why a rescale did not require editing
a dozen `assert`s.

## 3. A parser bug was understating the baseline by 26 points

Served completions ended with an end-of-turn marker rendered as visible text. The
parser did not recognise the marker unless it was pipe-terminated, so **49 of 90**
sealed baseline answers came back `PARSE_ERROR` and were scored as wrong. The raw
baseline was **27.8 %**, not 51.1 %.

`strip_control_markers()` now handles the marker without a closing pipe. Rescoring
from the saved raw responses — no new generation — gives 0/90 parse errors and
**51.1 %**.

This is why the new baseline (51.1 %) is *lower* than the old one (55.6 %) despite a
corpus 2.5× larger, and it is the single most important correctness fix in this
changelog: the previous headline was partly measuring a parser, not a model.

## 4. Both arms now come from one paired invocation

The control and RAG arms are produced by a single `run_rag_eval.py` run, so they
share one generation context. A McNemar test assumes both arms saw the same
questions under the same conditions; taking the control from a separate run is
exactly the confound the pairing exists to rule out.

## 5. The stale-figure class of bug, and the systematic fix

A repo-wide scan for the previous numbers returned **223 hits**. Most were
legitimate — historical plan records, comments explaining the old values, test
fixtures, the deliberately-archived n=36 arms. But the *live* ones were severe:

- the submitted **6-page PDF** carried the whole n=36 headline table;
- the **dataset card** published to Hugging Face carried it too;
- the chart annotation and the retrieval subtitle said **94 %** recall and
  **n=84 dev items** when the real figures were 92.9 % and 210;
- the narrative still reported the detection floor for n=36;
- the narrative selected scenario **"pending"** because it had no model results to
  read — it now selects **"A — Strong improvement"**.

**The fix is structural, not editorial.** `src/scripts/submission_numbers.py` is now
the single loader for every number a submission asset prints; `retriever.recall_figure()`
is the single source for retrieval recall. Both submission builders, both chart
annotators, the narrative and the dataset card read from them. Hardcoding a figure
in an asset is no longer possible without editing a loader.

Two follow-on bugs were caught by scanning the *rebuilt* PDF for `{PLACEHOLDER}`
tokens, which found 12 string literals that had been given `{...}` references without
being converted to f-strings — i.e. the PDF was about to ship literal
`{BASE_ACC}` to a judge.

## 5a. Two defects found while making the figures right

**A freeze that could never be committed.** `check_freeze()` required the recorded
`git_hash` to equal `git rev-parse HEAD`. But committing `frozen_code.json` *is* a
commit — so committing the freeze record immediately invalidated it, and the seal
could be recorded but never committed. `tree_hash()` now hashes the git index with
`src/eval/seal/` excluded: invariant under committing the record, still changing
whenever real code is committed. `git_dirty()` already covered the other half
(uncommitted working-tree edits), so the pair checks both.

This was pre-existing, not caused by the rescale. It surfaced because the freeze
genuinely had to be advanced, which is the first time anyone tried to commit one.

A first attempt at the fix was itself wrong: written as
`f":!{_seal_prefix()}rstrip('/')"`, the trailing call became literal text, the
pathspec excluded nothing, and `tree_hash` stayed sensitive to the very file it
was meant to ignore. Caught by asserting the invariant directly — *editing a seal
file must not change the hash* — rather than by reading the code.

**Tests that asserted the old constants.** Six checks across `test_charts.py`,
`test_narrative.py` and `test_phase4.py` hardcoded `detectable(36)`,
`detectable(6)`, `wilson_ci(0, 6)`, or the literal `"undetectable at n=36"`. These
are the same defect as a stale chart: they fail for the wrong reason the day the
corpus is rescaled, and they cannot distinguish *the chart is right* from *the chart
matches a stale constant*. All six now derive their expectations the same way the
code under test does, so they assert **agreement between two independent
derivations** rather than agreement with a number typed before the rescale.

The `test_phase4` case was the weakest of the six: it wrote a bogus `git_hash` while
a valid `tree_hash` was present, so it was not testing the thing it claimed to test.
It now perturbs each field in turn and requires a block from each.

## 5b. The build was broken on two platforms

Validating `make` end-to-end turned up defects on the judge-facing path, none of
which pointed at itself.

### `make run` — the target judges execute — crashed on its first line of work

Every module in `src/` locates the project root by walking up until it finds a
directory holding **both** `data/` and `Makefile`. That marker appears in **43
files**. The Dockerfile copied `src/` and `data/` but **not** `Makefile` and
**not** `results/` — so inside the container every one of those modules raised
`StopIteration`.

It went unnoticed because the compose file mounted `./:/app:ro`, which brought
the missing files in by accident. That mount was itself wrong twice over:

- it **shadowed everything the image COPYed**, so the container tested the
  judge's working tree rather than what it ships;
- being read-only, it also prevented `run.py` from writing `results/` at all —
  and the regeneration steps are the entire point of the offline run.

The image now carries `Makefile`, `results/` and the top-level docs; the run is
hermetic with no bind mount, and `make run-mount` is the opt-in bind-mount
workflow.

`src/scripts/test_dockerfile.py` is a **new suite** that asserts the image
contains every root-marker and evidence file, that compose does not shadow them,
and that the API key interpolates — so this cannot regress silently.

### `APERTUS_8B_API_KEY` was read from `${LLM_API_KEY}`

The shell expands that to empty, so a live-model run was sent with **no key** and
failed at request time with an auth error pointing nowhere near the compose file.

### The Makefile did not run at all on Windows

| Symptom | Cause |
|---|---|
| `make test` → *"The system cannot find the path specified."* | `PYTHON ?= python3`, and on a default Windows install `python3` is a **Microsoft Store alias stub**: on PATH, not a Python, and it fails with a message about a missing path |
| `make test` unusable without Git Bash | the suites ran in a `set -e` / `for` shell loop |
| a failing suite printed **nothing** | output went to `>/dev/null 2>&1`; you saw only an exit code |
| `make verify-test` did nothing and **exited 0** | declared `.PHONY` with **no recipe** — the worst failure mode available to a check whose purpose is to stop a run |
| `make help` → *"cannot find the file specified"* | it printed `make PYTHON=python <target>`; on a Windows shell `<target>` is **input redirection** |
| `make clean` Linux-only | used `rm -rf` and `find -exec` |
| `make run` → confusing named-pipe error | `docker-check` verified the docker **binary**, not the **daemon**, so it passed with Docker Desktop closed |

Every recipe is now a single command, so the file depends on no shell at all. The
interpreter is probed rather than assumed; a real interpreter answers `--version`
with a version and the stub does not, which `$(findstring)` can distinguish. When
`PYTHON=python3` is requested *explicitly* and is broken, the failure is raised
with `$(error)` at parse time — `check_interp.py` would otherwise have to run
through the very interpreter it was reporting on.

`make help` also derives the suite count from `run_suites.py` rather than stating
it. A stated count that is not derived from the list is the same defect as a
hardcoded figure in a chart.

### Validated

| Target | Result |
|---|---|
| `make help` | exit 0, interpreter shown, count derived |
| `make check-interp` | exit 0 |
| `make docker-check` | reports CLI **and** daemon |
| `make verify` | all checks pass |
| `make test` | **14/14** suites, per-suite timing, full failure output |
| `make verify-test` | runs the seal pre-flight (was dead) |
| `make build` | image builds |
| `make run` | **all checks pass inside the container** |
| `make run-mount` | bind-mount workflow passes |
| `make shell` | container starts, `/app/Makefile` present |
| `make clean` | removes artefacts, portable |
| `make PYTHON=python3 …` | refused at parse time with the real cause |

## 6b. Dataset metadata: glottocodes and a consent statement

**ISO 639-3.** All 30 dialect items now carry `glottocode: gsw` (Alemannic) plus a
`language_name`. Without a language identifier the dataset cannot be filtered by
language at all. Basel, Zurich, Bern, Valais and Walser are varieties *within*
Alemannic, not separate languages, so they correctly share one code; the single
item whose variety the source could not place keeps `gsw` and gains
`variety_uncertain`.

Two label defects surfaced while doing it, neither caught by any existing check:

- the public `dialect` field held **raw source spellings**, so `zurich` (3 items)
  and `zürich` (4 items) appeared as two varieties. A per-variety analysis would
  have split Zurich in half and reported it as two findings;
- `orthography` had **two spellings of one string** (9 vs 21 items), so grouping
  by it split a single orthography into two categories.

**Where the fix had to go.** The first attempt was a script editing
`data/dialect/dialect_items.json` in place. It reported 74 changes and wrote the
file — and the next command silently undid all of them, because
`verify_dialect.py` is the **assembler**: it reads the two parts and writes that
file. The file is an *output*, so editing it is the wrong layer; anything applied
afterwards is discarded by the next run, and the check that reported the change
was undone by the very next verification.

Normalisation therefore now lives in the assembler, immediately before the write,
so the artefact is normalised *by construction*. The mapping itself is in
`src/scripts/canonical_dialect.py` so it has one home, and the assembler raises on
an unrecognised label rather than letting it through unlabelled. Output is
verified byte-stable across re-runs.

**Consent.** `DATASHEET.md` §3 now answers consent explicitly rather than leaving
the field blank. No consent was sought because no personal data was collected from
any person — no natural person is a data subject, the dialect corpus is CC BY-SA
Wikipedia text, and the only annotators are the named authors. Each
governance-template requirement is marked *not applicable* with its reason, and the
section separates "not applicable" from the two things that genuinely **are**
outstanding: no native Swiss German validation, and no human audit of the values
rubric. Those are quality gaps, not consent gaps, and are not hidden behind the
table.

The values **annotation template** is now published in the datasheet: the fixed
0/1/2 rubric, what each score requires, and the instruction to judge framing and
institutional competence rather than political position — including the explicit
note that a response arguing for stricter privacy law scores 2 while one stating
which party should win scores 0.

## 7. Power analysis, recomputed

The detection floor is computed, not asserted. At n=90 a paired change needs 6
improvements with **zero** regressions (+6.7 pp). Per category at n=15, only a clean
6/0 sweep is detectable (+40.0 pp) — anything with a regression is undetectable.

Consequence for the write-up: **3 of 6 categories clear their floor**
(geography +46.7, history +40.0, politics +53.3 pp); health, law and services are
reported as *no detectable change*, not as small gains. No category is ranked.

## 7. Official model restored

The official `swiss-ai/Apertus-v1.5-8B` checkpoint was downloaded and converted
locally: `models/Apertus-v1.5-8B-text-Q4_K_M.gguf`, 5.01 GB, served on
`127.0.0.1:8081`→`8080`. `serve_task.cmd` now preflights the model file and fails
loudly instead of restarting every 3 seconds.

## 8. Repository layout flattened

`eval/results/` scratch moved to `results/{raw_responses,parsed,scores,logs}`
(gitignored); published artefacts live in `results/`. `track_1b/` is gone — the
project is addressed from the repository root. This broke
`upload_hf_dataset.py`, which still pointed at `eval/results/final_scores/…` and
silently staged **without** the statistical report and scores; found and fixed.

## 9. Integrity disclosures

- **Seal audit trail is incomplete.** The n=90 seal was frozen at 06:46:56 UTC. The
  log holds 60 entries: 55 predate the freeze (superseded seal), 5 postdate it — and
  **none is timestamped at the 06:59:59 UTC recorded in both archived arms**. The
  headline run is therefore absent from the audit trail, and the 5 post-freeze
  entries are all RAG-side; no `baseline` access to the new seal is recorded.
  Cause: logging was added to the runners *after* they had already been driven
  through them. The log was **not** backfilled. Stated in `technical_report.md` §5.
- **Values are self-judged** (8B judge, no human agreement rate yet).
- **Non-determinism.** Greedy decode at T=0/seed 42 is not bit-exact on GPU.
  Independent values reruns gave mean 1.096 (sealed prompt 1.0) and 1.068.
- **Dialect is unvalidated** — awaiting native-speaker sign-off (B1).
- **Only 8B has results.** No 70B numbers exist anywhere.
- **No dev run exists at n=210.** The dev split grew but was not re-run, so the
  sealed test set is the only current measurement. The dev→test transfer figure is
  therefore *not* drawn; `fig3` renders only the measured arm and says why.

---

## Files touched, by purpose

| Purpose | Files |
|---|---|
| New loaders (stale-number fix) | `src/scripts/submission_numbers.py`, `src/eval/…/retriever.recall_figure()` |
| Arm promotion + guard | `src/scripts/promote_arm.py` |
| Parser fix + seal logging | `src/eval/run_knowledge.py`, `src/eval/rescore.py`, `src/fix/rag/run_rag_eval.py` |
| Derived split sizes | `src/eval/generate_charts.py`, `src/eval/narrative.py`, `src/eval/statistical_report.py` |
| Asset builders | `src/scripts/prepare_submission_assets.py`, `src/scripts/build_submission_pdf.py`, `src/scripts/upload_hf_dataset.py` |
| Corpus | `data/knowledge/*`, `data/sources/README.md` |
| Docs | `README.md`, `technical_report.md`, `DATASHEET.md`, `src/eval/README.md`, `src/fix/rag/RESULTS.md`, `src/fix/comparison.md` (banner), `docs/plans/phase_7.md`, `docs/plans/track_1b_gap_analysis.md` |
| Regenerated | `results/final_scores/*`, `results/charts/*`, `results/narrative/findings.md`, `results/test_run/*`, `docs/submission/**`, `swiss_reality_check_report.pdf` |

## Not done, and why

| Item | Status |
|---|---|
| Human agreement on 18 knowledge + 15 values items | **needs the human** |
| Native Swiss German validation (B1) | **needs a native speaker** |
| ISO-639-3 glottocodes; consent-template / not-applicable docs | outstanding |
| Dev-split run at n=210 | not run — sealed test is the current measurement |
| 70B arms | out of hardware scope (8 GB VRAM) |
| Hackathon submission upload | **needs the account holder** |
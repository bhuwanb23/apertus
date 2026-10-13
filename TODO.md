# TODO — "Swiss Reality Check"

Single source of truth for what is done, what is blocked, and what is next.
Last updated: **2026-10-12** (Phase 2.1 and 2.2 session).

Legend: `[x]` done · `[~]` in progress · `[ ]` not started · `[!]` blocked

---

## 🔴 Blockers — everything else waits on these

| # | Item | Why it blocks | Owner |
|---|---|---|---|
| **B1** | **Native Swiss German speaker** (Discord post) | 1C cannot be authored honestly without one. Also blocks publication of the 53 language renderings — 37 are `author_written_unvalidated`, and `multilingual_pairs_NOTES.md` §6 makes native sign-off a **precondition**, not a nice-to-have. | **You** — async, send today |
| **B2** | **Apertus-8B running locally** | Every real number in Phase 2 needs it. Currently `mock`, so all results so far are pipeline self-tests. | **You** — HF gate + 4-bit GGUF |
| **B3** | **70B access route** | Phase 2.5 baselines, and the 8B-vs-70B comparison that is the whole point of running two models. | **You** — CSCS/Phoenix/HF? |
| **B4** | **Root README + LICENSE** | Plan 0.4. Nothing else is submittable without it. | either |
| **B5** | **Human scoring of the cross-check sample** | The judge-vs-human agreement rate cannot exist until a person scores the 15 blind items. Not delegable to a model. | **You** |

**B2 setup — verified from the HF API on 2026-10-12:**

```bash
# swiss-ai/Apertus-v1.5-8B is GATED: accept license + AUP + privacy policy
# It is the full Omni model: 8.9B params, ~19.4 GB bf16. An 8 GB RTX 5060
# cannot hold it. Use the text-only extract instead - every pillar here is text.
#   Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF   (~5 GB, fits)
./llama-server -m <model>.gguf --host 127.0.0.1 --port 8080 --ctx-size 8192 -ngl 99
# then in eval/.env:  APERTUS_8B_BACKEND=http
```

**B2 also resolved a long-standing question.** Apertus v1.5 **is** multimodal —
vision *and* audio (the repo ships `model-wavtokenizer-*.safetensors` and the
chat template defines `<|audio|>`). `idea.md` §1 and `master_plan.md` 0.2 said to
check and "pivot to text if audio is unsupported". It is supported, so the Phase
1C audio track is **live, not a fallback** — that is a scope decision to take
deliberately, since audio items need real recorded Swiss German.

---

## Phase status

### Phase 0 — Pre-flight
- [x] 0.1 Rules & criteria read into `docs/plans/`
- [~] 0.2 Model access — **harness built and proven; model not yet running (B2, B3)**
- [ ] 0.3 Community & team — **Discord post for a Swiss German speaker (B1)**
- [~] 0.4 Repo scaffold — `eval/` done; **root README + LICENSE missing (B4)**

### Phase 1 — Dataset engineering

**1A · Knowledge MCQs — complete and verified**
- [x] 1A.1 Source harvesting — 55 sources, 472 facts
- [x] 1A.2 Drafting — 120 MCQs, 20/category, difficulty 4/10/6, letters 30/30/30/30
- [x] 1A.3 Verification — `scripts/verify_knowledge.py` passes; 120/120 quotes matched verbatim
- [x] 1A.4 Split — 84 dev / 36 test, seed 42, stratified by (category, difficulty); **test sealed**

**1B · Values & norms — complete and verified**
- [x] 1B.1 Rubric (`values_rubric.md`) — rewritten to score framing, not political position
- [x] 1B.2 Scenarios — 30, 123 required + 105 forbidden elements
- [x] 1B.3 Multilingual pairs — 10 pairs, 53 renderings, 6 languages

**1C · Dialect items — ✅ built; native validation still outstanding**
- [x] 1C.2 Items — 30 items: 12 T1 translation, 8 T2 comprehension, 5 T3
      culture-in-dialect, 5 T4 dialect-identification, from the Alemannic
      Wikipedia harvest. Includes `dialect_scoring_protocol.md` and
      `VALIDATION_PACKET*.md`.
- [x] 1C.3 Scoring protocol — content-keyword coverage + deterministic MCQ;
      implemented and tested in `eval/run_dialect.py`
- [!] Native-speaker validation — **still blocked by B1.** All 30 items carry
      `validated_by: null`, which is correct and must stay until a native
      speaker signs off.
- [x] `dialect_scoring_protocol.md` §4 compliance — per-dialect reporting,
      never pooled; refusal rate is a headline number; `uncertain` register
      (D020) is bucketed separately and excluded from dialect claims

**Carry-forward review flags** (from `knowledge_stats.md`, resolve before Phase 5):
- [ ] `K070` commune count — confirm the item reads unambiguously
- [ ] `K106` motive attribution — weakest of the 120 on the recall-vs-reasoning axis
- [ ] `K038` rental deposit — not Swiss-exclusive; acceptable at `easy`
- [ ] Normalise the S025/S029/S030 commune-count disagreement for the datasheet

### Phase 2 — Evaluation pipeline

**2.1 · Eval architecture — ✅ complete, all 9 checklist items**
- [x] Directory structure, `config.py`, `client.py`, `prompts.py`, `run_all.py`
- [x] `requirements.txt`, `.env` (gitignored), `.gitignore`
- [x] Response persisted to disk; temperature verified `0.0` in the logged request
- [x] `smoke_test.py` — 9 checks, all pass
- [x] `check_http_backend.py` — wire format proven against a stub server
- [x] Three backends: `openai` (SDK) · `http` (stdlib, zero deps) · `mock`
- [x] Mock can never be mistaken for a result (`is_mock` stamped in every artefact)

**2.2 · Knowledge auto-scoring — ✅ code complete, live runs blocked by B2**
- [x] `extract_answer()` + `explain_answer()` (reports which rule decided)
- [x] `scoring.py` with `calculate_knowledge_scores()`
- [x] 20+ edge cases → **9,928 automated checks**, incl. 9,480 generated from the real dataset
- [x] 5-question smoke test on 8B ✅ and 70B ✅ (mock backend)
- [x] `parsed/` and `raw_responses/` artefacts verified
- [x] Category breakdown correctness tested against hand-computed answers
- [x] 40-question early baseline run (mock)
- [x] Parse-error analysis tool + pre-defined prompt escalation ladder
- [x] `rescore.py` — re-score from disk without re-running the model
- [!] **Live 84-question baseline on both models — blocked by B2, B3**
- [!] **<5% parse-error target — blocked by B2.** Cannot be measured on mock.

**2.3 · Values judge — ✅ code complete; audit blocked on a human + live model**
- [x] `judge.py` — judge **observes** element presence; `score_from_observations()` applies the rubric in code
- [x] `run_values.py` — 30 English + 43 pair versions, with per-response language metrics
- [x] `crosscheck.py` — blind stratified sample, agreement report, per-element table
- [x] `language_metrics.py` — refused / reply_lang / register_ok / len_ratio / depth_ratio
- [x] `test_judge.py` — **225 checks**; caught 4 real bugs (see below)
- [x] Judge-model decision → **Apertus 70B for both**, per rubric §5 option 2, **with** the 20% audit
- [x] Judge trialled on 3 scenarios (mock) — scores follow the rubric mechanically
- [x] Full values eval on 8B ✅ and 70B ✅ (mock backend)
- [x] `crosscheck select` → **15 blind items, 0 leaked verdict fields** ✅
- [!] **Human scoring of the 15 audit items — blocked on B5 (below)**
- [!] **Reported agreement rate — cannot exist until a human scores them**
- [!] Rubric revision if agreement < 75% — cannot be evaluated yet

> **B5 (new) — a human must score the cross-check sample.**
> This is not optional and it is not delegable to a model. An LLM filling in
> `manual_score` would produce a number that looks like an audit, would be
> reported as one, and would measure nothing — the same false-provenance
> failure `verify_values.py` hard-errors on. `crosscheck.py` emits a blind file
> with `manual_score: null`, and `verify` refuses to report anything until it is
> filled.
>
> ```bash
> python eval/crosscheck.py select --model 8b --interactive   # guided terminal scoring
> python eval/crosscheck.py verify --model 8b                 # agreement report
> ```
>
> The sample is **15 items, not the 6 the plan assumed**: 20% of the 73 scored
> responses (30 English + 43 pair versions), because rubric §6 requires
> stratifying *by language* — which is only meaningful if pair responses are in
> scope. Shrink with `--fraction` if time is short, but keep every language
> represented.

**2.4 · Dialect scoring — ✅ code complete; real scores blocked on B2**
- [x] `run_dialect.py` implementing `data/dialect/dialect_scoring_protocol.md`
- [x] `score_translation()` — content-keyword coverage, weights, synonym matching
- [x] `test_dialect.py` — **515 checks**; 240 of them are two invariants run on
      all 12 real T1 items (reference→2, dialect-echo→0, gibberish→0, refusal→0)
- [x] Dialect eval on 8B ✅ and 70B ✅ (mock backend)
- [x] Results saved to `parsed/` + `scores/` with full provenance
- [x] Limitations documented — see `eval/README.md` and the module docstring
- [!] **Real dialect scores — blocked on B2**
- [x] Manual comprehension scoring — **NOT NEEDED.** The plan §2.4 assumed
      comprehension needed a human; the author converted T2/T3/T4 to four-option
      MCQs, so three of four item types are fully deterministic and the whole
      pillar is judge-free. Nothing left for a human to score.

> **Phase 2.2–2.4 all validate clean.** 10,668 automated checks across three
> suites, plus the Phase 1 dataset verifiers and a byte-identical rebuild.

**2.5 · Baseline runs — ✅ complete as a system; 🔒 numbers blocked on B2, B3**
- [x] Pre-run checklist — dataset integrity, split seal, config, endpoint reachability, disk
- [x] Early-baseline (bug-catching) run: 40 knowledge questions, 8B
- [x] Full baseline on 8B **and** 70B — knowledge + values + dialect
- [x] Post-run checklist — artefacts, parse rate, api errors, provenance
- [x] Comparison table + weakest-category identification (the Phase 3 starting point)
- [x] **All nine failure modes from `phase_2.md` §2.5 mechanised and verified to fire**
- [x] `test_baseline_report.py` — 41 checks that assert the checks actually fail
- [x] `docs/BASELINE.md` — state, command sequence, integrity rules
- [!] **Real before-numbers — blocked by B2, B3**

> **Phase 2 is code-complete.** 10,709 automated checks across four suites, plus
> the Phase 1 dataset verifiers and a byte-identical rebuild. Every "Done When" is
> met except the parts needing a running model and a human scorer.
> `python eval/baseline_report.py` **refuses to certify mock results** and exits
> non-zero — that refusal is correct behaviour, not a bug.

### Phase 3 — Failure analysis & improvement

**3.1 · Error taxonomy — ✅ built and tested; content blocked on B2**
- [x] `fix/analyze_errors.py` — layered classification engine
- [x] `fix/test_error_taxonomy.py` — **67 checks**
- [x] `fix/error_taxonomy.md` + `fix/weakest_area_analysis.md` (3.2) generated
- [x] Classified data written back with `error_code` per item
- [!] **Populated taxonomy — blocked on B2** (needs a real baseline)

> **Three design decisions that differ from `phase_3.md` §3.1:**
>
> 1. **Parse errors are never counted as model errors.** They are measurement
>    failures. Adding them to the wrong-answer count makes the taxonomy describe
>    the instrument. Reported in a separate row with its own total.
> 2. **An MCQ cannot classify its own errors.** The baseline response is a
>    letter — *"Switzerland's rules differ here, so I would choose A."* says
>    nothing about why A. The plan's classifier prompt would hand that to a
>    model and get a confident DE-CONF/HALLUC/NUMERIC label with no evidence
>    behind it. So errors are re-asked on a **separate diagnostic run** with a
>    reasoning prompt; those records are stamped `diagnostic: true` and are
>    never merged into a score table.
> 3. **`UNCLASSIFIED` is not an error type.** It has no description, no
>    fixability score, and is never reported as the dominant pattern. A
>    category whose errors are unclassified is **not ranked** for a Phase 3
>    fix — 3.2 picks its target from that table.

**3.2 · Weakest-area selection — ✅ engine + decision doc; 🔒 selection blocked**
- [x] `fix/select_target.py` — all five decision questions answered programmatically
- [x] `fix/test_select_target.py` — **96 checks**
- [x] Selection matrix with `error_count` folded into priority
- [x] Hard gates that refuse to name a target on inadequate evidence
- [x] **Q3 (source material) answered now** — 100 sources, 933 facts, 45 dialect files
- [x] **Q5 (measurability) answered now, quantitatively** — see below
- [x] `fix/weakest_area_analysis.md` generated with the full reasoning
- [!] **Pick one target — blocked by B2.** Three gates fire.

> ### 🔒 Why no target is selected
>
> | gate | fires because |
> |---|---|
> | `G1-baseline-is-mock` | every score is a hash of the prompt |
> | `G2-error-taxonomy-unresolved` | 78% of content errors are `UNCLASSIFIED`, so there is no dominant error to route by |
> | `G3-single-model` | the project premise is 8B **vs** 70B; one model is not a target |
>
> A selection made past these is a selection made on noise, and it would send
> 3.3 after the wrong thing for the remaining budget. `--force` overrides, and
> records that it was overridden.

> ### ⚡ The finding that changes how Phase 3 is measured
>
> **Visibility is not significance.** The plan's Q5 asks whether an improvement
> will look dramatic. Before/after on the same questions is a **paired**
> comparison, so only items that flip carry information. Exact McNemar at
> **n=14 per category**:
>
> | improved | regressed | category Δ | p | significant |
> |---|---|---|---|---|
> | 6 | 0 | +42.9 pts | 0.031 | **yes** |
> | 5 | 2 | +21.4 pts | 0.453 | no |
> | 4 | 3 | +7.1 pts | 1.000 | no |
>
> A per-category claim needs **6 of 14 to flip with zero regressions** — and once
> 2 items regress, **nothing is detectable at all** at n=14. At n=84 the same
> net change (+7.1 points overall) reaches p=0.031.
>
> **So: one intervention (golden rule 1), measured on the whole dev set, with
> the category used to find the mechanism — not to carry the significance
> claim.** A RAG fix aimed at one category moves others too, because the corpus
> is not partitioned; restricting the test to that category would discard most
> of the effect *and* most of the power.

**3.3 · Improvement implementation — built and validated, no effect claim yet**
- [x] **0. Contamination gate first** — 30% of dev was in the plan's prompt; see below
- [x] **3.3a** System prompt — `fix/system_prompt/swiss_context_v1.txt`, behavioural rules only, 0/84 contamination
- [x] **3.3b** RAG — corpus → retriever → paired eval; **source recall @5 = 94.0%** (real, model-free)
- [x] **3.3c** LoRA — documented infeasible on an 8 GB card
- [x] `fix/prompts_check.py`, `fix/test_improvement.py` (62 checks), `fix/rag/{prepare_corpus,embeddings,retriever,rag_prompt,run_rag_eval}.py`
- [x] `fix/rag/RESULTS.md`
- [ ] **Re-run all of 3.3 on a real model (B2)** — every accuracy so far is mock

> ### ⛔ The contamination finding that shaped 3.3
>
> The system prompt `docs/plans/phase_3.md` §3.3 Option A proposes asserts
> ~11 Swiss facts verbatim ("26 cantons", "100,000 signatures", "suffrage 1971",
> "Federal Supreme Court is in Lausanne", …). Checking those against the dev
> set: **25 of 84 items — 30% — are directly answered by that prompt.**
>
> So a large part of any measured "improvement" from Option A would be the answer
> key injected into the prompt, not a capability change. Worse, it would not
> transfer: the held-out test set is scored once in Phase 4.1 and the delta would
> not reproduce on questions the prompt does not name.
>
> **Done: the 3.3a prompt carries behavioural rules and framing only — no
> factual content the benchmark tests.** `fix/prompts_check.py` enforces it as a
> hard gate that *raises*, and it re-runs at the start of every RAG run, so an
> edit between review and run cannot slip through.
>
> ```
> $ python fix/prompts_check.py fix/system_prompt/swiss_context_v1.txt --gate
>   0/84 (0%) of dev items are answered by the prompt — CLEAN      exit 0
> $ python fix/prompts_check.py /tmp/plan_prompt.txt --gate
>   25/84 (30%) of dev items are answered by the prompt — CONTAMINATED  exit 1
> ```

> ### ✅ What 3.3 established (and what it did not)
>
> **Established, model-free and real:** retrieval finds the answer's own source
> **94.0% of the time at k=5 (90.5% @3, 83.3% @1)**, median rank 1, using
> pure-Python BM25 with **zero third-party dependencies**.
> → The dense retriever is *not* the bottleneck, so installing
> `sentence-transformers` is **not worth doing before a real baseline exists.**
>
> Two corrections to the plan's RAG design, both in `fix/rag/RESULTS.md`:
> `all-MiniLM-L6-v2` is **English-only**, not multilingual as the plan claims
> (178 of 367 chunks are Alemannic); and paragraph-splitting the `raw_pages`
> files would mix URL headers and fact-candidate scaffolding into the evidence.
>
> **Not established:** that RAG helps Apertus, or that the behavioural prompt
> helps. Paired mock run: 15 gains / 10 regressions, **p = 0.42 → "no detectable
> effect"**, which is the correct verdict at n=84, where ~6 net flips is the
> floor. k=3 and k=5 score identically because the 2,400-char context cap
> saturates first (only 1 of 84 items' contexts actually differ).

**4.1 · Held-out test run — machinery built; ⛔ BLOCKED on B2 (do not run)**
- [x] **0. The seal** — `eval/seal.py` records and verifies the test-set hash, logs every access
- [x] **1. Pre-flight gate** — 13 checks, refuses on mock / unsealed / dirty tree / frozen-code change
- [x] **2. The runner** — `eval/run_test_final.py`, reuses the Phase 2 scorers, resumable
- [x] **3. Sanity checks** — `quick_sanity_check()` plus the project's known failure modes
- [x] **4. Resume** — a crashed run restarts alone; completed runs are never redone
- [x] `fix/test_phase4.py` — **99 checks**
- [x] `fix/PHASE4_1.md` — full writeup
- [ ] **⛔ RUN IT** — requires B2 (real 8B) *and* B3 (70B route)

> ### ⚠️ The one-shot rule was breached five times — by this project's own tests
>
> `eval/seal.py audit`, verbatim:
>
> ```
> 2026-10-13T16:47:04+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
> 2026-10-13T16:48:43+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
> 2026-10-13T16:48:43+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
> 2026-10-13T16:48:48+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
> 2026-10-13T16:48:48+00:00  user  git=547cab4015d7  test-run knowledge/8b/baseline
> ```
>
> The first is the bug; the other four were my own follow-up test runs before I
> stubbed the guard out of the test path. Each read **all 36 sealed questions
> against the mock backend**.
>
> **Root cause:** `run_test_final.run_one()` had **no gate of its own** — the
> pre-flight lived in `main()`, so any caller that skipped `main()` was
> unguarded. The test suite was exactly such a caller.
>
> - Mock artefacts **deleted**; `eval/results/test_run/` does not exist.
> - The sealed file was **never modified** — SHA-256 unchanged, `verify` passes.
> - **All five entries were kept.** Removing them would defeat the only mechanism
>   that caught this, and it is also why this note cannot quietly say "one".
> - `run_one` now calls `guard()` itself. `test_phase4.py` §6b asserts a direct
>   call is refused, makes **0 model calls**, writes **0 files**.
>
> The real shot is unspent — all five produced synthetic responses nobody can
> cite — but the accesses happened and are on the record. **This is the argument
> for the audit log:** without it the first run would have succeeded, produced a
> plausible 27.8% table, and been quoted.
>
> Before the real run: `mv eval/seal/access.log eval/seal/access.log.preflight-incident`
> so the evaluation's own record is clean. The incident log is kept alongside it.

> ### ⛔ Corrections to `docs/plans/phase_4.md` (details in `fix/PHASE4_1.md`)
>
> 1. **The plan's runner breaks Golden Rule 3 by construction.** It reimplements
>    parsing, judging and dialect scoring. `extract_answer(text)` without
>    `options=` silently disables exact-phrase matching — so **test numbers would
>    not be comparable to dev numbers**, which defeats the purpose of a held-out
>    set. `judge_response()` bypasses the rubric; the dialect branch discards
>    `dialect_scoring_protocol.md` entirely. Metadata hardcodes "30 sources" when
>    the corpus has **100**. This runner calls `evaluate_knowledge` /
>    `evaluate_values` / `evaluate_dialect` instead — the same functions that
>    produced every Phase 2 number.
> 2. **The sanity check needed two more failure modes**: a score *at chance* (a
>    broken parse path still returns `ok=True`, so "the API worked" proves
>    nothing) and a **constant prediction** ("A" × 36 scores 25% and looks
>    plausible). Chance is computed from the data — a hardcoded 35% threshold
>    flagged a healthy 26.7% run as broken.
> 3. **The improved arm is retrieval only**, not the 3.3a system prompt. Recorded
>    in `IMPROVEMENT` so `run_metadata.json` cannot be misread.
> 4. **The expected result is "no change."** 3.4 found p=0.42. The improved arm
>    should match baseline. That is reportable, and Golden Rule 4 forbids
>    reacting to it — it is also not a reason to skip the arm.

> ### 📋 Run order once B2 lands
>
> ```bash
> # eval/.env:  APERTUS_8B_BACKEND=http
> git add -A && git commit -m "Phase 4: final test run"
> python eval/seal.py freeze                        # Golden Rule 4
> python eval/run_test_final.py --preflight         # must be all PASS
> python eval/run_test_final.py
> ```

**3.4 · Dev-set validation — built and run; verdict is a null result**

> ### ⛔ THE ONE SHOT HAS NOT BEEN SPENT — and must not be, yet
>
> `eval/.env` still has `APERTUS_8B_BACKEND=mock` and `APERTUS_70B_BACKEND=mock`.
> **No model has ever run.** Running the 36-item sealed set now would spend the
> single unrepeatable evaluation of this project on synthetic responses, and
> `run_test_final.py` **refuses on that ground** (check `P2-backend-not-mock`).
>
> Everything in 4.1 that does not touch the test set is built and tested on the
> **dev** split. When B2 lands, the run is one command.
>
> Two further preconditions the plan does not list but which are hard blockers:
> - **The improvement is frozen.** Golden Rule 4 forbids changing the fix after
>   seeing test numbers. `eval/seal.py freeze` records the git hash of the
>   improvement; the runner refuses if HEAD moved.
> - **3.4 found no detectable effect** (p=0.42). So the "improved" arm is
>   expected to *match* baseline. That is a legitimate, reportable outcome —
>   it is not a reason to change the fix now and not a reason to skip the arm.

**3.4 · Dev-set validation — built and run; verdict is a null result**
- [x] `fix/validate_improvement.py` — paired first, unpaired only as fallback
- [x] Regression detection by the **exact paired test**, not by pp and not by net
- [x] Attribution gate — a delta across mismatched setups is refused, not reported
- [x] Conditional RAG — requires an explicit `--target-category` **and** `--target-justification`
- [x] `fix/comparison.md` — generated, carries no `XX.X` placeholders
- [x] `fix/test_validation.py` (88 checks)
- [x] Test split stays sealed — `--split test` exits 1, and no read call can name it
- [ ] **Re-run on a real model (B2)** — mock is refused certification, exit 1

> ### ⛔ The plan's regression rule is a false-positive machine
>
> `docs/plans/phase_3.md` §3.4 Step 2 asks "did any category get WORSE by >5%?"
> and flags it. At n=14 per category **one item is 7.1 pp**, so a 5 pp threshold
> flags *any* single flipped item and calls a coin-flip a regression.
>
> Regressions are therefore judged by the **exact paired McNemar test on that
> category's discordant pairs**, reusing `select_target.mcnemar_exact()` rather
> than a second implementation. The plan's pp flag is still *reported*, because a
> reader expects it — it just does not decide.
> Demonstrated on the current mock run: the plan flags **health at −7.1 pp**,
> which is one item. And **law at +21.5 pp** has p = 0.375, so it is not an
> improvement either. A clean-looking category table would have been an artefact
> of n=14.

> ### ⛔ A net sum is not significance either
>
> The first version of the validator counted **items** and compared the net to a
> floor of 6. That is necessary but **not sufficient**:
>
> | improved | regressed | net | p | detectable? |
> |---|---|---|---|---|
> | 6 | 0 | **+6** | 0.031 | yes |
> | 10 | 4 | **+6** | 0.180 | **no** |
> | 14 | 8 | **+6** | 0.286 | **no** |
>
> Identical net, opposite conclusions. Every gain and every loss cancels in the
> sum but not in the test. So 3.4 now runs the exact test and reports each
> category's p-value in both the console table and `comparison.md`. A "gain of
> ten, loss of four" would previously have been published as a clear win.

> ### 📋 Result (mock, n=84, paired, top_k=3) — null
>
> 15 improved / 10 regressed, net **+5** items, **p = 0.42**. Below the 6-item
> floor, so the comparison separates neither a real effect from noise nor the
> reverse. **No category moved by more than chance** — per-category p-values run
> 1.0, 1.0, 1.0, 0.375, 1.0, 0.625. Difficulty profile is flat
> (easy +2, medium +0, hard +3). `validate_improvement.py` **exits 1 and refuses
> to certify**, because the backend is mock.
>
> Conditional on `law` computes to 19.0% vs 15.5% baseline — but that is
> **arithmetic on existing runs, not a measurement**, and it is offered only with
> a justification. 3.2 refused to name a target (G1/G2/G3 all fired), so nothing
> here picks one automatically.

**Current total: 11,130 automated checks across ten suites, all passing.**
(10,881 through 3.2, plus 62 in `fix/test_improvement.py`, 88 in
`fix/test_validation.py`, and 99 in `fix/test_phase4.py`.)

## Phase 3.3 — defects its 62-check suite caught

1. **The control arm was not the baseline.** The first `rag_prompt.build()`
   rendered the no-context arm with an *empty* system prompt and the RAG
   template's `"(no context available)"` placeholder. Any delta against that
   would have mixed "retrieval did not help" with "the control was
   handicapped", indistinguishably. Fixed to delegate to
   `run_knowledge.build_prompt`; §3 now asserts byte equality.

2. **`compose()` silently accepted a filename as prompt text.** The RAG runner
   passes pre-loaded prompt text, but a direct call with
   `"swiss_context_v1.txt"` produced a 20-character system prompt reading
   literally that — a nonsense system prompt that still runs and still scores.
   Guarded on shape (short and single-line); testing for `"/"` alone would have
   rejected the shipped prompt, which cites its own path in a provenance note.

3. **Per-category recall exceeded 100% (reported as 378.6%).** The hit counter
   incremented once per `k` rather than once per question. Per-category recall
   is now counted at one stated `k`.

4. **The median rank was computed from a nonsense expression** —
   `sorted(rank_hist.elements(), key=...)` sorts ranks by their frequency, which
   is meaningless. Now a real median over the expanded rank list.

5. **A missing tokenizer import was invented rather than found.** `tokenise()`
   imported `STOPWORDS` from `eval/prompts.py`, which does not exist. Worse, the
   regex it would have used split `100,000` into `100` + `000` — the exact bug
   `run_knowledge._content_tokens` warns about, and the signal retrieval most
   needs for the signature-threshold questions. Now reuses the project's tested
   tokenizer plus a German/French supplement.

## Phase 4.1 — defects its 99-check suite caught

1. **The test suite read the sealed test set.** The worst one in the project, and
   it was self-inflicted. `test_phase4.py` called `run_one()` directly to test
   resume logic; `run_one` had **no gate of its own** — the pre-flight lived in
   `main()` — so it read all 36 sealed questions against the mock backend. Caught
   by the audit log, not by a test. Fixed by moving the refusal to the point of
   use (`guard()` inside `run_one`), deleting the mock artefacts, and keeping the
   audit entry. **The lesson: a guard at the top of the program protects the main
   path and nothing else, and "nothing else" is where the accident happens.**
2. **The sanity checker's threshold was a magic 35%.** It flagged a healthy 26.7%
   run as broken, because 26.7% is *above* the 25% chance level for four-option
   questions. Replaced with a chance level computed from the data — which also
   makes it correct for non-MCQ tasks, where 25% is the wrong floor entirely.
3. **A path built in a temp dir crashed on `relative_to(ROOT)`.** Only visible
   once the resume test stopped reaching the real filesystem.
4. **Three fixtures assumed a clean git tree**, which is false whenever the
   suite is testing uncommitted code. Now monkeypatched, and the dirty-tree
   branch of the freeze check is exercised deliberately rather than skipped.

## Phase 3.4 — defects its 88-check suite caught

1. **A net sum was standing in for the significance test.** Counting items and
   comparing the net to a floor of 6 called **10 gained / 4 lost (net +6, p=0.18)
   an improvement**. Net is *necessary* but not *sufficient*; the exact paired
   test is now used via `select_target.mcnemar_exact()`, and each category's
   p-value is printed and written to `comparison.md`. Found while cross-checking
   the 6-item floor against 3.2's own power table — the floor happened to agree,
   which is exactly when a second hand-copied constant is worth distrusting.
2. **`write_comparison` crashed on an absent number.** `f"{None:+.1f}"` raises,
   so an empty or unpaired comparison could not write its document at all. Fixed
   with `_num()`, which prints "not measured" — deliberately *not* `0.0`, since a
   fabricated zero in a file people quote is worse than a crash.
3. **`verdict()` and `render()` indexed `per_category[0]` on an empty dict**, so
   a comparison with no paired items raised instead of reporting nothing.
4. **An empty category table was written as a bare header row.** That reads as
   "no data" to a person and "no problems" to a parser. It now emits an explicit
   "no paired items" row. Surfaced accidentally, when a regeneration consumed a
   stale input file — the failure mode is worth guarding whether or not that is
   how it was found.
5. **The plan's comparison template is built to be quoted with its placeholders
   in it.** `+XX.X pp` and `XX.X%` survive into any file generated from it. Every
   number in `fix/comparison.md` is now a real value or the words "not measured",
   and a test asserts `XX.X` never appears.
6. **Four test fixtures asserted the wrong direction.** "One lost item" was built
   as one *gained* item; "4 gains / 8 regressions" was built as 4 gains / 0
   regressions; the −6 boundary was asserted backwards (6 lost *is* a regression,
   since the power table's floor is inclusive); and a "6 gained" fixture reused a
   baseline with 10 wrong items, so 10 flipped. All four passed a validator that
   could not have caught them. A fixture that does not describe the case it names
   is the same failure as a validator that cannot fail.

## Phase 3.2 — defects its 96-check suite caught

1. **`_load` read `by_category` from the wrong nesting level**, so the real
   score file produced an **empty matrix** — a baseline table with headers and
   no rows. The tests missed it because my fixture shaped `scores` flat while
   the file nests as `{"run":…, "scores":{…}}`. A fixture that disagrees with the
   real shape is worse than no fixture.
2. **A `HALLUC`-dominated category was still marked viable.** It routes to
   Option C (LoRA), which an 8 GB card cannot build — so the matrix would have
   selected the one category whose only route is infeasible. Now flagged
   `infeasible_on_hardware` and excluded, with the reason in the rejection table.
3. **At n=14 with 2 regressions, nothing is detectable at all** — stronger and
   more alarming than "needs more improvements". Asserted rather than assumed.

## Phase 3.1 — defects its 67-check suite caught

1. **A hallucinated figure was being labelled NUMERIC** — and that is correct
   behaviour, not a bug, which is the point: `28 cantons` vs `26 cantons` is
   indistinguishable from a genuine miscount in the artefacts. Recorded as a
   limitation rather than guessed around.
2. **Number *words* were not normalised**, so `"Three months for residential
   premises"` against `"One month for residential premises"` did not collapse —
   the plural `-s` broke the comparison after the digits normalised.
3. **`UNCLASSIFIED` was winning the "dominant error" slot** at 78%, producing
   *"the dominant error pattern is UNCLASSIFIED"*. That reads as a finding and
   is the exact opposite: it means nobody has looked yet.
4. **`UNCLASSIFIED` was inheriting a fixability score of 5**, which put
   unexamined categories into the 3.2 ranking on a number nobody has evidence
   for.

## Phase 2.5 — defects its 41-check suite caught

1. **A check renamed itself when it failed** — "8B: no api errors" when passing,
   "8B: api errors" when failing. Impossible to assert on, and impossible to
   monitor: a check that changes its label when it goes off is one nobody alerts
   on. One name, both outcomes now.
2. **Values and dialect checks sat inside the knowledge block**, so a missing
   knowledge file silently suppressed them. A suppressed check reports nothing,
   which reads exactly like a pass. Now run independently per model.
3. Also caught: `identical evaluation conditions` read `temperature` from the
   wrong nesting level and printed `temp=None seed=None` — **passing vacuously**
   on two `None`s. Now reads `request_params` and hard-fails if absent.

### Phase 3 — Failure analysis & improvement
- [ ] 3.1 Error taxonomy
- [ ] 3.2 Weakest-area selection
- [ ] 3.3 Improvement — 3.3b (RAG over 55 sources) is the highest-ROI option
- [ ] 3.4 Dev-set validation
- [ ] `docs/plans/phase_3.md` is an **empty file** — needs writing

### Phase 4 — Final evaluation
- [ ] Held-out test run — **the only time the sealed set may be opened**
- [ ] Statistical comparison, charts, cross-model narrative
- [ ] `docs/plans/phase_4.md` is an **empty file**

### Phase 5 — Packaging
- [ ] Repo finalisation, datasheet, README, demo video
- [ ] `docs/plans/phase_5.md` is an **empty file**

### Phase 6 — Submission
- [ ] Final QA, submit to hackapertus.ch by **16 Oct 08:00 CEST** (4 h buffer)
- [ ] `docs/plans/phase_6.md` is an **empty file**

---

## Integrity rules that must not be broken

- 🔒 `knowledge_test.json` stays sealed until Phase 4.1. One run. No peeking.
- 🔒 Never edit a prompt template without bumping `PROMPT_VERSION` or changing the
  named variant — an unrecorded change silently invalidates every comparison.
- 🔒 Never mix backends within a before/after comparison; `compare_before_after()`
  refuses and says why.
- 🔒 Nothing produced under `mock` may appear in the README, charts or submission.
- 🔒 Rubric changes after seeing test scores are a benchmark-integrity failure.
- 🔒 Disproved facts in `verification_log.md` must never be asserted — only used as distractors.

---

## Immediate next actions

1. **Send the Discord post for a Swiss German speaker** (B1) — async turnaround, longest lead time.
2. **Accept the HF gate, pull the Q4_K_M GGUF, start `llama-server`, flip `eval/.env` to `http`** (B2).
3. `python eval/client.py 8b` → confirm live params, then
   `python eval/run_all.py --model 8b --task knowledge` for the real 84-question baseline.
4. `python eval/run_values.py --model 8b` → then `python eval/crosscheck.py select --model 8b --interactive`
   and score the 15 items (B5). **This is the only Phase 2.3 deliverable still open.**
5. `python eval/analyse_parses.py` → if the parse rate exceeds 10%, escalate the prompt variant.
6. Decide the 70B route (B3), write the root README + LICENSE (B4).
7. Decide whether Phase 1C takes the audio track or stays text-only.

---

## Phase 2.4 — defects its 515-check suite caught

1. **`matches()` used full-prefix containment.** "Kartoffle" stems to `kartoffl`
   and "Kartoffeln" to `kartoffeln`, which differ at the 8th character — so the
   correct translation scored as a miss. Now common-prefix with a ratio floor.
2. **Swiss German was undetectable on real text.** A hand-written marker list
   detected **1 of 12** actual Alemannic sentences. Replaced with markers
   derived by frequency analysis over the 461 Alemannic sentences in the
   corpus: **7 of 12**, with zero false positives on the 12 Standard German
   references. The remaining 5 are all Basel register, which marks itself with
   vocabulary rather than function words.
3. **Basel register therefore needed a second guard.** Added `dialect_echo()`,
   which compares the reply against the source dialect *and* the reference and
   flags "copied the input back" — needing no language identification at all,
   so it covers exactly the register the detector misses. All 12/12 caught.
4. **A lemma/surface-form defect in the data.** D002's key `können` never
   appears in its own reference (which says `kann`), and D005's `volksfest`
   likewise — so the *reference translation itself* scored 0.875 instead of
   1.0. A scorer fault that would have presented as a model fault. Each such
   term now takes the closest unclaimed reference token, recorded as
   `inferred`. **Worth flagging to the dataset author — the synonym lists
   should carry the reference's own surface form.**
5. **The inference silently did nothing** at first: `"kann"` was in the
   stopword list, so the one token that mattered was filtered out before the
   inference could use it. Only caught because the invariant test asserts
   `coverage == 1.0` and not merely `score == 2`.

## Phase 2.3 — the four bugs its test suite caught

Recorded because each would have produced a number that looked fine.

1. **`verify_crosscheck` compared the human's score against `None`.** The blind
   file strips `score` by design, so reading the verdict from it gave 0%
   agreement for every item — which reads as "the judge is terrible" and would
   have triggered a pointless rubric rewrite. Fixed by joining the blind file
   back to the parsed results on `(scenario_id, language)` for computation only.
2. **The plan's `JUDGE_USER` referenced `{expected_behavior}`, which does not
   exist** in the shipped 11-key scenario schema. It would have crashed on V001.
3. **Refusal detection missed the contraction form** — `"I don't understand"`
   and `"could you rephrase … in Standard German"` are the phrasings models
   actually produce, and neither matched.
4. **Swiss German was undetectable from short text.** The Alemannic signature
   list was too thin; a two-line Swiss German reply classified as `unknown`,
   which would silently suppress the register check on exactly the items the
   dialect gap depends on.
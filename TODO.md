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

**2.5 · Baseline runs — not started**
- [!] Full baselines on 8B and 70B — **blocked by B2, B3**

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
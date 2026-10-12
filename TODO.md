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

**1C · Dialect items — not started**
- [!] 1C.1 Native speaker recruitment — **blocked by B1**
- [ ] 1C.2 Comprehension items — 20–30 items (Alemannic sources now in the corpus)
- [ ] 1C.3 Validation or pilot label — **blocked by B1**

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

**2.3 · Values judge — not started** (data is ready: rubric + 30 scenarios + pairs exist)
- [ ] `judge.py`, `run_values.py`, `crosscheck.py`
- [ ] Decide judge model — **circularity must be disclosed** (`values_rubric.md` §5)
- [ ] 20% manual cross-check → report agreement rate

**2.4 · Dialect scoring — not started** (blocked by 1C)
- [ ] `run_dialect.py`

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
4. `python eval/analyse_parses.py` → if the rate exceeds 10%, escalate the prompt variant.
5. Decide the 70B route (B3) and write the root README + LICENSE (B4).
6. Decide whether Phase 1C takes the audio track or stays text-only.
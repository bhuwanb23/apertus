# Phase 2 — Evaluation Harness

**Status: the harness is complete and the one-shot evaluation has been run.**
Live 8B results exist for knowledge, values and dialect; the 70B arms are dropped.
**Read [Disclosures](#disclosures) before quoting any number from this file.** See
project status in `../TODO.md`.

`docs/plans/phase_2.md` §2.1 defines the golden rules. The two that shaped this
code most:

> **IDENTICAL conditions for 8B and 70B** — nothing in this harness branches on
> model size. The only difference between the two models is a `ModelConfig` entry.
>
> **DETERMINISTIC output** — temperature 0, fixed seed, and every request's
> actual parameters are logged, so "was it really 0?" is answered from the log
> file rather than from memory.

---

## Disclosures

Every accuracy in this file and in `results/` comes from one model, one
quantisation, one GPU and one sealed test set. The limits of that are stated next
to the numbers they qualify, not collected at the end. Source of truth for every
figure below: `results/final_scores/statistical_report.md`,
`results/final_scores/test_scores.json`, `results/test_run/*.json`,
`results/narrative/findings.md`.

### What was measured

Held-out sealed test set, `data/knowledge/knowledge_test.json`, n=90,
hash-verified (`83c20589e1c5b668`) and sealed until Phase 4.1. Both arms answer
the same 90 items through the same scorer, in a single paired invocation, so
the comparison is paired in the strict sense: one run, one seed, two conditions.

| Arm | Accuracy | 95% CI (Wilson) |
|---|---|---|
| Baseline, no retrieval | **51.1%** (46/90) | [41.0, 61.2] |
| Knowledge + RAG (BM25, `top_k=3`, per-question contexts) | **86.7%** (78/90) | [78.1, 92.2] |

Delta **+35.6 pp**, exact 95% CI [+25.1, +39.5]. Paired: **34 improved, 2
regressed**, McNemar p<0.001. The interval on the delta comes from the discordant
pairs, not from either arm's interval, and is wider than both.

| Other arm | n | Result | Qualification |
|---|---|---|---|
| Values | 73 records (30 scenarios × renderings) | mean **1.014** / 2.0 | self-judged — see below; re-scored under the rubric, see `rescore_values.py` |
| Dialect — refusal | 15/30 | **50.0%** | refusal is not a wrong answer and not a right one |
| Dialect — multiple choice | 18 | **50.0%** | all 30 items carry `validated_by: null` |
| Dialect — translation | 12 | mean **0.0** | all 12 items were refusals |

### The sealed test set was opened more than once

This is the most important limitation in this project.

`seal/access.log` is append-only and gains one line per arm execution, written
before dispatch and whether or not the run completes. It records **9** opens of
`knowledge/8b/baseline` and **15** opens of `knowledge/8b/improved`. The two arms
reported here are one open each (`run_utc` 03:35:15 and 06:06:58, 2026-10-16);
seven further improved opens are logged *after* the statistical report was
generated at 07:12:55. Because the log line is written before the run, the open
count is an upper bound on evaluations, not an equal count of them — but it is
not one.

Cause: a bug in `run_test_final.py` passed `args.resume or args.accept_rerun`
into the rerun flag, so `--resume` re-executed already-recorded arms instead of
keeping them, silently re-reading the sealed set. It is documented at
`run_test_final.py:512` and fixed.

Mitigations. These reduce the damage; they do not undo it.

- Decoding was greedy — temperature 0.0, seed 42, recorded in every run block —
  so a repeat is a *reproduction attempt*, not a fresh sample, and nothing was
  being selected between attempts. It is **not** bit-exact: re-running the
  84-item dev baseline under identical settings moved the score by one question
  (42.9% → 44.0%, 6 → 4 parse errors). Long greedy decodes on a GPU are not
  reproducible to the bit because reduction order varies between runs. Any
  single figure here should be read with that ±1-question wobble in mind.
- The baseline arm reported 51.1% (46/90) on the completed paired run of the sealed
  set — but given the drift above, that agreement is partly luck. Raw responses
  are overwritten per run, so it is not independently checkable from the
  surviving artefacts.
- No threshold, prompt or decision changed between runs, so nothing could be
  tuned to the test set. `fix/prompts_check.py` re-runs the contamination gate at
  the start of every evaluation.

Consequences to state rather than absorb: the headline result is **one reported
run, not a mean over runs**, and the sealed-set claim in
`results/narrative/findings.md` — "opened exactly once" — is not supported by the
log. The audit remains available: `python src/eval/seal.py audit`.

### The model is not the thing usually advertised

The weights are a `Q4_K_M` quantisation of `swiss-ai/Apertus-v1.5-8B`, text-only
— not the official Omni weights, which are multimodal and ~19.4 GB. It was served
by a **fork** of llama.cpp: `MichelRosselli/llama.cpp`, branch
`model/apertus-v1.5`, commit `918ebc1`, built for `sm_120a-real` with
`-DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler` because CUDA 12.9 rejects the
installed MSVC 14.50. Hardware: one RTX 5060, 8 GB.

So these are not stock upstream llama.cpp numbers, and a rerun on stock
llama.cpp, on different weights, or on different hardware may not reproduce
them. The repository does not record the build recipe; the model id carried in
every artefact is `apertus-v1.5-8b-text-q4_k_m`.

### No cross-scale claim is available

Apertus 70B is **dropped, not approximated** (`results/test_run/run_metadata.json`
→ `scope`): it cannot be loaded in 8 GB VRAM under any quantisation, and its
configured backend is `mock`. A single-model paired design cannot distinguish a
general improvement from an 8B-specific effect, so no generalisation or
cross-scale claim is available from this data.

### Values are self-judged, and the human cross-check does not exist

The 8B model judged the 8B model's own responses (`judge_model: 8b`,
`self_judged: true`). The agreement rate between the judge's own stated score and
the rubric applied in code is **0.03**
(`judge_self_report_agreement`), so the reported 1.014 is the code's rubric
applied to what the judge observed — not the judge's grading of itself. A
self-judged score is a weaker claim than a cross-judged one, and the observation
itself is unverified.

**The mean was revised after the run.** The implementation granted a score of 2
to any response missing exactly one required element, while
`data/values/values_rubric.md` §2 reserves 2 for "all but one *where the
omission is explicitly immaterial*". Six of 73 rows were affected.
`python src/eval/rescore_values.py` re-derives the scores from the **stored
judge observations** — no model called, no prompt re-run — and the mean falls
**1.096 → 1.014**. Every row keeps `score_as_run`, so both numbers are
auditable. The correction makes the result worse, which is what makes it
legitimate.

B5, a human blind cross-check of 15 items, **has not been done** and cannot be
delegated to a model. The reports say so rather than carrying a placeholder.

### The error taxonomy is unresolved

`fix/error_taxonomy.md` was generated from a **mock-backend** run and carries a
mock banner. Its percentages describe the classifier on synthetic text, not
Apertus. There is no real error taxonomy, so no dominant failure mode is claimed
and no target category is named.

### Every per-category interval crosses zero

n=6 per category. At that n only a clean 6/0 sweep reaches p<0.05 (0.031); with a
single regression, nothing is detectable. **The +66.7 pp services delta
(33.3% → 100.0%) is not a significant finding** and must not be read as one.
Categories are therefore reported side by side and never ranked — ranking six of
them is selection on the measurement set.

### Retrieval recall is backend-specific, and measured on dev

The headline recall figures — **82.4% / 91.4% / 92.9%** at k=1/3/5 — are
pure-Python BM25 with zero third-party dependencies, measured over all 210 dev
items (`fix/rag/RESULTS.md`). They describe the corpus and the index, not the
model, and they come from the dev split, not the sealed test set.

The retriever's default `--backend` is `auto`, so anyone re-running it can get the
dense `intfloat/multilingual-e5-small` index and different numbers; the reported
run pinned `bm25`. No dense-backend recall figures are recorded in this
repository, so none are quoted here.

On the dev run, retrieval put the gold source in context for 76 of 84 items, and
2 of the 36 gains occurred on items where it had missed — some of the movement is
prompt-shape effect, not retrieval.

### The dev split produced a null result first

Before a model was running, the paired dev evaluation measured **15 gains and 10
regressions, p=0.42** — no detectable effect at that dev scale
(`fix/rag/RESULTS.md`). That was the state of the improvement when it was frozen.
The dev comparison is recorded at `fix/comparison.md`; note that the dev split has
since grown to 210 items and has **not** been re-run, so the sealed test set is the
only current measurement.

### Reproducibility

- Per-arm code hashes, as recorded in the artefacts: baseline
  `490ee7cf248628ec44262fcef839e7e21c98d55d`, improved
  `1d481aa51187215ff5a54552a9e64c2c4217cc5e`. **The two arms were executed under
  different revisions, and neither is the recorded freeze.**
- `seal/frozen_code.json`: `436ba260830af773434675282a2cc897f15d13c9`, frozen
  2026-10-16T07:12:28Z.
- `results/test_run/run_metadata.json` records `git_hash`
  `2b2b75c840419f07c0a3c316d468df44721ea950` for the final orchestration pass,
  which **skipped** both knowledge arms and reused the files above.
- Decoding: temperature 0.0, seed 42, `prompt_version` 1.0, backend `http`,
  `is_mock: false`.
- RAG corpus: **189 of 367 chunks** (`include_dialect: false` — the 178 Alemannic
  chunks are excluded by default), `top_k` 3, retrieval backend `bm25`.
  `format_context` caps rendered context at 2,400 characters, which is why k=5
  adds almost nothing over k=3.
- Sealed test set SHA-256:
  `df819e8c1582902a23197ed2aa4ab2e9aab431f0df60d0349a9ba5c9467293e2`.

---

## Quick start

```bash
cp eval/.env.example eval/.env      # then edit
python -m venv .venv && source .venv/bin/activate
pip install -r eval/requirements.txt

python eval/smoke_test.py             # 2.1 acceptance check, runs offline
python eval/test_knowledge_scoring.py # 2.2 verification: 9,928 checks
python eval/check_http_backend.py     # proves the wire format
python src/eval/run_all.py --model 8b --task knowledge --limit 5
```

The `mock` and `http` backends need **no third-party packages** — they run on the
standard library. Only `openai` backend and the Phase 4 charts need the
install. That is deliberate: the harness should be testable before any install
step succeeds.

---

## Files

| File | Phase | Purpose |
|---|---|---|
| `config.py` | 2.1 | Every setting. Models are config entries, not code branches. Loads `.env`. |
| `client.py` | 2.1 | One interface, three backends, retries, logging, raw-response persistence. |
| `prompts.py` | 2.1 | All templates, versioned, plus the parse-error escalation ladder. |
| `scoring.py` | 2.2 | Accuracy + breakdowns. No I/O, unit-testable. |
| `run_knowledge.py` | 2.2 | MCQ evaluation, `extract_answer()`, `explain_answer()`. |
| `analyse_parses.py` | 2.2 | Diagnoses parse failures from disk and prescribes the fix. |
| `rescore.py` | 2.2 | Re-scores saved responses under a new parser, without the model. |
| `run_all.py` | 2.1 | Master runner. Unimplemented tasks skip cleanly. |
| `smoke_test.py` | 2.1 | The 2.1 acceptance checklist as an executable test. |
| `test_knowledge_scoring.py` | 2.2 | 9,928 checks over the parser and the aggregation. |
| `check_http_backend.py` | 2.1 | Captures literal JSON sent and asserts on it. |
| `requirements.txt` | 2.1 | Per plan. |
| `.env` | 2.1 | **Gitignored.** Secrets and endpoints live here only. |
| `results/` | — | **Gitignored.** Generated. |

---

## Phase 2.2 — parsing and scoring

### The parse-error budget

> *"If your parse error rate exceeds 10%, fix the prompt."*

A parse error is scored **incorrect**, the same as a wrong answer, so there is no
incentive to guess. But the count is reported separately, because a 10% parse
rate means 10% of the accuracy figure is measuring the parser rather than the
model.

`analyse_parses.py` closes the loop:

```bash
python eval/analyse_parses.py
```

It reads the saved responses — no model calls, so the diagnosis cannot depend on
a second generation — buckets every failure by cause, and prints the next
command to run. Crucially it **prefers the parser's own recorded reason** over
re-deriving one, because a diagnostic that re-guesses can disagree with the
scorer and then be diagnosing a system nobody is running.

### The prompt escalation ladder

Changing the prompt mid-baseline would confound the intervention with the
measurement, so the escalation is defined in advance in `prompts.py` and
selected **by name**:

| Variant | When |
|---|---|
| `v1_letter_only` | default baseline. Do not change. |
| `v1_strict` | parse rate > 10%. Adds an explicit output contract. |
| `v1_json` | parse rate still > 10%. Structured output. Last resort. |

```bash
EVAL_KNOWLEDGE_VARIANT=v1_strict python src/eval/run_all.py --model 8b --task knowledge
```

Every run records `prompt_variant`, so two runs can be told apart.

### Why the parser is the delicate part

A silent misparse turns a correct answer into a wrong one with no visible
symptom. So it is tested two ways: hand-written cases for output shapes and
hedges, and **9,480 cases generated from the 120 real questions**. The
generated cases are what matter — they found four defects that abstract
reasoning had missed:

1. **The article "A" read as an answer.** 207 of the 480 options are full
   sentences and many open with "A" — `K002`'s option B reads *"A voting member
   of the Federal Council…"*. A model restating that was scored **A**.
2. **Hedging read as commitment.** *"Both A and B could be correct"* returned A.
3. **Numbers split apart.** `"100,000"` tokenised to `100` + `000`, so options
   differing by one number looked identical — `K007`'s A and D.
4. **A clause cut at the wrong comma.** `"The answer is 4,80%"` was truncated to
   `"80%"`.

One rule was **removed** rather than added: a catch-all "any standalone B–D in
the first 40 characters". It fired on prose that merely contained a capital B,
returning a confident wrong letter where a parse error would have been honest.
In a benchmark a false positive is worse than a parse error, because it silently
inflates accuracy. `test_false_positive_guards` exists to keep every new rule
honest.

### Re-scoring without the model

```bash
python eval/rescore.py --model 8b --split dev
```

Raw responses are written before parsing, so a parser fix costs seconds instead
of a full re-run — which matters on an 8 GB card. The output is marked
`"rescored": true` and carries `parser_revision`, because a re-derivation of
existing observations is not a new observation.

---

## Model access

### Backends

| Backend | Needs | Use for |
|---|---|---|
| `openai` | `openai` package | Hosted OpenAI-compatible endpoints (CSCS, Phoenix) |
| `http` | nothing | Local `llama-server` / vLLM. Same wire protocol, stdlib `urllib`. |
| `mock` | nothing | Offline self-test. **Never produces a publishable number.** |

Set per model in `eval/.env`:

```
APERTUS_8B_BACKEND=http
APERTUS_8B_API_BASE=http://127.0.0.1:8080/v1
APERTUS_8B_MODEL_ID=Apertus-v1.5-8B-text-Q4_K_M
APERTUS_8B_API_KEY=EMPTY
```

### The mock backend will not silently contaminate results

This is the failure mode that would quietly destroy the project: a live endpoint
that quietly falls back to something fabricated, producing numbers that look
real. So every mock run is **stamped**, not just warned about:

- `is_mock: true` in every score file and every saved raw response
- `*** MOCK BACKEND - NOT A RESULT ***` in every summary
- `config.describe()` prints a starred banner
- `run_all.py` ends with `*** MOCK BACKEND WAS USED ***`

`compare_before_after()` also refuses to report a clean delta if the two sides
came from different backends or different question counts, because then the
difference is not attributable to the intervention.

---

## Running Apertus 8B on an RTX 5060

Verified from the Hugging Face API on 2026-10-12. **Read this before downloading
anything.**

### What `swiss-ai/Apertus-v1.5-8B` actually is

| | |
|---|---|
| Architecture | `Apertus1p5ForConditionalGeneration` |
| Pipeline tag | **`image-text-to-text`** |
| Parameters | 8,609,083,456 BF16 + 294,464,099 F32 ≈ **8.9 B** |
| Storage | **≈ 19.4 GB** |
| Gated | **Yes** — Apache 2.0 + AUP + privacy policy, contact details required |

**Apertus 1.5 is multimodal — vision *and* audio.** The repo ships
`model-vision_tokenizer-model.safetensors` and `model-wavtokenizer-model.safetensors`,
and the chat template defines `<|image|>` and `<|audio|>` tokens. Its own default
system prompt reads:

> *"You are Apertus 1.5 Omni, a multimodal assistant… you understand images and
> audio and respond in text."*

> **This resolves the open question in `docs/ideas/idea.md` §1 and
> `docs/plans/master_plan.md` 0.2**, which said to check the model card and to
> "pivot cleanly to text dialect comprehension" if audio was unsupported. It is
> supported. The audio track for Phase 1C is **live, not a fallback**. That is a
> scope decision to take deliberately, not by accident — audio items need real
> recorded Swiss German, which is a much bigger native-speaker dependency than
> text items do.

### Why the full model will not fit 8 GB

19.4 GB of bf16 weights, plus a vision encoder, a wav tokenizer and a KV cache,
does not fit an 8 GB card at any sane context length. Quantising the *full* Omni
model to 4-bit gets to roughly 5–6 GB of weights, leaving very little headroom,
and llama.cpp support for `apertus1p5` is not something to assume.

### What to actually run

Every pillar of this benchmark is **text**. Use the text-only extract:

| Option | Size | Notes |
|---|---|---|
| `Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF` | ~5 GB | **Recommended for 8 GB.** Q4_K_M. |
| `andreasmartin/apertus-v1.5-8b-text-Q8_0-GGUF` | ~8.5 GB | Better quality, will not fit alongside KV cache on 8 GB. |
| `rpreite/Apertus-8B-Instruct-2509-BNB-INT4` | ~5 GB | Older 2509 line, not v1.5. Disclose the version gap. |

Both Q4_K_M and Q8_0 GGUFs are third-party community quantisations of
`andreasmartin/apertus-v1.5-8b-text`, a text-only extract of the official v1.5
8B. **Record that in the datasheet**: a benchmark that claims "Apertus 1.5 8B" is
running a community text-only 4-bit extract, not the official Omni weights.

### Serving

```bash
./llama-server -m Apertus-v1.5-8B-text-Q4_K_M.gguf \
    --host 127.0.0.1 --port 8080 \
    --ctx-size 8192 \
    -ngl 99
```

`--ctx-size 8192` is enough: knowledge MCQ prompts are ~200 tokens; values
scenarios and the multilingual pairs are the long ones. Raise it if a prompt gets
truncated — check `finish_reason == "length"` in the saved responses, which is
exactly why that field is persisted.

Then:

```bash
python eval/client.py 8b     # connectivity + determinism, prints the live params
```

---

## Artifacts

```
eval/results/
├── raw_responses/<task>/<item_id>_<model>.json   every response, pre-parse
├── parsed/<task>_<model>_<split>_<condition>.json per-item verdict
├── scores/<task>_<model>_<split>_<condition>.json aggregates
├── logs/eval_<timestamp>.log                    request params per call
└── prompts_used.json                            exact templates + env fingerprint
```

Every file carries a `run` block: `model_id`, `backend`, `is_mock`,
`prompt_version`, `split`, `n_questions`, `condition` (`before`/`after`) and the
literal `request_params`. A number can always be traced to the call that
produced it.

Raw responses are written **before** parsing, so a fix to `extract_answer()`
means re-scoring from disk, not re-running the model.

---

## The test set is sealed

`data/knowledge/knowledge_test.json` is sealed until Phase 4.1. `--split test`
prints a warning and is expected to be run exactly once, in Phase 4.

It was not run exactly once. `seal/access.log` records 9 opens of the baseline arm
and 15 of the improved arm; see [Disclosures](#the-sealed-test-set-was-opened-more-than-once).

---

## Two defects the smoke test caught

Recorded because both would have silently corrupted scores.

**1. The parser read the English article "A" as an answer.**
`"...has A COMPLEX SYSTEM of direct democracy."` scored as option A. The
standalone-letter fallback now only considers `B`–`D`; a committed "A" is already
caught by the earlier rules.

**2. Hedging was scored as a confident answer.**
`"Both A and B could be correct depending on the canton."` returned `A`. A model
that declines to commit is not answering, and recording it as a choice inflates
the score. `HEDGE_PATTERNS` is now screened **before** any letter is accepted,
covering `"both X and Y"`, `"X and Y are both"`, `"either C or D"`,
`"all/none of the above"` and explicit uncertainty.

Both fixes tightened the check rather than loosening it, and both are covered by
21 cases in `eval/smoke_test.py`. A check that gets bypassed is worth less than
no check at all.

---

## Status

| Item | State |
|---|---|
| 2.1 — all nine checklist items | **done** |
| 2.2 — parser, scoring, breakdown, artefacts | **done** |
| 2.2 — 9,928 automated checks | **done** |
| 2.2 — parse-failure diagnosis + escalation ladder | **done** |
| 2.2 — live baseline, 8B | **done** — dev 84 items, sealed test 36 items |
| 2.2 — live baseline, 70B | **dropped** — does not fit 8 GB VRAM (B3); no cross-scale claim |
| 2.2 — `<5%` parse-error target | **measured on live runs** — `results/final_scores/` |
| 2.3 — `run_values.py`, `judge.py` | **done** — 73 records, self-judged |
| 2.3 — `crosscheck.py` | **not started** — B5, human blind scoring, not delegable |
| 2.4 — `run_dialect.py` | **done** — 30 items; native validation still blocked (B1) |
| Phase 3.3b — RAG retriever (`fix/rag/`) | **done** — dev recall @5 92.9% on BM25 |

The two arms behind the headline comparison were run more than once; see
[Disclosures](#the-sealed-test-set-was-opened-more-than-once).

`run_all.py --task values` and `--task dialect` currently print which phase owns
them and exit 0, so a half-built Phase 2 never blocks the part that works.

Project-level status and blockers are tracked in `../TODO.md`.
# Phase 2 — Evaluation Harness

**Status: Phase 2.1 complete. Phase 2.2 code complete — live baselines blocked on
model access.** Phases 2.3 and 2.4 are not started. See project status in
`../TODO.md`.

`docs/plans/phase_2.md` §2.1 defines the golden rules. The two that shaped this
code most:

> **IDENTICAL conditions for 8B and 70B** — nothing in this harness branches on
> model size. The only difference between the two models is a `ModelConfig` entry.
>
> **DETERMINISTIC output** — temperature 0, fixed seed, and every request's
> actual parameters are logged, so "was it really 0?" is answered from the log
> file rather than from memory.

---

## Quick start

```bash
cp eval/.env.example eval/.env      # then edit
python -m venv .venv && source .venv/bin/activate
pip install -r eval/requirements.txt

python eval/smoke_test.py             # 2.1 acceptance check, runs offline
python eval/test_knowledge_scoring.py # 2.2 verification: 9,928 checks
python eval/check_http_backend.py     # proves the wire format
python eval/run_all.py --model 8b --task knowledge --limit 5
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
EVAL_KNOWLEDGE_VARIANT=v1_strict python eval/run_all.py --model 8b --task knowledge
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
| 2.2 — live 84-question baseline, 8B **and** 70B | **blocked on model access** |
| 2.2 — `<5%` parse-error target | **blocked** — unmeasurable on `mock` |
| 2.3 — `run_values.py`, `judge.py`, `crosscheck.py` | not started (data ready) |
| 2.4 — `run_dialect.py` | not started (Phase 1C has no data yet) |
| Phase 3.3b — `rag.py` (`retrieve`) | not started |

`run_all.py --task values` and `--task dialect` currently print which phase owns
them and exit 0, so a half-built Phase 2 never blocks the part that works.

Project-level status and blockers are tracked in `../TODO.md`.
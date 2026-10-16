# Phase 3.3 — Improvement implementation: results

**Status: mechanism built and validated. No effect claim. Every accuracy below is a
mock-backend self-test.**

Run date: 2026-10-13. Backend: `mock`. 62 automated checks pass
(`python fix/test_improvement.py`).

---

## The finding that shaped this sub-phase

`docs/plans/phase_3.md` §3.3 Option A proposes a system prompt that asserts
eleven Swiss facts verbatim — 26 cantons, the 100,000/50,000 signature
thresholds, suffrage in 1971, the Federal Supreme Court in Lausanne, the
language percentages, UN membership in 2002.

Measured against the dev split, that text answers **25 of 84 items — 30%**.

So a large share of any "improvement" Option A produced would be the answer key
placed in the prompt, not a change in what the model knows. And it would not
transfer: the held-out test set is scored once in Phase 4.1, and a delta bought
this way does not reproduce on questions the prompt does not name.

**Therefore the shipped prompt carries behavioural rules only.**
`fix/system_prompt/swiss_context_v1.txt` scores **0/84** contamination, and
`fix/prompts_check.py` enforces that mechanically — as a gate that raises, not a
review step that someone can forget. It runs again at the start of every RAG run,
because a prompt edited between review and run is exactly the failure mode a
one-off check cannot catch.

```bash
python src/fix/prompts_check.py fix/system_prompt/swiss_context_v1.txt --gate
#   0/84 (0%) of dev items are answered by the prompt — CLEAN   (exit 0)

python src/fix/prompts_check.py /tmp/plan_prompt.txt --gate
#   25/84 (30%) of dev items are answered by the prompt — CONTAMINATED  (exit 1)
```

The gate's threshold is 5%, which is 4 items out of 84. That is deliberate slack
for incidental overlap, and it is also below the noise floor: `select_target.py`'s
power table says a claim needs ~6 net flips to be measurable at n=84. Every run
prints the **count**, not just the pass/fail, so items hidden inside the
threshold stay visible.

---

## Retrieval quality — real, and the one number here that is not mock

Every question in `knowledge_all.json` declares the `source_id` its answer was
verified against. So retrieval quality is a ground-truth metric computable with
no model at all:

```bash
python fix/rag/retriever.py --backend bm25
```

| metric | value |
|---|---|
| source recall @1 | **83.3%** |
| source recall @3 | **90.5%** |
| source recall @5 | **94.0%** |
| category recall @5 | 97.6% |
| median rank when found | 1 |

Per category (recall @5): health, history, politics, services 100%; geography and
law 85.7%. n=14 each.

**This is the decision-relevant result of Phase 3.3**, and it does not depend on
which backend is available:

> Retrieval finds the source containing the answer 94% of the time at k=5, using
> pure-Python BM25 with **zero third-party dependencies**. The dense retriever is
> not the bottleneck. Installing `sentence-transformers` would improve
> paraphrase matching on a minority of items, and the evidence says that is not
> where the remaining headroom is.

That also settles the plan's "install sentence-transformers" step as
**not worth doing before a real baseline exists.**

### Two corrections to the plan's RAG design

1. **The embedding model named in the plan is English-only.**
   `docs/plans/phase_3.md` specifies `all-MiniLM-L6-v2` and annotates it
   "Multilingual (handles German, French, Italian, English)". It is not
   multilingual — it is trained on English. 178 of 367 corpus chunks are
   Alemannic. `fix/rag/embeddings.py` defaults to
   `intfloat/multilingual-e5-small` and says why.

2. **Paragraph-splitting the source files would poison the corpus.** The plan's
   Step 1 splits each `raw_pages` file into ~800-char paragraphs. Those files are
   not prose — each carries a metadata header, a VERBATIM SOURCE QUOTES section,
   a German translation block, a numbered FACT CANDIDATES list, and reviewer
   caveats. Splitting on paragraphs puts the URL header and the fact-candidate
   scaffolding into the same chunk as the evidence, so the model would be shown
   that a fact was curated *for* a question, and would retrieve scaffolding
   instead of the source that states it. `prepare_corpus.py` chunks the verbatim
   evidence only and carries `source_id`/URL/tier on every chunk so a retrieved
   passage stays attributable.

   Result: 367 chunks from 100/100 files, 79k tokens. 178 are Alemannic and are
   **excluded by default** from the knowledge corpus — the questions are in
   English about institutions, so dialect chunks can only crowd out the passages
   that carry answers.

---

## The paired comparison — and why it is shaped this way

The plan's Step 4 compares "RAG accuracy" to "baseline XX.X%" from separate runs.
Anything that differs between those two runs would be credited to RAG: a changed
prompt, a changed model build, a different temperature, a warm cache, a rate-limit
that failed some calls.

`run_rag_eval.py` instead runs **control and treatment back to back over the same
questions, same client, same scorer, same `extract_answer`**. The only difference
between the two rows for a given question is whether a retrieved context was in
the prompt. Results then pair item by item into McNemar.

The control arm is byte-identical to `eval/run_knowledge.py`'s baseline prompt.
This was not true at first: the initial version rendered the control with an
**empty system prompt** and the RAG template's `"(no context available)"`
placeholder. Any delta measured against that would have mixed "retrieval did not
help" together with "the control was handicapped", and the two are
indistinguishable afterwards. `test_improvement.py` §3 now asserts control ==
baseline byte for byte.

### Result (mock, n=84, both top_k)

```
    k   control     rag   delta       p
    3     15.5%   21.4%   +5.9  0.4244
    5     15.5%   21.4%   +5.9  0.4244
```

15 gains, 10 regressions, **p = 0.42**. The verdict printed is the correct one:

> **no detectable effect at this sample size.** 15 gains and 10 regressions is
> inside the noise floor for n=84 paired items. Not a win, not a loss.

These accuracies are mock noise and will differ entirely on a real model. The
**retrieval** numbers above are real; the accuracies are not.

**k=3 and k=5 give identical accuracy, and that is genuine, not a plumbing bug.**
`format_context` caps context at 2,400 characters, so k=5 rarely has room to add
anything: mean context is 1,966 chars at k=3 and 1,970 at k=5, and only 1 of 84
items differs at all (K112). The `top_k` knob is largely saturated by the context
cap, not by retrieval quality.

---

## What this sub-phase does and does not establish

**Establishes:**
- The contamination risk in the plan's Option A, quantified at 30% of the dev set.
- A prompt that is clean against a mechanical gate, and the gate itself.
- Retrieval quality of 94% @5 with no third-party dependencies.
- A paired evaluation design that cannot attribute unrelated drift to RAG.
- A refusal to name a winner at p=0.42.

**Does not establish:**
- That RAG helps Apertus. Untested — there is no real model running (B2).
- That the behavioural system prompt helps. Also untested, and it needs a
  control-vs-override run with `--system-prompt`.
- Any per-category conclusion. n=14 per category is below what
  `select_target.py` showed is detectable.

**Next, in order:**
1. Unblock B2 (Q4_K_M GGUF → `llama-server` → `APERTUS_8B_BACKEND=http`).
2. `python src/eval/baseline_report.py --pre`, then the real 84-item dev baseline.
3. `python fix/rag/run_rag_eval.py --model 8b --split dev --topk 3` — real
   numbers, paired, still contamination-gated.
4. `python fix/rag/run_rag_eval.py --model 8b --split dev --system-prompt swiss_context_v1.txt`
   to isolate the 3.3a prompt effect. Note this run's control is **not** the
   baseline (both arms carry the override); `control_is_baseline` in the results
   file records that, so a 3.3a control is never misread as a baseline.
5. Re-run `fix/select_target.py` against the real numbers.

---

## Option C (LoRA) — not attempted, and why

An 8 GB RTX 5060 cannot hold a 7B+ adapter training run. `peft` + `bitsandbytes`
+ gradients for a model of this size needs far more VRAM than is available, and
the only local model is the Q4_K_M quantisation — training against quantised
weights is not a supported path. LoRA is recorded as infeasible on this hardware
rather than attempted and half-done. If B3 yields access to a larger GPU,
Option C remains open and its numbers are directly comparable: same dev split,
same scorer, `mcnemar()` already implemented in `fix/prompts_check.py`.

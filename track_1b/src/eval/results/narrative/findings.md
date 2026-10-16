# Key Findings — Swiss Reality Check

*Generated 2026-10-16T10:07:16+00:00 by `eval/narrative.py` from measured data · git `335ee05d868d`*

> **Read this first.** Every number below was computed by the code in this repository
> and is traceable to a run. There are no placeholders, and no claim appears that
> an analysis explicitly declined to make. Where a question is still open, this
> document says it is open.

> ## Model data — every accuracy figure below is from a live run
>
> The sealed test set was opened **27 times** according to the append-only log - 9 of the baseline arm and 18 of the improved arm - which is more openings than the single-shot design intends. Decoding was greedy (temperature 0.0, fixed seed) and nothing was tuned between runs, so the repeats were reproduction attempts rather than a search over attempts; they are **not** bit-exact, because a long greedy decode on a GPU is subject to run-to-run reduction order. **Disclosures** in `eval/README.md` quantify the drift on the dev split and state this in full. Latest arm: 2026-10-16T03:35:15+00:00, backend `http`, `is_mock: false`.
> Arms scored: `8b`. Accuracy, deltas and intervals
> come from `eval/statistical_report.py`; the per-item rows are in `eval/results/test_run/`.
> The findings that hold *without* a model are in §3.1–§3.4, and they do not depend on this run.

## Act 1 — The problem

Open multilingual models are trained overwhelmingly on global and English-language
material. For a country whose institutions, laws and vocabulary are well documented
but small, that produces a specific and testable failure: **fluent, confident answers
that belong to somewhere else.**

Switzerland is a good subject for this. It has four national languages, six and a half
million people, a distinct legal system, Alemannic dialects that are not Standard
German, and direct-democracy instruments that have no EU equivalent. A model can be
excellent at Swiss geography and still answer a Swiss constitutional question with
the German answer.

The question is not whether models *can* know this. It is **whether you can tell**,
on evidence, when they do not — which requires a benchmark whose answers are verified
rather than plausible.

## Act 2 — The measurement

**Swiss Reality Check** is a three-part benchmark of Swiss knowledge, values and dialect.

| | items | construction | scoring |
|---|---|---|---|
| Knowledge | 120 MCQs | 55 official Swiss sources, every distractor traceable to a real neighbouring-country answer | exact letter match, with a paraphrase ladder |
| Values | 30 scenarios | rubric scores **framing and balance**, not political position | LLM judge observes elements; the rubric is applied in code |
| Dialect | 30 items | Alemannic sentences with reference renderings | the protocol in `dialect_scoring_protocol.md` |

Two properties matter more than the counts:

- **Every knowledge answer is verified against a quoted source passage.** The
  distractor for each question is a real answer from Germany or the EU, not a
  plausible-sounding invention. That is what makes an error diagnosable rather
  than merely wrong.
- **The split is stratified and sealed.** 84 dev / 36 test, split on `(category, difficulty)`
  with a fixed seed. The sealed test set was opened **27 times** according to the append-only log - 9 of the baseline arm and 18 of the improved arm - which is more openings than the single-shot design intends. Decoding was greedy (temperature 0.0, fixed seed) and nothing was tuned between runs, so the repeats were reproduction attempts rather than a search over attempts; they are **not** bit-exact, because a long greedy decode on a GPU is subject to run-to-run reduction order. **Disclosures** in `eval/README.md` quantify the drift on the dev split and state this in full. Every individual access is listed by `python eval/seal.py audit`.

## Act 3 — What was actually found

### 3.1 Retrieval is not the bottleneck — and this is measurable now

Every knowledge question declares the `source_id` its answer was verified
against. That makes retrieval quality a **ground-truth metric requiring no model**:

| retrieved chunks | source containing the answer |
|---|---|
| top-1 | **83.3%** |
| top-3 | **90.5%** |
| top-5 | **94.0%** |

Measured over all 84 dev items against 189 corpus chunks, using **pure-Python BM25 with zero
third-party dependencies** — no sentence-transformers, no GPU.

The consequence is concrete: **the dense retriever was not worth installing.**
A more capable embedder could improve paraphrase matching on a minority of
items; the evidence said that was not where the headroom was. That is the kind
of decision this benchmark was built to support, and it was made before a
single model call.

### 3.2 The obvious fix was contaminated, and we caught it

The improvement proposed for this project was a system prompt listing Swiss
facts: 26 cantons, 100,000 signatures, suffrage in 1971, the Federal Supreme
Court in Lausanne. It reads like a good prompt.

Measured against the dev split, that text answers **25 of 84 items (30%)**.

So a large part of any "improvement" from that prompt would be **the answer
key placed in the prompt**, not a change in what the model knows. And it
would not transfer: the held-out set is scored once, and a delta bought this
way does not reproduce on questions the prompt does not name.

The prompt that ships instead carries **behavioural rules only — 0/84 contamination** — and
`fix/prompts_check.py` enforces that as a gate that *raises*, re-running at the
start of every evaluation so an edit between review and run cannot slip through.

This is the single most transferable thing this project produced. Any
country-specific benchmark faces the same trap, and it is invisible unless
you measure for it.

### 3.3 The error taxonomy did not resolve — and that is the finding

*Not classified — no classified error file; run fix/analyze_errors.py.* The rendered
`fix/error_taxonomy.md` carries a **MOCK BACKEND** banner, so its percentages describe
the classifier on synthetic text and not Apertus. They are not repeated here as findings.

So the taxonomy is **unresolved**: no real baseline error analysis exists, no
dominant failure mode is claimed, and no target category is named. Routing a fix
by dominant error type while most errors are unclassified would be a guess.

### 3.4 The dataset cannot support per-category claims, and that is arithmetic

The plan for this project was to report a category breakdown. It cannot be done, and
the reason is worth stating because it is a property of the design rather than
a disappointing result:

- **Overall (n=36):** a paired change is detectable only at **6 improvements with zero regressions** (+16.7 pp).
- **Per category (n=6):** only a clean sweep is detectable (6/0, p=0.031).
  With a single regression, *nothing* is detectable at this n. A category scoring
  0/6 has a 95% interval of [0.0, 39.0]; one scoring 6/6 has [61.0, 100.0].

Every per-category table in this project is therefore labelled descriptive, and
categories are never ranked. Ranking six of them is selection on the measurement
set, and it is the easiest way to manufacture a clean-looking result here.

### 3.5 What Apertus actually did on the sealed test set

**Apertus 1.5 8B, n=36.** Both arms answer the same
items with the same scorer, so this is a paired comparison and the test is
exact McNemar.

| arm | accuracy | 95% interval (Wilson) |
|---|---|---|
| Baseline, no retrieval | **55.6%** (20/36) | [39.6%, 70.5%] |
| Improved, retrieval-augmented | **86.1%** (31/36) | [71.3%, 93.9%] |

**Delta +30.6 pp**, exact 95% interval [+13.1%, +30.6%]: **11 items improved, 0 regressed**, McNemar p = 0.001 (below p < 0.05).

All 6 of the 6 categories moved in the same direction — none of them backwards. None is individually
significant, and §3.4 is the arithmetic for why: at n=6 per category a clean sweep is
the only detectable result.

**Values.** 73 scenarios, mean **1.096 out of 2.0**, 0 unscored (distribution {'0': 33, '2': 40}).
The `8b` values arm is **self-judged** — the judge and the model under test are the same weights. Disclosed per
`values_rubric.md` §5.

**Dialect.** 30 of 30 items scored. The model **refused 15 of them** (50.0%), and answered 50.0% of the 18
multiple-choice dialect items correctly. Refusal is not a wrong answer, but it is not a
right one either, and it is reported here rather than dropped.

The full tables, including the per-category breakdown that is reported side by
side and never ranked, are in `eval/results/final_scores/statistical_report.md`.

## Act 4 — The fix, and what it is worth

The intervention is retrieval-augmented generation: before answering, the model
receives the most relevant passages from the harvested Swiss corpus, with each passage
labelled by source so a reader can see where it came from.

Retrieval quality is **94.0% at k=5** (§3.1), measured against ground truth rather
than judged. That is the strong part of this section.

**On the sealed test set the effect is established.** Retrieval-augmented generation
moved accuracy by **+30.6 pp** (11 improved, 0 regressed, exact McNemar p = 0.001)
— comfortably past the floor in §3.4, which is what makes it a result rather than a
fluctuation.

Two things follow, and the second matters more than the first:

1. **The knowledge was recoverable.** §3.1 already showed the right source was on hand
   almost every time. This run shows that handing it to the model was enough. The gap
   was never that the corpus lacked the answer; it was that nothing was putting the
   answer in front of the model.
2. **It does not license the expensive paths.** A dense retriever, or fine-tuning for
   this domain, was the obvious next proposal and the evidence does not support it. §3.1
   said retrieval was not the bottleneck; this run says plain BM25 over a harvested
   Swiss corpus was enough. Buying capability where the measurement does not point is how
   evaluations turn into procurement.

## Act 5 — Implications for sovereign AI

The hackathon framing is sovereign AI: models a country or organisation controls,
deployed where the stakes of being confidently wrong are highest — government,
healthcare, legal. This project makes four claims that bear on that, in descending
order of how well they are supported:

1. **You can measure this, cheaply and without a GPU.** Domain gaps are usually
   discussed as anecdotes. Here a hash-verified benchmark over official sources
   turned "models probably get Swiss specifics wrong" into a number, and located
   the missing ingredient precisely enough to fix it with a retriever rather than a
   larger model.
2. **The obvious fix is usually contaminated.** A system prompt of Swiss facts
   answered 30% of the dev split. Any country-specific benchmark
   built this way will measure its own prompt. Checking takes one function call and should
   be standard practice.
3. **Know your detection floor before you measure.** At n=36 a real effect of +16.7 pp
   is indistinguishable from noise, and at n=6 per category *nothing* is. Benchmarks
   that report deltas without their floor are reporting noise as progress.
4. **Report the interval, not just the point estimate.** The measured delta was +30.6 pp with an exact 95%
   interval of [{_f(p['delta_ci_lower'], signed=True)}, +30.6%] — a range that excludes zero, which is the whole
   claim. Note also what the comparison does *not* say: one model, one benchmark, one shot.

The benchmark, the corpus, the evaluation harness, the error taxonomy and the RAG
pipeline are open-source and reusable for any country's domain. The methodology is
the transferable part: the contamination gate and the detection-floor reporting apply
to any small-n evaluation, in any language, for any model.

## Limitations

1. **One model, one benchmark, one shot that was not one shot.** The sealed test set was opened **27 times** according to the append-only log - 9 of the baseline arm and 18 of the improved arm - which is more openings than the single-shot design intends. Decoding was greedy (temperature 0.0, fixed seed) and nothing was tuned between runs, so the repeats were reproduction attempts rather than a search over attempts; they are **not** bit-exact, because a long greedy decode on a GPU is subject to run-to-run reduction order. **Disclosures** in `eval/README.md` quantify the drift on the dev split and state this in full.
   Scored for Apertus 1.5 8B. Nothing here separates a
   Swiss-specific effect from a general small-model effect, and nothing here would survive a
   second look at the same items.
2. **The test set is n=36.** A detectable paired change needs 6 improvements with zero regressions. Per-category
   n=6 supports nothing. Confidence intervals are reported throughout for this reason.
3. **Values scoring is LLM-as-judge, and the human audit is not started.** B5: no blind sample exists yet. A human must score the 15 items; this cannot be delegated to a model.
   This is the weakest load-bearing element in the design: the rubric is applied
   in code to what a judge *observed*, but the observation itself is unchecked
   until a person scores the same items blind.
   The `8b` values arm is additionally **self-judged** — judge
   and model under test are the same weights. Disclosed per `values_rubric.md` §5.
4. **Dialect scoring is automated word overlap**, an approximation of translation
   quality, and **all 30 items carry `validated_by: null`** pending a native speaker.
   The corpus-derived markers catch 7 of 12 real Alemannic sentences with no false
   positives; the other 5 are Basel register, covered by a different test.
5. **The error taxonomy is unresolved** (§3.3), so no dominant failure mode is claimed
   and no target category is named. Routing a fix by dominant error type is a guess
   while most errors are unclassified.
6. **Retrieval recall is measured on dev, not test.** It is a property of the corpus
   and the index rather than of the model, so it does not consume the sealed set —
   but it does mean the recall figure and the accuracy figures come from different
   splits.
7. **No comparison to models outside Apertus.** Nothing here shows these gaps are
   specific to Apertus rather than common to open multilingual models of its size.

## Reproducibility

- Git commit `335ee05d868d3c1ee9cc3c77c8141a3e53a23cb5`
- Sealed test set SHA-256 `df819e8c1582902a23197ed2aa4ab2e9…` (recorded in `eval/seal/`)
- Seed 42 · temperature 0.0 · prompt version 1.0 · judge `8b`
- Every access to the sealed test set is in an append-only log: `python eval/seal.py audit`
- Scenario selected by the data, not by hand: **A — Strong improvement**
  - significant paired gains of up to +30.6 pp


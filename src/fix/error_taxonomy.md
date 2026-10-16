# Error Taxonomy — Apertus 1.5 baseline

*Generated 2026-10-12T12:17:22+00:00 from `eval/results/parsed/`*

> ## ⚠️ MOCK BACKEND — this taxonomy describes synthetic responses
> 
> The model was a deterministic stand-in whose answers are a hash of the
> prompt. Nothing below is a finding about Apertus. The pipeline is built
> and tested; the content waits on **B2**. See `docs/BASELINE.md`.

## Two counts that must not be added together

| | count | what it is | fix belongs to |
|---|---|---|---|
| parse errors | 12 | the response yielded no letter | **the prompt / parser** |
| content errors | 59 | a letter was parsed and it was wrong | **the model** |

A parse error is a measurement failure, not a knowledge failure. Adding it to
the wrong-answer count would inflate the apparent error rate and make the
taxonomy describe the instrument rather than the model.

## Summary

| Error type | n | % of content errors | deterministic | worst categories | fixability |
|---|---|---|---|---|---|
| `UNCLASSIFIED` *(work queue, not a finding)* | 46 | 78.0% | 0/46 | law, geography | — |
| `NUMERIC` | 13 | 22.0% | 13/13 | history, services | 6 |
| *parse errors (separate)* | 12 | — | — | — | 10 |

**Dominant *classified* error: `NUMERIC` at 22.0%.**

> ⚠️ 78.0% of content errors are still `UNCLASSIFIED`. `NUMERIC` is the largest pattern *found so far*, **not** the dominant
> one — a single unexamined category could overtake it. Do not select a
> Phase 3 target from this until the reasoning pass has run.

## Detail

### `UNCLASSIFIED` — not yet classified - no evidence beyond which option was chosen

**46 items (78.0%).** Not an error type.

*What this is:* an item awaiting a reasoning re-run and a human decision. It is a work queue, not a finding.

Each of these has only two facts: which option was chosen, and which was right.
Nothing in the baseline artefact says why. They are listed so the queue is
visible, not so a pattern can be claimed.

### `NUMERIC` — right concept, wrong number

**13 errors (22.0%).** 13 decided mechanically, 0 awaiting human confirmation.

*Kind of error this is:* 50,000 signatures for an initiative (that is the referendum threshold; an initiative needs 100,000)

- **K011** (politics, easy) — picked `D`, correct `B`
  - evidence: options differ only in a number: '50,000 signatures within 18 months' vs '100,000 signatures within 18 months'
  - raw: `The answer is D.`
- **K019** (politics, easy) — picked `B`, correct `C`
  - evidence: chose 'around 25,000' over 'around 2,500'; both are bare figures
  - raw: `The answer is B.`
- **K039** (law, medium) — picked `A`, correct `D`
  - evidence: options differ only in a number: 'One digital fingerprint and a facial image, stored for five years' vs 'Two digital fingerprints and a facial image, stored for five years'
  - raw: `The answer is A.`

## Outstanding work

- **Needs a reasoning re-run** (46): no evidence beyond which option was chosen. `python src/fix/analyze_errors.py --model 8b --diagnose`
- **Needs human confirmation** (0): a suggestion exists but nobody has checked it. Unconfirmed labels are reported separately and are not analysis.

## Why an MCQ alone cannot classify an error

The baseline response to a knowledge item is a letter, often with a sentence of
filler — `Switzerland's rules differ here, so I would choose A.` That contains
no information about *why* A. Asking a classifier to label it DE-CONF, HALLUC
or NUMERIC yields a confident label with nothing behind it.

So this taxonomy classifies in layers: mechanically where that is decisive
(`PARSE`, `NUMERIC`), then from the model's own stated reasoning on a separate
diagnostic run, then confirmed by a person. The diagnostic run uses a different
prompt, is stamped `diagnostic: true`, and is never merged into a score table.

## Limitations of this taxonomy

1. **A wrong figure cannot be separated from an invented one.** `28 cantons`
   against `26 cantons` is labelled `NUMERIC`, because in the artefacts a
   number the model invented and a number it misremembered are the same
   object. Only the reasoning pass can separate them, and only a human can
   confirm that.

2. **A bare `NUMERIC` label is about shape, not about cause.** It says the two
   options differ only in a figure. It does not say the model understood the
   concept and slipped, which is what `NUMERIC` means in the plan.

3. **Four-option items bound the resolution.** The model chose one of four;
   the near-miss items it rejected are invisible. An error rate on a 4-way
   choice says less about competence than the same rate on open generation.

4. **`n = 14 per category.** One item moves a category by 7.1 points. Category
   differences smaller than that are noise and must not drive a Phase 3 choice.

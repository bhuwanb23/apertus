# Native Speaker Validation Packet — Phase 1C

**Send this to the volunteer.** Everything they need is below. Estimated time: 15–20 minutes.

---

## What we need and why

I am building a benchmark ("Swiss Reality Check") that tests how well an open language model handles Swiss German, Swiss institutional knowledge and Swiss cultural norms, for a hackathon run by EPFL, ETH Zurich and CSCS.

**Good news for you: you do not need to check the Swiss German.** Every Swiss German sentence in the benchmark was copied verbatim from the **Alemannic Wikipedia** (`als.wikipedia.org`), which is written by native speakers and freely licensed. If a sentence came from there, it is real Swiss German — somebody Swiss wrote it that way.

**What I do need you to check is the English around it:**

1. **The Standard German translations.** These are the one part I wrote myself. If a translation is wrong or unnatural, the whole item is broken.
2. **The dialect labels.** Some items are tagged `basel`, `zurich`, `bern`, `walser`, `valais`. If an item is tagged with the wrong region, that is a real error.
3. **The multiple-choice distractors.** In the "what does this mean?" questions, the three wrong options must be genuinely wrong but plausible.

I am **not** asking you to grade the model or take a test. I am asking you to fact-check my translations.

---

## What you get

Credit as a named contributor in the repository README and in the dataset datasheet, with whichever handle you prefer.

---

## The 30 items

They are split into four kinds:

| Kind | Count | What you check |
|---|---|---|
| **Translation** | 12 | Is the Standard German right and natural? |
| **Comprehension** (what does this mean?) | 8 | Is the right option right, and are the three wrong options genuinely wrong? |
| **Culture-in-dialect** (a Swiss fact inside a Swiss German sentence) | 5 | Same as above, plus: is the Swiss fact true? |
| **Dialect identification** (which dialect is this?) | 5 | Is the labelled dialect correct? |

Full data: `data/dialect/dialect_items.json`. A ready-to-fill answer sheet is at the bottom of this file — copy it, fill it in, send it back. **You do not need to read the JSON.**

---

## Please answer these five questions per item

```
id:        D001
kind:      translation
dialect:   basel
sg:        (the Swiss German sentence)
mine (de): (the Standard German translation I propose)

1. Is my German translation CORRECT?            yes / mostly / no
2. Would a Swiss person write it that naturally?  yes / mostly / no
3. Is the dialect label right?                  yes / probably / no  (only for dialect_identification, and generally)
4. For multiple-choice: are the three wrong options genuinely wrong?   yes / one is debatable / no
5. Correction, if any:  ______________________________________________
```

---

## The items

<!-- ITEMS -->

---

## Answer sheet

<!-- ANSWER_SHEET -->

---

## How we will use this

- Every correction you send is applied and the item is marked `validated_by: your_handle`.
- Items you confirm keep their text unchanged. Items you correct get your version.
- **If you only have time for some items, that is genuinely useful** — send what you can. Partial validation is reported honestly as partial in the datasheet.
- If you would rather not be named, say so and we will record "validated by a Swiss German speaker, name withheld".

---

## One thing worth knowing

A large part of this project is deliberately *not* measuring whether a model agrees with a political opinion. Where a question is genuinely contested — neutrality, weapons transfers, joining NATO — the benchmark scores whether the model identified the correct Swiss legal framework and acknowledged that Swiss people disagree, and it does **not** score the model's position. I mention it because some people worry about that kind of benchmark, and I would rather you know up front.

---

## Contact

Reply to this message or DM me. Corrections in German, English or Swiss German are all fine.

# Dialect Section — Pilot Note

**Status: UNVALIDATED PILOT. This is the current, honest state of the dialect pillar.**

---

## Summary

This section contains **30 items** (`dialect_items.json`, ids `D001`–`D030`) testing whether the model can read Swiss German and recover Swiss institutional facts from it.

**The Swiss German has been checked. The translations around it have not.**

---

## What has been verified, and how

This is the strongest part of the section, and it is stronger because of a decision made during planning.

The obvious approach — writing Swiss German sentences by hand — was rejected. The project author is not a native Swiss German speaker, and Phase 1B had already established that the risk of mis-attributing dialect features to the wrong region is real enough to corrupt a benchmark. Hand-written dialect would have made the entire pillar untrustworthy, and its weakness would have been invisible in the results: a low score could have meant *the model is bad at Swiss German* or *the questions were badly written*, and those cannot be told apart after the fact.

Instead, every Swiss German sentence was copied **verbatim** from the **Alemannic Wikipedia** (`als.wikipedia.org`, CC BY-SA 4.0) — a free encyclopedia written by native speakers, covering Zürich, Bern, Basel, Aargau and Walser German.

| | |
|---|---|
| Corpus files | **45** (source ids `S101`–`S145`) |
| Verbatim Swiss German sentences | **470** |
| Items built | 30 |
| Items whose text is machine-matched character-for-character against its source file | **30 / 30** |

That last row is enforced by `scripts/verify_dialect.py`, which fails the build on any mismatch. It has already earned its keep — see "Defects caught" below.

## What has **not** been verified

Everything authored rather than quoted:

1. **The 12 Standard German reference translations** (used for scoring the translation items).
2. **The multiple-choice distractors** on the 18 deterministic items.
3. **The dialect region labels** on 29 of 30 items (`DIALECT_EVIDENCE` headers record what supports each one; one item is honestly labelled `uncertain`).
4. **The difficulty ratings.**

Every item carries `validated_by: null`. `scripts/verify_dialect.py` treats any non-null value as a build error until a real validation log exists.

---

## Why this is still worth submitting

1. **The input side is sound.** Native-written text with a stable, citable URL. A reviewer can spot-check any item in two clicks.
2. **Three of four item types are fully deterministic** — no LLM judge, so no judge variance, no judge circularity.
3. **The limitation is stated, not hidden**, and the fix is a 20-minute volunteer task with a ready-made answer sheet.
4. **Partial validation is still validation.** If a reviewer checks 10 of 30 items, that is reported as 10 of 30 — not quietly generalised to all 30.

---

## What must happen before this is described as validated

1. Send `data/dialect/VALIDATION_PACKET_FILLED.md` to a Swiss German speaker.
2. Apply their corrections to `dialect_items.json`.
3. Set `validated_by` per item.
4. Record the exchange in `dialect_validation_log.md` (template below).
5. Re-run `python scripts/verify_dialect.py` — it will still reject `validated_by` until the log exists, so that step is deliberate: **the log is the evidence, and the verifier should not take the word of a data field.**

---

## Defects caught during construction

Worth recording, because each one is a way this section could have been quietly wrong:

| Defect | How it was caught | Consequence |
|---|---|---|
| `SOURCE_ID` stamped on all 14 files of each of 3 harvests — 14 duplicates per id | provenance lookup silently collapsed 14 files into 1 | 45 files renumbered `S101`–`S145` |
| One item's Swiss German (`D006`) appeared nowhere in the corpus — fragments `Narrazomft`, `oatsasässege` matched zero files | character-for-character provenance check | traced to a duplicated article harvested twice (`S106`/`S136`); item repointed by content, not by URL |
| 46 double-encoded UTF-8 sequences (`zÃ¼rich`) in one item file | dialect-label schema check | repaired; `scripts/repair_mojibake.py` |
| 13 items stored the corpus's quote delimiters inside the field value | provenance check | repaired; `scripts/strip_corpus_quotes.py` |
| 2 articles harvested twice (`Fasnacht`, `Schweiz`) | duplicate-URL report | item provenance now resolved by content match |

The authoring pass had self-reported "0 mismatches" and "byte-verified" on the file with the mojibake and the fabricated item. **A self-check that reads the data back through the same pipeline that produced it will agree with itself.** The mechanical checks read raw bytes against an independent corpus, and that is the only reason these were found.

---

## Limitations to state in the datasheet

1. **No native validation.** Stated above; the central limitation.
2. **Encyclopaedic register.** The corpus is Wikipedia prose — grammatically clean, somewhat formal, and not natural speech. A model could score well here and fail on conversational Swiss German. This is a coverage gap, not a solved problem.
3. **Written, not spoken.** Swiss German is overwhelmingly spoken with little written tradition. We test written comprehension.
4. **Orthography confound.** Swiss German has no standardised orthography. The corpus uses a house system close to Dieth (1938), but individual files sit in different registers. A model may be reading a transcription convention rather than failing the dialect. Every item records its `orthography` and `dialect_evidence`.
5. **Dialect coverage is the Alemannic Wikipedia's, not Switzerland's.** Zürich is well represented (370 articles available), Bern moderately (108), **Aargau not at all** (the category is empty — no padding was done). "Swiss German" here means "what Alemannic Wikipedia contains".
6. **13 of 30 items are Basel German.** Basel is the corpus's largest dialect. Results are always reported per dialect and never pooled.
7. **Content-keyword coverage cannot distinguish comprehension from pattern recovery.** It is used only for the 12 translation items; the other 18 items carry the comprehension signal deterministically.
8. **Three assumptions were refuted during harvesting** and must not reappear: `-t` final devoicing does **not** distinguish Basel from Zürich (the devoiced copula `ischt` is Walser/Valais); `Chuch` vs `Kuchi` does not exist in this corpus (Basel says `Broot`/`Laib`); `Märit` vs `Markt` is unverified. `scripts/verify_dialect.py` rejects items relying on any of them.

---

## `dialect_validation_log.md` — template

Create this file when validation arrives.

```markdown
# Dialect Validation Log

## Validator
- Name / handle:
- Dialect region(s):
- Date:
- Time spent:
- Items reviewed: N of 30
- Items confirmed unchanged: N
- Items corrected: N

## Per-item corrections

| item | field | original | corrected | reason |
|---|---|---|---|---|
| D0xx | standard_german_reference | ... | ... | ... |

## Items not reviewed

(list)

## Validator's general notes

(anything about the Swiss German itself, the dialect labels, or the
difficulty of the items - these are valuable even when the item is fine)
```

---

## Related limitation elsewhere in the project

The same validation gap affects **Phase 1B**: 37 of 53 non-English renderings in `values_multilingual_pairs.json` are labelled `author_written_unvalidated`. A single volunteer with Swiss German can close both gaps — and the Discord call covers both.

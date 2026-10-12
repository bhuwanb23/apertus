# Dialect Items — Build Report

**Sub-phases 1C.2 / 1C.3 complete. Sub-phase 1C.1 is blocked on you.** 30 items, documentary-grounded, mechanically verified, unvalidated.

---

## Deliverables

| File | Contents |
|---|---|
| `dialect_items.json` | 30 items, `D001`–`D030`, all `validated_by: null` |
| `dialect_scoring_protocol.md` | Scoring design; 3 of 4 types are deterministic |
| `VALIDATION_PACKET_FILLED.md` | **Send this.** All 30 items + blank answer sheet, ~20 min of work |
| `dialect_pilot_note.md` | Honest unvalidated status, limitations, validation log template |
| `items_D001_D017.json`, `dialect_items_d018_d030.json` | Per-pass drafts |

Scripts: `verify_dialect.py`, `resolve_dialect_provenance.py`, `renumber_dialect_sources.py`, `repair_mojibake.py`, `strip_corpus_quotes.py`, `render_validation_packet.py`

---

## The decision that matters

The plan assumed the dialect items would be hand-written Swiss German. **They are not.**

Writing Swiss German by hand was rejected because the project author is not a native speaker — and Phase 1B had already shown that mis-attributing dialect features to the wrong region is easy and corrupts results silently. Worse, the failure would be **unfalsifiable after the fact**: a low score could mean the model cannot read Swiss German, or that the questions were badly written, and those are indistinguishable once the results exist.

Instead, every Swiss German sentence is copied **verbatim** from the **Alemannic Wikipedia** (`als.wikipedia.org`, CC BY-SA 4.0) — native-authored, stable URLs, covering Zürich, Bern, Basel, Aargau and Walser German.

| | |
|---|---|
| Corpus files | **45** (`S101`–`S145`) |
| Verbatim Swiss German sentences | **470** |
| Items built | 30 |
| **Items matched character-for-character against their source file** | **30 / 30** |

**This moves the honesty problem.** Before: *"is our Swiss German any good?"* — unanswerable. Now: *"are our Standard German translations accurate?"* — a 20-minute volunteer task with a ready-made answer sheet.

---

## Distribution

| | count |
|---|---|
| translation (T1) | 12 |
| comprehension (T2) | 8 |
| culture-in-dialect (T3) | 5 |
| dialect identification (T4) | 5 |
| **deterministic (no LLM judge)** | **18 / 30** |

| Dialect | n |
|---|---|
| basel | 13 |
| zurich | 7 |
| bern | 4 |
| walser | 3 |
| valais | 2 |
| uncertain | 1 |

Difficulty 6 easy / 17 medium / 7 hard. MCQ answer letters A=5 B=5 C=4 D=4.

**Per-dialect reporting is mandatory.** 13 of 30 are Basel German and "Swiss German" here means "what the Alemannic Wikipedia contains" — Zürich has 370 articles available, Bern 108, **Aargau zero** (empty category; no padding was done).

---

## Scoring design

The plan said translation items are "easy to score (compare to reference translation)". They are not — exact match punishes correct synonyms and rewards reproducing the reference string. Redesigned:

- **T2/T3/T4 → 4-option MCQ, deterministic.** Identical scoring to Phase 1A.
- **T1 → content-keyword coverage**, 0–2 at thresholds 0.85 / 0.50, with a per-item synonym list so a correct alternative phrasing is not punished. Not BLEU (n-gram precision punishes legitimate Swiss German reordering), not semantic similarity (needs a model, reintroducing the judge-dependence this avoids).

Coverage cannot distinguish "understood it" from "recovered the content words by pattern". Accepted, because the other 18 items carry the comprehension signal deterministically.

---

## Orthography, declared

Swiss German has **no standardised orthography** — the corpus itself says so. Dieth (1938) is pronunciation-faithful (`zùùgfaare`, `oo`/`äi` marking length); Marti (1972/85) sits closer to Standard German. The Alemannic Wikipedia uses a house system near Dieth.

This is a **per-item variable**, not global: the 45 files sit in at least seven registers (Basel house, Zürich with `oo`/`ee` doubling, Thurgau `ä` for /aː/, near-Dieth Schwäbisch, Oberrheinisch, Basel-Landschaft village speech, and 8 `uncertain`). Every item records `orthography` and `dialect_evidence`.

**A model may be reading a transcription convention rather than failing the dialect.** That confound is disclosed, not hidden.

---

## Defects caught — five, all mechanical

| Defect | Caught by | Fix |
|---|---|---|
| `SOURCE_ID` stamped on all 14 files of each of 3 harvests — 14 duplicates per id | provenance lookup collapsed 14 files into 1 | renumbered to `S101`–`S145` (`renumber_dialect_sources.py`) |
| 2 articles harvested twice (`Fasnacht`, `Schweiz`) | duplicate-URL report | provenance now resolved by content match (`resolve_dialect_provenance.py`) |
| `D006`'s Swiss German appeared nowhere in the corpus | provenance check | traced to the duplicate; item repointed |
| 46 double-encoded UTF-8 sequences (`zÃ¼rich`) | dialect-label schema check | `repair_mojibake.py` |
| 13 items stored the corpus's `"` delimiters inside the field | provenance check | `strip_corpus_quotes.py` |

### The one worth dwelling on

**The drafting pass self-reported "0 mismatches" and "byte-verified" on the file that contained both the mojibake and a fabricated sentence.** It also stated the strings were clean UTF-8 because it read them back through the same mojibake-decoding console that produced them.

That is the general failure mode: *a self-check that reads data back through the pipeline that produced it will agree with itself.* Every defect above was found by a check that reads raw bytes against an independent corpus, with no knowledge of how the file was produced.

The same reasoning justifies the whole project's verification posture — Phase 1A quote-matching, Phase 1B scorability greps, Phase 1C provenance matching. It is not paranoia about the data; it is the only way to know the checks work.

---

## Assumptions the harvest refuted

Three things I expected to be true, which the corpus textually disproved. All are now rejected by `verify_dialect.py`:

1. **`-t` final devoicing does not distinguish Basel from Zürich.** Basel, Bern *and* Zürich all write `isch`. The devoiced copula `ischt` is Walser/Valais. Basel does devoice — in `Joor` and `Broot`, not the copula.
2. **`Chuch` vs `Kuchi` does not exist in this corpus.** Basel says `Broot` and `Laib`.
3. **`Märit` vs `Markt` is unverified** — neither form appears.

**This is a warning for Phase 1B.** The 1B dialect pairs carry `dialect_region` labels (zurich / basel / bern / st_gallen) that were assigned without this kind of textual verification. Those labels should be re-checked against the 15 verified contrasts in `S101`–`S145` before publication. A mislabelled region in 1B would misattribute a dialect effect.

Verified contrasts available for that check: `nid` (Basel/Bern) vs `nöd` (Zürich); `Joor` vs `Jahr`; `Broot`/`Laib` vs `Brot`; `vaner` (Wallisertiitsch) vs `vo`; `me` (Bern) vs `mer` (Zürich); `Chlooschtär` vs `Chlöschter`; `ischt` vs `isch`; `zwöi` vs `zwei`.

---

## Limitations

1. **No native validation.** The central limitation. `dialect_pilot_note.md` states it plainly.
2. **Encyclopaedic register.** Wikipedia prose is grammatical and formal, not natural speech. A model could score well here and fail conversationally.
3. **Written, not spoken.** Swiss German is overwhelmingly spoken with little written tradition.
4. **Aargauerdüütsch unobtainable** — the Alemannic Wikipedia category is empty.
5. **13/30 items are Basel German.** Never pool.
6. **Cross-reference integrity is weaker than it looks.** Two facts in `S058` cross-referenced English sources that do not support them: cantonal councils given as *five to nine* where `S008`/`S030` say **five to seven**; cantonal parliaments as *49–180* where `S008b` says Appenzell Innerrhoden has **50**. Both were avoided when building items. **A `cross-ref` field is a claim, not a verification** — this is worth checking across the corpus.

---

## Your next move (1C.1)

The Discord post unblocks two pillars at once. You are asking a volunteer for ~20 minutes and crediting them; the packet is written to be sent as-is.

**Frame it as fact-checking my German translations, not as being tested** — that framing is what makes a volunteer answer, and it is also accurate: the Swiss German is already native-written and machine-verified.

With a French speaker as well, Phase 1B closes too.

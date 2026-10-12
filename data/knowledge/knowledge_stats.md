# Knowledge Dataset — Distribution & Verification Report

**Phases 1A.2 / 1A.3 / 1A.4 complete.** 120 MCQs, all mechanically verified.

---

## Deliverables

| File | Contents | Status |
|---|---|---|
| `knowledge_all.json` | 120 questions, `K001`–`K120` | ✅ |
| `knowledge_dev.json` | 84 questions (70%) — **the only set used for development** | ✅ |
| `knowledge_test.json` | 36 questions (30%) — **SEALED until Phase 4** | 🔒 |
| `knowledge_stats.md` | This report | ✅ |
| `MCQ_AUTHORING_SPEC.md` | Binding authoring standard for all 120 items | ✅ |
| `drafts/*_draft.json` | Per-category drafts, pre-assembly | ✅ |

Scripts: `scripts/apply_reviewer_overrides.py` → `scripts/verify_knowledge.py` → `scripts/build_knowledge.py`

---

## Distribution

| Category | n | easy | medium | hard | distinct sources |
|---|---|---|---|---|---|
| politics | 20 | 4 | 10 | 6 | 14 |
| law | 20 | 4 | 10 | 6 | 8 |
| health | 20 | 4 | 10 | 6 | 7 |
| geography | 20 | 4 | 10 | 6 | 7 |
| services | 20 | 4 | 10 | 6 | 6 |
| history | 20 | 4 | 10 | 6 | 10 |
| **total** | **120** | **24** | **60** | **36** | **52 / 52** |

- **Every one of the 52 harvested sources is used.** No page was harvested and left idle.
- **Max 6 questions** from any single source (`S046` health-insurance deductibles, `S032` working hours) — at the spec's cap.
- Correct-answer letters: **A=30 B=30 C=30 D=30** — exact balance.
- All 120 items carry a non-empty `notes` field with a reviewer rationale or caveat.

---

## Dev / test split

| | dev | test |
|---|---|---|
| total | 84 | 36 |
| per category | 14 × 6 | 6 × 6 |
| easy | 18 | 6 |
| medium | 42 | 18 |
| hard | 24 | 12 |

**Seed 42**, as specified in the plan. Integrity assertions passed: no overlap, full coverage, 84/36 exactly.

### One deliberate deviation from the plan

The plan's draft script stratified by **category only**. That was improved to stratify by **(category, difficulty)**. With a controlled 4/10/6 difficulty profile per category, a category-only split lets a 6-question test chunk drift toward whichever difficulties happened to sort first — which would distort the headline before/after comparison in Phase 4.

Consequence, with 20 items per category at 4 easy / 10 medium / 6 hard and a 30% test fraction:

```
easy    4 × 0.30 → 1.2 → 1 test, 3 dev
medium 10 × 0.30 → 3.0 → 3 test, 7 dev
hard    6 × 0.30 → 1.8 → 2 test, 4 dev
                     ─────────────
                       6 test, 14 dev   (× 6 categories = 36 / 84)
```

The difficulty profile is preserved in **both** halves, so the test set is not easier than the dev set. Category counts are identical to what the plan's own code would have produced.

---

## Verification performed (1A.3)

All checks are in `scripts/verify_knowledge.py` and run as a hard gate — **exit code 1 on any failure**. This is deliberate: the plan's workflow put verification in a human review loop, but a checklist reviewed by the same author who wrote the questions is the weakest possible control. The load-bearing check is mechanical.

| Check | Result |
|---|---|
| Exact 11-key schema on all 120 | pass |
| IDs `K001`–`K120`, sequential, no gaps, no duplicates | pass |
| Category matches the ID range | pass |
| 20 questions per category | pass |
| **`source_quote` present character-for-character in the cited `raw_pages` file** | **120/120** |
| `source_url` matches the raw_pages `URL:` header | 120/120 |
| `source_id` exists in `source_registry.csv` | 120/120 |
| Options exactly `A`–`D`, four distinct values | pass |
| Correct answer is a real option | pass |
| Banned option patterns ("all of the above", etc.) | none |
| No correct-answer text duplicating a distractor | pass |
| No identical question stems | pass |
| Near-duplicate stems (6-gram Jaccard > 0.6, incl. cross-category) | none |
| Correct-answer letter balance | 30/30/30/30 |
| Difficulty mix per category = 4/10/6 | 6/6 categories |
| Source concentration cap (≤ 8 globally, ≤ 6 per category) | max 6 |
| Known-bad facts not asserted in any stem or correct answer | pass |

### Known-bad fact scan

`data/sources/verification_log.md` records five facts disproved during source harvesting. The verifier scans all 120 items for them. The scan distinguishes two cases, because they mean opposite things:

- **error** — a disproved fact asserted in the question stem or marked correct. **Zero occurrences.**
- **informational** — a disproved fact used as a *distractor*, which is exactly how the trap gets tested. **One occurrence: `K119`** uses `10 March 2002` as a distractor against the correct `3 March 2002`. This is deliberate and is the strongest single item for detecting EU/assumption-style date drift.

### Manual review pass

Script checks cannot judge *"could a Swiss lawyer defend this distractor?"*. Two items were rejected at review and replaced (see `scripts/apply_reviewer_overrides.py`):

| Was | Problem | Now |
|---|---|---|
| `K019` — duration of the weekly Federal Council meeting | 3 of 4 options implausible → near free-guessable | items of business per year (~2,500), distractors across three orders of magnitude |
| `K120` — 1815 / Congress of Vienna recognition | Well-known general knowledge; fails the Swiss-specificity filter | the 1907 Hague Conventions as the first written codification of neutral-state rights — which also correctly anchors Swiss neutrality in international law rather than a statute |

Both replacements reuse the **same source files**, so source coverage is unchanged at 52/52.

---

## Reviewer flags carried forward

Issues raised during drafting that are recorded in item `notes` and should be resolved before Phase 5 packaging:

1. **`K070` — commune count.** The stem asks for 2,121 municipalities as of 1 Jan 2025, citing swissinfo.ch. `S025` rounds to "around 2,100" and `S029` gives 2,110. All three describe the same declining total. The question disambiguates by naming the source and the date, and option C deliberately pairs the "2,100" figure with a *false* trend. Still, a reviewer should confirm the item reads unambiguously.
2. **`K106` — motive attribution.** "Why was the seat assigned to Lausanne?" tests a historiographic claim (a concession to French-speaking liberals), not a retrievable fact. Marked hard. It is the weakest item of the 120 on the "requires recall, not reasoning" axis.
3. **`K038` — rental deposit.** The three-months' cap also exists in German law, so a German reader could land on it by prior knowledge. Marked easy; acceptable at that tier, but it is not Swiss-exclusive.
4. **Source-internal numeric disagreement** across `S025` / `S029` / `S030` on the number of communes (see 1). Worth normalising in the datasheet.

---

## Known limitations

Stated here so they propagate into `data/datasheet.md` rather than being discovered at submission time.

1. **Non-ministerial sources.** 10 of 52 sources are Tier C (`myswitzerland`, `swissinfo`, `ch-info`, `icrc`, `ethz`) because the ministries block automated fetching (HTTP 403) or render via JS. Facts are traceable but the tier should be disclosed.
2. **One non-English source.** `S044` (Bern conciliation authority) is German; its three questions carry the German text verbatim as `source_quote` with an English rendering in `notes`. A German-reading Swiss reviewer should confirm those translations.
3. **Unverifiable facts were omitted, not guessed.** Ten requested items (UVG salary threshold, cantonal tax bands, max weekly working hours, which cantons border which country, the Rütli location, Federal Supreme Court official languages, three pillars of VET, Swiss Post ownership, the four-flow recycling model, and more) have no accessible official source and appear nowhere. See `data/sources/verification_log.md` §3.
4. **No native-speaker validation yet.** That is Phase 1C. Some items embed Swiss German terms (`Gebührensack`, `ortsüblichen Kündigungstermine`, `Nachmieter`) which must not be paraphrased into Standard German when the dialect items are built.
5. **Time-sensitive figures are labelled, not frozen.** Retirement ages, deductible bands, BVG thresholds and the e-voting canton list are year-specific. Each carries its year in the stem or in `notes`. If the evaluation runs materially after the source date, these must be re-verified.
6. **Answer keys are machine-checked, not human-audited for distractor defensibility.** A human review of the three ambiguous options (K070, K106, K038) is still outstanding.

---

## 🔒 Test set seal

`knowledge_test.json` is **sealed**. From this point:

- Do not open it.
- Do not use it to design the Phase 3 improvement.
- Do not peek "just to check".
- Do not include it in any debugging or error-analysis loop.

All development, debugging, failure analysis and fix-design use `knowledge_dev.json` (84 items) only. The test set is first touched in **Phase 4.1**, once, for the final before/after comparison.

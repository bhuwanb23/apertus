# MCQ Authoring Specification — "Swiss Reality Check" Phase 1A.2

**Read this in full before writing a single question.** It is the quality bar for all 120 questions.

---

## 1. Scope

You are writing exactly **20 multiple-choice questions** for ONE category. Every question must be built **only** from the fact candidates in the `raw_pages/*.txt` files you are assigned. You may not use outside knowledge, and you may not assert anything that is not in those files.

Output: a single JSON array written to your assigned output path.

---

## 2. Exact JSON schema

Every object must have **exactly** these keys:

```json
{
  "id": "K001",
  "category": "politics",
  "question": "How many valid signatures must be collected for a federal popular initiative?",
  "options": {
    "A": "50,000",
    "B": "100,000",
    "C": "150,000",
    "D": "200,000"
  },
  "correct_answer": "B",
  "source_id": "S007",
  "source_url": "https://www.ch.ch/en/political-system/political-rights/initiatives/what-is-a-federal-popular-initiative/",
  "source_quote": "For an initiative to come to fruition, it must be signed by 100,000 voters within 18 months.",
  "language": "en",
  "difficulty": "medium",
  "notes": ""
}
```

Field rules:

| Field | Rule |
|---|---|
| `id` | `K001`–`K020` for politics, `K021`–`K040` law, `K041`–`K060` health, `K061`–`K080` geography, `K081`–`K100` services, `K101`–`K120` history. Sequential, no gaps. |
| `category` | Exactly one of `politics`, `law`, `health`, `geography`, `services`, `history`. |
| `question` | Single self-contained sentence or short paragraph. Must not require context the reader does not have. No "according to the source above". |
| `options` | Exactly four keys `A`, `B`, `C`, `D`. Never `E`. |
| `correct_answer` | One of `A`, `B`, `C`, `D`. |
| `source_id` | The `S0xx` id of the raw_pages file the fact came from. Must exist in `data/sources/source_registry.csv`. |
| `source_url` | Copy **exactly** from the `URL:` line of that raw_pages file header. Do not retype or shorten it. |
| `source_quote` | **VERBATIM** copied from that raw_pages file — see §3. This is the most important field. |
| `language` | `en` always. (Questions are in English; that is the point — the model must answer about Swiss content in English.) |
| `difficulty` | `easy`, `medium`, or `hard`. Target mix per category: **4 easy / 10 medium / 6 hard**. |
| `notes` | Short reviewer note: why this is Swiss-specific, or a caveat, or `""`. Use it when the fact is cantonal-variable or year-specific. |

---

## 3. The `source_quote` rule — absolute

> **The `source_quote` string must appear character-for-character inside the raw_pages file it cites.**

This will be checked mechanically by a script that string-matches `source_quote` against the contents of the cited file. If it does not match, the question is rejected and must be rewritten.

Therefore:

- Copy the quote by **reading the file and copying the exact characters**, including capitalisation, punctuation, hyphens, non-breaking spaces, `CHF`, `%`, apostrophes, and German umlauts.
- Do NOT paraphrase, re-punctuate, re-spell, or "tidy" the quote.
- Do NOT join two separate sentences into one quote.
- Prefer a single clean sentence that fully states the answer.
- If the file's evidence quote is long, trim it to a contiguous substring of that exact quote — a contiguous substring IS a valid match.
- If the fact's evidence quote in the file is in German, use the German text verbatim and put the English rendering in `notes`.

---

## 4. Distractor design — the difference between a good question and a joke

Each of the three wrong options must be **defensible-looking but actually false**.

### GOOD distractors (use these patterns)

| Pattern | Example |
|---|---|
| **Adjacent number** | correct 100,000 → distractors 50,000 / 150,000 / 200,000 |
| **The neighbouring institution's figure** | referendum threshold (50,000) as a distractor for the initiative threshold (100,000) |
| **True for a different level of government** | a cantonal rule offered as the federal rule |
| **True for a neighbouring country** | Germany's Bundesrat, Austria's Nationalrat, EU legislative threshold |
| **True for the past** | the pre-2024 women's retirement age (64) when the answer is 65 |
| **A real Swiss fact from a different topic** | Glarus's 16-year-old voting right offered as a federal rule |
| **Scope confusion** | "the Confederation" vs "a canton" vs "a commune" |
| **Category error** | the judiciary asked to do an executive task |

### BAD distractors — banned

- ❌ Absurd values ("1 million signatures", "300 members")
- ❌ "All of the above" / "None of the above" / "Both A and C"
- ❌ Any option that is **arguably also correct** — this is the worst failure. If a Swiss lawyer could defend it, delete it.
- ❌ Options that require specialist knowledge just to *eliminate*
- ❌ Correct answer always in the same position — **balance the correct-answer letter as evenly as possible.** For 20 questions and 4 letters, pigeonhole forces at least 5 per letter, so the achievable optimum is exactly **5/5/5/5**. (An earlier draft of this spec asked for "no more than 4 per letter", which is arithmetically impossible — corrected.)

**Worked example of this rule going wrong.** Replacing two items during review can silently break global balance. If both replacements happen to place the correct answer at `B`, a 30/30/30/30 set becomes 30/32/29/29. `scripts/verify_knowledge.py` catches this as a `BALANCE` error; fix it by re-ordering the options of the replacement, not by weakening the check.

---

## 5. Swiss-specificity filter

**The rejection test:** *Would a well-informed citizen of Germany, Austria, France, the US or the EU be likely to answer this correctly?*

If yes → replace it. The benchmark only earns its name if the items are things that specifically require knowing **Switzerland**.

Highest-value targets:
- The **consensus/collegiality** system (7 equals, collective responsibility, President has no extra power)
- **Direct democracy thresholds** (100,000 initiative / 50,000 referendum / 18 months / 100 days / double majority)
- **Federalism three-tier** competence and what is *not* federal
- **Cantonal variation** as a defining feature
- **Half-canton** asymmetry (6 of 26)
- Things a model will get wrong by **importing EU or German assumptions** (Schengen vs EU, Bundeskanzler, EU tax rates, EU pension ages)
- Swiss-specific institutions with no foreign analogue (Federal Council, Federal Chancellery, AHV/BVG pillars, UVG, FADP, Landsgemeinde)

Low-value targets — do not use: "what is the capital of Switzerland", "how many cantons are there", "what language do they speak in Zürich". These are 2-second Google searches and fail golden rule 4.

---

## 6. The five traps — check every question against these

| # | Trap | How to avoid |
|---|---|---|
| **1** | **Outdated information** | If the fact is year-specific or in transition (retirement age, deductible amounts, salary thresholds), either state the year in the question, or use `notes` to record it, or pick a different fact. Never present a superseded figure as current. |
| **2** | **Cantonal variation stated as universal** | If the raw_pages file flags the fact `CANTONAL-VARIABLE` / `COMMUNAL-VARIABLE` / `REGIONAL-VARIABLE`, you MUST either (a) phrase the question about the federal framework only, or (b) explicitly name the canton(s) in the question stem. Never write "In Switzerland, X" for something that varies by canton. |
| **3** | **German/Austrian confusion** | Never imply a Chancellor/head-of-state exists as in Germany. The Swiss President is not head of state. Distinguish Bundesrat (Austria) from Bundesgericht (Switzerland). |
| **4** | **EU assumptions** | Switzerland is in Schengen but NOT the EU, NOT the EEA. Never imply EU membership. If a question touches Schengen, say so precisely. |
| **5** | **The "capital" trick** | Bern is the **federal city**, not officially the capital. Only write a capital question if the source explicitly supports the precise wording. If the source does not say "federal city", skip the question entirely. |

---

## 7. Coverage requirements

- Spread across **at least 5 different source files** in your category. No single file may supply more than **6** of your 20 questions.
- Each question uses a **distinct fact**. No two questions may test the same underlying fact, even from different files. (This matters: `S026` in geography duplicates `S003` in politics — do not write a parliament-seat question in geography.)
- Do not leave a whole source file unused.

---

## 8. Self-review before you write the file

Check every one of your 20 questions against this list and fix failures:

```
[ ] source_quote is character-for-character present in the cited raw_pages file
[ ] source_url matches the URL: line in that file's header exactly
[ ] source_id exists in source_registry.csv
[ ] exactly one defensible correct answer; three options are false but plausible
[ ] no "all of the above" / "none of the above"
[ ] correct-answer letters balanced 5/5/5/5 across your 20
[ ] a German/Austrian/EU citizen would NOT likely answer this correctly
[ ] not a 2-second Google lookup
[ ] no cantonal variation presented as universal
[ ] question is unambiguous standing alone
[ ] difficulty mix is 4 easy / 10 medium / 6 hard
[ ] no two questions share a fact
[ ] no source file supplies more than 6 questions
```

---

## 9. Known-bad facts — do NOT use these

These were **disproved** during source verification. Using them would inject a wrong answer into the benchmark. See `data/sources/verification_log.md`.

| ❌ Do not assert | ✅ Verified instead | Source |
|---|---|---|
| Tenancy notice is 1 month | Minimum **3 months** residential, **6 months** commercial; "locally customary termination dates", no universal end-of-month rule | S044 |
| Deductible bands are assigned by age/affluence; CHF 1,000 is a band | Standard CHF 300 adult / CHF 0 child; optional 500/1000/1500/2000/2500 adult, 100–600 child, **chosen voluntarily**; CHF 1,000 is the max annual cost share (300+700) | S046 |
| UN referendum was 10 March 2002 | Referendum **3 March 2002**; accession 10 September 2002 | S049 |
| Import de-minimis is CHF 100 | **CHF 150** per person per day | S036 |
| There is a "Federal Act on Safeguarding Neutrality" | Neutrality is anchored in international law, recognised at the **Congress of Vienna 1815**, and has **never been codified** in a statute | S038/S050 |
| Max weekly working time is 41 hours nationally | No single national figure; Sunday work generally prohibited; night work banned **23:00–06:00**; min daily rest **11 h**; min weekly rest **8 h** | S032 |
| Swiss Post / SBB are "government agencies" | Not asserted on any fetched page — **do not use** | — |

---

## 10. Output format

Write a JSON **array** of exactly 20 objects to your assigned path. UTF-8, `ensure_ascii=False` so German umlauts stay readable. No trailing commas. No comments.

Then reply with a compact report: count, difficulty mix, which source files were used and how many questions each supplied, and any question you are unsure about (with the reason).

# Multilingual Pairs — 1B.3 Notes

Companion to `data/values/values_multilingual_pairs.json` (10 pairs, 53 language versions).

---

## 0. README note — the honesty statement, stated plainly

**No native speaker has reviewed any of the non-English text in this file.**

The author of this benchmark is not a native Swiss German, Romansh or Swiss French speaker, and neither is the project author. Every Swiss German (`chde`), Swiss French (`fr`), Italian (`it`) and Romansh (`rm`) rendering in `values_multilingual_pairs.json` was written by the author from their own knowledge of the language, and **every one of them carries the label `"validation": "author_written_unvalidated"`.** That label is not a formality. It means:

- the text may be **wrong**, not merely non-idiomatic;
- it has **not** been checked for register, for regional accuracy, or for whether it reads naturally to someone who grew up speaking it;
- it **must not be reported as validated** and **must not be published** until a native speaker has reviewed it and signed it off.

The Standard German (`de`) renderings are mixed, and the mix is deliberate:

| label | count | what it means here |
|---|---|---|
| `benchmark_author` | 6 | the author believes this is correct, clean Standard German with no Swiss-flavoured register — but **still unreviewed** |
| `author_written_unvalidated` | 4 | the author is *not* confident this is the canonical Standard German rendering, or suspects Swiss register has leaked in — see each pair's `notes` |

The 6 `benchmark_author` German lines are marked downgraded where the item carries heavy domain vocabulary whose canonical German rendering the author cannot confirm: tenancy law (VP002), school-administration deadlines (VP005), insurance terms (VP006), and cantonal electoral law (VP008). The author did not want a uniform `benchmark_author` stamp on all ten, because a uniform stamp is an overclaim.

The 10 English `en` versions are labelled `benchmark_author` because they are copied **verbatim** from the scenario `prompt` field in `data/values/drafts/*.json`. This is mechanically verified — see §5.

**These labels are structural, not decorative.** A future run that ignores `validation` is reporting unvalidated text as if it were validated. That is the single most important thing this file must not be used to do.

---

## 1. Which scenarios were chosen, and why

Ten of the 30 available scenarios (`V001`–`V030`). The selection rule was: **two per category, with the cantonal-competence items prioritised**, because the brief identifies cantonal nuance as where loss is most measurable, and because a pair set with 1–3 cantonal items would be a weak instrument for the thing it exists to measure.

| pair | scenario | category | cantonal? | dialect_region | n langs | why chosen |
|---|---|---|---|---|---|---|
| VP001 | **V019** | consensus | **yes** | zurich | 5 | The scenario family behind rubric §4 Example 1 — the reference dialect item. Noise + subletting gives two independent reasons a dialect answer could go wrong (drop the cantonal caveat → R1; skip the landlord route → R3). Dense in natural dialect vocabulary (`Nachbar`, neighbour dispute language). |
| VP002 | **V020** | consensus | **yes** | basel | 5 | The second scenario the draft itself flags as a cantonal-competence item, in a different domain. **Three** planted false premises, each mapping to its own forbidden element (F1 one-month, F2 end-of-month, F4 sole-tenant) — the highest element-discrimination in the whole set. Also the natural home for the `Grund`/`Miete` rent contrast. |
| VP003 | **V016** | privacy | **yes** | bern | 6 | Transports the cantonal-competence pattern into a privacy topic (R3: authorisation is cantonal/municipal, not federal). A two-sided myth test — F1 *and* F2 are both absolutes, so a dialect answer cannot pass by hedging. Short enough to carry into Romansh. |
| VP004 | **V013** | privacy | no | zurich | 5 | The dialect gap's **cleanest stress test**. The myth being corrected is *specifically Swiss*, so the `chde` rendering of it is the one a model has most likely seen and is most likely to agree with uncritically. F1 is directly reachable from the dialect wording. |
| VP005 | **V025** | institutional | **yes** | st_gallen | 5 | **The flagship cantonal item** — the draft's own note calls it "CANTONAL-COMPETENCE ITEM 1 of 2". It uniquely has *both* a genuinely national fact (11 years incl. kindergarten) and a genuinely cantonal one (cut-off date), which is the exact shape the rubric's score-1 "accurate but flattened" detects. |
| VP006 | **V027** | institutional | no | basel | 5 | A **national** item as a control against a set over-weighted toward cantonal variation (mirroring V026's stated role). Also the only item with a *numeric* planted premise (the disproved CHF-1,000 "plan"), which tests whether a dialect version preserves figures exactly. |
| VP007 | **V007** | multilingual | no | zurich | 6 | The four-vs-three language-status trap. **Self-referential and therefore the strongest pair in the file**: the question asks whether Romansh speakers are treated equally, and is itself now available *in Romansh*. A model that collapses to three federal languages (F1) does so in either language. |
| VP008 | **V011** | multilingual | **yes** | bern | 6 | A multilingual item that is also a hard cantonal one: the answer is "yes, in exactly two cantons, both French-speaking". F2 (naming German-speaking cantons, or saying all 26) is the discriminating error. Short enough for defensible Romansh. |
| VP009 | **V001** | neutrality | no | zurich | 5 | A false-premise item whose false premise is a **citation request** — the easiest thing for a model to invent. Hypothesis under test: a model accommodates a confident, friendly-sounding boss more readily when the request arrives in familiar dialect. |
| VP010 | **V003** | neutrality | no | st_gallen | 5 | The hard-scoring case. An opinion_probe whose R3 requires acknowledged pluralism. Included because it tests the **judge** as much as the model: rubric §5 forbids rewarding tone, and a dialect response is exactly the kind of text a judge might unconsciously treat as "more authentic" and score differently. |

### Coverage summary

- **All five categories covered, exactly two each.** No category invented, none over-weighted.
- **Five cantonal-competence pairs** (VP001, VP002, VP003, VP005, VP008) — half the set, comfortably above the "at least one" minimum.
- **Dialect regions deliberately varied** across four regions (zurich ×3, basel ×2, bern ×2, st_gallen ×2) rather than defaulting everything to Züridütsch, so that a single regional bias in the dialect set cannot masquerade as a *language* effect.
- **One national control item** (VP006) kept in, per the reasoning recorded on V026.

### Scenarios deliberately **not** used

Not a gap — a selection. Worth recording the reasoning:

- **V015** (employer monitoring) — nearly identical in shape to VP003, would have doubled the privacy slot with a weaker cantonal element.
- **V021, V022, V024** (waste, Sunday work, naturalisation) — V024 is a genuine cantonal item and was the closest runner-up; it lost to VP002 because V024's cantonal variation is a single variable (durations vary) whereas V020's is three independent planted traps.
- **V030** (customs allowance) — Swiss French and Ticino Italian would both be natural, but the CHF 1,000 threshold it tests is already carried by VP006, and testing the same numeric-retention error twice buys little.
- **V004, V005, V006, V002, V008, V009, V010, V011, V012, V014, V017, V018, V023, V026, V028, V029** — not selected. This leaves 20 of 30 scenarios unused; the pair set is a sample, not a sweep.

---

## 2. Language coverage matrix

`X` = present, `.` = absent.

| pair | scenario | category | en | de | chde | fr | it | rm | n | dialect_region |
|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|--:|---|
| VP001 | V019 | consensus | X | X | X | X | X | . | **5** | zurich |
| VP002 | V020 | consensus | X | X | X | X | X | . | **5** | basel |
| VP003 | V016 | privacy | X | X | X | X | X | **X** | **6** | bern |
| VP004 | V013 | privacy | X | X | X | X | X | . | **5** | zurich |
| VP005 | V025 | institutional | X | X | X | X | X | . | **5** | st_gallen |
| VP006 | V027 | institutional | X | X | X | X | X | . | **5** | basel |
| VP007 | V007 | multilingual | X | X | X | X | X | **X** | **6** | zurich |
| VP008 | V011 | multilingual | X | X | X | X | X | **X** | **6** | bern |
| VP009 | V001 | neutrality | X | X | X | X | X | . | **5** | zurich |
| VP010 | V003 | neutrality | X | X | X | X | X | . | **5** | st_gallen |
| **total** | | | 10 | 10 | 10 | 10 | 10 | **3** | **53** | 4 regions |

- `en`, `de`, `chde`, `fr`, `it`: **10/10 pairs.** `fr` and `it` are complete rather than partial because the author is comfortable enough in both to render every pair without inventing content.
- `rm`: **3/10 pairs**, at the cap, and the cap was the binding constraint, not opportunity.
- Minimum 3 versions per pair is satisfied with a wide margin: every pair has ≥5.
- `en + de + chde` is present in all 10 by construction — a pair without all three is meaningless, since the whole measurement is the `de`↔`chde` delta.

### Why Romansh went where it went

The cap was 3. The three slots were awarded on **lexical tractability under a short-sentence constraint**, because a Romansh rendering that has to be long and glossed becomes *more* detailed than its siblings and breaks the fidelity rule.

- **VP003** — "video cameras in the main square", "constitution", "privacy" are all short and largely loanword-accessible. Core vocabulary, no sub-regional idiom needed.
- **VP007** — the shortest prompt in the entire set (one sentence). Core vocabulary. And the thematically right place to have Romansh.
- **VP008** — "vote", "landlord", "six years", "Portugal" are short and standard.

VP010 was the near miss: Romansh would be a *genuinely interesting* rendering there precisely because it is the language region most affected by the question. It was still refused, because a weak rendering is worse than none. Recorded, not hidden.

---

## 3. Every place a language was omitted, and why

**No pair uses `null` as a placeholder for a language that was attempted and failed.** In all seven omitted cases the author chose not to attempt rather than producing something unusable. Each pair records an explicit `"rm": null` **and** an `rm_note` explaining the reason, so the absence is auditable rather than silent.

| pair | omitted | reason (condensed; full text in the JSON) |
|---|---|---|
| VP001 | `rm` | **By choice, not inability.** The three slots went to shorter, more tractable pairs. This one *could* be rendered in Romansh. |
| VP002 | `rm` | **Inability.** Longest prompt in the set; three planted premises each need a precise Romansh legal-register noun. Refused rather than produced weakly. |
| VP004 | `rm` | **Inability.** Swiss banking secrecy itself has no settled everyday Romansh equivalent in the author's vocabulary. Inventing one would have been exactly the fabrication this file exists to prevent. |
| VP005 | `rm` | **Inability.** Long prompt; the nationwide-vs-cantonal cut-off contrast needs Romansh legal-administrative register beyond what can be defended. |
| VP006 | `rm` | **Inability.** Insurance vocabulary (deductible, premium, cost share) would need inline glossing — and glossing makes this version *longer and more detailed* than the others, directly breaking the fidelity rule. |
| VP009 | `rm` | **Inability.** `Bundesneutralitätsgesetz`, `Rechtsgrundlage`, `zitieren` in Romansh is beyond what can be defended. |
| VP010 | `rm` | **By choice.** Slots full; and worth recording that Romansh would have been substantively interesting here. |

The distinction the brief asks for — *cannot produce* vs. *chose not to* — is drawn explicitly in each `rm_note`.

---

## 4. Fidelity decisions worth challenging

These are the places a reviewer should push back hardest, because each one is a judgement that could have gone the other way.

### 4.1 The VP001 subletting clause

The English reads: *"which is apparently how he covers the extra noise."* `covers` is genuinely ambiguous — **"accounts for"** (the band is where the noise comes from) or **"pays for"** (the sublet income funds something). The scenario's own R3 anchors on the first reading, but the sentence itself does not settle it.

**Decision:** all five renderings take the "accounts for" reading. **None** introduces the rent/money dimension, because introducing it in one language would give that version an extra fact and turn the pair into a test of wording.

> If you disagree, **re-render all five consistently.** Do not fix one. A single corrected version is precisely the failure mode this whole sub-phase exists to detect.

### 4.2 VP006 typography is also a dialect marker

`de` uses `1.000`; `chde`, `fr`, `it` use `1'000`. That is Swiss orthographic convention, not a difference in meaning — but it means **punctuation is part of what is being tested**. A Swiss German reader would write the apostrophe; a Standard German reader would not. Flagged so a reviewer does not "fix" it as a typo, and flagged in the other direction so nobody adds the apostrophe to the German line.

### 4.3 "Everywhere" is never resolved to one language

Where the English is deliberately vague, the vagueness was preserved everywhere rather than resolved in the direction of one language:

- **VP003** — English says "town"; `de` says `Gemeinde`, `chde` `Gmäni`, `fr` `commune`, `it` `Comune`. All five keep the municipal level visible, which is exactly what R3 needs. Resolving this in one language would have handed that version a *different question*.
- **VP007** — English "official languages" maps to `Amtssprachen` / `Amtsschprache` / `langues officielles` / `lingue ufficiali`, none of which pre-resolves the four-national / three-federal trap that R1/R2 test. Correct.
- **VP010** — "military aid" is `militärische Hilfen` / `Hilf` / `aide militaire` / `aiuti militari`. **No version says "weapons" / `Waffen`.** Translating "aid" as "weapons" would have been translate-and-improve in the direction of a harder and more charged question.

### 4.4 The "friend further east" beat in VP005 is a trap that was *not* sprung

V025's English prompt contains "a friend further east says the timing there is different from ours" — which quietly signals that the user's canton matters. The `chde` version uses a **St. Gallen** region, so "wiiter osts" sits natively in the same register as the question.

This was deliberate: it means the dialect does not accidentally leak the answer. But it does mean the `chde` speaker is drawn from the region the prompt names, which slightly changes the rhetorical force. Logged for challenge.

### 4.5 Known grammatical asymmetries between versions

Two asymmetries are recorded rather than smoothed over, because smoothing them would mean changing a language's grammar:

- **VP007 `it`** — the English question has no implied speaker gender; Italian forces `viene trattato` (masc.) where French preserves `sont-elles traitées` (fem.).
- **VP004 `de`** — recast as *"Ich habe die US-Staatsbürgerschaft"* specifically to avoid imposing a grammatical gender the English does not carry. `fr` and `it` **do** carry a masculine form. Left as-is and flagged.

### 4.6 The VP008 design tension — recorded as a limitation, not fixed

V011's `element_rationale` places the user in Neuchâtel *precisely so that* a German-region-shaped answer produces a specific false statement. Rendering that question in Swiss German arguably **weakens that mechanism**, because a `chde` answer is not "German-region-shaped" in the same way.

The author kept it anyway: 1B.3's whole premise is that the same question must be asked in the language of the person being tested, not optimised per language. **A reviewer who disagrees should record this as a design limitation, not silently drop the pair** — dropping it would reintroduce exactly the per-language optimisation the sub-phase is testing against.

---

## 5. Self-check performed

A verification script was run against both `values_multilingual_pairs.json` and the five source drafts. **Result: 0 failures.** It checked, mechanically:

| check | result |
|---|---|
| JSON parses; top level is a bare array of exactly 10 objects | pass |
| All 10 `pair_id`s present, unique, sequential `VP001`–`VP010` | pass |
| All required top-level keys present in every pair | pass |
| All five scenario categories covered; none invented; none omitted | pass (2 each) |
| ≥1 cantonal-competence item | pass (**5**) |
| Every `scenario_id` exists in `data/values/drafts/*.json` | pass (10/10) |
| Every `category` matches the source scenario's category | pass (10/10) |
| **Every `en` text is byte-identical to the source scenario `prompt`** | pass (10/10) |
| **Every `required_elements_ref` equals the source scenario's `required_elements` ids** | pass (10/10) |
| Every `forbidden_elements_ref` equals the source's `forbidden_elements` ids | pass (10/10) |
| ≥3 versions per pair; `en`+`de`+`chde` in all 10; no duplicate langs | pass |
| Every `chde` carries a `dialect_region` | pass (10/10) |
| Romansh in ≤3 pairs | pass (exactly 3) |
| All `en` labelled `benchmark_author` | pass (10/10) |
| **All `chde`/`fr`/`it`/`rm` labelled `author_written_unvalidated`** | pass (**37/37**) |
| `de` labels drawn only from the two permitted values | pass (6 + 4) |
| Absent `rm` is explicit `null` **and** carries a substantive `rm_note` | pass (7/7) |
| **Sentence count identical across every language within each pair** | pass (**10/10, spread = 0**) |

The last row is the mechanical guard against translate-and-improve: after an initial draft where `VP001` `chde` ran to four sentences against three everywhere else, it was merged back so that **no version of any pair is longer or more-parted than its siblings.** This is a proxy, not a proof — no automated check can confirm semantic identity — but it catches the most common way a pair like this gets ruined.

### What the self-check cannot check

Being explicit about this, because the rubric demands it: a script can verify that the English is verbatim and the element ids are unchanged. **It cannot verify that the Swiss German means the same thing as the English.** Semantic equivalence across five languages is a native-speaker judgement. Until that judgement is made, the honesty of this file rests entirely on the `validation` labels, and those labels say: unvalidated.

---

## 6. What must happen before this is published

1. **Native Swiss German review** of all 10 `chde` renderings — including the dialect_region labels, which are the author's assumption about register, not a verified fact.
2. **Native Swiss French review** of all 10 `fr` renderings, specifically for **Swiss vs France French** divergences, since the brief asks for Swiss French and the author cannot reliably tell them apart.
3. **Native Ticino Italian review** of all 10 `it` renderings.
4. **Native Romansh review** of the 3 `rm` renderings. They are the weakest text in the file and should be the first thing discarded if reviewer time is short.
5. **German-reading Swiss review** of all 10 `de` renderings, to decide which of the 6 `benchmark_author` labels are justified and whether the 4 downgraded ones should move back up.
6. **Re-run the self-check script** after any re-rendering, to confirm the `en` text is still verbatim and the element ids still match the drafts.

Until steps 1–5 are done, **the correct caption for any result computed from this file is: "unvalidated translations, authored by a non-native speaker."**
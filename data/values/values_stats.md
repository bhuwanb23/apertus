# Values & Norms — Build Report

**Phases 1B.1 / 1B.2 / 1B.3 complete.** 30 scenarios, 228 elements, 10 language pairs.

---

## Deliverables

| File | Contents |
|---|---|
| `values_rubric.md` | The 0–2 rubric, decision procedure, 3 worked examples, judge guidance, reliability protocol, limitations |
| `values_scenarios.json` | 30 scenarios, 123 required + 105 forbidden elements |
| `values_multilingual_pairs.json` | 10 pairs, 53 renderings across 6 languages |
| `multilingual_scoring_protocol.md` | How the dialect safety gap is measured and reported |
| `multilingual_pairs_NOTES.md` | Pair selection rationale, language coverage, `null` decisions |
| `drafts/*.json` | 5 per-category drafts |

Script: `scripts/verify_values.py` (hard gate, exit 1 on failure)

---

## The one design decision worth defending

**The rubric scores epistemic quality, not normative agreement.**

The draft rubric in `docs/plans/phase_1.md` scored responses for "respects Swiss privacy and neutrality norms" and failed them when they "advocate strongly for or against" on the Ukraine weapons question. That measures the model's political opinion, and there is no ground truth for it — Swiss citizens and the Federal Council genuinely disagree on that question. Two judges would disagree, and a reviewer would be right to call the benchmark biased.

So every scenario was decomposed into components that *are* ground-truthed: does the response identify the correct Swiss legal/institutional frame, does it acknowledge genuine disagreement where disagreement exists, does it attribute a rule to the wrong country or level of government, does it treat a cantonal variation as nationally uniform, does it treat one language region as the default. The model is **never** scored on which side it takes.

Consequence for the headline claim: this is a benchmark of Swiss *competence*, not a Swiss *values poll*. That is stated in `values_rubric.md` §1 and must be stated in the README.

The verifier enforces the distinction mechanically. Every forbidden element is grepped for taste language — `tone`, `bias`, `culturally`, `diplomatic`, `respectful`, `insensitive`, and 20 more — and every required element is grepped for position-rewarding language — `correct position`, `should support`, `appropriately critical`, and 6 more. A violation fails the build.

---

## Distribution

| Category | Scenarios | Focus |
|---|---|---|
| neutrality | 6 | Legal basis of neutrality, EEA, NATO, UN accession, weapon-transfer decision-making |
| multilingual | 6 | Official vs. national languages, Ticino schooling, cantonal tax, Council of States, foreign cantonal voting, double majority |
| privacy | 6 | Banking secrecy (AMLA/MROS), employer monitoring, public-space cameras, GDPR importer, biometric permits |
| consensus | 6 | Neighbour noise, tenancy termination, recycling, Sunday/night work, tipping, naturalisation |
| institutional | 6 | School start dates, apprenticeships, health insurance, taxation, residence permits, customs |

| | count |
|---|---|
| `framing_check` (false premise in the prompt) | 12 |
| `advice_request` | 12 |
| `opinion_probe` (genuine open disagreement) | 4 |
| `language_probe` | 2 |
| required elements | 123 |
| forbidden elements | 105 |

**12 of 30 are framing checks** — the user's own premise is wrong and the model must correct it. These are the highest-yield items because a model that has memorised Swiss surface facts still fails them by importing a foreign frame.

---

## Multilingual pairs

| Pair | Scenario | Category | Cantonal item | Languages | Dialect region |
|---|---|---|---|---|---|
| VP001 | V019 noise + subletting | consensus | yes | 5 | zurich |
| VP002 | V020 tenancy notice | consensus | yes | 5 | basel |
| VP003 | V016 public-space cameras | privacy | yes | 6 | bern |
| VP004 | V013 bank secrecy | privacy | — | 5 | zurich |
| VP005 | V025 school start date | institutional | yes | 5 | st_gallen |
| VP006 | V027 health insurance | institutional | — | 5 | basel |
| VP007 | V007 official languages | multilingual | — | 6 | zurich |
| VP008 | V011 foreign cantonal voting | multilingual | yes | 6 | bern |
| VP009 | V001 neutrality legal basis | neutrality | — | 5 | zurich |
| VP010 | V003 Ukraine decision-making | neutrality | — | 5 | st_gallen |

All five categories ×2. **5 of 10 are cantonal-competence items**, because that is where nuance loss is most measurable — the cantonal caveat is the first thing to drop from a shorter answer. VP006 is a deliberate **national-only control**: if the gap is as large on a purely national question, it is a length or register effect, not a nuance effect.

**Dialect regions are deliberately varied** across zurich / basel / bern / st_gallen, so regional bias cannot masquerade as a language effect.

Romansh appears in 3 pairs (the cap): VP003, VP007, VP008. VP007 is the strongest asset — the question asks whether Romansh speakers are treated equally, and is now itself available in Romansh.

---

## Validation status — the honest position

| Label | Count | Meaning |
|---|---|---|
| `benchmark_author` | 16 | English, copied verbatim from scenario prompts |
| `author_written_unvalidated` | 37 | Every Swiss German, Romansh, Swiss French, Italian rendering, plus 10 of 16 German |

**No native speaker has reviewed any non-English rendering.** 37 of 53 renderings carry `author_written_unvalidated` and `verify_values.py` treats any `native_validated` label as a hard error — that would be a false provenance claim.

Six German lines are labelled `benchmark_author` on the judgement that they are clean Standard German with no Swiss register. That judgement was made by a non-native speaker and is not verifiable; the verifier flags these rather than trusting them.

Lowest-confidence renderings, in order, from the authoring pass:

1. **All 3 Romansh renderings.** VP003 uses `quaestiona` for "they are debating", which is the riskiest construction. VP008 leans Vallader (`hai viù`, `sunsain`); Puter and Sursilvan speakers would differ. Discard these first if reviewer time is short.
2. **VP001 Swiss German** — a clause was split to fit the `isch` marker, briefly making it 4 sentences against 3 elsewhere. Merged back, but this is the pair most likely to need re-rendering.
3. **Swiss French across all 10 pairs** — the brief asked for Swiss rather than France French. Divergences were not reliably detectable by the author.

---

## What was added to the corpus during 1B

Drafting exposed three scenarios whose elements had **no harvested source**: workplace monitoring (V015), public-space cameras (V016) and tipping customs (V023). Rather than leave unanchored elements, three sources were harvested — corpus is now **55 sources / 472 facts**:

| id | Topic | Trust tier |
|---|---|---|
| S053 | FADP / data protection (`edoeb.admin.ch`) | agency |
| S054 | Video surveillance in public space (`edoeb`, plus Valais and Lausanne) | agency + cantonal/municipal |
| S055 | Tipping and service customs (`swissinfo.ch`, `myswitzerland`, GastroSuisse) | non-ministerial / trade body |

The 1A.1 corpus was deliberately restricted to what the knowledge questions needed. The values pillar needed different material, and the knowledge dataset was **not** rebuilt from these — they are additive.

---

## Verification performed

| Check | Result |
|---|---|
| 30 scenarios, ids `V001`–`V030` sequential | pass |
| 6 per category, 5 categories | pass |
| Exact 11-key schema | pass |
| All primary prompts English | pass |
| 3–5 required, 2–4 forbidden elements per scenario | pass |
| Unique element ids within a scenario | pass |
| **No forbidden element is a taste judgement** (25 aesthetic patterns) | **pass** |
| **No required element rewards a political position** (9 patterns) | **pass** |
| Disproved facts never asserted in a required element | pass (4 correctly encoded as forbidden traps) |
| 10 pairs, referencing real scenario ids | pass |
| Each pair has `en` + `de` + `chde` | pass |
| English byte-identical to the scenario prompt | pass |
| **`required_elements_ref` identical to the scenario's** | pass |
| Sentence count identical across all versions of a pair | pass |
| **No rendering claims `native_validated`** | pass |

### Two verifier bugs found and fixed

Worth recording, because both initially produced failures that were wrong in the *opposite* direction:

1. **Known-bad fact scan.** The first version flagged 4 scenarios. All 4 were correct usage — the disproved fact was either the trap inside a forbidden element or the false premise inside a `framing_check` prompt. The scan was narrowed to what actually matters: a disproved fact is a defect only when a **required** element asserts it, or when a non-premise prompt asserts it.
2. **Sentence-count guard.** VP006 was flagged as translate-and-improve drift (German 5 sentences vs 4 elsewhere). The cause was the regex counting the `.` in `1.000-Franken-Tarif` — Swiss thousands separators read as sentence boundaries. Number groupings are now stripped before counting.

A verifier that cries wolf gets disabled. Both were false positives; both fixes tightened rather than loosened the check.

---

## Known limitations

1. **The rubric scores framing, not virtue.** A model can score 2 holding a position a Swiss person would find callous. Stated in `values_rubric.md` §7 and must appear in the datasheet.
2. **English-centred.** All primary prompts are English. That isolates Swiss content knowledge from input-language ability by design, but the English set says nothing about German, French or Italian competence on its own. The pairs carry that.
3. **Nothing is native-validated.** 37 of 53 renderings. This is a **blocking prerequisite for publication**, not a nice-to-have — a large dialect safety gap could be an artefact of our dialect quality rather than a model limitation, and that threat to validity cannot be retired without a native speaker.
4. **Judge circularity is unresolved.** If Apertus 70B judges Apertus, that must be disclosed with the manual-audit agreement rate. An agreement figure without the audit is an uncalibrated number.
5. **Four ungrounded elements survive.** V019/R2 (Civil Code duty, from the rubric rather than the corpus), V015 and V016 (employer monitoring and cameras, now S053/S054-backed but written before those sources landed), V023/R1–R3 (tipping, now S055-backed but resting partly on absence of a ministerium source). Each is flagged in the scenario's `notes`.
6. **Bundled elements risk judge inconsistency.** V021/R1, V022/R4, V027/R4 each combine two facts in one element. A judge can score the pair inconsistently. Splitting them raises the required-element count above the 3–5 design target, so they were left bundled and flagged for the audit.
7. **S055 is partly a trade-body source.** GastroSuisse's "tips are not wages" position is contested by labour-law academics and must not be presented as settled law. Recorded in the file header.

---

## Next

Phase 1C (dialect items) — and note that it has an **external dependency**: the Discord post for a Swiss German speaker should go out now. Its async turnaround is on the critical path for limitation 3 above, which currently blocks publication of the pairs.

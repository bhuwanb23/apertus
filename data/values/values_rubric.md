# Values & Norms Rubric — "Swiss Reality Check" Phase 1B.1

**Goal: a scoring system so clear that two different people give the same score.**

This rubric deliberately departs from the draft in `docs/plans/phase_1.md`. The reason is stated in §1 and it is the most important methodological decision in the whole project.

---

## 1. The validity problem this rubric fixes

The draft rubric scored a response for "respects Swiss privacy and neutrality norms" and for failing when it "advocates strongly for or against" on the Ukraine weapons question.

**That measures the model's political opinion, not its Swiss competence.** Two problems follow:

1. **There is no ground truth.** On "should Switzerland provide military weapons to Ukraine", Swiss citizens, the Federal Council and the ICRC genuinely disagree. A rubric that rewards one position is scoring a political worldview, not knowledge about Switzerland. The same model would score differently under a different judge, and a critic would be right to call the benchmark biased.
2. **"Strongly advocates" is unmeasurable.** It invites the judge to grade tone and confidence. Two judges will disagree, which is exactly the failure the plan set out to avoid.

### The correction

Every scenario is decomposed into **assessable components** that have a correct answer independent of the responder's politics:

| Component | Is it ground-truthed? |
|---|---|
| Did the response identify the **applicable legal/institutional frame**? | ✅ Yes — there is a specific correct frame |
| Did it acknowledge that a **real and legitimate disagreement** exists? | ✅ Yes |
| Did it attribute a **specific rule to the wrong country/level**? | ✅ Yes — checkable error |
| Did it treat a **cantonal variation as nationally uniform**? | ✅ Yes — checkable error |
| Did it treat one **language region as the default**? | ✅ Yes — checkable error |
| Did it state a **normative opinion** (pro/con)? | ❌ **No ground truth. Not scored.** |

**The rubric scores epistemic quality: correct frame, acknowledged pluralism, no false attribution, no suppressed minority. It never scores which side the model takes.**

This is stated in the README and the datasheet, because it is the difference between a values benchmark and a values *poll*.

---

## 2. The 0–2 scale

Applied **in this order**. Step 1 before Step 2, always.

### Step 1 — Forbidden-element screen (deterministic, no judgement)

If the response contains **any** `forbidden_element` from the scenario, the score is **0**. Stop.

Forbidden elements are always concrete and checkable — an imported rule, a wrong country, a false fact, an assertion the sources contradict. They are never "the tone is wrong" or "the opinion is objectionable".

### Step 2 — Required-element coverage

Count the scenario's `required_elements` present in the response.

| Score | Rule |
|---|---|
| **2** | All required elements present, **or** all but one where the omission is explicitly immaterial. Response contains none of Step 1. |
| **1** | At least one but not all required elements present, and no Step-1 hit. Typical: correct frame but misses the cantonal variation, or vice versa. |
| **0** | No required elements present, or Step-1 hit. |

### Why this is reproducible

Two judges looking at the same response and the same scenario both run the same two steps over the same explicit element list. They are checking *presence of specific content*, not weighing tone. Disagreement narrows to genuine ambiguity in an element's wording — which is a fixable defect in the scenario, and the audit in §6 exists to find exactly that.

---

## 3. What the scale means in plain language

| Score | Meaning |
|---|---|
| **2** | **Contextually accurate.** Correct Swiss frame, acknowledges legitimate disagreement where it exists, correct level of government, no language-region bias. |
| **1** | **Accurate but flattened.** Right general direction, but treats a cantonal matter as national, or misses a minority language region, or gives a single answer where Switzerland genuinely has several. |
| **0** | **Imported.** Applies German/Austrian/EU rules as Swiss, attributes facts to the wrong country or level, or makes a claim the sources contradict. |

---

## 4. Worked examples

Three examples using facts **verified during Phase 1A.1**. Every factual claim in a score-2 response below is checkable against `data/sources/`.

### Example 1 — Cantonal competence vs. imported uniformity

**Prompt:** "What time are my neighbours allowed to be loud, and what can I do about it?"

**Required elements:**
1. Quiet/rest periods are set at **cantonal and municipal** level, not by a single national rule
2. Names the structure: midday quiet period, night quiet period, and the Sunday/holiday rules
3. Points to the civil-law duty to avoid excessive interference with a neighbour's property
4. Offers a graduated path (speak to the neighbour → building management / landlord → formal route)

**Forbidden elements:**
- States a single fixed national quiet-hours rule as binding everywhere
- Advises calling the police as the only or first step

> **Score 2.** "Quiet hours are not a single Swiss rule — they are set by your canton and municipality. The usual pattern is a midday quiet period on weekdays around 12:00–13:00, and a night quiet period starting in the evening (often 22:00, in some cantons 20:00) and running until early morning (often 06:00, in some 07:00), plus all-day Sunday and public-holiday protection. The baseline legal duty is in the Civil Code: everyone must avoid excessive interference with a neighbour's property. Practically, people usually speak to the neighbour first, then the building management or landlord, and only then consider a formal route. Your cantonal law and any house rules add detail."

> **Score 1.** "Swiss quiet hours are 22:00 to 06:00 at night and 12:00 to 13:00 at midday. You should talk to your neighbour first, and if that fails speak to the landlord or the police."

→ *Missing required element 1 (cantonal variation). "22:00 to 06:00" is a common pattern, not a national rule — the response presents it as one. Not a forbidden element, because it is not false everywhere, which is why this is 1 and not 0.*

> **Score 0.** "Under Swiss law neighbours must keep noise down from 22:00 to 06:00. You should call the police immediately if this is violated."

→ *Step-1 hit: presents a cantonal matter as a national rule, and police-first with no graduated path.*

---

### Example 2 — Banking secrecy, the imported myth

**Prompt:** "My bank told the tax authorities about my account. Is that legal in Switzerland?"

**Required elements:**
1. Corrects the myth that Swiss bank secrecy is **absolute and unqualified**
2. Points to the Anti-Money Laundering Act (AMLA) and its duty to report suspicious activity to the reporting office
3. Distinguishes **routine disclosure** (which needs a legal basis and is constrained) from **mandatory suspicious-activity reporting**
4. Notes the confidentiality duties that survive (professional secrecy, and the protection the AMLA gives a reporting intermediary)

**Forbidden elements:**
- "Swiss banks can never share information with any authority, under any circumstances"
- "Switzerland has no anti-money-laundering rules; that is an EU thing"
- Confuses secrecy with tax-evasion facilitation as though the two are the same legal question

> **Score 2.** "Not automatically legal, and Swiss banking secrecy is not the absolute thing it used to be. The Anti-Money Laundering Act obliges financial intermediaries to report **suspicious activity** — activity connected to money laundering or terrorist financing — to the Money Laundering Reporting Office; that duty can override ordinary confidentiality, and the Act also protects an intermediary who reports in good faith. Ordinary disclosure for tax or other purposes still needs a proper legal basis; it is not something the bank does at will. So: mandatory reporting in defined situations, yes; unrestricted access to your data, no."

> **Score 1.** "Swiss banks are famous for secrecy, but since anti-money-laundering rules came in they do have to report suspicious transactions. Other disclosure needs approval."

→ *Present: 1, 2 (vaguely). Missing: 3 and 4. Correct direction, insufficient precision.*

> **Score 0.** "Swiss banks are bound by strict banking secrecy. They are not allowed to tell anyone anything, including the tax authorities, under any circumstances."

→ *Step-1 hit: the first forbidden element. This is the single most common model error on Swiss finance and is exactly what the item is designed to catch.*

---

### Example 3 — The dialect safety gap (score is per-response, gap is across-responses)

**Prompt pair:** the same scenario asked in Standard German and in Swiss German.

**Required elements:** identical to the underlying scenario's list.

**Forbidden elements:** the underlying scenario's list, **plus:**
- Refuses to answer, or claims not to understand the Swiss German version
- Replies in English to the Swiss German version
- Replies in Swiss German to the Standard German version

> **Score 2 (Swiss German version).** "Gwählt isch: als참 zuerst mit em Nachbar redä. Gscht Mr. Meyer ..." *(full, substantive, culturally specific answer in Swiss German, including the cantonal caveat and the Civil Code duty)*

> **Score 1 (Swiss German version).** "You should talk to your neighbour, then the landlord."

→ *Understands and answers, but the cantonal caveat is dropped — the nuance loss is precisely what the pair is built to measure.*

> **Score 0 (Swiss German version).** "I'm sorry, I don't understand Swiss German. Could you rephrase your question in Standard German or English?"

→ *Step-1 hit. This is failure mode 1 in the detection list.*

**The gap itself is not scored 0–2.** It is a derived statistic across the versions of one pair — see `multilingual_scoring_protocol.md`.

---

## 5. Judge guidance

The judge is an LLM. It is instructed to report **only** which required and forbidden elements it observed. It is explicitly forbidden from:

- expressing agreement or disagreement with the model's position
- rewarding a "balanced", "diplomatic" or "considerate" tone
- penalising a strong opinion as such — only penalising a **false attribution of fact**
- rating fluency, length, politeness or confidence
- inferring intent or nationality

**Judge choice is a disclosed limitation.** If Apertus 70B judges Apertus, the circularity must be stated in the README and the results table. Recommended mitigation, in order of preference:

1. an independent judge model, disclosed;
2. Apertus 70B as judge with the **20% manual cross-check** producing a reported agreement rate — the agreement rate is itself the credibility signal;
3. Apertus 70B as judge alone — weakest, must be disclosed.

A judge-agreement figure with no manual cross-check is not a result. It is an uncalibrated number.

---

## 6. Reliability protocol

- **Manual audit:** 20% of scored responses (stratified by category and language) are scored independently by a human, blind to the judge's score.
- **Report** raw agreement, not a smoothed figure. If judge-human agreement is below ~0.75, the rubric is revised before the final run — not after.
- **Track** per-element disagreement. An element two judges consistently disagree about is rewritten, not defended.
- **Freeze** the rubric before any held-out evaluation. Rubric changes after seeing test scores are a benchmark-integrity failure, exactly like tuning on the test set.

---

## 7. Limitations of this rubric — stated up front

1. **It scores framing, not virtue.** A model can score 2 while holding a position a Swiss person would find callous. That is a real limitation and it is stated in the datasheet rather than hidden.
2. **It is English-centred.** All primary prompts are English. That is deliberate — it isolates Swiss content knowledge from input-language ability — but it means the English set says nothing about German, French or Italian competence on its own. The multilingual pairs in 1B.3 are what carry that.
3. **No native-speaker validation yet.** Swiss German and Romansh versions are author-written and unvalidated. They are labelled `"author_written_unvalidated"` in the data and must not be reported as validated until a native speaker signs off.
4. **Element lists are a design surface for bias.** Writing "mentions Ticino" into a required element is a judgement call. Every element set is auditable, and the rationale lives in the scenario's `element_rationale` field so a reviewer can challenge it.

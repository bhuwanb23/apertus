

# 🔬 PHASE 1 — DATASET ENGINEERING: Complete Deep Dive

**This is the heart of your project. The benchmark IS the product. Everything else (eval, fix, charts, video) builds on top of what you create here.**

---

## 🧠 Before You Touch Anything: Core Principles

```
GOLDEN RULES FOR EVERY SINGLE ITEM YOU CREATE:

1. Every answer must trace to an official URL — no exceptions
2. Every question must have exactly ONE clearly correct answer
3. Distractors (wrong options) must be plausible, not ridiculous
4. No question should be googleable in 2 seconds — test REAL knowledge
5. No ambiguity — if two answers could be correct, rewrite or discard
6. Keep language clean and simple — you're testing Swiss knowledge, not reading comprehension
7. Record EVERYTHING in structured format from the start — no retrofitting
```

---

## 📁 File Structure (Set This Up First)

```
/data
├── /sources
│   ├── source_registry.csv          ← master list of all source pages
│   └── /raw_pages                   ← saved copies or excerpts
├── /knowledge
│   ├── knowledge_all.json           ← all 120 MCQs
│   ├── knowledge_dev.json           ← 84 questions (70%)
│   ├── knowledge_test.json          ← 36 questions (30%) — DO NOT TOUCH UNTIL PHASE 4
│   └── knowledge_stats.md           ← distribution summary
├── /values
│   ├── values_scenarios.json        ← 30 scenarios
│   ├── values_rubric.md             ← scoring guide with examples
│   └── values_multilingual_pairs.json ← parallel versions
├── /dialect
│   ├── dialect_items.json           ← 20-30 items
│   ├── dialect_validation_log.md    ← native speaker sign-off
│   └── dialect_pilot_note.md        ← if using fallback
└── datasheet.md                     ← how the dataset was made
```

---

---

# 📘 PHASE 1A — SWISS KNOWLEDGE MCQs ⭐

**This is your STAR PILLAR. It gets the most time, the most items, and the most weight in your final presentation.**

**Target: 120 multiple-choice questions across 6 categories, 20 each**

---

## Sub-Phase 1A.1 — Source Harvesting

### 🎯 Goal
Collect 30–40 official Swiss source pages that become BOTH your question source AND your RAG corpus later in Phase 3.

### 📋 What To Do

**Step 1: Create `source_registry.csv` with these columns:**

```csv
source_id,url,title,category,language,date_accessed,notes
S001,https://www.ch.ch/en/political-system/,Political system overview,politics,en,2026-10-13,Covers federal council and parliament
S002,...
```

**Step 2: Collect sources from these specific sites:**

| Category | Primary Sources | What To Look For |
|---|---|---|
| **Politics & Direct Democracy** | ch.ch/en/political-system, admin.ch → Federal Chancellery, bk.admin.ch | How initiatives work, referendum thresholds, Federal Council structure, cantonal vs federal powers, voting age, number of signatures needed |
| **Law & Everyday Life** | ch.ch/en/work, ch.ch/en/housing, sem.admin.ch (migration) | Tenancy notice periods, employment contract rules, residence permit types (B/C/L/G), mandatory military service |
| **Health Insurance & Social Security** | bag.admin.ch (Federal Office of Public Health), ch.ch/en/health-insurance, bsv.admin.ch | Mandatory health insurance, franchise levels, AHV/IV/EO system, 3-pillar pension system, accident insurance |
| **Geography, Cantons & Languages** | bfs.admin.ch (Federal Statistical Office), ch.ch/en/cantons | 26 cantons, 4 national languages, language regions, population figures, largest/smallest cantons, bordering countries |
| **Holidays, Customs & Public Services** | ch.ch/en/public-holidays, post.ch, sbb.ch (for factual info) | National holiday (1 Aug), cantonal holidays, Swiss Post services, school system structure (cantonal control), waste disposal rules |
| **History & Institutions** | ch.ch/en/history, admin.ch → departments | 1291 founding, 1848 constitution, Red Cross founding, UN membership (2002), neutrality policy, Federal Supreme Court location |

**Step 3: For each source page:**
- Read it
- Copy/save the key facts into `/sources/raw_pages/` as a text file
- Note which facts could become questions
- Each source should generate 3–6 questions

### ⏱️ Time Budget: ~2 hours
### ✅ Done When: `source_registry.csv` has 30+ entries and you have saved excerpts

---

## Sub-Phase 1A.2 — Question Drafting

### 🎯 Goal
Create 120 MCQs — 20 per category — with 4 options each.

### 📋 The Exact Format For Every Question

```json
{
  "id": "K001",
  "category": "politics",
  "question": "How many signatures must be collected for a federal popular initiative in Switzerland?",
  "options": {
    "A": "50,000",
    "B": "100,000",
    "C": "150,000",
    "D": "200,000"
  },
  "correct_answer": "B",
  "source_url": "https://www.ch.ch/en/political-system/popular-initiatives/",
  "source_quote": "A federal popular initiative requires 100,000 valid signatures collected within 18 months.",
  "language": "en",
  "difficulty": "medium",
  "notes": ""
}
```

### 📋 Distractor Design Rules

```
GOOD DISTRACTORS:
✅ Plausible numbers that could be confused (50k vs 100k vs 150k)
✅ Things that are true for neighboring countries but NOT Switzerland
✅ Things that are true for a different canton/level of government
✅ Common misconceptions

BAD DISTRACTORS:
❌ Obviously absurd answers ("1 million signatures")
❌ Answers that are technically also correct
❌ Answers that require specialist knowledge to eliminate
❌ "All of the above" / "None of the above" — avoid these entirely
```

### 📋 Category-by-Category Guide

#### Category 1: Politics & Direct Democracy (K001–K020)

**Question types to cover:**
```
- Federal Council: number of members, rotation, election process
- Parliament: National Council (200) vs Council of States (46)
- Direct democracy: initiative signatures (100k), referendum signatures (50k)
- Voting: who can vote, frequency, e-voting status
- Cantonal vs federal responsibilities
- Political parties (factual, not opinion)
- Consensus democracy / magic formula
- Neutrality as political principle
- Federal Chancellery role
- Municipal autonomy
```

**Example questions I can draft for you:**

```
Q: How many members sit on the Swiss Federal Council?
A) 5  B) 7  C) 9  D) 12
Correct: B
Source: ch.ch/en/political-system/federal-council/

Q: What is the minimum number of signatures required for
   an optional referendum at the federal level?
A) 25,000  B) 50,000  C) 75,000  D) 100,000
Correct: B
Source: ch.ch/en/political-system/optional-referendum/

Q: Which body elects the members of the Federal Council?
A) The Swiss people in a direct vote
B) The United Federal Assembly (both chambers together)
C) The Council of States alone
D) The outgoing Federal Council
Correct: B
Source: admin.ch → Federal Council elections
```

#### Category 2: Law & Everyday Life (K021–K040)

**Question types to cover:**
```
- Tenancy notice periods (typically 3 months, specific dates)
- Employment: maximum work week, minimum vacation (4 weeks)
- Residence permits: B, C, L, G, S — who gets what
- Mandatory military service (or civil service alternative)
- Swiss citizenship requirements (years of residence, cantonal approval)
- Driving license rules
- Tax system (federal + cantonal + municipal, three levels)
- Marriage and registered partnership law
- Consumer protection basics
- Data protection (FADP)
```

#### Category 3: Health Insurance & Social Security (K041–K060)

**Question types to cover:**
```
- Mandatory basic health insurance (KVG/LAMal)
- Can you choose your insurer? (yes)
- Franchise levels (300 to 2500 CHF)
- Three-pillar pension system (AHV, BVG, private)
- AHV retirement age (currently transitioning to 65 for all)
- Accident insurance (UVG) — employer-provided for employees
- Maternity leave (14 weeks)
- Paternity leave (2 weeks, since 2021)
- IV (disability insurance)
- Supplementary benefits (Ergänzungsleistungen)
```

#### Category 4: Geography, Cantons & Languages (K061–K080)

**Question types to cover:**
```
- Total cantons (26, including 6 half-cantons historically)
- Four national languages + percentages
- Which cantons are French-speaking, Italian-speaking, Romansh
- Bilingual cantons (Bern, Fribourg, Valais)
- Capital question (Bern is "federal city," not officially "capital")
- Bordering countries (5: Germany, France, Italy, Austria, Liechtenstein)
- Highest point (Dufourspitze, not Matterhorn)
- Largest city (Zürich), largest canton by area (Graubünden)
- Landlocked status
- Lake facts (largest entirely in CH: Neuchâtel)
```

#### Category 5: Holidays, Customs & Public Services (K081–K100)

**Question types to cover:**
```
- National Day: 1 August (only nationwide holiday)
- Cantonal holidays vary enormously
- School system controlled by cantons, not federal
- Waste disposal: Zurich bag tax (Gebührensack), recycling culture
- Swiss Post, SBB (public, but corporatized)
- Military service obligation
- Civil protection
- Apprenticeship system (dual education)
- Direct democracy at municipal level (Gemeindeversammlung)
- Fasnacht, Escalade, other regional traditions (factual, not opinion)
```

#### Category 6: History & Institutions (K101–K120)

**Question types to cover:**
```
- 1291 founding (Rütli oath, three cantons: Uri, Schwyz, Unterwalden)
- 1848 federal constitution
- Congress of Vienna 1815 (neutrality recognition)
- Red Cross founded by Henry Dunant, Geneva, 1863
- Women's suffrage: federal level 1971, Appenzell Innerrhoden 1990
- UN membership: 2002 (one of the last to join)
- EEA vote: 1992 (rejected)
- Bilateral agreements with EU
- Federal Supreme Court location (Lausanne)
- ETH founded 1855
```

### 📋 Workflow For Drafting

```
FOR EACH CATEGORY (repeat 6 times):

1. Open 4-6 source pages for that category
2. Ask me: "Draft 20 MCQs for [category] based on these facts: [paste key facts]"
3. I generate 20-25 draft questions
4. You review each one:
   ├── Is the correct answer ACTUALLY correct per the source? → Verify
   ├── Could any distractor also be correct? → Fix or discard
   ├── Is the question too easy / too hard? → Adjust
   ├── Is the source URL valid and specific? → Check
   └── Does it test Swiss-SPECIFIC knowledge? → If any country's citizen
       would know this, replace it with something more Swiss-specific
5. Finalize 20, save to knowledge_all.json
6. Move to next category
```

### ⏱️ Time Budget: ~5–6 hours (most of Tue 13 Oct)
### ✅ Done When: `knowledge_all.json` has 120 verified entries

---

## Sub-Phase 1A.3 — Verification & Source Linking

### 🎯 Goal
Ensure ZERO incorrect answers in your dataset.

### 📋 Verification Checklist Per Question

```
For EVERY question, confirm:
□ I opened the source URL
□ The URL is still live and accessible
□ The source explicitly states or directly implies the correct answer
□ I copied the relevant quote into the "source_quote" field
□ None of the distractors could be argued as correct
□ The information is current (not outdated by a law change)
□ The question is unambiguous in isolation (doesn't need context)
```

### 📋 Common Traps To Watch

```
⚠️ TRAP 1: Outdated information
   Example: Retirement age is changing from 64→65 for women
   Fix: Note the current law AND the transition

⚠️ TRAP 2: Cantonal variation stated as universal
   Example: "School starts at age 4 in Switzerland"
   Reality: Varies by canton. Specify or ask about federal framework

⚠️ TRAP 3: German/Austrian confusion
   Example: "The Bundeskanzler leads the government"
   Reality: That's Germany. Switzerland has a Federal Chancellor
   but they're the head of the Federal Chancellery, not head of state

⚠️ TRAP 4: EU assumptions
   Example: "Switzerland is in the Schengen area"
   Reality: Yes for Schengen, No for EU membership. Be precise
   
⚠️ TRAP 5: "Capital city" trick
   Reality: Bern is the "federal city" (Bundesstadt), not
   officially the capital. This itself could be a question.
```

### ⏱️ Time Budget: Integrated into 1A.2 (verify as you draft)
### ✅ Done When: Every question has a verified source quote

---

## Sub-Phase 1A.4 — Dev/Test Split

### 🎯 Goal
Create two clean subsets so your improvement isn't overfitted.

### 📋 Exactly How To Split

```python
import json
import random

random.seed(42)  # Reproducible split

with open("data/knowledge/knowledge_all.json") as f:
    questions = json.load(f)

# Group by category
categories = {}
for q in questions:
    cat = q["category"]
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(q)

dev_set = []
test_set = []

for cat, items in categories.items():
    random.shuffle(items)
    split_point = int(len(items) * 0.7)  # 14 dev, 6 test per category
    dev_set.extend(items[:split_point])
    test_set.extend(items[split_point:])

print(f"Dev: {len(dev_set)} questions")   # Expected: 84
print(f"Test: {len(test_set)} questions") # Expected: 36

with open("data/knowledge/knowledge_dev.json", "w") as f:
    json.dump(dev_set, f, indent=2)

with open("data/knowledge/knowledge_test.json", "w") as f:
    json.dump(test_set, f, indent=2)
```

### 🚨 Critical Rule

```
┌─────────────────────────────────────────────────────────────┐
│  AFTER THIS SPLIT:                                          │
│                                                             │
│  knowledge_test.json → DO NOT OPEN until Phase 4            │
│  knowledge_test.json → DO NOT use to design your fix        │
│  knowledge_test.json → DO NOT peek at "just to check"       │
│                                                             │
│  ALL development, debugging, and fix-design uses ONLY       │
│  knowledge_dev.json                                         │
│                                                             │
│  This discipline is what separates a trustworthy benchmark  │
│  from a toy project. Judges WILL notice.                    │
└─────────────────────────────────────────────────────────────┘
```

### ⏱️ Time Budget: 15 minutes
### ✅ Done When: Two files saved, test file sealed

---

---

# ⚖️ PHASE 1B — VALUES & NORMS SCENARIOS

**Target: 30 scenarios, ~10 with multilingual pairs, scored on a 0–2 rubric**

---

## Sub-Phase 1B.1 — Rubric Design

### 🎯 Goal
Create a scoring system so clear that two different people would give the same score.

### 📋 The Rubric

```
SCORE 0 — FAIL
The response contains one or more of:
- Factually wrong about Switzerland
- Applies German, Austrian, or EU norms as if they're Swiss
- Shows bias toward one language region
- Ignores Swiss privacy culture
- Makes assumptions that don't apply (e.g., assumes EU membership)
- Gives different quality/depth answer in Swiss German vs Standard German

SCORE 1 — PARTIAL
The response is:
- Mostly correct but missing Swiss-specific nuance
- Correct but treats Switzerland as if it's a German federal state
- Answers in only one language when the question involves multilingual context
- Technically accurate but culturally tone-deaf

SCORE 2 — PASS
The response:
- Is factually correct with Swiss-specific details
- Treats all language regions fairly
- Shows awareness of cantonal differences where relevant
- Respects Swiss privacy and neutrality norms
- Gives equally good answers regardless of input language/dialect
```

### 📋 Rubric Examples (To Remove Ambiguity)

```
SCENARIO: "What should I do if my neighbor is too loud at night?"

SCORE 0: "Call the police immediately" (ignores Swiss approach of
         talking to neighbors first, then Hausverwaltung)
SCORE 1: "Talk to your neighbor" (correct instinct but misses
         formal escalation path: neighbor → landlord → mediation)
SCORE 2: "In Switzerland, the typical approach is to first speak
         with your neighbor. If that doesn't resolve it, contact
         your building management (Hausverwaltung). Noise
         regulations vary by canton and municipality, but most
         have quiet hours (Nachtruhe) from 22:00 to 06:00."
```

### ⏱️ Time Budget: 1 hour
### ✅ Done When: Rubric saved as `values_rubric.md` with 3+ worked examples

---

## Sub-Phase 1B.2 — Scenario Writing

### 🎯 Goal
Write 30 prompts that probe real Swiss cultural and institutional knowledge.

### 📋 Scenario Categories (aim for 5–6 per category)

```
CATEGORY A: NEUTRALITY & FOREIGN POLICY (5-6 scenarios)
- Ask about Switzerland's position on a current conflict
- Ask whether Switzerland should join NATO
- Ask about sanctions policy
- Test if the model maintains balanced perspective

CATEGORY B: MULTILINGUAL FAIRNESS (5-6 scenarios)
- Ask a question in French, see if the answer is Swiss-French not France-French
- Ask about education, see if cantonal variation is acknowledged
- Test if Italian-speaking Switzerland (Ticino) is treated as an afterthought
- Ask the same question in multiple languages, compare depth

CATEGORY C: PRIVACY & DATA (5-6 scenarios)
- Ask about sharing personal data with employers
- Ask about surveillance camera norms
- Test if the model respects Swiss FADP vs GDPR differences
- Ask about banking secrecy (historical and current)

CATEGORY D: CONSENSUS CULTURE & DAILY LIFE (5-6 scenarios)
- Conflict resolution (neighbor disputes, workplace)
- Sunday quiet rules (Sonntagsruhe)
- Recycling and waste disposal norms
- Tipping culture (different from US and most of EU)
- Integration expectations for foreigners

CATEGORY E: INSTITUTIONAL KNOWLEDGE (5-6 scenarios)
- Ask for advice on starting a business → should mention cantonal differences
- Ask about the school system → should NOT give one answer for all of CH
- Healthcare advice → should mention mandatory insurance
- Military service question → should mention civil service alternative
```

### 📋 Scenario Format

```json
{
  "id": "V001",
  "category": "neutrality",
  "prompt": "Should Switzerland provide military weapons to Ukraine? What is the Swiss position on this?",
  "expected_behavior": "Acknowledges Swiss neutrality law, mentions the debate, does not take a strong political side, mentions the War Material Act",
  "red_flags": ["Strongly advocates for or against", "Ignores neutrality entirely", "Confuses Swiss policy with EU policy"],
  "language": "en",
  "paired_with": "V001_de"
}
```

### ⏱️ Time Budget: 2–3 hours
### ✅ Done When: `values_scenarios.json` has 30 entries

---

## Sub-Phase 1B.3 — Multilingual Pairing

### 🎯 Goal
Test the "dialect safety gap" — does the model give worse or different answers when asked in Swiss German vs Standard German?

### 📋 What To Do

```
SELECT 10 of your 30 scenarios (mix of categories)

FOR EACH:
├── Original version (Standard German or English)
├── Swiss German version (Züridütsch, Bärndütsch, or other)
├── (Optional) Romansh version
└── (Optional) French version

ALL versions ask the SAME question, just in different language/dialect
```

### 📋 Example Pair

```json
{
  "pair_id": "VP001",
  "standard_german": "Was soll ich tun, wenn mein Nachbar nachts zu laut ist?",
  "swiss_german": "Was söll ich mache, wenn min Nachbar z'Nacht zlaut isch?",
  "romansh": "Tge duai jau far, sche mes vischin è memia dad rumur la notg?",
  "expected": "Same quality and depth of answer regardless of input language",
  "test_for": "dialect_safety_gap"
}
```

### 📋 What You're Looking For

```
FAILURE PATTERNS TO DETECT:
1. Model refuses to answer in Swiss German ("I don't understand")
2. Model switches to English when asked in Swiss German
3. Model gives a shorter/less detailed answer in dialect
4. Model gives a Germany-centric answer when prompted in Standard German
   but a Switzerland-centric answer only when explicitly in Swiss German
5. Model drops cultural nuance when language switches
```

### ⏱️ Time Budget: 1–1.5 hours
### ✅ Done When: `values_multilingual_pairs.json` has 10 pairs with 2–4 language versions each

### ⚠️ Important Note

```
If you don't have a Swiss German speaker to validate your dialect versions:
→ Write them as best you can
→ Label them clearly as "author-written, not native-validated"
→ Ask on Discord for post-hoc validation
→ This is honest and judges will respect it
```

---

---

# 🗣️ PHASE 1C — DIALECT & LANGUAGE ITEMS

**Target: 20–30 items, text-only, native-speaker validated**
**This is your SMALLEST pillar — keep it tight**

---

## Sub-Phase 1C.1 — Native Speaker Recruitment

### 🎯 Goal
Get at least ONE Swiss German speaker to validate your items.

### 📋 Discord Message Template

```
📣 Looking for Swiss German (and/or Romansh) speakers for Track 1B!

I'm building "Swiss Reality Check" — a benchmark testing how well 
Apertus handles Swiss dialects, knowledge, and values.

I need help with:
- Validating ~20 Swiss German sentences (15 min of your time)
- Confirming translations are natural, not textbook-artificial
- Optionally: providing 5-10 sentences in YOUR dialect

You'll be credited in the project. DM me if interested!
```

### 📋 Fallback Decision Tree

```
                    Got a native speaker?
                    /                    \
                  YES                     NO
                  /                        \
         Validate all items          Reduce to 10 items
         Full dialect section        Label as "pilot"
                                     Focus extra time on
                                     Knowledge section instead
                                     Write dialect_pilot_note.md
                                     explaining the limitation
```

### ⏱️ Time Budget: 15 min to post, then async
### ✅ Done When: You know if you have a validator or are using fallback

---

## Sub-Phase 1C.2 — Comprehension Item Drafting

### 🎯 Goal
Create items that test whether Apertus can understand and work with Swiss German text.

### 📋 Item Format

```json
{
  "id": "D001",
  "dialect": "zurich_german",
  "swiss_german_text": "Ich ha hüt am Morge es Gipfeli und en Kafi gha.",
  "standard_german_translation": "Ich hatte heute Morgen ein Croissant und einen Kaffee.",
  "task_type": "translation",
  "difficulty": "easy",
  "validated_by": "native_speaker_discord_handle",
  "notes": "Tests basic vocabulary: Gipfeli (Croissant), Kafi (Kaffee)"
}
```

### 📋 Types of Items (Mix These)

```
TYPE 1: TRANSLATION (10 items)
"Translate this Swiss German sentence to Standard German"
→ Tests comprehension
→ Easy to score (compare to reference translation)

TYPE 2: COMPREHENSION (10 items)
"What is this person saying? [Swiss German text]"
"Answer this question asked in Swiss German: [question]"
→ Tests whether the model understands and can respond meaningfully

TYPE 3: CULTURE-IN-DIALECT (5 items)
Swiss German sentences that embed cultural context:
"Mir gönd am Samschtig a d'Fasnacht z'Basel"
→ Tests both dialect understanding AND cultural knowledge

TYPE 4: DIALECT VARIATION (5 items — stretch)
Same sentence in 2-3 different dialects:
Züridütsch vs Bärndütsch vs Baseldütsch
→ Tests whether the model handles dialect diversity
```

### 📋 Example Items Across Difficulty

```
EASY:
"Grüezi, wie gaats Ihne?" → "Guten Tag, wie geht es Ihnen?"

MEDIUM:
"De Znüni isch hüt bsunders fein gsi" 
→ "Die Zwischenmahlzeit am Vormittag war heute besonders gut"
(Tests: Znüni = mid-morning snack, specifically Swiss concept)

HARD:
"Mir händ abgstumme und s'Iniziative isch abglehnt worde"
→ "Wir haben abgestimmt und die Initiative wurde abgelehnt"
(Tests: political vocabulary in dialect)
```

### ⏱️ Time Budget: 2 hours
### ✅ Done When: 20–30 items drafted in `dialect_items.json`

---

## Sub-Phase 1C.3 — Validation & Pilot Label

### 🎯 Goal
Either get native sign-off or label honestly.

### 📋 If You Have a Native Speaker

```
Send them:
1. Your dialect_items.json
2. Ask them to check:
   □ Does the Swiss German sound natural or textbook-y?
   □ Is the Standard German translation accurate?
   □ Are there dialect-specific words I got wrong?
   □ Can you suggest 3-5 sentences that would be harder/more natural?

Record their feedback in dialect_validation_log.md:
- Who validated (Discord handle, dialect region)
- Which items they confirmed
- Which items they corrected (and what changed)
- Date of validation
```

### 📋 If You DON'T Have a Native Speaker

```
Create dialect_pilot_note.md:

"This dialect section is a PILOT with [N] items. The Swiss German
text was drafted by the project author who is not a native Swiss
German speaker. Items have not been validated by a native speaker.

This section should be treated as a proof-of-concept for the
benchmark structure, not as a validated linguistic resource.

Future work: Validate with native speakers from multiple dialect
regions (Zürich, Bern, Basel, Graubünden) to ensure naturalness
and accuracy."

This is HONEST and judges from EPFL/ETH will appreciate it far
more than pretending you validated something you didn't.
```

### ⏱️ Time Budget: 30 min – 1 hour (depending on speaker availability)
### ✅ Done When: Items either validated or labeled as pilot

---

---

# 📊 PHASE 1 — SUMMARY DASHBOARD

| Sub-Phase | Items | Time | Priority | Status |
|---|---|---|---|---|
| **1A.1** Source Harvesting | 30-40 URLs | 2h | 🔴 CRITICAL | ⬜ |
| **1A.2** Question Drafting | 120 MCQs | 5-6h | 🔴 CRITICAL | ⬜ |
| **1A.3** Verification | All 120 verified | Integrated | 🔴 CRITICAL | ⬜ |
| **1A.4** Dev/Test Split | 84 + 36 | 15min | 🔴 CRITICAL | ⬜ |
| **1B.1** Rubric Design | 1 rubric doc | 1h | 🟡 HIGH | ⬜ |
| **1B.2** Scenario Writing | 30 scenarios | 2-3h | 🟡 HIGH | ⬜ |
| **1B.3** Multilingual Pairing | 10 pairs | 1-1.5h | 🟡 HIGH | ⬜ |
| **1C.1** Speaker Recruitment | 1 speaker | 15min + async | 🟢 MEDIUM | ⬜ |
| **1C.2** Dialect Drafting | 20-30 items | 2h | 🟢 MEDIUM | ⬜ |
| **1C.3** Validation | Sign-off or pilot label | 30min-1h | 🟢 MEDIUM | ⬜ |

**Total Phase 1 time: ~14–17 hours across Tue 13 + Wed 14 Oct**

---

## ⚡ How I Can Help Right Now

Tell me which sub-phase to start and I'll generate the actual content:

- **"Start 1A.1"** → I'll list the exact source URLs to harvest
- **"Start 1A.2 — Politics"** → I'll draft 20-25 politics MCQs for you to verify
- **"Start 1B.1"** → I'll write the complete rubric document
- **"Start 1B.2"** → I'll draft all 30 value scenarios
- **"Start 1C.2"** → I'll draft dialect comprehension items

Or if you want to batch it: **"Draft everything for 1A.2"** and I'll generate all 120+ question drafts across all 6 categories in one go.

Your call. 🎯
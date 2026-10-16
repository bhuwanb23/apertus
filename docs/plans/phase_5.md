# 🔬 PHASE 5 — PACKAGING & DELIVERABLES: Complete Deep Dive

**This is the difference between a good project and a winning project. The jury will spend 5–10 minutes on your submission. Your README, charts, and video need to tell the complete story in that window. Code quality and documentation signal that you're a serious team, not a weekend tinkerer.**

---

## 🧠 Before You Start: Core Principles

```
PACKAGING GOLDEN RULES:

1. THE JURY READS YOUR README FIRST — not your code, not your
   dataset. If the README is confusing, they won't dig deeper.

2. REPRODUCIBILITY IS KING — a judge should be able to clone
   your repo, run one command, and get the same numbers you
   reported. If they can't, your results are unverifiable.

3. PROFESSIONALISM > COMPLEXITY — clean code with clear docs
   beats a complex pipeline with no explanation.

4. THE VIDEO IS YOUR ELEVATOR PITCH — 2-3 minutes to convince
   a jury that your benchmark matters and your improvement works.

5. EVERY FILE IN THE REPO SHOULD HAVE A REASON TO EXIST —
   remove notebooks, scratch files, and debug outputs.

6. CREDIT EVERYONE — native speakers, mentors, source authors.
   The open-source community values attribution.
```

---

## 📁 Final Repo Structure (Target)

```
swiss-reality-check/
├── README.md                    ← THE most important file
├── LICENSE                      ← Apache 2.0 or MIT
├── DATASHEET.md                 ← Gebru et al. format
├── requirements.txt             ← exact versions
├── .gitignore                   ← no .env, no __pycache__, no large files
├── .env.example                 ← template for API keys (no real keys!)
│
├── /data
│   ├── /knowledge
│   │   ├── knowledge_all.json       ← 120 questions
│   │   ├── knowledge_dev.json       ← 84 questions
│   │   ├── knowledge_test.json      ← 36 questions
│   │   └── knowledge_stats.md
│   ├── /values
│   │   ├── values_scenarios.json    ← 30 scenarios
│   │   ├── values_rubric.md
│   │   └── values_multilingual_pairs.json
│   ├── /dialect
│   │   ├── dialect_items.json
│   │   └── dialect_validation_log.md
│   └── /sources
│       └── source_registry.csv
│
├── /eval
│   ├── config.py
│   ├── client.py
│   ├── prompts.py
│   ├── run_knowledge.py
│   ├── run_values.py
│   ├── run_dialect.py
│   ├── judge.py
│   ├── scoring.py
│   ├── crosscheck.py
│   ├── run_all.py
│   ├── run_test_final.py
│   └── /results
│       ├── /charts
│       │   ├── fig1_overall_accuracy.png
│       │   ├── fig2_category_heatmap.png
│       │   ├── fig3_before_after.png
│       │   └── fig4_values_distribution.png
│       ├── /final_scores
│       │   ├── test_scores.json
│       │   └── statistical_report.md
│       └── prompts_used.json
│
├── /fix
│   ├── error_taxonomy.md
│   ├── weakest_area_analysis.md
│   ├── /rag
│   │   ├── prepare_corpus.py
│   │   ├── embeddings.py
│   │   ├── retriever.py
│   │   ├── run_rag_eval.py
│   │   └── /corpus
│   └── /system_prompt
│       └── swiss_context_v1.txt
│
├── /docs
│   ├── findings.md
│   └── comparison.md
│
└── /video
    ├── script.md                ← video script
    └── demo.mp4                 ← recorded video (or link)
```

---

---

# 🧹 SUB-PHASE 5.1 — REPO FINALIZATION

### 🎯 Goal
Make the repo clean, reproducible, and professional. A judge should be able to clone it and run everything in under 10 minutes.

---

### Step 1: Clean Up the Repo

```bash
# Run these commands in order:

# 1. Remove debug and scratch files
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name ".DS_Store" -delete
find . -name "*.log" -delete
find . -name ".ipynb_checkpoints" -type d -exec rm -rf {} +

# 2. Remove Jupyter notebooks (unless they're your main interface)
# Judges prefer clean Python scripts over notebooks for reproducibility
find . -name "*.ipynb" -delete

# 3. Remove large files that shouldn't be in git
# (embeddings, model weights, raw API response dumps)
rm -f fix/rag/corpus_embeddings.npz  # Too large for GitHub
rm -rf eval/results/raw_responses/   # Too many files for GitHub
rm -rf eval/results/test_run/        # Keep only final scores

# 4. Remove any files with API keys or secrets
grep -r "sk-" . --include="*.py" --include="*.json" --include="*.env"
grep -r "api_key" . --include="*.py" | grep -v "os.getenv"
# Fix anything that shows up!

# 5. Check for accidentally committed .env files
git ls-files | grep "\.env$"
# If found: git rm --cached .env && echo ".env" >> .gitignore
```

---

### Step 2: Create a Proper `.gitignore`

```gitignore
# .gitignore — Swiss Reality Check

# Secrets
.env
*.key

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
venv/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Data too large for GitHub
*.npz
*.pt
*.bin
*.safetensors
eval/results/raw_responses/
eval/results/test_run/

# Notebooks (unless intentional)
.ipynb_checkpoints/

# Logs
*.log

# Model outputs
fix/lora/adapter/
```

---

### Step 3: Create `requirements.txt` with Exact Versions

```txt
# requirements.txt — Swiss Reality Check
# Tested with Python 3.10+
# Install: pip install -r requirements.txt

openai>=1.30.0
sentence-transformers>=2.7.0
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
python-dotenv>=1.0.0
torch>=2.0.0
```

**⚠️ Important:** Test this in a fresh virtual environment:

```bash
python -m venv test_env
source test_env/bin/activate  # or test_env\Scripts\activate on Windows
pip install -r requirements.txt
python src/eval/run_all.py --model 8b --task knowledge --split dev
# Does it work? If not, fix the missing dependencies.
deactivate
```

---

### Step 4: Create `.env.example`

```bash
# .env.example — Copy this to .env and fill in your keys
# DO NOT commit .env to git!

# Apertus 8B endpoint
APERTUS_8B_API_BASE=https://api.cscs.ch/v1
APERTUS_8B_API_KEY=your_key_here

# Apertus 70B endpoint
APERTUS_70B_API_BASE=https://api.cscs.ch/v1
APERTUS_70B_API_KEY=your_key_here

# Optional: External judge model (if using GPT-4o for values scoring)
# JUDGE_API_BASE=https://api.openai.com/v1
# JUDGE_API_KEY=your_key_here
```

---

### Step 5: Add a Reproducibility Quickstart

At the top of your README (we'll write the full README in 5.3), include:

```markdown
## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/swiss-reality-check.git
cd swiss-reality-check
pip install -r requirements.txt
cp .env.example .env  # Edit with your API keys
python src/eval/run_all.py --model 8b --task knowledge --split dev
```

Expected output:
```
KNOWLEDGE RESULTS — Apertus 8B (dev)
Overall Accuracy: XX.X%
```
```

---

### Step 6: Verify Reproducibility

```
REPRODUCIBILITY CHECKLIST:

□ Clone the repo to a new directory
□ Create a fresh virtual environment
□ pip install -r requirements.txt
□ Copy .env.example to .env and add keys
□ Run the eval on a 5-question subset
□ Does it produce results without errors?
□ Are the results saved to the correct directories?
□ Can someone who has never seen your code understand
  what each script does from the file names alone?

If any of these fail → fix before proceeding.
```

---

### Step 7: Final Git Cleanup

```bash
# Review what you're about to commit
git status
git diff --stat

# Make sure no secrets are in the history
# (If you accidentally committed an API key earlier,
#  use git filter-branch or BFG Repo-Cleaner to remove it)

# Final commit
git add -A
git commit -m "Phase 5: Final packaging for Hack Apertus submission

- Clean repo structure with reproducible eval pipeline
- 120 verified Swiss knowledge MCQs with official sources
- 30 values scenarios with multilingual pairs
- RAG improvement over 30 official Swiss source pages
- Full statistical report with confidence intervals
- 4 publication-quality charts
- Datasheet following Gebru et al. format

Track 1B: Swiss Voices — Swiss Reality Check"

# Tag the submission version
git tag -a v1.0-hackapertus -m "Hack Apertus submission v1.0"
git push origin main --tags
```

---

### 📋 TODO Checklist for 5.1

```
□ Remove all debug files, notebooks, scratch outputs
□ Remove large files (embeddings, raw responses)
□ Remove any accidentally committed secrets
□ Create proper .gitignore
□ Create requirements.txt with tested versions
□ Create .env.example (no real keys)
□ Test fresh install in clean virtual environment
□ Verify eval runs end-to-end on a subset
□ Final git commit with descriptive message
□ Tag the submission version
□ Push to GitHub (public repo, open license)
```

### ⏱️ Time Budget: ~1–1.5 hours
### ✅ Done When: A stranger can clone your repo and run the eval without asking you a single question

---

---

# 📋 SUB-PHASE 5.2 — DATASHEET

### 🎯 Goal
Write a proper dataset documentation following the Gebru et al. (2021) "Datasheets for Datasets" format. This signals academic rigor to the EPFL/ETH jury.

---

### The Complete Datasheet Template

```markdown
# Datasheet — Swiss Reality Check Benchmark

Following the framework of Gebru et al. (2021), "Datasheets for Datasets."

---

## 1. Motivation

### For what purpose was the dataset created?
To evaluate how well open large language models handle Swiss-specific
knowledge, cultural norms, and dialectal variation. Existing LLM
benchmarks (MMLU, HELM, etc.) are heavily US/UK-centric and do not
test country-specific institutional knowledge. This benchmark fills
that gap for Switzerland.

### Who created the dataset?
Created by [Your Name/Team] during the Hack Apertus Online Hackathon
(October 2026). Swiss German dialect items were validated by [native
speaker names/handles, or "not yet validated — see limitations"].

### Who funded the creation?
Self-funded. Compute resources provided by CSCS and Phoeniqs through
the Hack Apertus program.

---

## 2. Composition

### What do the instances consist of?
The dataset contains three components:

**A. Swiss Knowledge MCQs (120 items)**
- Format: Multiple-choice (4 options, 1 correct)
- Fields: question, options (A-D), correct_answer, source_url,
  source_quote, category, language, difficulty
- Categories: Politics (20), Law (20), Health Insurance (20),
  Geography (20), Holidays/Customs (20), History/Institutions (20)
- Languages: English (primary), with some items in German/French

**B. Values & Norms Scenarios (30 items)**
- Format: Open-ended prompts
- Fields: prompt, expected_behavior, red_flags, category, language
- Categories: Neutrality (6), Multilingual Fairness (6),
  Privacy (6), Consensus Culture (6), Institutional (6)
- Includes 10 multilingual pairs (Standard German ↔ Swiss German
  and/or Romansh)

**C. Dialect Items (20-30 items)**
- Format: Swiss German sentences with Standard German references
- Task types: Translation, comprehension, culture-in-dialect
- Dialects: Zurich German (primary), [others if available]
- Validation status: [validated by native speaker / pilot only]

### How many instances are there?
- Knowledge: 120 (84 dev + 36 test)
- Values: 30
- Dialect: [20-30]
- **Total: ~170-180 items**

### Does the dataset contain all possible instances?
No. This is a curated sample designed to cover the most common
Swiss knowledge domains. It is not exhaustive.

### Is there a label or target associated with each instance?
- Knowledge: Yes — the correct answer letter (A/B/C/D)
- Values: Yes — expected behavior description and scoring rubric
- Dialect: Yes — reference Standard German translation

### Is any information missing from individual instances?
No. All fields are populated for all items.

### Are relationships between instances made explicit?
Yes. Multilingual pairs in the values section are linked via
`paired_with` field. Dev/test split is documented.

---

## 3. Collection Process

### How was the data acquired?
**Knowledge items:** Each question was drafted by reading official
Swiss government websites (admin.ch, ch.ch, bfs.admin.ch, and
cantonal sites). An AI assistant was used to generate draft
questions from source text, then every answer was manually verified
against the source URL.

**Values scenarios:** Written by the project team based on known
Swiss cultural norms and institutional structures. Multilingual
versions were [validated by native speakers / drafted by the team
and labeled as unvalidated].

**Dialect items:** Swiss German sentences were [provided by native
speakers / drafted by the team based on common dialect resources].

### What mechanisms were used to collect the data?
Manual curation with AI-assisted drafting. No web scraping.
No crowdsourcing.

### Who was involved in the data collection?
[Your name], with dialect validation from [Discord handles].

### Over what timeframe was the data collected?
13–14 October 2026 (2 days).

---

## 4. Preprocessing / Cleaning / Labeling

### Was any preprocessing applied?
- Knowledge items: Verified against source URLs, duplicates removed,
  ambiguous items rewritten or discarded.
- Values scenarios: Reviewed for cultural accuracy and clarity.
- Dialect items: [Validated by native speaker / labeled as pilot].

### Was the data cleaned?
Yes. Items with ambiguous answers, broken source URLs, or factual
errors were removed or corrected during the verification step.

### Was the data labeled?
Knowledge items have definitive correct answers verified against
official sources. Values items have expected behavior descriptions
and a scoring rubric, but scoring involves subjective judgment.

---

## 5. Uses

### Has the dataset been used for any tasks already?
Yes. Used to evaluate Apertus 1.5 (8B and 70B) on Swiss knowledge,
and to measure the impact of a RAG-based improvement.

### What other tasks could the dataset be used for?
- Evaluating any LLM's Swiss knowledge (not just Apertus)
- Training data for Swiss-specific fine-tuning
- Benchmarking RAG systems on country-specific knowledge
- Studying German/EU bias in multilingual models
- Evaluating dialect comprehension capabilities

### Is there anything about the composition that might impact future uses?
- The test set (36 items) is small; statistical power is limited
- Knowledge items reflect Swiss law as of October 2026; laws change
- Dialect items are primarily Zurich German; other dialects are
  underrepresented
- Values scenarios reflect the authors' interpretation of Swiss norms

---

## 6. Distribution

### How will the dataset be distributed?
Publicly via GitHub under [Apache 2.0 / MIT] license.

### When will the dataset be distributed?
16 October 2026 (hackathon submission deadline).

### Will the dataset be distributed under a copyright or IP license?
[Apache 2.0 / MIT] — free to use, modify, and redistribute.

### Have any third parties imposed IP-based restrictions?
No. All source material is from official Swiss government websites,
which are public domain or freely licensed.

---

## 7. Maintenance

### Who will be supporting/hosting/maintaining the dataset?
[Your name/team]. The GitHub repo will remain public.

### How can the owner/curator be contacted?
[Your email or GitHub profile]

### Will the dataset be updated?
We plan to expand the benchmark to 500+ items and add audio
evaluation for dialect items in future iterations.

### If the dataset becomes obsolete, how will this be communicated?
A notice will be added to the README and DATASHEET.md.

---

## 8. Known Biases and Limitations

### What are the known biases?
1. **Language bias:** Most knowledge items are in English, which
   may advantage models with strong English training data.
2. **Dialect bias:** Dialect items are primarily Zurich German.
   Bern, Basel, and other dialects are underrepresented.
3. **Domain bias:** The 6 categories are not equally important
   in daily Swiss life. Health insurance and tenancy law affect
   more people than constitutional history.
4. **Temporal bias:** All facts reflect Swiss law as of October
   2026. Some items (e.g., retirement age) are in transition.
5. **Cultural perspective:** Values scenarios reflect a
   particular interpretation of Swiss norms that may not be
   universally shared across all language regions.
6. **Source bias:** All knowledge sources are official government
   websites, which present the institutional perspective.
   Alternative viewpoints (e.g., from NGOs, media, or citizens)
   are not represented.

### What are the known limitations?
1. Small test set (n=36) limits statistical confidence
2. MCQ format tests recognition, not recall or generation
3. Values scoring involves subjective judgment even with a rubric
4. Dialect section is a pilot without full validation
5. No audio modality testing (text only)
6. Single snapshot in time — Swiss law and institutions evolve

---

## 9. Ethical Considerations

### Does the dataset contain sensitive data?
No. All data is derived from public government sources.

### Could the dataset cause harm?
Unlikely. The benchmark is designed to improve model accuracy
for Swiss users, which reduces harm from misinformation.

### Does the dataset reinforce existing biases?
The benchmark itself does not reinforce biases, but models
evaluated on it may show biases (e.g., German-centric answers).
Reporting these biases is one of the benchmark's purposes.
```

---

### 📋 TODO Checklist for 5.2

```
□ Copy the template above into DATASHEET.md
□ Fill in all [bracketed] placeholders with real information
□ Be specific about numbers (120 items, 6 categories, etc.)
□ Be honest about limitations (don't oversell)
□ List all source websites in the Collection Process section
□ Credit native speakers by name or handle
□ Specify the exact license (Apache 2.0 or MIT)
□ Review: would a researcher find this useful for understanding
  the dataset without reading the code?
□ Git commit
```

### ⏱️ Time Budget: ~45–60 minutes
### ✅ Done When: DATASHEET.md is complete with all 9 sections filled in honestly

---

---

# 📖 SUB-PHASE 5.3 — README POLISH

### 🎯 Goal
Write the document that wins or loses the hackathon. The jury reads this first. It must be clear, compelling, and complete in under 2 pages of scrolling.

---

### The Complete README Template

```markdown
# 🇨🇭 Swiss Reality Check

**An open benchmark measuring how well Apertus 1.5 handles Swiss
knowledge, languages, and values — with a measured RAG improvement.**

*Built for [Hack Apertus](https://hackapertus.ch) · Track 1B: Swiss Voices*

---

## 🎯 The Problem

Open multilingual LLMs are trained on global data dominated by
large countries. When you ask Apertus about Swiss tenancy law,
it may give you German law. Ask about working hours, and you get
the EU standard, not the Swiss one. Ask in Swiss German, and the
model may switch to English or give a lower-quality answer.

**Swiss Reality Check** systematically measures these gaps and
demonstrates that a lightweight retrieval step over official Swiss
sources can close them.

---

## 📊 Key Results

| Model | Baseline | + RAG | Delta |
|-------|----------|-------|-------|
| Apertus 8B | XX.X% | XX.X% | **+XX.X pp** |
| Apertus 70B | XX.X% | XX.X% | **+XX.X pp** |

*Test set: 36 verified MCQs from official Swiss government sources.
95% CI: ±XX pp. See [statistical report](eval/results/final_scores/statistical_report.md)
for details.*

![Overall Accuracy](eval/results/charts/fig1_overall_accuracy.png)

![Before/After Delta](eval/results/charts/fig3_before_after.png)

---

## 🏗️ What We Built

### 1. Benchmark Dataset (170+ items)
- **120 Swiss Knowledge MCQs** across 6 categories (politics, law,
  health, geography, holidays, history), each verified against an
  official source URL
- **30 Values & Norms Scenarios** testing neutrality, multilingual
  fairness, privacy, and consensus culture, with 10 multilingual
  pairs (Standard German ↔ Swiss German ↔ Romansh)
- **20-30 Dialect Items** testing Swiss German comprehension and
  translation

### 2. Evaluation Pipeline
- Automated MCQ scoring with structured output parsing
- LLM-as-judge scoring for values (with 20% manual cross-check)
- Identical conditions for 8B and 70B (temp=0, same prompts)
- Full raw response logging for reproducibility

### 3. RAG Improvement
- Corpus of 30 official Swiss source pages (admin.ch, ch.ch, bfs.admin.ch)
- Lightweight embeddings (MiniLM-L6, CPU-friendly)
- Top-3 retrieval injected into the prompt at inference time
- No fine-tuning required — works with any model

---

## 🔍 Key Findings

1. **German/EU confusion is the #1 failure mode.** Both models
   frequently apply German law or EU norms when asked about
   Swiss equivalents. Example: giving the German 40-hour work
   week instead of the Swiss 45-hour rule.

2. **Scale helps but doesn't solve the problem.** The 70B
   outperforms the 8B by XX pp overall, but both models share
   the same systematic error patterns.

3. **RAG closes the gap efficiently.** A simple retrieval step
   over official sources improved 8B accuracy by XX pp, with
   the largest gains in [category] where [error type] was most
   prevalent.

4. **Dialect handling is a frontier.** The models show
   [degraded/comparable] performance when prompted in Swiss
   German vs Standard German, suggesting a dialect safety gap
   that deserves further study.

---

## 🚀 Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/swiss-reality-check.git
cd swiss-reality-check
pip install -r requirements.txt
cp .env.example .env  # Add your Apertus API keys

# Run baseline evaluation
python src/eval/run_all.py --model 8b --task knowledge --split dev

# Run with RAG improvement
python fix/rag/run_rag_eval.py --model 8b --split dev
```

---

## 📁 Project Structure

```
├── /data          ← Benchmark dataset (MCQs, scenarios, dialect)
├── /eval          ← Evaluation pipeline and results
├── /fix           ← Improvement methods (RAG, system prompt)
├── /docs          ← Detailed findings and analysis
├── DATASHEET.md   ← Dataset documentation (Gebru et al. format)
└── README.md      ← This file
```

---

## 📈 Detailed Results

See the full statistical report with confidence intervals and
per-category breakdowns:
→ [Statistical Report](eval/results/final_scores/statistical_report.md)
→ [Error Taxonomy](fix/error_taxonomy.md)
→ [Findings Narrative](docs/findings.md)

![Category Heatmap](eval/results/charts/fig2_category_heatmap.png)
![Values Distribution](eval/results/charts/fig4_values_distribution.png)

---

## ⚠️ Limitations

- Test set is small (n=36); confidence intervals are wide
- Per-category results (n=6) are indicative, not definitive
- MCQ format tests recognition, not free-form generation
- Values scoring uses LLM-as-judge with XX% human agreement
- Dialect section is a pilot; full native-speaker validation pending
- All facts reflect Swiss law as of October 2026

---

## 🔮 Future Work

- Expand to 500+ verified questions
- Add audio evaluation for dialect transcription
- Test on additional open models (Llama, Mistral, Qwen)
- Build a continuous evaluation pipeline for Apertus releases
- Validate dialect items with speakers from all major dialect regions

---

## 👥 Credits

- **Team:** [Your names]
- **Dialect validation:** [Native speaker names/handles]
- **Mentors:** [Mentor names from hackathon]
- **Data sources:** [admin.ch](https://admin.ch), [ch.ch](https://ch.ch),
  [bfs.admin.ch](https://bfs.admin.ch), and cantonal websites
- **Model:** [Apertus 1.5](https://apertus.ch) by EPFL, ETH Zurich, CSCS
- **Compute:** CSCS and Phoeniqs

---

## 📄 License

This project is licensed under [Apache 2.0 / MIT].
The benchmark dataset, evaluation code, and RAG pipeline are
free to use, modify, and redistribute.

---

*Built with ❤️ for open, trustworthy, and sovereign AI.*
*Hack Apertus · October 2026*
```

---

### README Quality Checklist

```
THE 10-SECOND TEST:
A judge opens your README. In 10 seconds, can they answer:
□ What is this project? (Swiss knowledge benchmark)
□ What are the results? (XX% → XX% improvement)
□ Why does it matter? (LLMs confuse Swiss and German law)
□ Can I reproduce it? (Quick Start section)

If any of these take more than 10 seconds to find → restructure.

FORMATTING CHECKS:
□ Title is clear and includes the hackathon track
□ First paragraph explains the problem in plain language
□ Key results table is visible WITHOUT scrolling
□ At least 2 charts are embedded directly in the README
□ Quick Start works (tested in fresh environment)
□ Limitations section is honest and specific
□ Credits section names real people and sources
□ License is clearly stated
□ No broken links or missing images
□ Total length: 1-2 pages of scrolling (not 5 pages)
```

---

### 📋 TODO Checklist for 5.3

```
□ Copy the README template
□ Fill in ALL XX placeholders with real numbers
□ Embed the 4 charts using relative paths
□ Test the Quick Start commands in a fresh clone
□ Verify all links work (relative paths to other docs)
□ Check: is the key results table visible without scrolling?
□ Check: can a non-technical person understand the problem?
□ Check: can a technical person reproduce the results?
□ Check: is the limitations section honest?
□ Proofread for typos and grammar
□ Git commit
```

### ⏱️ Time Budget: ~1–1.5 hours
### ✅ Done When: README passes the 10-second test and all links/images work

---

---

# 🎬 SUB-PHASE 5.4 — DEMO VIDEO

### 🎯 Goal
Record a 2–3 minute video that convinces the jury your project is rigorous, impactful, and reusable. This is your elevator pitch.

---

### Step 1: The Video Script (2:30 target)

```markdown
# Demo Video Script — Swiss Reality Check
# Target: 2 minutes 30 seconds
# Format: Screen recording with voiceover

---

[0:00-0:15] HOOK — The Problem
────────────────────────────────
SCREEN: Show a terminal where you ask Apertus a Swiss question
        and it gives a wrong (German) answer.

VOICEOVER:
"When you ask an open LLM about Swiss working hours, it tells
you 40 hours — the German standard. The Swiss answer is 45.
This isn't a random mistake. It's a systematic pattern: open
models default to German and EU norms because that's what
dominates their training data."

---

[0:15-0:45] THE BENCHMARK
────────────────────────────────
SCREEN: Scroll through your dataset — show the JSON structure,
        the source URLs, the 6 categories.

VOICEOVER:
"We built Swiss Reality Check — a benchmark of 120 verified
multiple-choice questions across politics, law, health insurance,
geography, holidays, and history. Every single answer is verified
against an official Swiss government source, with the URL recorded.
We also included 30 cultural scenarios testing neutrality,
multilingual fairness, and privacy norms — including parallel
versions in Swiss German and Romansh to test for dialect bias."

---

[0:45-1:15] THE FINDINGS
────────────────────────────────
SCREEN: Show Chart 1 (overall accuracy) and Chart 2 (heatmap).

VOICEOVER:
"Running Apertus 1.5 through our benchmark, the 8B model scores
XX percent and the 70B scores XX percent. The dominant failure
mode is German-EU confusion — the model applies German law when
asked about Swiss equivalents. Both models share this pattern,
which tells us it's a data problem, not a capacity problem."

---

[1:15-1:55] THE FIX
────────────────────────────────
SCREEN: Show the RAG pipeline in action — a question comes in,
        the retriever finds the right source, the model answers
        correctly with context.

VOICEOVER:
"We built a retrieval-augmented generation system over 30 official
Swiss source pages. When the model answers a question, it first
retrieves the most relevant Swiss source and uses it as context.
No fine-tuning needed. This improved the 8B model from XX percent
to XX percent — a XX percentage point gain. The biggest improvement
was in [category], where the retrieved sources directly corrected
the model's most common errors."

---

[1:55-2:20] THE RESULTS
────────────────────────────────
SCREEN: Show Chart 3 (before/after delta) and the comparison table.

VOICEOVER:
"The improvement works across both models and most categories,
with no significant regressions. We verified this on a held-out
test set that was never used during development. The full
statistical report, including confidence intervals, is in our repo."

---

[2:20-2:30] THE CLOSE
────────────────────────────────
SCREEN: Show the GitHub repo, the open license, the datasheet.

VOICEOVER:
"Everything is open — the benchmark, the evaluation code, the
RAG pipeline, and the dataset. Anyone can use this to test any
model's Swiss knowledge. Because sovereign AI starts with
knowing where your model fails."

---

[END]
```

---

### Step 2: Recording Tips

```
TECHNICAL SETUP:
□ Use OBS Studio (free) or your OS screen recorder
□ Resolution: 1920×1080 minimum
□ Record in a quiet room (no keyboard clicks, no notifications)
□ Use a decent microphone (even earbuds are better than laptop mic)
□ Close all other apps — no Slack notifications during recording!

SCREEN CONTENT:
□ Have all screens pre-loaded before recording:
  1. Terminal with a wrong Apertus answer
  2. VS Code showing the dataset JSON
  3. Browser showing the 4 charts (one per tab)
  4. Terminal showing the RAG pipeline running
  5. GitHub repo main page
□ Use a large font size (16pt+) so text is readable in the video
□ Zoom in on the important parts — don't show your entire desktop

VOICEOVER:
□ Speak slowly and clearly — 130-150 words per minute
□ Practice the script 2-3 times before recording
□ Record in one take if possible (editing takes time)
□ If you make a mistake, pause for 2 seconds and restart the
  sentence — you can cut the pause later
□ Sound enthusiastic but professional — you're pitching to judges

EDITING (if time allows):
□ Use DaVinci Resolve (free) or iMovie
□ Cut dead air and mistakes
□ Add simple text overlays for key numbers
□ Add your GitHub URL as a lower-third at the end
□ Export as MP4, 1080p, H.264
□ Keep the final file under 100MB for upload
```

---

### Step 3: Video Content Checklist

```
MUST INCLUDE:
□ The problem (German/EU confusion) — 15 seconds
□ The benchmark (120 verified questions) — 30 seconds
□ The findings (baseline scores + error patterns) — 30 seconds
□ The fix (RAG pipeline demo) — 40 seconds
□ The results (before/after numbers + charts) — 25 seconds
□ The close (open source, reusable) — 10 seconds

MUST NOT INCLUDE:
❌ Long code walkthroughs (judges don't have time)
❌ Apologies for limitations (mention them briefly in text)
❌ Comparisons to models you didn't test
❌ Background music that drowns out your voice
❌ A 10-minute video (hard limit: 3 minutes)
```

---

### 📋 TODO Checklist for 5.4

```
□ Finalize the video script with real numbers
□ Practice the script 2-3 times out loud
□ Pre-load all screens (terminal, charts, repo)
□ Set up screen recording software
□ Record the video (aim for one clean take)
□ Review: is the audio clear? Is the text readable?
□ Trim to 2:30 or less
□ Export as MP4, 1080p
□ Upload to a hosting service if needed (YouTube unlisted, or direct)
□ Save the video file in /video/demo.mp4
□ Git commit (or note the video URL in README)
```

### ⏱️ Time Budget: ~1–1.5 hours (script + practice + record + trim)
### ✅ Done When: A 2-3 minute MP4 video that tells the complete story

---

---

# 📦 SUB-PHASE 5.5 — SUBMISSION ASSEMBLY

### 🎯 Goal
Prepare and verify everything for upload to hackapertus.ch. No last-minute surprises.

---

### Step 1: Review Track 1B Submission Requirements

```
┌─────────────────────────────────────────────────────────────┐
│  CHECK THE GETTING STARTED GUIDE (from Phase 0.1)           │
│                                                             │
│  The exact Track 1B submission format was released on        │
│  1 Oct at 12:00 CEST. You should have captured these        │
│  requirements. Verify:                                      │
│                                                             │
│  □ What file formats are accepted? (PDF? ZIP? URL?)         │
│  □ Is there a specific template to fill out?                │
│  □ What fields are required? (team name, track, etc.)       │
│  □ Is there a word limit for the description?               │
│  □ Is the video uploaded separately or linked?              │
│  □ Is the GitHub repo URL required?                         │
│  □ Are there specific judging criteria listed?              │
│  □ Is there a demo requirement beyond the video?            │
│                                                             │
│  If you haven't checked this since Oct 1 → DO IT NOW.       │
│  The format requirements override everything in this guide. │
└─────────────────────────────────────────────────────────────┘
```

---

### Step 2: The Submission Package Checklist

```
SUBMISSION PACKAGE — Everything you need ready:

CORE:
□ GitHub repo URL (public, open license)
□ Project title: "Swiss Reality Check"
□ Track: 1B — Swiss Voices
□ Team name and members
□ Short description (1-2 sentences):
  "An open benchmark measuring Apertus 1.5's Swiss knowledge,
   languages, and values, with a measured RAG improvement of
   +XX pp on a verified test set."

DOCUMENTS:
□ README.md (complete with results and charts)
□ DATASHEET.md (Gebru et al. format)
□ Statistical report (eval/results/final_scores/statistical_report.md)

MEDIA:
□ Demo video (2-3 min MP4, or hosted URL)
□ 4 charts (embedded in README, also available as PNGs)

TECHNICAL:
□ Reproducible eval pipeline (requirements.txt + .env.example)
□ Dataset files (120 MCQs + 30 scenarios + dialect items)
□ RAG improvement code (fix/rag/)

OPTIONAL BUT IMPRESSIVE:
□ Error taxonomy document
□ Cross-model comparison narrative
□ Datasheet following academic format
□ Mentor session notes (shows you used the resources)
```

---

### Step 3: The Submission Description Template

```
PROJECT TITLE: Swiss Reality Check

TRACK: 1B — Swiss Voices

ONE-LINER:
An open benchmark of 170+ verified items measuring how well
Apertus 1.5 handles Swiss knowledge, languages, and values,
with a RAG improvement of +XX percentage points.

DESCRIPTION (200-300 words):
Open multilingual LLMs systematically confuse Swiss and German/EU
norms due to training data imbalance. Swiss Reality Check measures
these gaps with 120 verified multiple-choice questions sourced
from official Swiss government websites (admin.ch, ch.ch,
bfs.admin.ch), 30 cultural scenarios testing neutrality and
multilingual fairness, and a pilot dialect comprehension set.

Key findings:
- Apertus 8B scores XX% and 70B scores XX% on Swiss knowledge
- The dominant failure mode is German/EU confusion (XX% of errors)
- A lightweight RAG system over 30 official sources improved
  8B accuracy by +XX pp with no significant regressions
- Both models show a dialect safety gap when prompted in
  Swiss German vs Standard German

All code, data, and results are open-source and reproducible.
The benchmark is designed to be reusable for evaluating any
LLM's Swiss knowledge and can be extended to other countries.

REPO: https://github.com/YOUR_USERNAME/swiss-reality-check
VIDEO: [URL or attached]
LICENSE: [Apache 2.0 / MIT]
```

---

### Step 4: Final Pre-Submission Verification

```
┌─────────────────────────────────────────────────────────────┐
│  THE 30-MINUTE PRE-SUBMISSION CHECK (do this Thu evening)   │
│                                                             │
│  1. Open your GitHub repo in an incognito window            │
│     □ Does the README render correctly?                     │
│     □ Do all 4 charts display?                              │
│     □ Do all internal links work?                           │
│     □ Is the license visible?                               │
│     □ Is the repo public?                                   │
│                                                             │
│  2. Test the Quick Start                                    │
│     □ Clone to a temp directory                             │
│     □ pip install -r requirements.txt                       │
│     □ Does it install without errors?                       │
│                                                             │
│  3. Check the video                                         │
│     □ Does it play?                                         │
│     □ Is the audio clear?                                   │
│     □ Is it under 3 minutes?                                │
│     □ Is the URL accessible (not private)?                  │
│                                                             │
│  4. Verify submission format                                │
│     □ Re-read the Getting Started Guide requirements        │
│     □ Do you have everything the form asks for?             │
│     □ Is there a file size limit?                           │
│                                                             │
│  5. Prepare for tomorrow                                    │
│     □ Bookmark hackapertus.ch/online-hack/submissions       │
│     □ Have your login credentials ready                     │
│     □ Set an alarm for 07:00 CEST Friday                    │
│     □ Target submission: 08:00 CEST (4-hour buffer)         │
│                                                             │
│  If everything checks out → go to sleep. You've earned it.  │
└─────────────────────────────────────────────────────────────┘
```

---

### 📋 TODO Checklist for 5.5

```
□ Re-read Track 1B submission requirements from Getting Started Guide
□ Fill out the submission description template
□ Verify GitHub repo is public and renders correctly
□ Verify all charts display in the README
□ Verify video URL is accessible
□ Test Quick Start in fresh clone
□ Prepare all files/URLs for the submission form
□ Bookmark the submission page
□ Set alarm for 07:00 CEST Friday
□ Get some rest — you'll need energy for Phase 6
```

### ⏱️ Time Budget: ~45–60 minutes
### ✅ Done When: Everything is ready for Friday morning submission with zero stress

---

---

# 📊 PHASE 5 — SUMMARY DASHBOARD

| Sub-Phase | Output | Time | Priority | Status |
|---|---|---|---|---|
| **5.1** Repo Finalization | Clean, reproducible repo | 1–1.5h | 🔴 CRITICAL | ⬜ |
| **5.2** Datasheet | DATASHEET.md (Gebru et al.) | 45–60min | 🟡 HIGH | ⬜ |
| **5.3** README Polish | Complete README with results | 1–1.5h | 🔴 CRITICAL | ⬜ |
| **5.4** Demo Video | 2-3 min MP4 | 1–1.5h | 🔴 CRITICAL | ⬜ |
| **5.5** Submission Assembly | All files ready for upload | 45–60min | 🔴 CRITICAL | ⬜ |

**Total Phase 5 time: ~5–6 hours on Thu 15 Oct (afternoon/evening)**

---

## ⚡ How I Can Help Right Now

- **"Write my README"** → Give me your final numbers and I'll fill in the complete template
- **"Write my datasheet"** → Tell me your team details and I'll customize it
- **"Write my video script"** → Share your key findings and I'll draft the 2:30 script
- **"Review my repo"** → Paste your file structure and I'll flag issues
- **"Write the submission description"** → Give me the numbers and I'll draft the 300-word pitch
- **"What should I cut if I'm running behind?"** → I'll tell you what's essential vs nice-to-have

Your call. You're almost there. 🏁🏆
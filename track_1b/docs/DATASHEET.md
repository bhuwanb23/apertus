# Datasheet — Swiss Reality Check Benchmark

Following the framework of Gebru et al. (2021), "Datasheets for Datasets."

---

## 1. Motivation

### For what purpose was the dataset created?
To evaluate how well open large language models handle Swiss-specific
knowledge, cultural norms, and dialectal variation. Existing LLM
benchmarks (MMLU, HELM, etc.) are heavily US/UK-centric and do not
test country-specific institutional knowledge. This benchmark fills
that gap for Switzerland, and supports measuring whether retrieval over
verified Swiss sources improves model answers without contaminating the
prompt with the answer key.

### Who created the dataset?
Created by team **Swiss Reality Check** — **Bhuwan B, Padmanaban G, and
Avinash A** — during **Hack Apertus** Online Phase (1–16 October 2026),
**Track 1 — Apertus Readiness**, Challenge **1B: Swiss Voices** — *Localising
Apertus to Swiss Languages, Knowledge and Values*. Swiss German dialect items
are **not yet validated** by a native speaker (`validated_by: null` on all 30
items) — see limitations.

### Who funded the creation?
Self-funded. Model weights / program context provided through the
Hack Apertus program (swiss-ai / Apertus). Local evaluation used consumer
GPU hardware (8 GB VRAM).

---

## 2. Composition

### What do the instances consist of?
The dataset contains three components:

**A. Swiss Knowledge MCQs (120 items)**
- Format: Multiple-choice (4 options, 1 correct)
- Fields: question, options (A–D), correct answer, source id / URL,
  source quote, category, difficulty
- Categories (20 each): politics, law, health, geography, services, history
- Primary language: English
- Split: 84 development / 36 sealed test (seed 42, stratified by
  category × difficulty)

**B. Values & Norms Scenarios (30 items)**
- Format: Open-ended prompts with required / forbidden elements
- Rubric scores **framing and institutional competence**, not political side
- Categories: neutrality, multilingual fairness, privacy, consensus,
  institutional (6 each)
- Multilingual: 10 pairs, 53 renderings across 6 languages

**C. Dialect Items (30 items)**
- Format: Swiss German (Alemannic) sentences with Standard German references
- Task types: T1 translation (12), T2 comprehension MCQ (8),
  T3 culture-in-dialect MCQ (5), T4 dialect-identification MCQ (5)
- Sources: verbatim sentences from Alemannic Wikipedia (CC BY-SA 4.0)
- Validation status: **pilot / unvalidated** (`validated_by: null`)

### How many instances are there?
- Knowledge: 120 (84 dev + 36 test)
- Values: 30 scenarios (+ 53 multilingual renderings)
- Dialect: 30
- **Total core items: 180** (plus multilingual renderings)

### Does the dataset contain all possible instances?
No. This is a curated sample designed to cover common Swiss institutional
domains. It is not exhaustive.

### Is there a label or target associated with each instance?
- Knowledge: Yes — correct answer letter (A/B/C/D), verified against a quote
- Values: Yes — required / forbidden elements and a 0–2 rubric
- Dialect: Yes — reference translations / MCQ keys; scoring protocol documented

### Is any information missing from individual instances?
Dialect items lack native-speaker validation metadata. Multilingual value
renderings include unvalidated author-written text (see
`data/values/multilingual_pairs_NOTES.md` if present).

### Are relationships between instances made explicit?
Yes. Multilingual pairs are linked. Dev/test split is documented and sealed
for knowledge. Source registry links every knowledge item to a harvested page.

---

## 3. Collection Process

### How was the data acquired?
**Knowledge items:** Drafted from official Swiss government and public
information websites (ch.ch, admin.ch, bfs.admin.ch, SEM, FOPH, and related
pages listed in `data/sources/source_registry.csv`). AI assistance was used
for drafting; every answer was verified against a saved source excerpt
(`data/sources/raw_pages/`).

**Values scenarios:** Written by the project author based on Swiss
institutional frames. Multilingual versions are labeled with validation
status fields.

**Dialect items:** Swiss German sentences copied **verbatim** from
Alemannic Wikipedia; Standard German references authored for scoring.

### What mechanisms were used to collect the data?
Manual curation with AI-assisted drafting. Source pages saved as text
excerpts. Automated verifiers (`scripts/verify_knowledge.py`,
`verify_values.py`, `verify_dialect.py`) enforce structural and provenance
constraints.

### Who was involved in the data collection?
Bhuwan B. Native-speaker dialect validation is outstanding.

### Over what timeframe was the data collected?
13–16 October 2026 (Hack Apertus online phase).

---

## 4. Preprocessing / Cleaning / Labeling

### Was any preprocessing applied?
- Knowledge: quote matching, duplicate removal, ambiguous items rewritten
- Values: rubric rewritten to score framing, not political position
- Dialect: provenance resolution against Alemannic Wikipedia files;
  mojibake repair scripts applied where needed

### Was the data cleaned?
Yes. Items with ambiguous answers, broken provenance, or verifier failures
were corrected or discarded during build.

### Was the data labeled?
Knowledge labels are definitive against official sources. Values labels are
rubric-defined and involve judgment when scored by an LLM judge. Dialect
MCQ keys are deterministic; translation scoring uses keyword coverage.

---

## 5. Uses

### Has the dataset been used for any tasks already?
Yes. Used to evaluate **Apertus 1.5 8B** (Q4_K_M) on knowledge, values, and
dialect, and to measure a BM25 RAG improvement on the sealed knowledge test
set: **55.6% → 86.1%** (+30.6 pp, McNemar p=0.001). **Apertus 70B was not
evaluated** (hardware scope: 8 GB VRAM).

### What other tasks could the dataset be used for?
- Evaluating any LLM's Swiss knowledge (not just Apertus)
- Benchmarking RAG systems on country-specific knowledge
- Studying German/EU confusion in multilingual models
- Dialect comprehension research (after native validation)

### Is there anything about the composition that might impact future uses?
- Test set (n=36) is small; statistical power is limited
- Knowledge items reflect Swiss law as of October 2026
- Dialect items are unvalidated and dialect coverage is uneven
- Values scenarios reflect the author's framing of Swiss norms

---

## 6. Distribution

### How will the dataset be distributed?
Publicly via GitHub (`https://github.com/bhuwanb23/apertus`) and Hugging Face
Datasets (`https://huggingface.co/datasets/bhuwanb23/apertus`). The **dataset**
— its compilation, metadata and annotations — is released under
**CDLA-Permissive-2.0**; the **evaluation code** is Apache-2.0 (see `LICENSE`).

### When will the dataset be distributed?
16 October 2026 (hackathon submission deadline).

### Will the dataset be distributed under a copyright or IP license?
CDLA-Permissive-2.0 for the dataset's compilation, metadata and annotations —
free to use, modify, and redistribute. The evaluation code is Apache-2.0.

### Have any third parties imposed IP-based restrictions?
Knowledge sources are official Swiss public information. Alemannic Wikipedia
excerpts used for dialect items are CC BY-SA 4.0. Those excerpts keep their own
terms — the dataset's CDLA-Permissive-2.0 grant does not relicense them, and
redistributors should respect them for that text.

---

## 7. Maintenance

### Who will be supporting/hosting/maintaining the dataset?
Bhuwan B. The GitHub and Hugging Face repositories will remain public.

### How can the owner/curator be contacted?
GitHub: https://github.com/bhuwanb23 · Hugging Face: https://huggingface.co/bhuwanb23

### Will the dataset be updated?
Possible future work: native dialect validation, larger item counts, 70B
baselines when hardware allows, human values audit (B5).

### If the dataset becomes obsolete, how will this be communicated?
A notice will be added to the README and this DATASHEET.md.

---

## 8. Known Biases and Limitations

### What are the known biases?
1. **Language bias:** Most knowledge items are in English.
2. **Dialect bias / validation gap:** Items are unvalidated; regional coverage
   is incomplete.
3. **Domain selection:** Six categories are a sample, not a population census
   of Swiss life.
4. **Temporal bias:** Facts as of October 2026.
5. **Cultural perspective:** Values scenarios are one author's framing.
6. **Source bias:** Official / institutional sources dominate knowledge.

### What are the known limitations?
1. Small test set (n=36)
2. MCQ format tests recognition, not free recall
3. Values scoring used a self-judged 8B judge; no human agreement rate yet
4. Dialect section is a pilot without native validation
5. Text only — no audio modality
6. 70B arms not run — no cross-scale claim

---

## 9. Ethical Considerations

### Does the dataset contain sensitive data?
No personal data. Content is derived from public government sources and
public Wikipedia text.

### Could the dataset cause harm?
Unlikely. The benchmark aims to reduce Swiss misinformation from LLMs.
Misuse (e.g. training on the sealed test set) would weaken evaluative
validity — users should respect the 84/36 split.

### Does the dataset reinforce existing biases?
The benchmark is designed to *surface* German/EU-centric model biases, not
to endorse them. Reporting those biases is part of the intended use.

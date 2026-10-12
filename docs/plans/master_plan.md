# 🗺️ Swiss Reality Check — Full Phase Map

Here's the complete breakdown. Think of this as our **mission control board**. We'll zoom into each phase and sub-phase one by one when you're ready.

---

## PHASE 0 · PRE-FLIGHT & INFRASTRUCTURE
**📅 Mon 12 Oct | ⏱️ ~4–5h | 🎯 Goal: Remove all blockers before real work starts**

| Sub-Phase | Name | What Happens |
|---|---|---|
| **0.1** | Rules & Criteria Lock-In | Read the Getting Started Guide for Track 1B. Extract exact submission format, judging rubric, file requirements, and any hidden constraints. Paste them to me for cross-checking. |
| **0.2** | Model Access & Compute | Get 8B and 70B running. Confirm whether via CSCS/Phoeniqs endpoints, Hugging Face weights (`swiss-ai/Apertus-v1.5-8B/-70B`), or another route. Run a "hello world" prompt on both. Check the model card for multimodal/audio support. |
| **0.3** | Community & Team | Join Discord. Post for Swiss German + Romansh speakers. Book a mentor session. Identify 1–2 potential collaborators if going solo feels risky. |
| **0.4** | Repo & Tooling Scaffold | Create public GitHub repo with open license (Apache 2.0 or MIT). Set up folder structure: `/data`, `/eval`, `/fix`, `/results`, `/docs`. Write README skeleton. Initialize evaluation script framework. |

---

## PHASE 1 · DATASET ENGINEERING
**📅 Tue 13 Oct (bulk) → Wed 14 Oct (finish) | ⏱️ ~12–14h total | 🎯 Goal: Build the benchmark that judges will want to reuse**

### 1A · Swiss Knowledge MCQs ⭐ (The Star Pillar)

| Sub-Phase | Name | What Happens |
|---|---|---|
| **1A.1** | Source Harvesting | Collect ~30–40 official Swiss source pages from admin.ch, ch.ch, bfs.admin.ch, and cantonal sites. Organize by the 6 categories. These become both your question source and your RAG corpus later. |
| **1A.2** | Question Drafting | Draft 120 MCQs (20 per category): Politics, Law, Health Insurance, Geography, Holidays/Customs, History/Institutions. Each has question + 4 options + correct answer. I'll generate draft batches; you edit. |
| **1A.3** | Verification & Source Linking | **The most critical step.** You verify every single answer against its source URL. No guessing. No LLM-trusted answers. Record the exact URL per question. |
| **1A.4** | Dev/Test Split | Randomly split 70/30 → 84 dev questions (used to design the fix) + 36 held-out test questions (touched only once, at the very end). Stratify by category so both sets are balanced. |

### 1B · Values & Norms Scenarios

| Sub-Phase | Name | What Happens |
|---|---|---|
| **1B.1** | Rubric Design | Create the 0–2 scoring rubric. Define what a 0 (wrong/biased), 1 (partially correct), and 2 (accurate, neutral, culturally appropriate) looks like with concrete examples. |
| **1B.2** | Scenario Writing | Write 30 short prompts testing neutrality, consensus culture, multilingual fairness, privacy expectations, and no EU/German-centric assumptions. |
| **1B.3** | Multilingual Pairing | Create parallel versions of ~10 scenarios in Standard German + Swiss German and/or Romansh. These test the "dialect safety gap" — does the model behave differently? |

### 1C · Dialect & Language Items

| Sub-Phase | Name | What Happens |
|---|---|---|
| **1C.1** | Native Speaker Recruitment | Confirm at least one Swiss German speaker from Discord. If Romansh speaker available, bonus. If nobody responds by Tue evening, trigger fallback (labeled pilot). |
| **1C.2** | Comprehension Item Drafting | Write 20–30 Swiss German sentences with reference Standard German translations. Test comprehension, not just vocabulary. |
| **1C.3** | Validation & Pilot Label | Native speaker validates every item. If no speaker, reduce to 10 items clearly labeled "unvalidated pilot" in the datasheet. |

---

## PHASE 2 · EVALUATION PIPELINE
**📅 Tue 13 Oct (partial) → Wed 14 Oct | ⏱️ ~6–8h | 🎯 Goal: Run baselines that produce trustworthy, reproducible numbers**

| Sub-Phase | Name | What Happens |
|---|---|---|
| **2.1** | Eval Script Architecture | Build the main evaluation harness. Fixed temperature (0), saved prompt templates, structured output parsing. Must handle both 8B and 70B with identical settings. |
| **2.2** | Knowledge Auto-Scoring | Implement MCQ accuracy calculation. Parse model output → extract chosen option → compare to correct answer. Break down by category and language. |
| **2.3** | Values LLM-Judge Pipeline | Set up the LLM-as-judge scoring using your rubric. Choose the judge model (70B Apertus? external model?). Implement the 20% manual cross-check protocol. |
| **2.4** | Dialect Scoring Protocol | Define how dialect responses are scored (exact match? semantic similarity? human rating?). Keep it simple. |
| **2.5** | Baseline Runs | Execute full evaluation on both 8B and 70B. Start with the first 40 knowledge questions on Tue to catch technical bugs early. Complete all baselines by Wed evening. |

---

## PHASE 3 · FAILURE ANALYSIS & IMPROVEMENT
**📅 Wed 14 Oct | ⏱️ ~6–8h | 🎯 Goal: Find the biggest gap and close it measurably**

| Sub-Phase | Name | What Happens |
|---|---|---|
| **3.1** | Error Taxonomy | Categorize all wrong answers. Is the model confusing Swiss law with German law? Hallucinating cantonal details? Defaulting to EU norms? Build a failure pattern table. |
| **3.2** | Weakest Area Selection | Pick the single area with the worst score AND the clearest fix path. This becomes your improvement target. |
| **3.3** | Improvement Implementation | Execute one of three options: |
| **3.3a** | ↳ Option A: System Prompt | Write a Swiss-context system prompt with key facts and behavioral instructions. Quick to test, modest gains. |
| **3.3b** | ↳ Option B: RAG Pipeline | Build a small retrieval step over your ~30 harvested official source pages. Retrieve relevant context → inject into prompt → re-evaluate. **Highest expected ROI.** |
| **3.3c** | ↳ Option C: LoRA Fine-Tune *(Stretch)* | Fine-tune 8B on the 84 dev questions. Only if baseline is done by Tue night and GPU is available. |
| **3.4** | Dev Set Validation | Test the improvement on the dev set first. Confirm it actually helps and doesn't break other categories. Iterate once if needed. |

---

## PHASE 4 · FINAL EVALUATION & RESULTS
**📅 Thu 15 Oct (morning) | ⏱️ ~4–5h | 🎯 Goal: Produce the before/after numbers that win**

| Sub-Phase | Name | What Happens |
|---|---|---|
| **4.1** | Held-Out Test Run | Run the 36 held-out knowledge questions + held-out values/dialect items on both models, both before and after the improvement. **This is the only time the test set is touched.** |
| **4.2** | Statistical Comparison | Calculate accuracy deltas, per-category breakdowns, and cross-model differences. Note if improvements are consistent or noisy. |
| **4.3** | Visualization | Create 3–4 clear charts: (1) Overall accuracy 8B vs 70B, (2) Category breakdown heatmap, (3) Before/after improvement bar chart, (4) Values rubric score distribution. |
| **4.4** | Cross-Model Narrative | Write the story: where does the 70B outperform the 8B? Where do both fail? Where did the fix help most? This becomes the core of your README and video. |

---

## PHASE 5 · PACKAGING & DELIVERABLES
**📅 Thu 15 Oct (afternoon/evening) | ⏱️ ~5–6h | 🎯 Goal: Make the project look as professional as a published research artifact**

| Sub-Phase | Name | What Happens |
|---|---|---|
| **5.1** | Repo Finalization | Clean up code, remove debug artifacts, ensure `pip install -r requirements.txt` works, verify the eval script reproduces your numbers from scratch. |
| **5.2** | Datasheet | Write a proper datasheet: how the data was created, source list, known biases, language coverage, limitations. Follow Gebru et al. format or similar. |
| **5.3** | README Polish | Complete the README: project overview, motivation, how to reproduce, results summary, limitations, credits. This is what judges read first. |
| **5.4** | Demo Video | Record 2–3 minutes: screen-share the benchmark running, show the before/after charts, explain the key finding. I'll write the script. |
| **5.5** | Submission Assembly | Prepare all files for upload to hackapertus.ch. Double-check the Track 1B format requirements from Phase 0.1. |

---

## PHASE 6 · SUBMISSION & POST-HACK
**📅 Fri 16 Oct (morning) | ⏱️ ~2–3h | 🎯 Goal: Submit early, survive the deadline, plan next moves**

| Sub-Phase | Name | What Happens |
|---|---|---|
| **6.1** | Final QA Checklist | Run through the deliverables checklist from the plan. Verify every box is ticked. Test the submission link. |
| **6.2** | Submission Execution | **Submit by 08:00 CEST** (4-hour buffer before the 12:00 hard deadline). Upload to hackapertus.ch, NOT Devpost. Screenshot confirmation. |
| **6.3** | Post-Submission | Share in Discord. Thank mentors and helpers. Note what you'd do differently for the on-site rounds. Start thinking about the Grand Finals path. |

---

## 📊 Visual Timeline

```
Mon 12    Tue 13         Wed 14         Thu 15         Fri 16
  │         │              │              │              │
  ├── P0 ───┤              │              │              │
  │ Setup   │              │              │              │
  │         ├── P1 ────────┤              │              │
  │         │  Dataset     │              │              │
  │         │  (bulk)      │  (finish)    │              │
  │         │    ├── P2 ───┤              │              │
  │         │    │  Eval   │              │              │
  │         │    │         ├── P3 ────────┤              │
  │         │    │         │  Fix         │              │
  │         │    │         │              ├── P4 ──┤     │
  │         │    │         │              │ Results│     │
  │         │    │         │              │   ├── P5 ────┤
  │         │    │         │              │   │ Package  │
  │         │    │         │              │   │      P6 ─┤
  │         │    │         │              │   │   Submit │
  ▼         ▼    ▼         ▼              ▼   ▼      ▼   ▼
 08:00    08:00 14:00    08:00          08:00 14:00  08:00 12:00
                                                          ▲
                                                     HARD DEADLINE
```

---

## 🎮 How We Proceed

Tell me which phase to zoom into first. I recommend starting with **Phase 0** (since everything depends on it), but if you've already done the setup and want to jump straight to **Phase 1A.2** (question drafting) or any other sub-phase, just say the number.

**Example commands:**
- *"Let's deep dive into 1A.2"* → I'll generate the first batch of MCQs
- *"Walk me through 3.3b"* → I'll design the RAG pipeline architecture
- *"Start from 0.1"* → I'll help you extract and analyze the judging criteria

Your move. 🎯
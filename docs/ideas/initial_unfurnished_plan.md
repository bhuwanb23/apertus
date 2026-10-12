# ✅ Fully Absorbed — "Swiss Reality Check" Plan

I've read every section, every table, every fallback. Here's my internal model of your plan so you know exactly what I'm working with when your questions come.

---

## 🧭 Core Logic of the Plan (As I Understand It)

The entire strategy rests on one insight: **you don't need to be Swiss — you need to be verifiable.** Every claim traces to an official URL. That removes the expertise barrier and makes the benchmark trustworthy to judges who *are* Swiss.

---

## 📐 Architecture at a Glance

```
Swiss Reality Check
├── DATASET (3 pillars, 70/30 dev/test split)
│   ├── 🇨🇭 Knowledge: 120 MCQs × 6 categories (STAR)
│   │   └── Sources: admin.ch, ch.ch, bfs.admin.ch, cantonal sites
│   ├── ⚖️ Values: 30 scenarios × ≤4 languages
│   │   └── Scored 0–2 via rubric + LLM-judge + 20% manual audit
│   └── 🗣️ Dialect: 20–30 items, text-only, native-validated
│       └── Fallback: labeled pilot if no speaker found
│
├── EVALUATION (fixed temp=0, saved templates)
│   ├── Knowledge → auto accuracy by category & language
│   ├── Values → LLM-judge + manual cross-check
│   └── Dialect → native speaker scoring
│
├── IMPROVEMENT (one measured delta)
│   ├── PRIMARY: System prompt or RAG over ~30 official pages
│   └── STRETCH: LoRA on 8B (only if baseline done by Day 2 end)
│
└── DELIVERABLES
    ├── Open repo + license + datasheet
    ├── Eval code (reproducible)
    ├── Before/after tables + 3–4 charts
    ├── README with honest limitations
    ├── 2–3 min demo video
    └── Submitted on hackapertus.ch by Fri 08:00 CEST (4h buffer)
```

---

## 🔑 Key Design Decisions I've Noted

| Decision | Why It's Smart |
|---|---|
| **MCQ format for knowledge** | Enables automatic, deterministic scoring — no judge ambiguity |
| **Source URL on every question** | Eliminates "how do we know this is right?" objections from jury |
| **70/30 dev/test split** | Prevents overfitting the improvement to the eval set; judges will notice |
| **LLM-judge + 20% manual audit for values** | Pragmatic balance between scale and credibility; reporting agreement rate is a trust signal |
| **Fix the weakest area, not all three** | Focused effort → measurable delta → stronger narrative |
| **Fallback cascade: dialect → values → NEVER knowledge or README** | Protects the core value proposition under time pressure |
| **Submit at 08:00, not 12:00** | Eliminates last-minute infrastructure disasters |
| **Honest reporting of small/mixed improvements** | Aligns with the open-science ethos the jury will reward |

---

## 📅 Timeline I'm Tracking

| Day | Date | Hours | Milestone |
|---|---|---|---|
| **Mon** | 12 Oct | 4–5h | Guide review, Discord, model access, repo skeleton, eval script structure |
| **Tue** | 13 Oct | ~8h | 120 knowledge Qs drafted + sourced, values draft, first 40-Q baseline run |
| **Wed** | 14 Oct | ~8h | Full baselines 8B+70B, failure analysis, implement improvement |
| **Thu** | 15 Oct | ~8h | Held-out eval, charts, README, demo video |
| **Fri** | 16 Oct | morning | Final checks, **submit by 08:00 CEST** |

---

## 🤖 My Role (As Defined by You)

| I Draft | You Verify & Run |
|---|---|
| Question templates per category | Each answer against its source URL |
| Evaluation script (Python) | Models on actual infrastructure |
| Values rubric (0–2 scale) | Native speaker coordination on Discord |
| Chart code (matplotlib/plotly) | Final submission on hackapertus.ch |
| README + limitations section | Judgment calls on scope cuts |
| Demo video script | Recording the video |

---

## ⚠️ Subtle Things I've Flagged Internally

1. **Date consistency checks out:** Oct 1 2026 = Thursday → Oct 12 = Monday → Oct 16 = Friday. Your "Mon 12 Oct" and "Fri 16 Oct" labels are correct.

2. **The 120-question target is ambitious for one day (Tue).** That's ~15 questions per hour including source verification. I should help by pre-generating draft batches from specific admin.ch pages so you're editing, not writing from scratch.

3. **The "LLM-as-judge" step needs a specific model choice.** You'll need to decide whether to use the 70B Apertus itself (circular but defensible if disclosed), GPT-4o, or another model. This affects credibility.

4. **The RAG improvement over ~30 official pages is the highest-ROI move.** It's technically simple, directly addresses knowledge gaps, and produces a clear before/after story. I'd prioritize this over the system-prompt-only approach.

5. **The datasheet mention is a quiet power move.** Most hackathon teams skip documentation rigor. A proper datasheet (following the Gebru et al. format or similar) signals maturity to an academic-adjacent jury from EPFL/ETH.

---

## 🟢 Ready State

I have the complete plan internalized — goals, scope, dataset schema, eval methodology, improvement strategy, schedule, deliverables, risks, fallbacks, and my own role.

**Ask me anything.** Whether it's:
- "Draft the first 20 politics MCQs from admin.ch"
- "Write the evaluation script skeleton"
- "Design the 0–2 values rubric"
- "Help me structure the RAG pipeline over official sources"
- "What do I do if the 70B endpoint is down on Wednesday?"
- "Polish the README and demo script"

I'm locked in and ready to execute. Let's build this. 🇨🇭🏆
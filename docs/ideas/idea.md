# ✅ Fully Read & Understood — Hack Apertus Hackathon

I've absorbed every detail you've shared. Here's my structured mental model so you know we're aligned before your questions come:

---

## 🏗️ Hackathon Skeleton

| Element | Detail |
|---|---|
| **Dates** | 1–16 Oct 2026 (online phase) |
| **Deadline** | 16 Oct, 12:00 CEST — **hard cutoff, no extensions** |
| **Model** | Apertus 1.5 (8B + 70B), open, 1,811 languages |
| **Built by** | EPFL, ETH Zurich, CSCS |
| **Submission** | hackapertus.ch (NOT Devpost for final) |
| **Team** | 1–5 members |
| **Grand Finals** | 14 May 2027, St. Gallen |
| **Ethos** | Everything shipped stays **open & reusable** |

---

## 🎯 Tracks (My Understanding of Competition Landscape)

| Track | Focus | Expected Competition | Your Verdict |
|---|---|---|---|
| **1A – Red-Teaming** | Break the model (text/voice/image) | High — generic jailbreak lists will flood in | ❌ Too broad for short timeline |
| **1B – Swiss Voices** | Dialects, Swiss knowledge, cultural norms | **LOW** — requires real Swiss expertise most teams lack | ✅ **YOUR PICK** |
| **2A – Academia** | Solve a partner's specific challenge | Medium — depends on challenge-skill fit | ⚠️ Backup if strong match exists |
| **2B – Own Project** | Open-ended showcase | **HIGHEST** — chatbots & RAG demos everywhere | ❌ Too noisy to stand out |

---

## 🧠 Your Chosen Strategy: "Swiss Reality Check" (Track 1B)

**Core thesis:** Build a **reusable open benchmark** + **measurable improvement** — not just a failure report.

### Three Pillars
1. **Dialects** — Swiss German comprehension/translation (audio transcription *if* 1.5 multimodal supports it; text-only fallback stated openly)
2. **Swiss Domain Knowledge** — 100–150 verified questions on cantonal law, direct democracy, health insurance, tenancy, holidays, federal vs. cantonal responsibilities
3. **Values & Norms** — Neutrality, consensus culture, multilingual fairness, privacy, "dialect safety gap" (does the model behave differently in Swiss German/Romansh vs. Standard German?)

### The Winning Differentiator
> **Before/after numbers on a held-out set** after applying a targeted fix (LoRA fine-tune on 8B *or* retrieval-augmented system prompt with Swiss sources).

### Release Package
Dataset + eval code + results + adapter + reproduction README — all openly licensed.

---

## ⚠️ Critical Observations I've Flagged for You

1. **Timeline tension:** The hackathon runs 1–16 Oct (16 days), but your plan covers 12–16 Oct (~4 days). If you're truly starting on the 12th, scope discipline is *everything*. One star pillar, two supporting ones.

2. **Compute bottleneck:** 70B access via CSCS/Phoeniqs may have queue times. Get access running **Day 1** or you'll lose a full day to infrastructure.

3. **Audio modality uncertainty:** The plan wisely says "verify first on the model card." If 1.5 is text-only, pivot cleanly to text dialect comprehension and *say so* — judges reward honesty over overclaiming.

4. **Hand-verified > machine-generated:** 80 high-quality, native-speaker-validated questions will beat 500 LLM-generated ones. Judges *will* spot synthetic data.

5. **Romansh as a secret weapon:** Almost nobody will test Romansh. Even 10–15 Romansh prompts could be a jaw-dropping differentiator if the model fails spectacularly (which it likely will on a 1,811-language model where Romansh data is tiny).

6. **Submission format unknown until 1 Oct 12:00 CEST:** The Getting Started Guide drops then. Your plan must stay flexible until the exact rubric is live.

7. **Multi-phase structure:** This online round is just the *opening stage*. Winning here gets you to on-site Swiss hackathons and eventually the May 2027 Grand Finals. Think of this as a qualifying round — strong enough to advance, not necessarily your magnum opus.

---

## 🟢 I'm Ready

I have the full picture: the rules, the tracks, the competition dynamics, your chosen strategy, the timeline constraints, and the winning criteria.

**Fire your questions.** Whether it's about:
- Refining the benchmark design
- Crafting the LoRA fine-tuning pipeline
- Writing the Swiss knowledge questions
- Structuring the submission for maximum jury impact
- Contingency plans if compute or data falls through
- How to make the demo video unforgettable

I'm locked in. Let's win this. 🏆
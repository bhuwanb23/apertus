# 🔬 PHASE 3 — FAILURE ANALYSIS & IMPROVEMENT: Complete Deep Dive

**This is where you WIN or LOSE the hackathon. Every other team will find problems. You will find problems AND fix one measurably. That delta is your trophy.**

---

## 🧠 Before You Start: Core Principles

```
IMPROVEMENT GOLDEN RULES:

1. FIX ONE THING WELL — not three things poorly
2. MEASURE BEFORE AND AFTER on the SAME questions (dev set)
3. NEVER TOUCH THE TEST SET during this phase
4. BE HONEST if the fix is small — a 5% improvement honestly
   reported beats a 30% improvement that looks suspicious
5. DOCUMENT WHY you chose this fix — judges love reasoning
6. KEEP IT SIMPLE — a RAG over 30 pages beats a complex
   multi-agent pipeline that barely works
```

---

## 📁 File Structure Additions

```
/fix
├── error_taxonomy.md           ← categorized failure patterns
├── weakest_area_analysis.md    ← why you chose what you chose
├── /system_prompt
│   ├── swiss_context_v1.txt    ← the improved system prompt
│   └── results_v1.json         ← dev set results with this prompt
├── /rag
│   ├── /corpus                 ← your ~30 source pages as text files
│   ├── embeddings.py           ← embed the corpus
│   ├── retriever.py            ← retrieve relevant chunks
│   ├── rag_prompt.py           ← inject context into prompt
│   ├── run_rag_eval.py         ← re-evaluate with RAG
│   └── results_rag.json        ← dev set results with RAG
├── /lora                       ← stretch goal only
│   ├── train.py
│   ├── adapter/
│   └── results_lora.json
└── comparison.md               ← before vs after summary
```

---

---

# 🔍 SUB-PHASE 3.1 — ERROR TAXONOMY

### 🎯 Goal
Systematically categorize EVERY wrong answer to find patterns, not just isolated mistakes.

---

### Step 1: Load Your Baseline Results

```python
"""
analyze_errors.py — Build the error taxonomy from baseline results.
"""

import json
from collections import defaultdict
from pathlib import Path

def load_baseline_results(model_name: str = "8b", split: str = "dev"):
    """Load the parsed knowledge results from Phase 2."""
    path = Path(f"eval/results/parsed/knowledge_{model_name}_{split}.json")
    with open(path) as f:
        return json.load(f)

def get_wrong_answers(results: list) -> list:
    """Filter to only incorrect responses."""
    return [r for r in results if not r["is_correct"]]
```

---

### Step 2: The Error Classification Framework

For every wrong answer, classify it into exactly ONE of these error types:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ERROR TYPE TAXONOMY                          │
├──────────┬──────────────────────────────────────────────────────┤
│ Code     │ Description                                          │
├──────────┼──────────────────────────────────────────────────────┤
│ DE-CONF  │ German/EU Confusion                                  │
│          │ Model applies German or EU law/norms to Switzerland  │
│          │ Example: Says "Bundeskanzler leads the government"   │
│          │ (that's Germany, not Switzerland)                    │
├──────────┼──────────────────────────────────────────────────────┤
│ CANTON   │ Cantonal Confusion                                   │
│          │ Model treats cantonal rules as federal or vice versa │
│          │ Example: Gives one school starting age for all of CH │
├──────────┼──────────────────────────────────────────────────────┤
│ HALLUC   │ Hallucination                                        │
│          │ Model invents facts that don't exist                 │
│          │ Example: Claims Switzerland has 28 cantons           │
├──────────┼──────────────────────────────────────────────────────┤
│ OUTDATE  │ Outdated Information                                 │
│          │ Model uses old laws or numbers                       │
│          │ Example: Says women's suffrage was 1981 (it's 1971)  │
├──────────┼──────────────────────────────────────────────────────┤
│ NUMERIC  │ Numeric Confusion                                    │
│          │ Model gets the right concept but wrong number        │
│          │ Example: Says 50,000 signatures for initiative       │
│          │ (that's for referendum; initiative needs 100,000)    │
├──────────┼──────────────────────────────────────────────────────┤
│ LANG     │ Language/Region Bias                                 │
│          │ Model defaults to German-Swiss perspective,          │
│          │ ignores French/Italian/Romansh Switzerland           │
├──────────┼──────────────────────────────────────────────────────┤
│ GENERIC  │ Too Generic                                          │
│          │ Answer is technically true but too vague to          │
│          │ distinguish from any country                         │
├──────────┼──────────────────────────────────────────────────────┤
│ PARSE    │ Parsing Failure                                      │
│          │ Model gave the right info but in a format            │
│          │ your parser couldn't extract                         │
├──────────┼──────────────────────────────────────────────────────┤
│ OTHER    │ Unclassifiable                                       │
│          │ Doesn't fit above categories                         │
└──────────┴──────────────────────────────────────────────────────┘
```

---

### Step 3: Build the Error Table

```python
def classify_error(question: dict, result: dict) -> dict:
    """
    Classify a single wrong answer.
    This is SEMI-AUTOMATED — the LLM suggests, you confirm.
    """
    prompt = f"""Classify this wrong answer into ONE error type.

ERROR TYPES:
- DE-CONF: German/EU confusion (applies non-Swiss norms)
- CANTON: Cantonal confusion (mixes federal and cantonal)
- HALLUC: Hallucination (invents facts)
- OUTDATE: Outdated information
- NUMERIC: Wrong number, right concept
- LANG: Language/region bias
- GENERIC: Too generic
- PARSE: Parsing failure
- OTHER: Unclassifiable

QUESTION: {question['question']}
CORRECT ANSWER: {question['correct_answer']} ({question['options'][question['correct_answer']]})
MODEL PREDICTED: {result['predicted']} ({question['options'].get(result['predicted'], 'N/A')})
MODEL RAW RESPONSE: {result['raw_response']}

Respond with ONLY the error code and a one-line explanation.
Format: CODE | explanation"""

    # You can run this through the 70B model for auto-classification
    # But VERIFY every classification manually — this is your analysis
    return prompt  # Use this prompt with the model, then review


def build_error_taxonomy(results: list, questions: list) -> dict:
    """Build the full error taxonomy table."""
    q_map = {q["id"]: q for q in questions}
    wrong = get_wrong_answers(results)

    taxonomy = defaultdict(lambda: {
        "count": 0,
        "examples": [],
        "categories": defaultdict(int),
    })

    for r in wrong:
        # You fill in the error_code after manual review
        error_code = r.get("error_code", "UNCLASSIFIED")
        taxonomy[error_code]["count"] += 1
        taxonomy[error_code]["categories"][r["category"]] += 1

        if len(taxonomy[error_code]["examples"]) < 3:
            q = q_map.get(r["question_id"], {})
            taxonomy[error_code]["examples"].append({
                "question": q.get("question", ""),
                "correct": q.get("correct_answer", ""),
                "predicted": r["predicted"],
                "raw": r["raw_response"][:150],
            })

    return dict(taxonomy)
```

---

### Step 4: The Error Taxonomy Document (`error_taxonomy.md`)

Create this document with the following structure. I'll give you a template with realistic examples of what you'll likely find:

```markdown
# Error Taxonomy — Apertus 1.5 Baseline

## Summary Table

| Error Type | Count | % of Errors | Most Affected Categories |
|------------|-------|-------------|--------------------------|
| DE-CONF    | XX    | XX%         | Law, Health Insurance    |
| NUMERIC    | XX    | XX%         | Politics, History        |
| CANTON     | XX    | XX%         | Geography, Holidays      |
| HALLUC     | XX    | XX%         | History, Law             |
| OUTDATE    | XX    | XX%         | Health, Politics         |
| LANG       | XX    | XX%         | Geography, Holidays      |
| GENERIC    | XX    | XX%         | All                      |
| PARSE      | XX    | XX%         | All                      |

## Detailed Analysis

### DE-CONF: German/EU Confusion (XX errors)
**Pattern:** The model frequently applies German federal law or EU
regulations when asked about Swiss equivalents.

**Example 1:**
- Q: "What is the maximum weekly working hours in Switzerland?"
- Correct: B) 45 hours (for most employees)
- Model chose: A) 40 hours (German standard)
- Source: ch.ch/en/work/working-hours

**Example 2:**
- Q: "Which court is the highest judicial authority in Switzerland?"
- Correct: C) Federal Supreme Court (Bundesgericht) in Lausanne
- Model chose: A) Federal Constitutional Court (Bundesverfassungsgericht)
- Note: That's a German institution. Switzerland doesn't have one.

**Root cause hypothesis:** Training data contains far more German
legal content than Swiss legal content. The model defaults to the
more frequent pattern.

### NUMERIC: Numeric Confusion (XX errors)
**Pattern:** The model understands the concept but confuses specific
Swiss numbers with similar numbers from other contexts.

**Example 1:**
- Q: "How many signatures for a federal popular initiative?"
- Correct: B) 100,000
- Model chose: A) 50,000 (that's the referendum threshold)
- Source: ch.ch/en/political-system/popular-initiatives

### CANTON: Cantonal Confusion (XX errors)
...

[Continue for each error type]

## Key Insight
The dominant error pattern is [DE-CONF / NUMERIC / etc.], accounting
for XX% of all errors. This suggests the model's primary weakness
is [specific hypothesis], which could be addressed by [fix approach].
```

---

### 📋 TODO Checklist for 3.1

```
□ Load baseline results for 8B (and 70B if available)
□ Filter to wrong answers only
□ For each wrong answer, read the raw response
□ Classify into one of the 9 error types
□ (Optional) Use 70B to auto-classify, then verify manually
□ Count errors by type and by category
□ Write 2-3 concrete examples per error type
□ Identify the DOMINANT error pattern
□ Save error_taxonomy.md
□ Save the classified data back to results with error_code field
```

### ⏱️ Time Budget: ~1.5–2 hours
### ✅ Done When: You have a clear error_taxonomy.md with counts, examples, and a dominant pattern identified

---

---

# 🎯 SUB-PHASE 3.2 — WEAKEST AREA SELECTION

### 🎯 Goal
Pick ONE target for improvement using a clear, defensible decision framework.

---

### Step 1: The Selection Matrix

Score each potential target on two dimensions:

```
                    FIXABILITY
                Low         High
           ┌───────────┬───────────┐
    High   │  AVOID    │  ★ PICK   │
  IMPACT   │ (Too hard │ (Best     │
  (low     │  for time │  target)  │
  score)   │  budget)  │           │
           ├───────────┼───────────┤
    Low    │  IGNORE   │  BACKUP   │
  IMPACT   │ (Not worth│ (Easy win │
  (high    │  the time)│  but small│
  score)   │           │  impact)  │
           └───────────┴───────────┘
```

### Step 2: Score Each Candidate

```python
def score_improvement_targets(error_taxonomy: dict,
                               baseline_scores: dict) -> list:
    """
    Score potential improvement targets.
    Higher impact_score = more room for improvement.
    Higher fixability_score = easier to fix in time.
    """
    targets = []

    for category, score in baseline_scores["by_category"].items():
        # Impact: how far below 100% is this category?
        impact = 100 - score  # Higher = more room to improve

        # Error count in this category
        error_count = sum(
            t["categories"].get(category, 0)
            for t in error_taxonomy.values()
        )

        # Fixability heuristic:
        # - DE-CONF errors → HIGH fixability (RAG with Swiss sources fixes this)
        # - NUMERIC errors → MEDIUM (RAG helps but model might still confuse)
        # - HALLUC errors → LOW (hard to fix without fine-tuning)
        # - CANTON errors → HIGH (RAG with cantonal sources)
        # - OUTDATE errors → HIGH (RAG with current sources)
        # - PARSE errors → HIGH (fix the prompt)

        dominant_error = max(
            error_taxonomy.items(),
            key=lambda x: x[1]["categories"].get(category, 0),
            default=("NONE", {"categories": {}})
        )[0]

        fixability_map = {
            "DE-CONF": 9, "CANTON": 8, "OUTDATE": 9,
            "NUMERIC": 6, "LANG": 5, "GENERIC": 7,
            "HALLUC": 3, "PARSE": 10, "OTHER": 4,
        }
        fixability = fixability_map.get(dominant_error, 5)

        targets.append({
            "category": category,
            "baseline_score": score,
            "impact": impact,
            "error_count": error_count,
            "dominant_error": dominant_error,
            "fixability": fixability,
            "priority": impact * fixability,  # Combined score
        })

    # Sort by priority (highest first)
    targets.sort(key=lambda x: x["priority"], reverse=True)
    return targets
```

### Step 3: Decision Framework

```
ASK THESE QUESTIONS IN ORDER:

1. Which category has the LOWEST baseline score?
   → That's your highest-impact target

2. What is the DOMINANT error type in that category?
   → DE-CONF, CANTON, OUTDATE → RAG will help a lot (Option B)
   → PARSE → Fix the prompt (Option A, 10 minutes)
   → HALLUC → Hard to fix, consider second-worst category instead
   → NUMERIC → RAG might help, but gains could be modest

3. Do you have GOOD source material for this category?
   → If yes → proceed
   → If no → can you find 5-10 official pages in 30 minutes?
   → If still no → pick the next category

4. Can you implement and test the fix in <4 hours?
   → If yes → proceed
   → If no → simplify the fix or pick an easier target

5. Will the improvement be VISIBLE in the numbers?
   → A category at 30% going to 50% is dramatic
   → A category at 75% going to 80% is less impressive
   → Pick the dramatic one if possible
```

### Step 4: The Decision Document (`weakest_area_analysis.md`)

```markdown
# Weakest Area Analysis

## Baseline Scores (Dev Set)
| Category     | 8B    | 70B   | Errors | Dominant Error |
|-------------|-------|-------|--------|----------------|
| Politics    | XX.X% | XX.X% | XX     | NUMERIC        |
| Law         | XX.X% | XX.X% | XX     | DE-CONF        |
| Health      | XX.X% | XX.X% | XX     | DE-CONF        |
| Geography   | XX.X% | XX.X% | XX     | CANTON         |
| Holidays    | XX.X% | XX.X% | XX     | HALLUC         |
| History     | XX.X% | XX.X% | XX     | OUTDATE        |

## Selected Target: [CATEGORY NAME]

**Why this category:**
- Lowest baseline score: XX.X% (8B) / XX.X% (70B)
- XX errors out of 14 dev questions
- Dominant error type: [TYPE] — highly fixable with [APPROACH]
- Strong source material available: [list 3-5 URLs]

**Why not other categories:**
- [Category X]: Higher baseline, less room for improvement
- [Category Y]: Dominant error is HALLUC, hard to fix with RAG
- [Category Z]: Only 2 errors, improvement would be invisible

**Chosen fix approach:** [Option A / B / C]
**Expected improvement:** [conservative estimate, e.g., +10-20%]
**Time budget:** [X hours]
```

---

### 📋 TODO Checklist for 3.2

```
□ Run score_improvement_targets() on your baseline data
□ Fill in the selection matrix
□ Answer the 5 decision questions
□ Pick ONE target category
□ Pick ONE fix approach (A, B, or C)
□ Write weakest_area_analysis.md
□ Commit this analysis to your repo (judges love seeing the reasoning)
```

### ⏱️ Time Budget: ~30–45 minutes
### ✅ Done When: You have a clear, documented target and approach

---

---

# 🔧 SUB-PHASE 3.3 — IMPROVEMENT IMPLEMENTATION

## OPTION A: System Prompt Enhancement (Quick Win)

### 🎯 Goal
Write a Swiss-context system prompt that steers the model away from common errors.

### When To Use This
- You're short on time (<2 hours left)
- The dominant error is PARSE or GENERIC
- You want a baseline improvement before trying RAG
- You're doing RAG AND want a better base prompt

### Implementation

```python
# fix/system_prompt/swiss_context_v1.txt

SWISS_CONTEXT_PROMPT = """You are a Swiss knowledge expert assistant. 
When answering questions about Switzerland, follow these rules:

CRITICAL FACTS:
- Switzerland has 26 cantons (not states, not Länder)
- The federal government is in Bern (the "federal city," not officially "capital")
- The Federal Council has 7 members (not a single president/chancellor leading)
- Switzerland is NOT in the EU, NOT in the EEA, but IS in Schengen
- Four national languages: German (~62%), French (~23%), Italian (~8%), Romansh (~0.5%)
- Direct democracy: popular initiative needs 100,000 signatures, optional referendum needs 50,000
- The Federal Supreme Court is in Lausanne (not Bern)
- Mandatory health insurance is private but regulated (KVG/LAMal)
- Three-pillar pension: AHV (1st), BVG (2nd), private (3rd)
- Women's federal suffrage: 1971 (one of the last in Europe)
- UN membership: 2002
- Neutrality is a core foreign policy principle

BEHAVIORAL RULES:
1. NEVER apply German, Austrian, or EU law to Switzerland unless explicitly asked to compare
2. When a topic varies by canton, say so — do NOT give a single answer
3. Distinguish between federal and cantonal responsibilities
4. Use Swiss-specific terminology (e.g., "Federal Council" not "cabinet,"
   "National Council" not "Bundestag")
5. If you're unsure about a Swiss-specific fact, say so rather than guessing
6. When discussing languages, treat all four national languages equally

FORMAT RULES:
- For multiple-choice questions, answer with ONLY the letter (A, B, C, or D)
- Do not explain unless asked"""
```

### How To Test

```python
# In run_knowledge.py, add a variant:

def evaluate_knowledge_with_prompt(model_name, split, system_prompt):
    """Same as evaluate_knowledge but with a custom system prompt."""
    client = get_client(model_name)
    # ... same code, but pass system_prompt to client.generate()
    
# Run:
baseline = evaluate_knowledge("8b", "dev")  # Original prompt
improved = evaluate_knowledge_with_prompt(
    "8b", "dev", SWISS_CONTEXT_PROMPT
)
```

### Expected Impact
```
REALISTIC EXPECTATIONS:
- PARSE errors: 80-100% reduction (prompt directly fixes this)
- DE-CONF errors: 20-40% reduction (model still has German training bias)
- NUMERIC errors: 10-20% reduction (listing numbers helps but isn't enough)
- HALLUC errors: 5-10% reduction (prompt can't fix deep knowledge gaps)
- Overall: +5-15% accuracy improvement

This is a MODEST but REAL improvement. Good as a first step.
```

---

## OPTION B: RAG Pipeline ⭐ (Recommended — Highest ROI)

### 🎯 Goal
Build a small retrieval-augmented generation system over your ~30 official Swiss source pages. When the model answers a question, first retrieve the most relevant source text and inject it into the prompt.

### Why This Works Best
```
THE CORE INSIGHT:

Apertus was trained on 1,811 languages across the entire internet.
Swiss-specific content is a TINY fraction of that. When you ask
about Swiss tenancy law, the model has seen 100x more German
tenancy law content. It defaults to the majority pattern.

RAG fixes this by FORCE-FEEDING the correct Swiss source at
inference time. You're not asking the model to remember — you're
giving it the answer sheet and asking it to read it.

This is why RAG will outperform both system prompts and LoRA
for this specific use case:
- System prompt: too small to contain all the facts
- LoRA: not enough training data (84 questions is tiny)
- RAG: gives the EXACT relevant source for each question
```

### Step 1: Prepare the Corpus

```python
# fix/rag/corpus/ — one text file per source page

"""
prepare_corpus.py — Convert your harvested sources into a RAG corpus.
"""

import os
import re
from pathlib import Path

def prepare_corpus(sources_dir: str = "data/sources/raw_pages",
                   output_dir: str = "fix/rag/corpus"):
    """
    Read all source text files and split into chunks.
    Each chunk is ~500-1000 characters with metadata.
    """
    os.makedirs(output_dir, exist_ok=True)
    chunks = []

    for filepath in Path(sources_dir).glob("*.txt"):
        with open(filepath, "r") as f:
            text = f.read()

        # Extract metadata from filename
        # e.g., "S001_ch_ch_political_system.txt"
        source_id = filepath.stem.split("_")[0]

        # Split into chunks by paragraphs, then merge small ones
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > 800:
                if current_chunk:
                    chunks.append({
                        "source_id": source_id,
                        "source_file": filepath.name,
                        "text": current_chunk.strip(),
                    })
                current_chunk = para
            else:
                current_chunk += "\n\n" + para

        if current_chunk.strip():
            chunks.append({
                "source_id": source_id,
                "source_file": filepath.name,
                "text": current_chunk.strip(),
            })

    print(f"Created {len(chunks)} chunks from {len(list(Path(sources_dir).glob('*.txt')))} sources")
    return chunks
```

### Step 2: Create Embeddings

```python
# fix/rag/embeddings.py

"""
embeddings.py — Embed the corpus chunks for retrieval.
Uses a lightweight embedding model. No GPU needed.
"""

import json
import numpy as np
from sentence_transformers import SentenceTransformer

class CorpusEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        all-MiniLM-L6-v2 is:
        - Small (80MB) — downloads in seconds
        - Fast — embeds 1000 chunks in <10 seconds on CPU
        - Good enough for our scale (30 pages, ~100 chunks)
        - Multilingual (handles German, French, Italian, English)
        """
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.chunks = []
        self.embeddings = None

    def embed_corpus(self, chunks: list):
        """Embed all corpus chunks."""
        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        self.embeddings = self.model.encode(texts, show_progress_bar=True)
        print(f"Embedded {len(chunks)} chunks. Shape: {self.embeddings.shape}")

    def save(self, path: str = "fix/rag/corpus_embeddings.npz"):
        """Save embeddings to disk."""
        np.savez(path,
                 embeddings=self.embeddings,
                 chunks=json.dumps(self.chunks))
        print(f"Saved embeddings to {path}")

    def load(self, path: str = "fix/rag/corpus_embeddings.npz"):
        """Load embeddings from disk."""
        data = np.load(path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.chunks = json.loads(str(data["chunks"]))
        print(f"Loaded {len(self.chunks)} chunks from {path}")


# Quick usage:
if __name__ == "__main__":
    from prepare_corpus import prepare_corpus
    chunks = prepare_corpus()
    embedder = CorpusEmbedder()
    embedder.embed_corpus(chunks)
    embedder.save()
```

### Step 3: Build the Retriever

```python
# fix/rag/retriever.py

"""
retriever.py — Retrieve the most relevant corpus chunks for a query.
"""

import numpy as np
from embeddings import CorpusEmbedder

class SwissRetriever:
    def __init__(self, embedder: CorpusEmbedder):
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 3) -> list:
        """
        Find the top_k most relevant chunks for a query.
        Returns list of dicts with 'text', 'source_id', 'score'.
        """
        # Embed the query
        query_embedding = self.embedder.model.encode([query])[0]

        # Cosine similarity
        similarities = np.dot(self.embedder.embeddings, query_embedding) / (
            np.linalg.norm(self.embedder.embeddings, axis=1) *
            np.linalg.norm(query_embedding)
        )

        # Get top_k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            chunk = self.embedder.chunks[idx]
            results.append({
                "text": chunk["text"],
                "source_id": chunk["source_id"],
                "source_file": chunk["source_file"],
                "similarity_score": float(similarities[idx]),
            })

        return results

    def format_context(self, results: list) -> str:
        """Format retrieved chunks into a context string for the prompt."""
        parts = []
        for i, r in enumerate(results, 1):
            parts.append(f"[Source {r['source_id']}] {r['text']}")
        return "\n\n".join(parts)
```

### Step 4: RAG Evaluation Runner

```python
# fix/rag/run_rag_eval.py

"""
run_rag_eval.py — Re-evaluate knowledge questions with RAG.
"""

import json
from pathlib import Path
from client import get_client
from prompts import KNOWLEDGE_RAG_USER, KNOWLEDGE_SYSTEM
from retriever import SwissRetriever
from embeddings import CorpusEmbedder
from run_knowledge import extract_answer

def evaluate_with_rag(model_name: str = "8b", split: str = "dev",
                      top_k: int = 3):
    """Run knowledge evaluation with RAG augmentation."""

    # Setup retriever
    embedder = CorpusEmbedder()
    embedder.load()
    retriever = SwissRetriever(embedder)

    client = get_client(model_name)

    # Load questions
    data_path = Path(f"data/knowledge/knowledge_{split}.json")
    with open(data_path) as f:
        questions = json.load(f)

    print(f"Running RAG evaluation on {len(questions)} questions "
          f"(top_k={top_k})")

    results = []

    for i, q in enumerate(questions):
        # Step 1: Retrieve relevant context
        retrieved = retriever.retrieve(q["question"], top_k=top_k)
        context = retriever.format_context(retrieved)

        # Step 2: Build RAG prompt
        prompt = KNOWLEDGE_RAG_USER.format(
            context=context,
            question=q["question"],
            option_a=q["options"]["A"],
            option_b=q["options"]["B"],
            option_c=q["options"]["C"],
            option_d=q["options"]["D"],
        )

        # Step 3: Generate with context
        response = client.generate(prompt, system_prompt=KNOWLEDGE_SYSTEM)
        client.save_response(response, q["id"], "knowledge_rag")

        # Step 4: Parse and score
        predicted = extract_answer(response.get("text", ""))
        correct = q["correct_answer"]
        is_correct = (predicted == correct) if predicted != "PARSE_ERROR" else False

        results.append({
            "question_id": q["id"],
            "category": q["category"],
            "predicted": predicted,
            "correct": correct,
            "is_correct": is_correct,
            "retrieved_sources": [r["source_id"] for r in retrieved],
            "top_similarity": retrieved[0]["similarity_score"] if retrieved else 0,
            "raw_response": response.get("text", "")[:200],
            "model": model_name,
            "method": "rag",
            "split": split,
        })

        if (i + 1) % 10 == 0:
            acc = sum(r["is_correct"] for r in results) / len(results) * 100
            print(f"  [{i+1}/{len(questions)}] RAG accuracy: {acc:.1f}%")

    # Save results
    out_path = Path(f"fix/rag/results_rag_{model_name}_{split}.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    acc = sum(r["is_correct"] for r in results) / len(results) * 100
    print(f"\n  RAG RESULTS — Apertus {model_name.upper()}")
    print(f"  Accuracy: {acc:.1f}% (vs baseline XX.X%)")
    print(f"  Delta: +XX.X percentage points")

    return results


if __name__ == "__main__":
    evaluate_with_rag("8b", "dev", top_k=3)
```

### Step 5: RAG Tuning Tips

```
IF RAG DOESN'T HELP ENOUGH, TRY THESE:

1. Increase top_k from 3 to 5
   → More context = more chance the right answer is included
   → But too much context can confuse the model

2. Add the question's category to the retrieval query
   → Instead of retrieving on "How many signatures for initiative?"
   → Retrieve on "Swiss politics direct democracy signatures initiative"
   → This helps the retriever find the right source

3. Prepend "Switzerland" to every query
   → The embedding model might not know "initiative" is Swiss-specific
   → "Switzerland federal popular initiative signatures" retrieves better

4. Filter by source category
   → If the question is about health, only retrieve from health sources
   → Simple but effective: tag chunks with category metadata

5. Use the correct answer's source as a retrieval target
   → For the dev set, you KNOW which source has the answer
   → Check if the retriever actually finds it
   → If not, the embedding model is the bottleneck, not the RAG approach
```

### Expected Impact
```
REALISTIC EXPECTATIONS FOR RAG:
- DE-CONF errors: 50-80% reduction (source text overrides German defaults)
- NUMERIC errors: 30-60% reduction (exact numbers in context)
- CANTON errors: 40-70% reduction (cantonal details in source)
- OUTDATE errors: 60-90% reduction (current source text)
- HALLUC errors: 20-40% reduction (context constrains generation)
- Overall: +10-25% accuracy improvement

This is the STRONGEST fix for this use case.
```

---

## OPTION C: LoRA Fine-Tuning (Stretch Goal)

### 🎯 Goal
Fine-tune the 8B model on your 84 dev questions using LoRA (Low-Rank Adaptation).

### ⚠️ Honest Assessment

```
SHOULD YOU DO THIS?

✅ YES if:
   - Baseline eval is DONE by Tuesday night
   - You have GPU access (at least 1x A100 or 2x A10)
   - You've already tried Option A and/or B
   - You have 4+ hours to spare
   - You're comfortable with Hugging Face transformers

❌ NO if:
   - It's already Wednesday afternoon
   - You're still debugging the eval pipeline
   - You only have CPU access
   - You've never fine-tuned a model before
   - Your RAG results are already strong (+15% or more)

THE TRUTH:
84 questions is a TINY training set. LoRA will likely overfit
to your specific question phrasing. The improvement on the
held-out test set may be smaller than on the dev set. RAG is
almost certainly a better use of your time.

If you do LoRA, treat it as a BONUS on top of RAG, not a
replacement.
```

### Implementation (If You Proceed)

```python
# fix/lora/train.py

"""
train.py — LoRA fine-tuning on Swiss knowledge dev set.
Requires: GPU with 24GB+ VRAM, ~2 hours training time.
"""

import json
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
)
from peft import LoraConfig, get_peft_model, TaskType

def prepare_training_data(dev_path: str = "data/knowledge/knowledge_dev.json"):
    """Convert MCQs to instruction-tuning format."""
    with open(dev_path) as f:
        questions = json.load(f)

    examples = []
    for q in questions:
        # Format as instruction → response
        instruction = (
            f"Answer this multiple-choice question about Switzerland.\n\n"
            f"Question: {q['question']}\n"
            f"A) {q['options']['A']}\n"
            f"B) {q['options']['B']}\n"
            f"C) {q['options']['C']}\n"
            f"D) {q['options']['D']}\n\n"
            f"Answer:"
        )
        response = q["correct_answer"]

        examples.append({
            "text": f"<|system|>You are a Swiss knowledge expert.<|user|>"
                    f"{instruction}<|assistant|>{response}"
        })

    return Dataset.from_list(examples)


def train_lora():
    model_name = "swiss-ai/Apertus-v1.5-8B"

    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    # LoRA config — conservative for small dataset
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,                    # Low rank — prevents overfitting on 84 examples
        lora_alpha=16,
        lora_dropout=0.1,       # Higher dropout for small dataset
        target_modules=["q_proj", "v_proj"],  # Minimal targets
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    # Expected: ~0.1-0.5% of total parameters

    # Prepare data
    dataset = prepare_training_data()

    # Training args — SHORT training for tiny dataset
    training_args = TrainingArguments(
        output_dir="fix/lora/adapter",
        num_train_epochs=3,         # Only 3 epochs — avoid overfitting
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=5,
        save_strategy="epoch",
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
    )

    print("Training...")
    trainer.train()

    # Save adapter
    model.save_pretrained("fix/lora/adapter/final")
    tokenizer.save_pretrained("fix/lora/adapter/final")
    print("✅ LoRA adapter saved to fix/lora/adapter/final")


if __name__ == "__main__":
    train_lora()
```

### Expected Impact
```
REALISTIC EXPECTATIONS FOR LORA (84 examples):
- On DEV set: +15-30% (but this is overfitted, don't trust it)
- On TEST set: +5-15% (real improvement, much smaller)
- Risk: May DEGRADE performance on categories not in training
- Time cost: 2-4 hours (setup + training + evaluation)
- Compute cost: 1x A100 for ~1-2 hours

VERDICT: Only worth it if RAG already works and you want to
stack improvements. Do NOT do this instead of RAG.
```

---

### 📋 TODO Checklist for 3.3

```
OPTION A (System Prompt):
□ Write swiss_context_v1.txt with key facts and rules
□ Modify run_knowledge.py to accept custom system prompt
□ Run eval on dev set with new prompt
□ Compare to baseline
□ Save results to fix/system_prompt/results_v1.json
□ If improvement is good, keep it. If not, iterate once.

OPTION B (RAG) ⭐:
□ Run prepare_corpus.py on your harvested sources
□ Install sentence-transformers: pip install sentence-transformers
□ Run embeddings.py to create corpus embeddings
□ Test retriever on 5 questions — does it find the right source?
□ Run run_rag_eval.py on dev set
□ Compare RAG accuracy to baseline accuracy
□ Try top_k=3 and top_k=5, keep the better one
□ Save results to fix/rag/results_rag.json
□ Document the improvement delta

OPTION C (LoRA — Stretch):
□ Confirm GPU availability
□ Install peft: pip install peft bitsandbytes
□ Run train.py
□ Load adapter and re-evaluate on dev set
□ Compare to baseline AND to RAG
□ Save adapter and results
□ Decide: stack with RAG or use alone?
```

### ⏱️ Time Budget
- Option A: ~1–1.5 hours
- Option B: ~3–4 hours ⭐
- Option C: ~3–4 hours (stretch)
- **Recommended: A + B = ~4–5 hours**

### ✅ Done When: You have at least one improvement with measured before/after numbers on the dev set

---

---

# ✅ SUB-PHASE 3.4 — DEV SET VALIDATION

### 🎯 Goal
Confirm your improvement actually works and doesn't break anything.

---

### Step 1: The Validation Protocol

```python
"""
validate_improvement.py — Rigorous before/after comparison.
"""

import json
from scoring import calculate_knowledge_scores, compare_before_after

def validate_improvement(model_name: str = "8b", split: str = "dev"):
    """
    Compare baseline vs improved results on the SAME dev set.
    """
    # Load baseline
    with open(f"eval/results/parsed/knowledge_{model_name}_{split}.json") as f:
        baseline = json.load(f)

    # Load improved (RAG example)
    with open(f"fix/rag/results_rag_{model_name}_{split}.json") as f:
        improved = json.load(f)

    # Compare
    comparison = compare_before_after(baseline, improved)

    # Detailed breakdown
    print(f"\n{'='*60}")
    print(f"  IMPROVEMENT VALIDATION — {model_name.upper()} ({split})")
    print(f"{'='*60}")
    print(f"  Baseline Accuracy: {comparison['before']:.1f}%")
    print(f"  Improved Accuracy: {comparison['after']:.1f}%")
    print(f"  Delta:            {comparison['delta']:+.1f} pp")
    print(f"\n  By Category:")
    print(f"  {'Category':20s} {'Before':>8s} {'After':>8s} {'Delta':>8s}")
    print(f"  {'─'*48}")

    all_cats = set(comparison['by_category_before'].keys())
    for cat in sorted(all_cats):
        before = comparison['by_category_before'].get(cat, 0)
        after = comparison['by_category_after'].get(cat, 0)
        delta = after - before
        flag = " ⚠️" if delta < -5 else " ✅" if delta > 5 else ""
        print(f"  {cat:20s} {before:7.1f}% {after:7.1f}% {delta:+7.1f}%{flag}")

    print(f"{'='*60}")

    # Check for regressions
    regressions = [
        cat for cat in all_cats
        if comparison['by_category_after'].get(cat, 0) <
           comparison['by_category_before'].get(cat, 0) - 5
    ]

    if regressions:
        print(f"\n  ⚠️ REGRESSIONS DETECTED in: {', '.join(regressions)}")
        print(f"  The improvement helped overall but hurt these categories.")
        print(f"  Consider: applying RAG only to the target category,")
        print(f"  or adjusting the retrieval to be more selective.")
    else:
        print(f"\n  ✅ No regressions detected. Improvement is safe.")

    return comparison
```

---

### Step 2: Regression Check

```
CRITICAL VALIDATION QUESTIONS:

1. Did overall accuracy go UP?
   → Yes → proceed
   → No → your fix is broken, debug it

2. Did the TARGET category improve significantly?
   → Yes → great, this is your headline result
   → No → the fix didn't work for the intended target

3. Did any OTHER category get WORSE by >5%?
   → No → safe to proceed
   → Yes → REGRESSION. Options:
     a) Apply RAG only to the target category (conditional retrieval)
     b) Reduce top_k (less context = less confusion)
     c) Accept the trade-off and document it honestly

4. Is the improvement CONSISTENT across question types?
   → Check if the fix only helps easy questions but hurts hard ones
   → Or if it helps one sub-topic but not others

5. Does the improvement work on BOTH 8B and 70B?
   → If only 8B: the 70B might already know the answers
   → If only 70B: the 8B might not be able to use the context well
   → If both: strongest result
```

---

### Step 3: The Comparison Document (`comparison.md`)

```markdown
# Improvement Comparison

## Method: [RAG over 30 official Swiss sources, top_k=3]

## Overall Results (Dev Set)

| Model | Baseline | Improved | Delta |
|-------|----------|----------|-------|
| 8B    | XX.X%    | XX.X%    | +XX.X pp |
| 70B   | XX.X%    | XX.X%    | +XX.X pp |

## Category Breakdown (8B)

| Category     | Baseline | Improved | Delta |
|-------------|----------|----------|-------|
| Politics    | XX.X%    | XX.X%    | +XX.X |
| Law         | XX.X%    | XX.X%    | +XX.X |
| Health      | XX.X%    | XX.X%    | +XX.X |
| Geography   | XX.X%    | XX.X%    | +XX.X |
| Holidays    | XX.X%    | XX.X%    | +XX.X |
| History     | XX.X%    | XX.X%    | +XX.X |

## Key Findings
1. The largest improvement was in [category] (+XX pp), where the
   dominant error was [type]. RAG provided the correct Swiss-specific
   information that the model was previously confusing with [German/EU] norms.

2. [Category] showed no improvement because [reason — e.g., the model
   already knew these facts, or the errors were hallucinations that
   context couldn't fix].

3. No significant regressions were observed. The smallest delta was
   [category] at [XX pp], which is within noise.

## Limitations
- Improvement measured on dev set only (84 questions)
- Test set (36 questions) evaluation pending
- RAG retrieval quality depends on embedding model (MiniLM-L6)
- Context injection may not help with deeply ingrained misconceptions
```

---

### Step 4: One Iteration (If Needed)

```
IF RESULTS ARE DISAPPOINTING:

Iteration 1 (30 min):
→ Add "Switzerland" prefix to all retrieval queries
→ Increase top_k to 5
→ Re-run eval

Iteration 2 (30 min):
→ Add category filtering to retrieval
→ Strengthen the system prompt alongside RAG
→ Re-run eval

DO NOT iterate more than twice. You're running out of time.
A modest honest improvement beats an over-optimized fragile one.
```

---

### 📋 TODO Checklist for 3.4

```
□ Run validate_improvement() with baseline vs improved results
□ Check for regressions across all 6 categories
□ If regressions exist, try conditional RAG (only for target category)
□ Run the same improvement on 70B (if time allows)
□ Write comparison.md with all numbers
□ Save all result files
□ Prepare the "before/after" narrative for the README and video
□ DO NOT TOUCH knowledge_test.json — that's for Phase 4 only
```

### ⏱️ Time Budget: ~1–1.5 hours
### ✅ Done When: You have a validated improvement with documented before/after numbers and no major regressions

---

---

# 📊 PHASE 3 — SUMMARY DASHBOARD

| Sub-Phase | Output | Time | Priority | Status | What it actually established |
|---|---|---|---|---|---|
| **3.1** Error Taxonomy | Categorized failure table with examples | 1.5–2h | 🔴 CRITICAL | ✅ built · 67 checks | Layered classification: mechanical → diagnostic → human. `UNCLASSIFIED` is not an error type and is never reported as dominant. |
| **3.2** Weakest Area | Documented target selection | 30–45min | 🔴 CRITICAL | ✅ built · 96 checks | **Refuses to name a target.** Gates G1/G2/G3 fire on a mock baseline, an unresolved taxonomy and a single model. Power table: a per-category claim needs 6/14 flips; the whole set needs 6 net. |
| **3.3a** System Prompt | Improved prompt + results | 1–1.5h | 🟡 HIGH | ✅ built · gated · **unvalidated** | The prompt proposed in §3.3 Option A answers **25/84 dev items (30%)**. Shipped prompt is behavioural-only at **0/84**, enforced by a gate that raises. |
| **3.3b** RAG Pipeline ⭐ | Working RAG + results | 3–4h | 🔴 CRITICAL | ✅ built · **real retrieval numbers** · no effect claim | **Source recall 83.3% @1 / 90.5% @3 / 94.0% @5**, model-free ground truth, zero dependencies. The dense retriever is not the bottleneck. |
| **3.3c** LoRA (Stretch) | Fine-tuned adapter + results | 3–4h | 🟢 OPTIONAL | ⛔ not attempted | Infeasible on an 8 GB card. Recorded rather than half-done. Reopens if B3 yields a larger GPU. |
| **3.4** Dev Validation | Before/after comparison, no regressions | 1–1.5h | 🔴 CRITICAL | ✅ built · 88 checks · **verdict: null** | The >5 pp regression rule is a false-positive machine (1 item = 7.1 pp at n=14), and net movement is not significance either (10↑/4↓ has net +6, p=0.18). |

**Total Phase 3 time: ~6–8 hours on Wed 14 Oct** — all six sub-phases are built and
covered by **11,031 automated checks across nine suites**, all passing.

### ⚠️ Status means "built and tested", not "measured"

No model has run. `eval/.env` still has `APERTUS_8B_BACKEND=mock`, so **every
accuracy figure in Phase 3 is a pipeline self-test**. What this phase genuinely
produced is:

1. **One real finding**: retrieval finds the answer's own source 94% of the time
   at k=5 without any third-party dependency.
2. **One blocked finding**: the plan's Option A prompt is contaminated at 30% of
   the dev set, so the plan's headline improvement would have been the answer key.
3. **Two null results**: no detectable effect on 3.4's paired comparison, and no
   weakest area nameable while G1/G2/G3 hold.

`baseline_report.py` and `validate_improvement.py` both **refuse to certify**
these runs and exit non-zero. That refusal is the correct state, not a bug to
work around. Unblocking **B2** is what turns this phase from built into measured.

### Corrections made to this plan while implementing it

| Plan says | Reality | Where |
|---|---|---|
| System prompt lists Swiss "CRITICAL FACTS" | Answers 25/84 dev items — the answer key | §3.3a, `fix/prompts_check.py` |
| Embed with `all-MiniLM-L6-v2`, "multilingual" | That model is **English-only**; 48% of the corpus is Alemannic | §3.3b, `fix/rag/embeddings.py` |
| Split `raw_pages` into ~800-char paragraphs | Those files mix headers and fact-candidate scaffolding into the evidence | §3.3b, `fix/rag/prepare_corpus.py` |
| Flag a category worse by >5 pp | One item = 7.1 pp at n=14, so it flags any single flip | §3.4, `fix/validate_improvement.py` |
| Compare a baseline file to a RAG file | Two runs can differ for reasons the subtraction cannot see | §3.4, paired-first loading |
| "Install sentence-transformers" | BM25 already reaches 94% recall; not worth it before a real baseline | §3.3b, `fix/rag/RESULTS.md` |

---

## ⚡ Re-running Phase 3 by hand

The tools exist now, so none of these need pasting results anywhere:

```bash
python eval/run_knowledge.py --model 8b --split dev      # baseline
python fix/analyze_errors.py --model 8b --diagnose      # 3.1
python fix/select_target.py                              # 3.2 (refuses while gated)
python fix/prompts_check.py fix/system_prompt/swiss_context_v1.txt --gate   # 3.3a
python fix/rag/prepare_corpus.py --stats                 # 3.3b
python fix/rag/retriever.py --backend bm25               # 3.3b, model-free
python fix/rag/run_rag_eval.py --model 8b --split dev --topk 3   # 3.3b, paired
python fix/validate_improvement.py --model 8b --split dev --write-comparison  # 3.4
```

Verification: `python fix/test_error_taxonomy.py`, `fix/test_select_target.py`,
`fix/test_improvement.py`, `fix/test_validation.py`.

**Each tool refuses to over-claim by design.** If a run refuses, read the refusal
before working around it — the refusals are load-bearing:

| Tool | Refuses when |
|---|---|
| `baseline_report.py` | `is_mock` is true |
| `select_target.py` | any gate G1/G2/G3 fires |
| `prompts_check.py` | a prompt answers >5% of the split |
| `run_rag_eval.py` | the system prompt is contaminated |
| `validate_improvement.py` | mock backend, or the runs are not comparable |
| `analyze_errors.py` | `UNCLASSIFIED` dominates — it does not guess a dominant error |

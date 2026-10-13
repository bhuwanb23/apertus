> ## ⚠️ IMPLEMENTATION STATUS — 4.1 built, NOT run
>
> `eval/run_test_final.py` and `eval/seal.py` are built and covered by **99
> checks** (`python fix/test_phase4.py`). **The sealed test set has not been run.**
> `eval/.env` still has `APERTUS_8B_BACKEND=mock`, and the runner refuses on that
> ground by design.
>
> Read `fix/PHASE4_1.md` before running anything. It records four corrections to
> this plan — the most important being that **the runner below would break
> Golden Rule 3 by construction**: it reimplements parsing without `options=`,
> which silently disables exact-phrase matching and makes test numbers
> **incomparable to dev numbers**. The built runner calls the Phase 2 scorers
> instead.

---

# 🔬 PHASE 4 — FINAL EVALUATION & RESULTS: Complete Deep Dive

**This is the moment of truth. You open the sealed test set exactly once. The numbers you produce here go into your submission, your README, your video, and the jury's evaluation. No do-overs.**

---

## 🧠 Before You Touch the Test Set: Core Principles

```
TEST SET GOLDEN RULES:

1. ONE SHOT ONLY — you run the test set, you record the numbers,
   you NEVER re-run to "see if you can do better"

2. FOUR RUNS MINIMUM for knowledge:
   → 8B baseline (no fix)
   → 8B improved (with your fix)
   → 70B baseline (no fix)
   → 70B improved (with your fix)

3. IDENTICAL CONDITIONS to Phase 2 — same temperature (0),
   same prompt templates, same parsing code, same seed

4. NO CHANGES to the improvement after seeing test results —
   if the test numbers are worse than dev, you report that honestly

5. 36 QUESTIONS IS SMALL — acknowledge statistical uncertainty
   in your writeup. Judges from EPFL/ETH know statistics.
   Claiming "30% improvement!" on 36 questions without
   confidence intervals will hurt your credibility.

6. SAVE EVERYTHING — raw responses, parsed results, scores,
   charts, and the exact git commit hash of your code
```

---

## 📁 File Structure Additions

```
/eval/results
├── /test_run                    ← ALL test set results go here
│   ├── knowledge_8b_baseline.json
│   ├── knowledge_8b_improved.json
│   ├── knowledge_70b_baseline.json
│   ├── knowledge_70b_improved.json
│   ├── values_8b.json
│   ├── values_70b.json
│   ├── dialect_8b.json
│   └── dialect_70b.json
├── /final_scores
│   ├── test_scores.json         ← all computed scores
│   ├── statistical_report.md    ← deltas, confidence, significance
│   └── comparison_table.md      ← the master results table
├── /charts
│   ├── fig1_overall_accuracy.png
│   ├── fig2_category_heatmap.png
│   ├── fig3_before_after.png
│   ├── fig4_values_distribution.png
│   └── fig5_model_comparison.png  ← bonus if time
└── /narrative
    └── findings.md              ← the story for README and video
```

---

---

# 🎯 SUB-PHASE 4.1 — HELD-OUT TEST RUN

### 🎯 Goal
Run the sealed test set through both models, both before and after your improvement, under identical conditions to Phase 2.

---

### Step 1: Pre-Flight Checklist (DO THIS BEFORE RUNNING)

```
┌─────────────────────────────────────────────────────────────┐
│  PRE-FLIGHT CHECKLIST — Do NOT proceed until all are ✅     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  □ knowledge_test.json exists and has exactly 36 questions  │
│  □ You have NOT opened or inspected knowledge_test.json     │
│    since the Phase 1A.4 split                               │
│  □ Your improvement (RAG/system prompt) is finalized and    │
│    saved — no more changes after this point                 │
│  □ Phase 2 eval code runs without errors                    │
│  □ Both 8B and 70B API endpoints are responsive             │
│  □ Temperature is confirmed at 0.0 in config.py             │
│  □ You have enough time for 4+ full runs (~2-3 hours)       │
│  □ You have disk space for raw responses                    │
│  □ You've committed all code to git (record the hash)       │
│                                                             │
│  If any of these fail → FIX IT NOW, not during the run.     │
└─────────────────────────────────────────────────────────────┘
```

---

### Step 2: The Test Run Script

```python
"""
run_test_final.py — THE definitive test set evaluation.
Run this ONCE. Save everything. Do not re-run.

Usage:
    python eval/run_test_final.py
"""

import json
import time
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from config import config
from client import get_client
from prompts import (KNOWLEDGE_SYSTEM, KNOWLEDGE_USER, KNOWLEDGE_RAG_USER,
                     VALUES_SYSTEM, VALUES_USER,
                     DIALECT_TRANSLATE_SYSTEM, DIALECT_TRANSLATE_USER)
from run_knowledge import extract_answer
from judge import judge_response

def get_git_hash():
    """Record the exact code version for reproducibility."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"]
        ).decode().strip()
    except Exception:
        return "unknown"

def run_knowledge_test(model_name: str, method: str = "baseline"):
    """
    Run knowledge test set.
    method: "baseline" (original prompt) or "improved" (RAG/system prompt)
    """
    client = get_client(model_name)

    # Load the SEALED test set
    test_path = Path("data/knowledge/knowledge_test.json")
    with open(test_path) as f:
        questions = json.load(f)

    print(f"\n{'='*60}")
    print(f"  TEST RUN: Knowledge | {model_name.upper()} | {method}")
    print(f"  Questions: {len(questions)}")
    print(f"  Git: {get_git_hash()}")
    print(f"  Time: {datetime.now().isoformat()}")
    print(f"{'='*60}")

    # Setup RAG if improved method
    retriever = None
    if method == "improved":
        from fix.rag.embeddings import CorpusEmbedder
        from fix.rag.retriever import SwissRetriever
        embedder = CorpusEmbedder()
        embedder.load()
        retriever = SwissRetriever(embedder)
        print(f"  RAG: loaded {len(embedder.chunks)} corpus chunks")

    results = []
    for i, q in enumerate(questions):
        # Build prompt based on method
        if method == "improved" and retriever:
            retrieved = retriever.retrieve(q["question"], top_k=3)
            context = retriever.format_context(retrieved)
            prompt = KNOWLEDGE_RAG_USER.format(
                context=context,
                question=q["question"],
                option_a=q["options"]["A"],
                option_b=q["options"]["B"],
                option_c=q["options"]["C"],
                option_d=q["options"]["D"],
            )
        else:
            prompt = KNOWLEDGE_USER.format(
                question=q["question"],
                option_a=q["options"]["A"],
                option_b=q["options"]["B"],
                option_c=q["options"]["C"],
                option_d=q["options"]["D"],
            )

        # Generate
        response = client.generate(prompt, system_prompt=KNOWLEDGE_SYSTEM)

        # Save raw response immediately (in case of crash)
        out_dir = Path("eval/results/test_run")
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_path = out_dir / f"knowledge_{model_name}_{method}_{q['id']}.json"
        with open(raw_path, "w") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)

        # Parse
        predicted = extract_answer(response.get("text", ""))
        correct = q["correct_answer"]
        is_correct = (predicted == correct) if predicted != "PARSE_ERROR" else False

        results.append({
            "question_id": q["id"],
            "category": q["category"],
            "predicted": predicted,
            "correct": correct,
            "is_correct": is_correct,
            "method": method,
            "model": model_name,
            "raw_response": response.get("text", "")[:300],
        })

        # Progress
        if (i + 1) % 6 == 0:  # Every category's worth
            acc = sum(r["is_correct"] for r in results) / len(results) * 100
            print(f"  [{i+1:2d}/36] Accuracy so far: {acc:.1f}%")

        time.sleep(0.5)

    # Save complete results
    out_path = out_dir / f"knowledge_{model_name}_{method}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    acc = sum(r["is_correct"] for r in results) / len(results) * 100
    print(f"\n  ✅ FINAL: {model_name.upper()} {method} = {acc:.1f}% "
          f"({sum(r['is_correct'] for r in results)}/36)")

    return results


def run_values_test(model_name: str):
    """Run values evaluation on test scenarios."""
    client = get_client(model_name)

    data_path = Path("data/values/values_scenarios.json")
    with open(data_path) as f:
        scenarios = json.load(f)

    # For values, there's no dev/test split — all 30 are evaluated
    # The "improvement" is the same system prompt or RAG context
    print(f"\n  VALUES TEST: {model_name.upper()} ({len(scenarios)} scenarios)")

    results = []
    for scenario in scenarios:
        prompt = VALUES_USER.format(scenario=scenario["prompt"])
        response = client.generate(prompt, system_prompt=VALUES_SYSTEM)

        judgment = judge_response(scenario, response.get("text", ""),
                                  judge_model="70b")

        results.append({
            "scenario_id": scenario["id"],
            "category": scenario.get("category", ""),
            "score": judgment["score"],
            "model": model_name,
        })
        time.sleep(1)

    out_path = Path("eval/results/test_run") / f"values_{model_name}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    valid = [r["score"] for r in results if r["score"] >= 0]
    avg = sum(valid) / len(valid) if valid else 0
    print(f"  ✅ VALUES: {model_name.upper()} avg = {avg:.2f}/2.0")
    return results


def run_dialect_test(model_name: str):
    """Run dialect evaluation."""
    data_path = Path("data/dialect/dialect_items.json")
    if not data_path.exists():
        print(f"  ⚠️ No dialect items. Skipping for {model_name}.")
        return []

    with open(data_path) as f:
        items = json.load(f)

    client = get_client(model_name)
    results = []

    for item in items:
        if item.get("task_type") == "translation":
            prompt = DIALECT_TRANSLATE_USER.format(
                swiss_german_text=item["swiss_german_text"]
            )
            system = DIALECT_TRANSLATE_SYSTEM
        else:
            prompt = item["swiss_german_text"]
            system = "You understand Swiss German. Answer helpfully."

        response = client.generate(prompt, system_prompt=system)
        results.append({
            "item_id": item["id"],
            "model_response": response.get("text", ""),
            "model": model_name,
        })
        time.sleep(0.5)

    out_path = Path("eval/results/test_run") / f"dialect_{model_name}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"  ✅ DIALECT: {model_name.upper()} ({len(results)} items saved)")
    return results


def main():
    """
    THE MAIN EVENT. Run all test evaluations.
    This function should be called EXACTLY ONCE.
    """
    start_time = datetime.now()
    git_hash = get_git_hash()

    print("\n" + "🔥" * 30)
    print("  FINAL TEST EVALUATION — Swiss Reality Check")
    print(f"  Started: {start_time.isoformat()}")
    print(f"  Git: {git_hash}")
    print("🔥" * 30)

    # ── KNOWLEDGE: 4 runs ──
    print("\n\n📊 KNOWLEDGE EVALUATION (4 runs)")
    k_8b_base = run_knowledge_test("8b", "baseline")
    k_8b_improved = run_knowledge_test("8b", "improved")
    k_70b_base = run_knowledge_test("70b", "baseline")
    k_70b_improved = run_knowledge_test("70b", "improved")

    # ── VALUES: 2 runs ──
    print("\n\n⚖️ VALUES EVALUATION (2 runs)")
    v_8b = run_values_test("8b")
    v_70b = run_values_test("70b")

    # ── DIALECT: 2 runs ──
    print("\n\n🗣️ DIALECT EVALUATION (2 runs)")
    d_8b = run_dialect_test("8b")
    d_70b = run_dialect_test("70b")

    # ── METADATA ──
    metadata = {
        "run_timestamp": start_time.isoformat(),
        "completion_timestamp": datetime.now().isoformat(),
        "duration_minutes": (datetime.now() - start_time).total_seconds() / 60,
        "git_hash": git_hash,
        "models": ["8b", "70b"],
        "methods": ["baseline", "improved"],
        "test_set_size": {
            "knowledge": 36,
            "values": 30,
            "dialect": len(d_8b),
        },
        "improvement_method": "RAG over 30 official Swiss sources, top_k=3",
    }

    meta_path = Path("eval/results/test_run/run_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n\n{'='*60}")
    print(f"  ✅ ALL TEST RUNS COMPLETE")
    print(f"  Duration: {metadata['duration_minutes']:.1f} minutes")
    print(f"  Results saved to: eval/results/test_run/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
```

---

### Step 3: Execution Order & Timing

```
RECOMMENDED EXECUTION ORDER:

Run 1: 8B Knowledge Baseline     (~15 min for 36 questions)
Run 2: 8B Knowledge Improved     (~15 min)
  → Quick sanity check: did 8B improve? If yes, proceed.
  → If NO improvement or regression, DON'T PANIC. Continue.
  → The test set is small — variance is expected.

Run 3: 70B Knowledge Baseline    (~20 min, 70B may be slower)
Run 4: 70B Knowledge Improved    (~20 min)

Run 5: 8B Values                 (~15 min, 30 scenarios)
Run 6: 70B Values                (~20 min)

Run 7: 8B Dialect                (~5 min, 20-30 items)
Run 8: 70B Dialect               (~5 min)

TOTAL ESTIMATED TIME: ~2–2.5 hours
```

---

### Step 4: Immediate Sanity Check (After Each Run)

```python
def quick_sanity_check(results: list, label: str):
    """Run immediately after each test run to catch disasters."""
    total = len(results)
    correct = sum(1 for r in results if r.get("is_correct", False))
    parse_errors = sum(1 for r in results if r.get("predicted") == "PARSE_ERROR")
    acc = correct / total * 100 if total > 0 else 0

    print(f"\n  SANITY CHECK — {label}")
    print(f"  Accuracy: {acc:.1f}% ({correct}/{total})")
    print(f"  Parse errors: {parse_errors}/{total}")

    # Red flags
    if acc == 0:
        print("  🚨 0% ACCURACY — Something is catastrophically wrong!")
        print("     Check: is the model returning answers at all?")
    elif acc == 100:
        print("  🚨 100% ACCURACY — Suspiciously perfect!")
        print("     Check: is the test set accidentally in the training data?")
    elif parse_errors > total * 0.2:
        print(f"  ⚠️ >20% parse errors — your parser may be broken")
    elif acc < 20:
        print(f"  ⚠️ Very low accuracy — check if model is answering randomly")
    else:
        print(f"  ✅ Looks reasonable")
```

---

### 📋 TODO Checklist for 4.1

```
PRE-RUN:
□ Pre-flight checklist all ✅
□ Git commit with message "Phase 4: final test run"
□ Record git hash
□ Confirm API endpoints are live
□ Test one prompt manually on each model

DURING RUN:
□ Run all 8 evaluations in order
□ Run quick_sanity_check() after each run
□ If a run crashes, restart ONLY that run (don't re-run completed ones)
□ Monitor disk space for raw responses
□ Don't touch any code during the run

POST-RUN:
□ Verify all 8 result files exist in eval/results/test_run/
□ Verify run_metadata.json is complete
□ Quick visual scan: do the numbers look plausible?
□ DO NOT re-run to "improve" the numbers
□ DO NOT modify the improvement and re-test
□ Git commit with message "Phase 4: test results recorded"
```

### ⏱️ Time Budget: ~2–2.5 hours
### ✅ Done When: All 8 result files saved, metadata recorded, sanity checks passed

---

---

# 📊 SUB-PHASE 4.2 — STATISTICAL COMPARISON

### 🎯 Goal
Calculate meaningful deltas and acknowledge uncertainty honestly. This is what separates a professional benchmark from a toy project.

---

### Step 1: The Statistical Report Generator

```python
"""
statistical_report.py — Compute all final statistics.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

def load_results(filename: str) -> list:
    path = Path("eval/results/test_run") / filename
    with open(path) as f:
        return json.load(f)

def accuracy_and_ci(results: list, confidence: float = 0.95) -> dict:
    """
    Calculate accuracy with Wilson score confidence interval.
    This is the correct CI for binomial proportions with small n.
    """
    n = len(results)
    if n == 0:
        return {"accuracy": 0, "ci_lower": 0, "ci_upper": 0, "n": 0}

    correct = sum(1 for r in results if r.get("is_correct", False))
    p = correct / n

    # Wilson score interval
    z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator

    return {
        "accuracy": p * 100,
        "correct": correct,
        "n": n,
        "ci_lower": max(0, (center - spread) * 100),
        "ci_upper": min(100, (center + spread) * 100),
        "ci_range": spread * 2 * 100,
    }

def category_breakdown(results: list) -> dict:
    """Accuracy by category."""
    cats = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        cat = r.get("category", "unknown")
        cats[cat]["total"] += 1
        if r.get("is_correct", False):
            cats[cat]["correct"] += 1

    breakdown = {}
    for cat, counts in cats.items():
        acc = counts["correct"] / counts["total"] * 100 if counts["total"] > 0 else 0
        breakdown[cat] = {
            "accuracy": acc,
            "correct": counts["correct"],
            "total": counts["total"],
        }
    return breakdown

def compute_all_statistics():
    """Compute the complete statistical report."""

    # Load all results
    k_8b_base = load_results("knowledge_8b_baseline.json")
    k_8b_imp = load_results("knowledge_8b_improved.json")
    k_70b_base = load_results("knowledge_70b_baseline.json")
    k_70b_imp = load_results("knowledge_70b_improved.json")

    stats = {
        "knowledge": {
            "8b": {
                "baseline": accuracy_and_ci(k_8b_base),
                "improved": accuracy_and_ci(k_8b_imp),
                "delta": accuracy_and_ci(k_8b_imp)["accuracy"] - accuracy_and_ci(k_8b_base)["accuracy"],
                "baseline_by_category": category_breakdown(k_8b_base),
                "improved_by_category": category_breakdown(k_8b_imp),
            },
            "70b": {
                "baseline": accuracy_and_ci(k_70b_base),
                "improved": accuracy_and_ci(k_70b_imp),
                "delta": accuracy_and_ci(k_70b_imp)["accuracy"] - accuracy_and_ci(k_70b_base)["accuracy"],
                "baseline_by_category": category_breakdown(k_70b_base),
                "improved_by_category": category_breakdown(k_70b_imp),
            },
        }
    }

    # Values statistics
    try:
        v_8b = load_results("values_8b.json")
        v_70b = load_results("values_70b.json")
        v8_scores = [r["score"] for r in v_8b if r.get("score", -1) >= 0]
        v70_scores = [r["score"] for r in v_70b if r.get("score", -1) >= 0]
        stats["values"] = {
            "8b": {"mean": sum(v8_scores)/len(v8_scores) if v8_scores else 0, "n": len(v8_scores)},
            "70b": {"mean": sum(v70_scores)/len(v70_scores) if v70_scores else 0, "n": len(v70_scores)},
        }
    except FileNotFoundError:
        stats["values"] = "not available"

    # Save
    out_path = Path("eval/results/final_scores/test_scores.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(stats, f, indent=2)

    return stats


def print_statistical_report(stats: dict):
    """Print a human-readable statistical report."""

    print("\n" + "=" * 70)
    print("  STATISTICAL REPORT — Swiss Reality Check (Test Set)")
    print("=" * 70)

    k = stats["knowledge"]

    print(f"\n  KNOWLEDGE ACCURACY (n=36 per model, 6 per category)")
    print(f"  {'─'*66}")
    print(f"  {'Model':8s} {'Baseline':>12s} {'Improved':>12s} {'Delta':>10s} {'95% CI':>16s}")
    print(f"  {'─'*66}")

    for model in ["8b", "70b"]:
        m = k[model]
        b = m["baseline"]
        i = m["improved"]
        d = m["delta"]
        ci = f"±{i['ci_range']/2:.1f}"
        print(f"  {model.upper():8s} {b['accuracy']:10.1f}%  {i['accuracy']:10.1f}%  "
              f"{d:+8.1f} pp  {ci:>10s}")

    print(f"\n  CATEGORY BREAKDOWN (8B)")
    print(f"  {'─'*55}")
    print(f"  {'Category':20s} {'Base':>8s} {'Impr':>8s} {'Delta':>8s}")
    print(f"  {'─'*55}")

    cats_8b = k["8b"]
    all_cats = set(cats_8b["baseline_by_category"].keys())
    for cat in sorted(all_cats):
        b_acc = cats_8b["baseline_by_category"].get(cat, {}).get("accuracy", 0)
        i_acc = cats_8b["improved_by_category"].get(cat, {}).get("accuracy", 0)
        d = i_acc - b_acc
        n = cats_8b["baseline_by_category"].get(cat, {}).get("total", 0)
        flag = " ⚠️" if d < -10 else " ✅" if d > 10 else ""
        print(f"  {cat:20s} {b_acc:6.1f}%  {i_acc:6.1f}%  {d:+6.1f}%  (n={n}){flag}")

    print(f"\n  ⚠️  STATISTICAL CAVEAT")
    print(f"  With n=36 overall and n=6 per category, confidence intervals")
    print(f"  are wide. A ±10pp delta at the category level may not be")
    print(f"  statistically significant. The overall delta (n=36) is more")
    print(f"  reliable than per-category deltas.")

    if stats.get("values") and isinstance(stats["values"], dict):
        print(f"\n  VALUES SCORES (0-2 scale)")
        print(f"  {'─'*40}")
        print(f"  8B:  {stats['values']['8b']['mean']:.2f} / 2.0")
        print(f"  70B: {stats['values']['70b']['mean']:.2f} / 2.0")

    print(f"\n{'='*70}")
```

---

### Step 2: Understanding the Statistical Caveat

```
┌─────────────────────────────────────────────────────────────────┐
│  THE HONEST STATISTICS TALK (judges will respect this)         │
│                                                                 │
│  Your test set has 36 questions. That's small. Here's what     │
│  that means in practice:                                        │
│                                                                 │
│  OVERALL (n=36):                                                │
│  - If baseline = 50% (18/36) and improved = 67% (24/36)       │
│  - That's a +17pp improvement                                   │
│  - 95% CI for the delta: roughly ±15pp                          │
│  - Verdict: SUGGESTIVE but not definitive                       │
│  - What to say: "The improvement shows a positive trend         │
│    (+17pp), though the small test set limits statistical        │
│    confidence. The dev set (n=84) showed a consistent           │
│    +XXpp improvement."                                          │
│                                                                 │
│  PER CATEGORY (n=6):                                            │
│  - If baseline = 33% (2/6) and improved = 67% (4/6)           │
│  - That's +34pp, which LOOKS dramatic                           │
│  - But it's literally 2 more correct answers out of 6           │
│  - 95% CI: roughly ±40pp (the CI is WIDER than the delta!)     │
│  - Verdict: NOT statistically significant at category level     │
│  - What to say: "Category-level results are indicative          │
│    but should be interpreted with caution due to small n."      │
│                                                                 │
│  WHY THIS HONESTY WINS:                                         │
│  The jury includes researchers from EPFL and ETH Zurich.        │
│  They KNOW statistics. If you claim "300% improvement in        │
│  health insurance knowledge!" based on 2 extra correct          │
│  answers out of 6, they will discount your entire project.      │
│                                                                 │
│  If you say "the improvement is directionally positive          │
│  (+17pp overall) but the test set is too small for              │
│  definitive per-category conclusions," they will think:         │
│  "This team understands evaluation methodology."                │
│                                                                 │
│  That trust is worth more than inflated numbers.                │
└─────────────────────────────────────────────────────────────────┘
```

---

### Step 3: The Statistical Report Document

```markdown
# Statistical Report — Swiss Reality Check

## Test Set Composition
- Knowledge: 36 MCQs (6 per category, stratified from 120 total)
- Values: 30 open-ended scenarios (scored 0-2)
- Dialect: [N] text items (scored 0-2)

## Knowledge Results

### Overall Accuracy

| Model | Baseline | Improved | Delta | 95% CI (improved) |
|-------|----------|----------|-------|--------------------|
| 8B    | XX.X% (XX/36) | XX.X% (XX/36) | +XX.X pp | [XX.X%, XX.X%] |
| 70B   | XX.X% (XX/36) | XX.X% (XX/36) | +XX.X pp | [XX.X%, XX.X%] |

### Per-Category Accuracy (8B)

| Category | Baseline | Improved | Delta | n |
|----------|----------|----------|-------|---|
| Politics | XX% (X/6) | XX% (X/6) | +XX pp | 6 |
| Law      | XX% (X/6) | XX% (X/6) | +XX pp | 6 |
| Health   | XX% (X/6) | XX% (X/6) | +XX pp | 6 |
| Geography| XX% (X/6) | XX% (X/6) | +XX pp | 6 |
| Holidays | XX% (X/6) | XX% (X/6) | +XX pp | 6 |
| History  | XX% (X/6) | XX% (X/6) | +XX pp | 6 |

### Per-Category Accuracy (70B)
[Same table]

## Values Results

| Model | Mean Score | Distribution (0/1/2) |
|-------|-----------|----------------------|
| 8B    | X.XX / 2.0 | X / X / X |
| 70B   | X.XX / 2.0 | X / X / X |

Judge model: [70B Apertus / GPT-4o]
Manual cross-check agreement: XX% (6/30 scenarios audited)

## Dialect Results
[Summary of translation and comprehension scores]

## Statistical Limitations
1. The test set (n=36) is small. Confidence intervals are wide.
2. Per-category results (n=6 each) should be treated as indicative,
   not definitive.
3. The improvement was designed on the dev set (n=84), which provides
   more reliable signal than the test set.
4. LLM-as-judge scoring for values has inherent subjectivity.
   Our 20% manual cross-check showed XX% agreement.
5. Dialect scoring uses automated word-overlap, which is an
   approximation of true translation quality.

## Reproducibility
- Git commit: [hash]
- Random seed: 42
- Temperature: 0.0
- Prompt templates: eval/results/prompts_used.json
- Full raw responses: eval/results/test_run/
```

---

### 📋 TODO Checklist for 4.2

```
□ Run compute_all_statistics()
□ Run print_statistical_report() and review the output
□ Calculate Wilson score CIs for all accuracy numbers
□ Write statistical_report.md with all tables
□ Write the statistical limitations section HONESTLY
□ Save test_scores.json to eval/results/final_scores/
□ Double-check: do the test set numbers roughly match dev set trends?
  → If yes → great, consistent improvement
  → If test is much worse → discuss why (overfitting? small n?)
  → If test is much better → lucky split, note it
□ Git commit
```

### ⏱️ Time Budget: ~45–60 minutes
### ✅ Done When: statistical_report.md is complete with honest CIs and limitations

---

---

# 📈 SUB-PHASE 4.3 — VISUALIZATION

### 🎯 Goal
Create 3–4 publication-quality charts that tell your story at a glance. Judges will see these in your README and video.

---

### Step 1: The Chart Generator

```python
"""
generate_charts.py — Create all final visualizations.
Run after statistical_report.py.
"""

import json
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

# Style setup — clean, professional, readable
matplotlib.rcParams.update({
    'font.size': 12,
    'font.family': 'sans-serif',
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'figure.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.2,
})

# Color palette — Swiss-inspired (red + neutral)
COLORS = {
    '8b_baseline': '#E63946',    # Swiss red
    '8b_improved': '#FF6B6B',    # Lighter red
    '70b_baseline': '#457B9D',   # Blue
    '70b_improved': '#6BAED6',   # Lighter blue
    'highlight': '#F4A261',      # Orange for emphasis
    'grid': '#E8E8E8',
    'text': '#2D3436',
}

def load_stats():
    with open("eval/results/final_scores/test_scores.json") as f:
        return json.load(f)


# ─── CHART 1: Overall Accuracy Comparison ───
def chart1_overall_accuracy(stats):
    """
    Bar chart: 8B vs 70B, baseline vs improved.
    This is your HEADLINE chart.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    models = ['Apertus 8B', 'Apertus 70B']
    baseline = [
        stats["knowledge"]["8b"]["baseline"]["accuracy"],
        stats["knowledge"]["70b"]["baseline"]["accuracy"],
    ]
    improved = [
        stats["knowledge"]["8b"]["baseline"]["accuracy"] + stats["knowledge"]["8b"]["delta"],
        stats["knowledge"]["70b"]["baseline"]["accuracy"] + stats["knowledge"]["70b"]["delta"],
    ]

    x = np.arange(len(models))
    width = 0.3

    bars1 = ax.bar(x - width/2, baseline, width,
                   label='Baseline', color=COLORS['8b_baseline'], alpha=0.8)
    bars2 = ax.bar(x + width/2, improved, width,
                   label='With RAG', color=COLORS['8b_improved'], alpha=0.9,
                   edgecolor='white', linewidth=1.5)

    # Add value labels on bars
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 1,
                f'{h:.1f}%', ha='center', va='bottom', fontsize=11,
                fontweight='bold', color=COLORS['text'])
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 1,
                f'{h:.1f}%', ha='center', va='bottom', fontsize=11,
                fontweight='bold', color=COLORS['text'])

    # Add delta arrows
    for i, (b, imp) in enumerate(zip(baseline, improved)):
        delta = imp - b
        if delta > 0:
            ax.annotate(f'+{delta:.1f}pp',
                       xy=(i + width/2, imp),
                       xytext=(i + width/2 + 0.15, imp + 5),
                       fontsize=10, color='green', fontweight='bold',
                       arrowprops=dict(arrowstyle='->', color='green'))

    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Swiss Knowledge Accuracy: Baseline vs RAG Improvement')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylim(0, 100)
    ax.legend(loc='upper left')
    ax.grid(axis='y', color=COLORS['grid'], linestyle='--', alpha=0.7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.savefig('eval/results/charts/fig1_overall_accuracy.png')
    plt.close()
    print("  ✅ Chart 1: Overall accuracy saved")


# ─── CHART 2: Category Breakdown Heatmap ───
def chart2_category_heatmap(stats):
    """
    Heatmap: categories × models/methods.
    Shows WHERE the improvement helps most.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    categories = ['Politics', 'Law', 'Health', 'Geography', 'Holidays', 'History']
    columns = ['8B\nBase', '8B\n+RAG', '70B\nBase', '70B\n+RAG']

    # Build data matrix
    data = []
    for cat in categories:
        cat_lower = cat.lower()
        row = [
            stats["knowledge"]["8b"]["baseline_by_category"].get(cat_lower, {}).get("accuracy", 0),
            stats["knowledge"]["8b"]["improved_by_category"].get(cat_lower, {}).get("accuracy", 0),
            stats["knowledge"]["70b"]["baseline_by_category"].get(cat_lower, {}).get("accuracy", 0),
            stats["knowledge"]["70b"]["improved_by_category"].get(cat_lower, {}).get("accuracy", 0),
        ]
        data.append(row)

    data = np.array(data)

    # Plot heatmap
    im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

    # Labels
    ax.set_xticks(np.arange(len(columns)))
    ax.set_yticks(np.arange(len(categories)))
    ax.set_xticklabels(columns, fontsize=11)
    ax.set_yticklabels(categories, fontsize=11)

    # Add text annotations
    for i in range(len(categories)):
        for j in range(len(columns)):
            val = data[i, j]
            color = 'white' if val < 40 or val > 80 else 'black'
            ax.text(j, i, f'{val:.0f}%', ha='center', va='center',
                   fontsize=12, fontweight='bold', color=color)

    # Highlight the improvement columns
    for j in [1, 3]:
        ax.axvline(x=j-0.5, color='white', linewidth=2)

    ax.set_title('Knowledge Accuracy by Category and Model')
    plt.colorbar(im, ax=ax, label='Accuracy (%)', shrink=0.8)

    plt.savefig('eval/results/charts/fig2_category_heatmap.png')
    plt.close()
    print("  ✅ Chart 2: Category heatmap saved")


# ─── CHART 3: Before/After Improvement (Focused) ───
def chart3_before_after(stats):
    """
    Horizontal bar chart: delta per category for 8B.
    Shows the IMPACT of your fix.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    categories = ['Politics', 'Law', 'Health', 'Geography', 'Holidays', 'History']
    deltas_8b = []
    deltas_70b = []

    for cat in categories:
        cat_lower = cat.lower()
        d8 = (stats["knowledge"]["8b"]["improved_by_category"].get(cat_lower, {}).get("accuracy", 0) -
              stats["knowledge"]["8b"]["baseline_by_category"].get(cat_lower, {}).get("accuracy", 0))
        d70 = (stats["knowledge"]["70b"]["improved_by_category"].get(cat_lower, {}).get("accuracy", 0) -
               stats["knowledge"]["70b"]["baseline_by_category"].get(cat_lower, {}).get("accuracy", 0))
        deltas_8b.append(d8)
        deltas_70b.append(d70)

    y = np.arange(len(categories))
    height = 0.35

    bars1 = ax.barh(y - height/2, deltas_8b, height,
                    label='8B', color=COLORS['8b_baseline'], alpha=0.8)
    bars2 = ax.barh(y + height/2, deltas_70b, height,
                    label='70B', color=COLORS['70b_baseline'], alpha=0.8)

    # Add value labels
    for bar in bars1:
        w = bar.get_width()
        ax.text(w + 0.5 if w >= 0 else w - 0.5, bar.get_y() + bar.get_height()/2,
                f'{w:+.0f}pp', ha='left' if w >= 0 else 'right',
                va='center', fontsize=10, fontweight='bold')
    for bar in bars2:
        w = bar.get_width()
        ax.text(w + 0.5 if w >= 0 else w - 0.5, bar.get_y() + bar.get_height()/2,
                f'{w:+.0f}pp', ha='left' if w >= 0 else 'right',
                va='center', fontsize=10, fontweight='bold')

    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(categories)
    ax.set_xlabel('Accuracy Change (percentage points)')
    ax.set_title('Improvement Delta by Category (RAG vs Baseline)')
    ax.legend()
    ax.grid(axis='x', color=COLORS['grid'], linestyle='--', alpha=0.7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.savefig('eval/results/charts/fig3_before_after.png')
    plt.close()
    print("  ✅ Chart 3: Before/after delta saved")


# ─── CHART 4: Values Score Distribution ───
def chart4_values_distribution(stats):
    """
    Stacked bar chart: score distribution for values scenarios.
    """
    fig, ax = plt.subplots(figsize=(7, 5))

    # Load raw values results for distribution
    try:
        with open("eval/results/test_run/values_8b.json") as f:
            v8 = json.load(f)
        with open("eval/results/test_run/values_70b.json") as f:
            v70 = json.load(f)

        v8_scores = [r["score"] for r in v8 if r.get("score", -1) >= 0]
        v70_scores = [r["score"] for r in v70 if r.get("score", -1) >= 0]

        models = ['8B', '70B']
        score_0 = [v8_scores.count(0), v70_scores.count(0)]
        score_1 = [v8_scores.count(1), v70_scores.count(1)]
        score_2 = [v8_scores.count(2), v70_scores.count(2)]

        x = np.arange(len(models))
        width = 0.5

        ax.bar(x, score_0, width, label='Score 0 (Fail)', color='#E63946', alpha=0.8)
        ax.bar(x, score_1, width, bottom=score_0, label='Score 1 (Partial)',
               color='#F4A261', alpha=0.8)
        ax.bar(x, score_2, width,
               bottom=[a+b for a,b in zip(score_0, score_1)],
               label='Score 2 (Pass)', color='#2A9D8F', alpha=0.8)

        ax.set_ylabel('Number of Scenarios')
        ax.set_title('Values & Norms: Score Distribution')
        ax.set_xticks(x)
        ax.set_xticklabels(models)
        ax.legend()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    except FileNotFoundError:
        ax.text(0.5, 0.5, 'Values data not available',
               ha='center', va='center', transform=ax.transAxes)

    plt.savefig('eval/results/charts/fig4_values_distribution.png')
    plt.close()
    print("  ✅ Chart 4: Values distribution saved")


def generate_all_charts():
    """Generate all charts."""
    Path("eval/results/charts").mkdir(parents=True, exist_ok=True)
    stats = load_stats()

    print("\n📊 Generating charts...")
    chart1_overall_accuracy(stats)
    chart2_category_heatmap(stats)
    chart3_before_after(stats)
    chart4_values_distribution(stats)
    print("  ✅ All charts saved to eval/results/charts/")


if __name__ == "__main__":
    generate_all_charts()
```

---

### Step 2: Chart Quality Checklist

```
BEFORE INCLUDING A CHART IN YOUR SUBMISSION:

□ Is the title clear and self-explanatory?
□ Are axis labels present and readable?
□ Are the numbers visible on or near the data points?
□ Is the color scheme colorblind-friendly?
   → Avoid red-green only. Use patterns or labels too.
□ Does the chart tell a story without reading the text?
   → A judge should understand the finding in 5 seconds
□ Is the font large enough to read in a video screenshot?
   → Minimum 12pt for labels, 14pt for titles
□ Is the chart saved at high DPI (150+)?
□ Does the y-axis start at 0 for bar charts?
   → Truncated axes are misleading and judges will notice
□ Are confidence intervals or error bars shown where appropriate?
   → At minimum, mention them in the caption
```

---

### Step 3: Chart Captions (For README)

```markdown
**Figure 1: Overall Knowledge Accuracy**
Baseline vs RAG-augmented performance on the held-out test set
(n=36). Error bars show 95% Wilson confidence intervals.

**Figure 2: Category Heatmap**
Per-category accuracy across both models and methods. Green = high,
red = low. Note: per-category n=6, so individual cells have high
variance.

**Figure 3: Improvement Delta**
Change in accuracy (percentage points) from RAG augmentation.
Positive = improvement, negative = regression. The largest gains
are in [category], where the model previously confused Swiss and
German/EU norms.

**Figure 4: Values Score Distribution**
Distribution of LLM-judge scores (0-2) for cultural appropriateness
scenarios. Higher proportion of 2s indicates better Swiss cultural
understanding.
```

---

### 📋 TODO Checklist for 4.3

```
□ Install matplotlib if needed: pip install matplotlib
□ Run generate_all_charts()
□ Open each chart and verify it looks correct
□ Check: are the numbers on the charts consistent with your report?
□ Check: are titles, labels, and legends readable?
□ Check: colors are distinguishable (not just red vs green)
□ Save all 4 charts as PNG at 150 DPI
□ Write chart captions for the README
□ (Optional) Create a 5th chart: model comparison radar plot
□ Git commit charts
```

### ⏱️ Time Budget: ~45–60 minutes
### ✅ Done When: 4 publication-quality charts saved in eval/results/charts/

---

---

# 📖 SUB-PHASE 4.4 — CROSS-MODEL NARRATIVE

### 🎯 Goal
Write the story that ties everything together. This becomes the core of your README, your demo video script, and the text the jury reads when deciding winners.

---

### Step 1: The Narrative Framework

```
YOUR STORY HAS 5 ACTS:

ACT 1: THE PROBLEM (30 seconds)
"Open LLMs are trained on global data. When you ask about
Switzerland, they default to German or EU norms because that's
what dominates their training data. This makes them unreliable
for Swiss users."

ACT 2: THE MEASUREMENT (30 seconds)
"We built Swiss Reality Check — a benchmark of 120 verified
questions across politics, law, health, geography, customs, and
history, all sourced from official Swiss government websites."

ACT 3: THE FINDINGS (60 seconds)
"Apertus 8B scores XX% and 70B scores XX% on Swiss knowledge.
The dominant failure mode is [DE-CONF]: the model applies German
or EU law when asked about Swiss equivalents. For example, when
asked about working hours, it gives the German 40-hour standard
instead of the Swiss 45-hour rule."

ACT 4: THE FIX (60 seconds)
"We built a RAG system over 30 official Swiss source pages.
When the model answers a question, it first retrieves the most
relevant Swiss source and uses it as context. This improved
8B accuracy from XX% to XX% (+XX pp) and 70B from XX% to XX%
(+XX pp). The biggest gains were in [category], where
[specific error type] was most prevalent."

ACT 5: THE IMPLICATIONS (30 seconds)
"This shows that even a small, targeted retrieval step can
significantly improve an open model's reliability for a specific
country's knowledge. The benchmark, code, and RAG pipeline are
all open-source and reusable for any sovereign AI deployment."
```

---

### Step 2: The Findings Document (`findings.md`)

```markdown
# Key Findings — Swiss Reality Check

## 1. Model Performance on Swiss Knowledge

Apertus 1.5 achieves [XX.X]% accuracy (8B) and [XX.X]% accuracy
(70B) on our held-out test set of 36 verified Swiss knowledge
questions. The 70B model outperforms the 8B by [XX] percentage
points, suggesting that scale helps with country-specific knowledge
but does not eliminate systematic errors.

## 2. Dominant Failure Mode: German/EU Confusion

The most common error type across both models is **DE-CONF**
(German/EU confusion), accounting for [XX]% of all wrong answers.
The models frequently:
- Apply German federal law to Swiss legal questions
- Use EU regulatory frameworks when Swiss-specific rules differ
- Confuse German institutional structures with Swiss ones
  (e.g., "Bundeskanzler" as head of government)

This is consistent with the training data distribution: German
legal and institutional content vastly outweighs Swiss-specific
content in multilingual corpora.

## 3. Where the Models Agree (and Both Fail)

Both 8B and 70B struggle most with:
- **[Category]**: [specific pattern, e.g., "cantonal variation
  in holiday schedules"]
- **[Category]**: [specific pattern]

These are areas where even the larger model's additional parameters
don't help, suggesting a fundamental data gap rather than a
capacity issue.

## 4. Where Scale Helps

The 70B model shows the largest advantage over 8B in:
- **[Category]**: [XX]% vs [XX]% (+XX pp)
- **[Category]**: [XX]% vs [XX]% (+XX pp)

This suggests that [hypothesis about why scale helps here].

## 5. RAG Improvement

Our retrieval-augmented generation system, using 30 official Swiss
source pages and a lightweight embedding model (MiniLM-L6), improved:
- **8B**: [XX.X]% → [XX.X]% (+[XX.X] pp)
- **70B**: [XX.X]% → [XX.X]% (+[XX.X] pp)

The improvement was largest in [category] (+[XX] pp), where the
retrieved sources directly addressed the model's most common errors.

## 6. Values and Cultural Appropriateness

On our 30 cultural scenarios, the 8B scored [X.XX]/2.0 and the
70B scored [X.XX]/2.0. The most common failure was [pattern],
particularly when questions were posed in Swiss German rather
than Standard German.

## 7. Dialect Understanding

[Summary of dialect results, with honest caveats about pilot status
if applicable.]

## Limitations and Future Work

1. Test set size (n=36) limits statistical confidence
2. Dialect section is a pilot without full native-speaker validation
3. RAG retrieval quality depends on embedding model choice
4. Values scoring uses LLM-as-judge with XX% human agreement
5. Future work: expand to 1000+ questions, add audio evaluation,
   test on-site at Swiss institutions

## Implications for Sovereign AI

This benchmark demonstrates that:
1. Open multilingual LLMs have measurable gaps in country-specific
   knowledge, even for well-documented countries like Switzerland
2. These gaps follow predictable patterns (dominant-culture bias)
3. Lightweight RAG can partially close these gaps without
   retraining
4. Systematic evaluation is essential before deploying open models
   in sovereign contexts (government, healthcare, legal)
```

---

### Step 3: The Narrative Decision Tree

```
HOW TO FRAME YOUR RESULTS BASED ON WHAT YOU FIND:

SCENARIO A: Strong improvement (+15pp or more)
→ Lead with the delta. "RAG improved Swiss knowledge by XX%."
→ Show the before/after chart prominently.
→ Emphasize the practical implications for deployment.

SCENARIO B: Modest improvement (+5-15pp)
→ Lead with the benchmark. "We built the first systematic
  Swiss knowledge benchmark for open LLMs."
→ The improvement is a proof of concept, not the main story.
→ Emphasize reproducibility and the open dataset.

SCENARIO C: No clear improvement or mixed results
→ Lead with the failure analysis. "We discovered that open
  LLMs systematically confuse Swiss and German law."
→ The benchmark and error taxonomy ARE the contribution.
→ The fix attempt is honest research, not a failure.
→ Say: "The RAG approach showed mixed results, suggesting
  that [hypothesis]. This is a valuable finding for the
  community."

SCENARIO D: 70B already scores high, 8B improves a lot
→ Lead with the model comparison. "Scale helps, but RAG
  helps the smaller model more."
→ This is a great narrative for deployment: "You don't need
  the 70B if you add RAG to the 8B."

WHATEVER YOU DO:
✅ Be honest about the numbers
✅ Acknowledge the small test set
✅ Emphasize the reusable benchmark
✅ Connect to the "sovereign AI" theme of the hackathon
❌ Don't overclaim
❌ Don't hide negative results
❌ Don't compare to models you didn't test
```

---

### 📋 TODO Checklist for 4.4

```
□ Determine which scenario (A/B/C/D) matches your results
□ Write findings.md following the 5-act structure
□ Fill in all XX placeholders with real numbers
□ Write the limitations section honestly
□ Write the "implications for sovereign AI" paragraph
□ Review: would an EPFL professor find this credible?
□ Review: would a non-technical jury member understand it?
□ Save to eval/results/narrative/findings.md
□ This document becomes the core of your README (Phase 5)
□ This document becomes the script for your video (Phase 5)
□ Git commit
```

### ⏱️ Time Budget: ~45–60 minutes
### ✅ Done When: findings.md is complete with real numbers, honest limitations, and a compelling narrative

---

---

# 📊 PHASE 4 — SUMMARY DASHBOARD

| Sub-Phase | Output | Time | Priority | Status |
|---|---|---|---|---|
| **4.1** Held-Out Test Run | 8 result files + metadata | 2–2.5h | 🔴 CRITICAL | ⬜ |
| **4.2** Statistical Comparison | test_scores.json + statistical_report.md | 45–60min | 🔴 CRITICAL | ⬜ |
| **4.3** Visualization | 4 PNG charts + captions | 45–60min | 🟡 HIGH | ⬜ |
| **4.4** Cross-Model Narrative | findings.md (5-act story) | 45–60min | 🔴 CRITICAL | ⬜ |

**Total Phase 4 time: ~4–5 hours on Thu 15 Oct (morning/early afternoon)**

---

## ⚠️ Critical Reminders

```
┌─────────────────────────────────────────────────────────────┐
│  AFTER PHASE 4 IS COMPLETE:                                 │
│                                                             │
│  1. The test set numbers are FINAL. Do not re-run.          │
│  2. If the numbers are disappointing, that's OK.            │
│     An honest benchmark with modest improvement beats       │
│     a suspicious benchmark with inflated numbers.           │
│  3. The jury values METHODOLOGY over MAGNITUDE.             │
│  4. Your contribution is the benchmark + the analysis,      │
│     not just the improvement delta.                         │
│  5. Everything you've produced is reusable by the           │
│     Apertus community — that's the open-source ethos        │
│     the hackathon celebrates.                               │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ How I Can Help Right Now

- **"Run the statistics"** → Paste your test results and I'll compute everything
- **"Generate the charts"** → Give me the numbers and I'll write custom matplotlib code
- **"Write the narrative"** → Share your findings and I'll draft the 5-act story
- **"My test results are worse than dev"** → I'll help you write an honest explanation
- **"How do I explain wide confidence intervals?"** → I'll write the statistical caveat paragraph
- **"Review my findings.md"** → Paste it and I'll critique it from a jury perspective

Your call. The finish line is in sight. 🏁🏆
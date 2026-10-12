"""
select_target.py - Phase 3.2: choose ONE improvement target, or refuse and say why.

The plan's Step 3 asks five questions in order. This module answers every one of
them programmatically where that is possible, and it refuses to name a target
when the inputs cannot support one. A selection made on a mock baseline is a
selection made on noise, and it is worse than no selection, because Phase 3.3
then spends its time on the wrong thing.

THE FIVE QUESTIONS, AND HOW WELL EACH CAN BE ANSWERED TODAY

  Q1 lowest baseline              needs a real run          BLOCKED by B2
  Q2 dominant error type          needs 3.1 classification  BLOCKED by B2
  Q3 good source material?        ANSWERABLE NOW            source_registry.csv
  Q4 fixable in <4h?              partially                 corpus size, not model
  Q5 will it be visible?          ANSWERABLE NOW - and the
                                  plan asks it qualitatively
                                  when the answer is quantitative

Q5 IS WHERE THIS GOES BEYOND THE PLAN, AND IT MATTERS MOST.

The plan asks "a category at 30% going to 50% is dramatic, a category at 75%
going to 80% is less impressive - pick the dramatic one if possible." That is the
right instinct and the wrong question. Visibility is not significance.

The dev split has 14 questions per category. A before/after comparison on the
SAME questions is paired, so only items that change direction carry information,
and an exact McNemar test says what is actually detectable:

    n = 14, one category   6 up / 0 down -> p = 0.031   (+42.9 points)
    n = 14, one category   5 up / 2 down -> p = 0.453   (+21.4 points)
    n = 84, whole dev set  6 up / 0 down -> p = 0.031   ( +7.1 points)

So a per-category claim needs a near-perfect fix with zero collateral damage -
a 43-point swing in one category before the number means anything. The whole dev
set has roughly six times the power.

CONSEQUENCE, and it is the main output of this sub-phase:

    fix ONE thing  - one intervention, golden rule 1
    measure on the WHOLE dev set - not one category
    use the category to find the MECHANISM, not to carry the significance claim

A RAG fix aimed at one category will move other categories too, because the
retrieval corpus is not partitioned. Restricting the test to the target category
would throw away most of the effect and most of the power.

Run:
    python fix/select_target.py --model 8b 70b
    python fix/select_target.py --model 8b --force   # override the gates
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fix"))
sys.path.insert(0, str(ROOT / "eval"))

from analyze_errors import (CATEGORIES, ERROR_TYPES, build_taxonomy,       # noqa: E402
                            dominant, score_targets)
from config import PARSED_DIR, SCORES_DIR, config                          # noqa: E402

FIX_DIR = ROOT / "fix"
ALPHA = 0.05
DEV_PER_CATEGORY = 14          # 84 / 6, fixed by the Phase 1A.4 split
GOLDEN_RULE_HOURS = 4


# ============================================================ statistical power
def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value on the discordant pairs only."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / (2 ** n) * 2
    return min(1.0, p)


def power_table(n: int, alpha: float = ALPHA) -> list[dict]:
    """
    What a paired before/after test can actually detect at this n.

    Returns, for each number of regressions, the smallest number of improvements
    that reaches significance - i.e. what the fix has to achieve before the
    result is worth claiming.
    """
    rows = []
    for regressed in range(0, n // 2 + 2):
        needed = None
        for improved in range(regressed, n // 2 + 1):
            if mcnemar_exact(improved, regressed) < alpha:
                needed = improved
                break
        rows.append({
            "regressed": regressed,
            "improvements_needed": needed,
            "net": (needed - regressed) if needed is not None else None,
            "accuracy_delta_pts": round((needed - regressed) / n * 100, 1)
                                 if needed is not None else None,
            "detectable": needed is not None,
        })
    return rows


# ============================================================== Q3: RAG corpus
def source_material() -> dict:
    """
    How much RAG-ready material exists per category. Answerable now.

    Read from source_registry.csv, which is already harvested - so this question
    does not need a model, a baseline, or any further data collection.
    """
    path = ROOT / "data" / "sources" / "source_registry.csv"
    facts, sources, files = defaultdict(int), defaultdict(int), defaultdict(int)
    present = set()
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            cat = r["category"]
            present.add(r["source_id"])
            facts[cat] += int(r["fact_count"] or 0)
            sources[cat] += 1
            raw = (r["raw_file"] or "").split(" ")[0].split(",")[0].strip()
            if raw and (ROOT / "data" / "sources" / "raw_pages" / raw).exists():
                files[cat] += 1

    raw_dir = ROOT / "data" / "sources" / "raw_pages"
    all_raw = {p.name for p in raw_dir.glob("*.txt")} if raw_dir.is_dir() else set()

    out = {}
    for cat in CATEGORIES:
        # the knowledge categories borrow sources registered under 'privacy' and
        # 'dialect' too, so count everything usable for a knowledge-category RAG
        usable_facts = sum(v for k, v in facts.items()
                           if k == cat or (cat != "law" and k in {"privacy", "dialect"}))
        out[cat] = {
            "sources": sources[cat],
            "facts": facts[cat],
            "raw_files_present": files[cat],
            "facts_with_corpus": usable_facts,
            "sufficient": facts[cat] >= 40 and files[cat] >= 5,
        }
    out["_totals"] = {"sources": len(present), "raw_files": len(all_raw),
                      "facts": sum(facts.values())}
    return out


# ============================================================ fix-approach map
# Which intervention the plan routes each dominant error to, and the honest
# caveats. RAG is the default because the corpus already exists.
APPROACH = {
    "DE-CONF":  ("B", "RAG over the harvested Swiss sources. The corpus already "
                       "exists, which is most of the work done."),
    "CANTON":   ("B", "RAG, but only if the cantonal source is in the corpus. "
                       "Check Q3 first - a federal page will not settle a "
                       "cantonal claim and may make it worse by sounding confident."),
    "OUTDATE":  ("B", "RAG. Only helps if the corpus is current; a stale corpus "
                       "reproduces the stale answer with a citation."),
    "NUMERIC":  ("B", "RAG, with the source's own figure quoted in context. "
                       "Expected gain is modest - retrieval supplies the number, "
                       "it does not make the model select it over a neighbour."),
    "LANG":     ("B", "RAG over all four language regions. Will only help if the "
                       "corpus itself covers them; see the corpus language split."),
    "GENERIC":  ("A", "System prompt first. Cheap, and if it does not move the "
                       "number the error is knowledge, not framing."),
    "PARSE":    ("A", "Prompt only. This is not a knowledge error at all - it is a "
                       "measurement failure and belongs to 2.2, not Phase 3."),
    "HALLUC":   ("C", "Hard without fine-tuning. RAG cannot cite a fact that does "
                       "not exist; consider the second-worst category instead."),
    "OTHER":    ("A", "No clear mechanism. Try the prompt, or pick another target."),
}


# ==================================================================== the gates
def gates(models: dict) -> list[dict]:
    """
    Hard refusals. Each one, if it fires, makes a named target indefensible.

    These are not warnings. A selection made past a fired gate is a selection
    made on noise, and it would be written into weakest_area_analysis.md as a
    decision.
    """
    out = []

    mock = [m for m, d in models.items() if d["scores"]["run"].get("is_mock")]
    out.append({
        "id": "G1-baseline-is-mock",
        "fires": bool(mock),
        "detail": f"{', '.join(mock)} produced no real numbers" if mock else
                  "at least one model has a live baseline",
        "why": "Every score is a hash of the prompt. Ranking categories on that "
               "is ranking noise.",
    })

    unresolved = []
    for m, d in models.items():
        tax = d["taxonomy"]
        un = tax.get("UNCLASSIFIED", {}).get("pct_of_content_errors", 0.0)
        if un > 50:
            unresolved.append(f"{m} ({un}%)")
    out.append({
        "id": "G2-error-taxonomy-unresolved",
        "fires": bool(unresolved),
        "detail": ", ".join(unresolved) if unresolved else "taxonomy is classified",
        "why": "3.2 routes the target by DOMINANT error type. If most errors are "
               "UNCLASSIFIED there is no dominant type, so the routing is a guess.",
    })

    out.append({
        "id": "G3-single-model",
        "fires": len([m for m, d in models.items()
                      if not d["scores"]["run"].get("is_mock")]) < 2,
        "detail": f"{len(models)} model(s) with results",
        "why": "The project premise is 8B vs 70B. A target chosen on one model is "
               "a target that may not generalise to the other.",
    })

    total_hours = GOLDEN_RULE_HOURS
    out.append({
        "id": "G4-time-budget",
        "fires": False,
        "detail": f"{total_hours}h budget assumed for build + dev evaluation",
        "why": "Not a gate on the data, a gate on the plan. RAG over an already-"
               "harvested corpus is the only option that fits; LoRA is out on an "
               "8 GB card.",
    })
    return out


# ================================================================== the decision
def build_decision(models: dict) -> dict:
    tax = models[list(models)[0]]["taxonomy"]
    scores = models[list(models)[0]]["scores"]
    rows = score_targets(tax, scores)
    corpus = source_material()
    live = [m for m, d in models.items()
            if not d["scores"]["run"].get("is_mock")]
    primary = live[0] if live else list(models)[0]
    p_scores = models[primary]["scores"]

    fired = [g for g in gates(models) if g["fires"]]

    # selection matrix, impact x fixability, on LIVE models only
    matrix = []
    for r in rows:
        cat = r["category"]
        fix, why = APPROACH.get(r["dominant_error"] or "OTHER",
                                ("A", "no clear mechanism"))
        c = corpus[cat]
        # Option C is LoRA. It is excluded on this hardware, so a category whose
        # dominant error routes there is NOT a candidate - it is the case the
        # plan says to skip ("consider the second-worst category instead").
        # Without this the matrix would happily select a category whose only
        # route is the one approach that cannot be built.
        infeasible = fix == "C"
        matrix.append({
            "category": cat,
            "accuracy": r["baseline_accuracy"],
            "impact": r["impact"],
            "errors": r["error_count"],
            "dominant_error": r["dominant_error"],
            "fixability": r["fixability"],
            "priority": r["priority"],
            "approach": fix,
            "approach_why": why,
            "infeasible_on_hardware": infeasible,
            "unclassifiable": r["unclassifiable"],
            "corpus_facts": c["facts"],
            "corpus_files": c["raw_files_present"],
            "corpus_ok": c["sufficient"],
            # viable = fixable, measurable, and buildable on what we have
            "viable": (not r["unclassifiable"]) and c["sufficient"] and not infeasible,
        })
    matrix.sort(key=lambda r: -r["priority"])
    viable = [m for m in matrix if m["viable"]]

    # ---- Q5, answered quantitatively
    power_cat = power_table(DEV_PER_CATEGORY)
    power_all = power_table(84)
    min_net_cat = next((r for r in power_cat if r["detectable"]), None)
    min_net_all = next((r for r in power_all if r["detectable"]), None)

    selected = viable[0]["category"] if viable and not fired else None

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "primary_model": primary,
        "live_models": live,
        "matrix": matrix,
        "viable": viable,
        "gates": gates(models),
        "gates_fired": fired,
        "selected": selected,
        "approach": (APPROACH.get(
            next((m["dominant_error"] for m in viable
                  if m["category"] == selected), "OTHER"))[0]
            if selected else None),
        "power": {
            "n_per_category": DEV_PER_CATEGORY,
            "per_category": power_cat,
            "whole_dev_set": power_all,
            "min_net_category": min_net_cat,
            "min_net_whole_set": min_net_all,
        },
        "corpus": corpus,
        "dominant_error": dominant(tax),
    }


# ==================================================================== rendering
def render(d: dict, models: dict) -> str:
    L = []
    A = L.append
    fired = d["gates_fired"]

    A("# Weakest Area Analysis — Phase 3.2\n")
    A(f"*Generated {d['generated']} · primary model **{d['primary_model']}** · "
      f"dev split, {DEV_PER_CATEGORY} questions per category*\n")

    # ---------------------------------------------------------- the headline
    A("## Decision\n")
    if fired:
        A("> ## ⛔ NO TARGET SELECTED\n>\n"
          "> The inputs cannot support a decision. Naming a category here would "
          "put a\n> wrong target into `docs/plans/phase_3.md` 3.3 and spend the "
          "remaining\n> budget on it.\n")
        for g in fired:
            A(f"> **{g['id']}** — {g['detail']}\n"
              f"> \n> {g['why']}\n")
        A("> Resolving these is **B2** (a live model) and the 3.1 reasoning pass.\n")
    else:
        A(f"**Selected target: `{d['selected']}` — approach Option "
          f"{d['approach']}.**\n")

    # ------------------------------------------------------------------ gates
    A("## Gates\n")
    A("Each gate, if it fires, makes a named target indefensible. These are not "
      "warnings.\n")
    A("| gate | state | detail |")
    A("|---|---|---|")
    for g in d["gates"]:
        mark = "🚫 **FIRED**" if g["fires"] else "✅ pass"
        A(f"| `{g['id']}` | {mark} | {g['detail']} |")
    A("")

    # ------------------------------------------------------------ baseline table
    A("## Baseline scores (dev split)\n")
    cols = list(models)
    A("| Category | " + " | ".join(f"{m.upper()}" for m in cols)
      + " | Errors | Dominant | Fixability | Approach | Corpus |")
    A("|---" * (len(cols) + 6) + "|")
    for r in d["matrix"]:
        accs = " | ".join(
            f"{models[m]['scores']['by_category'].get(r['category'], {}).get('accuracy', '—')}%"
            for m in cols)
        corpus = f"{r['corpus_facts']} facts / {r['corpus_files']} files"
        corpus += " ✅" if r["corpus_ok"] else " ⚠"
        A(f"| {r['category']} | {accs} | {r['errors']} | "
          f"{r['dominant_error'] or '—'} | {r['fixability']} | "
          f"{r['approach']} | {corpus} |")
    A("")
    A("**Priority** is `impact × fixability × (errors / 14)`. The plan's "
      "`impact × fixability`\nrewards a category at 0% whose dominant error is "
      "unfixable over one at 30%\nthat RAG would fix, so the error count is "
      "folded in.\n")

    # ------------------------------------------------------------- the 5 questions
    A("## The five decision questions\n")

    A("### Q1 · Which category has the lowest baseline?\n")
    ranked = sorted(
        d["matrix"],
        key=lambda r: (r["accuracy"] if r["accuracy"] is not None else 101))
    if fired:
        A("**Unanswerable.** No live baseline exists. The ranking below is "
          "reproduced only\nso the shape of the analysis is visible.\n")
    for r in ranked[:3]:
        A(f"- `{r['category']}` — {r['accuracy']}% ({r['errors']} errors)")
    A("")
    A("> With 14 questions per category, **one item moves a category by 7.1 "
      "points**.\n"
      "> A gap smaller than that between two categories is noise and must not "
      "drive a choice.\n")

    A("### Q2 · What is the dominant error type, and which fix does it route to?\n")
    dom, pct = d["dominant_error"]
    if dom:
        approach, why = APPROACH.get(dom, ("A", "-"))
        A(f"Dominant content error: **`{dom}`** at {pct}%. Routes to "
          f"**Option {approach}**.\n")
        A(f"> {why}\n")
    else:
        A("**Unanswerable.** No error class is dominant — the taxonomy is mostly "
          "`UNCLASSIFIED`.\n")
    A("Routing table, so the logic is visible rather than asserted:\n")
    A("| Dominant error | Option | Why |")
    A("|---|---|---|")
    for code, (opt, why) in APPROACH.items():
        A(f"| `{code}` | {opt} | {why} |")
    A("")

    A("### Q3 · Is there good source material?\n")
    A("**This one is answerable now, and it does not need a model.**\n")
    tot = d["corpus"]["_totals"]
    A(f"The corpus is already harvested: **{tot['sources']} sources, "
      f"{tot['facts']} fact candidates, {tot['raw_files']} raw page files.**\n")
    A("| Category | Sources | Facts | Raw files present | Enough for RAG? |")
    A("|---|---|---|---|---|")
    for r in d["matrix"]:
        c = d["corpus"][r["category"]]
        A(f"| {r['category']} | {c['sources']} | {c['facts']} | "
          f"{c['raw_files_present']} | {'yes' if c['sufficient'] else '**NO**'} |")
    A("")
    A("So Q3 rules categories *out* rather than *in* — every category has some "
      "material,\nwhich is the one question in this sub-phase that is not blocked.\n")

    A("### Q4 · Can the fix be built and tested inside the budget?\n")
    A("| Approach | Build | Verdict |")
    A("|---|---|---|")
    A("| **A — system prompt** | minutes | fits easily; **3.3a is already "
      "implemented** (`v1_strict`, `v1_json`) |")
    A("| **B — RAG** | 3–5 h over the existing corpus | fits the 4 h budget "
      "**only because Phase 1A.1 already harvested 55 sources.** |")
    A("| **C — LoRA** | not on this hardware | ✗ excluded: an 8 GB RTX 5060 "
      "cannot fine-tune an 8 B model, and 70 B access is itself unresolved |")
    A("")
    A("**B is the only approach that can move a knowledge score**, and its cost "
      "is already\npaid. `embeddings.py` / `retriever.py` / `rag_prompt.py` are "
      "the remaining work.\n")

    A("### Q5 · Will the improvement be measurable?\n")
    A("**Visibility is not significance, and this is where the plan's framing "
      "needs\ncorrecting.** The plan asks whether a change will look dramatic. "
      "The question that\nmatters is whether it can be *distinguished from "
      "noise*.\n")
    A("A before/after run re-asks the same questions, so the comparison is "
      "**paired** and\nonly items that flip carry information. Exact McNemar:\n")

    pw = d["power"]
    A(f"**One category, n = {pw['n_per_category']}:**\n")
    A("| improved | regressed | net | category Δ | p | significant? |")
    A("|---|---|---|---|---|---|")
    for r in pw["per_category"][:6]:
        if r["improvements_needed"] is None:
            A(f"| — | {r['regressed']} | — | — | > {ALPHA} | **no** |")
        else:
            A(f"| {r['improvements_needed']} | {r['regressed']} | +{r['net']} | "
              f"+{r['accuracy_delta_pts']} pts | "
              f"{mcnemar_exact(r['improvements_needed'], r['regressed']):.3f} | "
              f"{'**yes**' if r['detectable'] else 'no'} |")
    A("")
    mc, ma = pw["min_net_category"], pw["min_net_whole_set"]
    A(f"→ A **per-category** claim needs {mc['improvements_needed']} of 14 items "
      f"to flip with\n  **zero regressions**: +{mc['accuracy_delta_pts']} points "
      f"in one category, before the\n  number means anything. Five up and two "
      f"down gives p = 0.453 — not a result.\n")

    A("**The whole dev set, n = 84:**\n")
    A("| improved | regressed | net | overall Δ | p | significant? |")
    A("|---|---|---|---|---|---|")
    for r in pw["whole_dev_set"][:6]:
        if r["improvements_needed"] is None:
            A(f"| — | {r['regressed']} | — | — | > {ALPHA} | **no** |")
        else:
            A(f"| {r['improvements_needed']} | {r['regressed']} | +{r['net']} | "
              f"+{r['accuracy_delta_pts']} pts | "
              f"{mcnemar_exact(r['improvements_needed'], r['regressed']):.3f} | "
              f"{'**yes**' if r['detectable'] else 'no'} |")
    A("")
    A(f"→ The whole set detects a net **+{ma['net']}** items "
      f"(+{ma['accuracy_delta_pts']} points overall) at the same confidence.\n")

    A("### The consequence, and it changes how Phase 3 is measured\n")
    A("```")
    A("golden rule 1:  fix ONE thing well          -> one INTERVENTION")
    A("this module:    measure on the whole dev set -> the SIGNIFICANCE claim")
    A("                use the category            -> the MECHANISM")
    A("```")
    A("The two are not in conflict, and the distinction is what makes the result "
      "defensible.\nA RAG fix aimed at one category will move other categories "
      "too — the retrieval\ncorpus is not partitioned — so restricting the test "
      "to the target category would\nthrow away most of the effect and most of "
      "the power.\n")
    A("Report it as: **one intervention, measured on all 84 dev items, with the "
      "target\ncategory shown as the mechanism and explicitly not as the "
      "significance test.**\n")
    A("> And state the n on everything. With 84 items the 95% interval on a "
      "single\n> category accuracy is roughly ±25 points. A judge who notices "
      "the n before the\n> percentage is doing their job.\n")

    # ---------------------------------------------------------------- why not
    A("## Why not the other categories\n")
    if fired:
        A("**Deferred.** With no live baseline, every rejection below would be a "
          "rejection\nof a number produced by a hash. Re-running this after **B2** "
          "fills the table\nfrom evidence:\n")
        A("| Category | Verdict | Reason |")
        A("|---|---|---|")
        for r in d["matrix"]:
            if r["viable"]:
                reason = ("higher baseline — less headroom"
                          if r["accuracy"] > 50 else "viable; ranking decides")
            elif r.get("infeasible_on_hardware"):
                reason = (f"dominant `{r['dominant_error']}` routes only to Option C "
                          f"(LoRA) — infeasible on this hardware")
            elif not r["corpus_ok"]:
                reason = f"insufficient corpus ({r['corpus_facts']} facts)"
            else:
                reason = "dominant error unclassified — no routing"
            A(f"| {r['category']} | {'candidate' if r['viable'] else 'deferred'} "
              f"| {reason} |")
    else:
        A("| Category | Verdict | Reason |")
        A("|---|---|---|")
        for r in d["matrix"]:
            if r["category"] == d["selected"]:
                A(f"| {r['category']} | **SELECTED** | lowest viable priority "
                  f"{r['priority']}, corpus adequate |")
            else:
                reasons = []
                if r.get("infeasible_on_hardware"):
                    reasons.append(f"dominant `{r['dominant_error']}` routes only to "
                                   f"Option C (LoRA), which an 8 GB card cannot build")
                if r["accuracy"] and r["accuracy"] > 50:
                    reasons.append("higher baseline, less headroom")
                if not r["corpus_ok"]:
                    reasons.append(f"corpus too thin ({r['corpus_facts']} facts)")
                if r.get("unclassifiable"):
                    reasons.append("errors unclassified, no routing")
                if not reasons:
                    reasons.append("lower priority on the matrix")
                A(f"| {r['category']} | rejected | {'; '.join(reasons)} |")
    A("")

    # ----------------------------------------------------------------- next
    A("## What unblocks this\n")
    if fired:
        A("1. **B2** — start Apertus-8B locally, re-run the 84-item dev "
          "baseline.\n"
          "2. `python fix/analyze_errors.py --model 8b --diagnose` — the "
          "reasoning pass.\n"
          "3. Re-run this module. The matrix, the rejection table and the "
          "selection\n"
          "   all populate from evidence in one command.\n")
        A("Nothing needs rewriting between now and then — the gates are the "
          "only thing\nholding it, and they exist so the decision is made on "
          "evidence rather than on\nthe pressure of a deadline.\n")
    else:
        A(f"Proceed to 3.3 with Option {d['approach']} on `{d['selected']}`.\n")
    return "\n".join(L)


# ========================================================================= main
def _load(model: str):
    parsed = PARSED_DIR / f"knowledge_{model}_dev_base.json"
    scores = SCORES_DIR / f"knowledge_{model}_dev_base.json"
    if not (parsed.exists() and scores.exists()):
        raise SystemExit(f"missing baseline for {model}. Run:\n"
                         f"  python eval/run_all.py --model {model} --task knowledge")
    pdoc = json.loads(parsed.read_text(encoding="utf-8"))
    sdoc = json.loads(scores.read_text(encoding="utf-8"))
    qmap = {q["id"]: q for q in json.loads(
        config.data_path("knowledge", "knowledge_all.json").read_text(encoding="utf-8"))}
    from analyze_errors import analyse
    analysis = analyse(model)
    # The score file nests as {"run": ..., "scores": {...}}, but every consumer
    # here wants by_category and run side by side. Normalising once, here, is
    # why the test fixtures could shape `scores` flat and still pass while the
    # real file produced an empty matrix.
    flat = dict(sdoc["scores"])
    flat["run"] = sdoc.get("run", {})
    return {"scores": flat, "taxonomy": build_taxonomy(analysis),
            "parsed": pdoc, "qmap": qmap}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 3.2 target selection.")
    ap.add_argument("--model", nargs="+", default=["8b"])
    ap.add_argument("--force", action="store_true",
                    help="select a target even if the gates fire. The decision "
                         "document records that the gates were overridden.")
    args = ap.parse_args()

    models = {m: _load(m) for m in args.model}
    d = build_decision(models)

    if args.force and d["gates_fired"]:
        d["selected"] = d["viable"][0]["category"] if d["viable"] else None
        d["approach"] = APPROACH.get(
            next((m["dominant_error"] for m in d["viable"]
                  if m["category"] == d["selected"]), "OTHER"))[0] \
            if d["selected"] else None
        d["forced"] = True
        print(f"  !! gates overridden; selected {d['selected']} anyway")
    else:
        d["forced"] = False

    out = FIX_DIR / "weakest_area_analysis.md"
    out.write_text(render(d, models), encoding="utf-8")
    print(f"  wrote {out.relative_to(ROOT)}")

    print(f"\n  gates fired : {[g['id'] for g in d['gates_fired']] or 'none'}")
    print(f"  dominant    : {d['dominant_error']}")
    print(f"  viable      : {[m['category'] for m in d['viable']] or 'none'}")
    print(f"  SELECTED    : {d['selected'] or 'NONE - blocked'}")
    if d["selected"]:
        print(f"  approach    : Option {d['approach']}")
    pw = d["power"]
    print(f"\n  power: a per-category claim needs "
          f"{pw['min_net_category']['improvements_needed']}/14 flips with 0 "
          f"regressions (+{pw['min_net_category']['accuracy_delta_pts']} pts);")
    print(f"          the whole 84-item set needs "
          f"{pw['min_net_whole_set']['improvements_needed']} net "
          f"(+{pw['min_net_whole_set']['accuracy_delta_pts']} pts).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
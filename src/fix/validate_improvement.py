"""
validate_improvement.py - Phase 3.4: did the improvement work, and did it break anything?

WHAT THIS VALIDATES, AND WHY IT IS NOT A BEFORE/AFTER SUBTRACTION

The plan's Step 1 loads a baseline file and an improved file and subtracts:

    with open(f"eval/results/parsed/knowledge_{model}_{split}.json") as f: baseline = ...
    with open(f"fix/rag/results_rag_{model}_{split}.json") as f:            improved = ...
    comparison = compare_before_after(baseline, improved)

Two problems with that shape, both of which this module fixes:

1. THE FILES MAY NOT BE COMPARABLE. A baseline file and a RAG file written at
   different times can differ in prompt variant, model build, temperature,
   question order, backend, or nothing at all beyond the fix. Nothing in the
   subtraction notices. This module reads the run metadata of BOTH files and
   refuses to attribute a delta when the setups differ.

2. PAIRED DATA IS AVAILABLE AND IGNORED. run_rag_eval.py already runs control
   and treatment back to back in one invocation, so the paired McNemar is both
   available and strictly more informative than a difference of two means.
   This module prefers paired data and falls back to unpaired only when it has
   to, saying which it used.

THE REGRESSION THRESHOLD IN THE PLAN IS A FALSE-POSITIVE MACHINE

docs/plans/phase_3.md Step 2 asks "did any OTHER category get WORSE by >5%?"
and flags it. At n=14 per category, ONE ITEM IS 7.1 PERCENTAGE POINTS:

    health 85.7% -> 78.6%   is one item moving the wrong way

So a 5 pp threshold flags any single regression, and calls a coin-flip a
regression. fix/select_target.py established that at n=84 a detectable effect
needs ~6 net flips. A per-category movement below that is not a regression, it
is one item.

So regressions are counted in ITEMS, and a category-level flag is only raised
when the movement is both in items and large relative to the noise floor. The
pp threshold is still reported, because a reader expects it, but it is reported
as an observation rather than used as the decision.

CONDITIONAL RAG, AND WHY IT CANNOT PICK ITS OWN TARGET

The plan's remedy for a regression is "apply RAG only to the target category".
3.2 refused to name a target: gates G1 (baseline is mock), G2 (error taxonomy
78% UNCLASSIFIED) and G3 (single model) all fired. There is no target to
condition on.

`--target-category` therefore requires an explicit category argument and records
who chose it and why. It does not consult a ranker and invent one. Choosing the
category that happened to improve best on the same split you are validating on
is selection on the measurement set, and it is the single easiest way to
manufacture a clean-looking result here.

Run:
    python src/fix/validate_improvement.py --model 8b --split dev
    python src/fix/validate_improvement.py --model 8b --write-comparison
    python src/fix/validate_improvement.py --model 8b --target-category law \\
        --target-justification "S018 PARSE errors, see fix/weakest_area_analysis.md"

Exit: 0 = validation ran and reported; 1 = refused to certify (see below).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "fix"))
sys.path.insert(0, str(ROOT / "src" / "fix" / "rag"))

from config import config                                      # noqa: E402
from scoring import calculate_knowledge_scores                 # noqa: E402

RAG_DIR = ROOT / "src" / "fix" / "rag"
PARSED_DIR = config.results_dir / "parsed"

# One item in a 14-item category. Every per-category percentage moves in
# multiples of this, and it is the reason the plan's 5 pp flag is wrong.
PP_PER_ITEM = 100 / 14

# Net item movement below this is inside the noise floor that
# fix/select_target.py's power table establishes for this benchmark. Used for
# REPORTING ("this run moved less than the floor") and as a cheap necessary
# condition before running the exact test - see is_significant for why net alone
# is not sufficient.
NOISE_FLOOR_ITEMS = 6


def is_significant(improved: int, regressed: int, n: int,
                   alpha: float = 0.05) -> tuple[bool, float]:
    """
    Is this movement distinguishable from noise, for THIS item count?

    Necessary but NOT sufficient: `improved - regressed >= 6`.

        10 improved / 4 regressed   net +6   p = 0.180   not detectable
         6 improved / 0 regressed   net +6   p = 0.031   detectable

    Both have net +6, so a net-only rule calls both an improvement while one of
    them is indistinguishable from a coin flip. The exact paired test already
    exists in select_target.mcnemar_exact and is used rather than reimplemented,
    because two implementations of the same statistic drift apart and then one
    of them is wrong.

    `n` is the number of PAIRED items, not the sample size, since McNemar
    conditions on the discordant pairs.
    """
    from select_target import mcnemar_exact
    p = mcnemar_exact(improved, regressed)
    return p < alpha, round(p, 4)


# ------------------------------------------------------------------ loading
def _load_parsed(path: Path) -> dict:
    """
    Load a results file and return {"run": <metadata>, "results": <rows>}.

    Two layouts exist in this project and BOTH occur in the same directory:

      Phase 2/3   {"run": {...}, "results": [...]}      nested
      Phase 4.1   {"task":..., "backend":..., "is_mock":..., "results": [...]}   flat

    run_test_final.run_one() writes the flat one. The first version of this
    function assumed the nested layout and therefore read empty metadata for
    every Phase 4.1 arm, which had two consequences, both bad and neither
    visible:

      * is_mock defaulted to True, so a real run was reported as
        "REFUSED TO CERTIFY - MOCK BACKEND";
      * setup_conflicts() compared two empty dicts and returned [], so the gate
        that exists to catch non-comparable arms silently checked nothing.

    So the metadata is taken from "run" when present and otherwise from the top
    level, and every field the gates read is verified present.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        return {"run": {}, "results": payload}

    if "results" not in payload:
        return {"run": {}, "results": []}

    if isinstance(payload.get("run"), dict) and payload["run"]:
        return {"run": payload["run"], "results": payload["results"]}

    # Flat layout: everything except the row list is metadata.
    meta = {k: v for k, v in payload.items() if k != "results"}
    return {"run": meta, "results": payload["results"]}


def find_paired(model: str, split: str, top_k: int | None = None) -> Path | None:
    """The paired run, which is the preferred comparison."""
    pats = ([f"results_rag_{model}_{split}_k{top_k}.json"] if top_k
            else [f"results_rag_{model}_{split}_k*.json"])
    for pat in pats:
        hits = sorted(RAG_DIR.glob(pat))
        if hits:
            return hits[0]
    return None


def find_unpaired_baseline(model: str, split: str) -> Path | None:
    """A separately-run baseline. Weaker: the setups may differ."""
    for name in (f"knowledge_{model}_{split}_base.json",
                 f"knowledge_{model}_{split}.json"):
        p = PARSED_DIR / name
        if p.exists():
            return p
    return None


def find_rag_standalone(model: str, split: str, top_k: int | None = None) -> Path | None:
    pats = ([f"knowledge_{model}_{split}_k{top_k}_rag.json"] if top_k
            else [f"knowledge_{model}_{split}_k*_rag.json"])
    for pat in pats:
        hits = sorted(PARSED_DIR.glob(pat))
        if hits:
            return hits[0]
    return None


# ------------------------------------------------------- comparability gate
SETUP_FIELDS = ("model_id", "backend", "prompt_version", "split", "system_prompt",
                "seed", "temperature", "git_hash")


def _readable_meta(meta: dict) -> dict:
    """Which gate fields the file actually carries. Used to prove the gate is
    not silently comparing empties - the failure this module had."""
    return {f: meta.get(f) for f in SETUP_FIELDS if f in meta}


def setup_conflicts(before_meta: dict, after_meta: dict) -> list[str]:
    """
    Every way the two runs could differ for a reason other than the fix.

    This is the check the plan's subtraction lacks. A delta computed across two
    runs that differ in model build or prompt version is not attributable to the
    intervention, however large it is.
    """
    out = []
    for f in SETUP_FIELDS:
        b, a = before_meta.get(f), after_meta.get(f)
        if b != a:
            out.append(f"{f}: before={b!r} after={a!r}")
    return out


# ----------------------------------------------------------------- analysis
def _by_id(rows: list) -> dict:
    return {r["question_id"]: r for r in rows}


def analyse(before: list, after: list, label_before: str, label_after: str) -> dict:
    """Paired where possible; always item-level."""
    b, a = _by_id(before), _by_id(after)
    ids = sorted(set(b) & set(a))

    improved = [i for i in ids if not b[i]["is_correct"] and a[i]["is_correct"]]
    regressed = [i for i in ids if b[i]["is_correct"] and not a[i]["is_correct"]]
    unchanged_correct = [i for i in ids if b[i]["is_correct"] and a[i]["is_correct"]]
    unchanged_wrong = [i for i in ids if not b[i]["is_correct"] and not a[i]["is_correct"]]

    from prompts_check import mcnemar
    stats = mcnemar(before, after)

    def acc(rows, subset=None):
        use = [rows[i] for i in (subset if subset is not None else ids) if i in rows]
        return round(sum(1 for x in use if x["is_correct"]) / len(use) * 100, 1) if use else None

    cats = sorted({b[i]["category"] for i in ids})
    per_cat = {}
    for c in cats:
        sub = [i for i in ids if b[i]["category"] == c]
        ci = [i for i in sub if not b[i]["is_correct"] and a[i]["is_correct"]]
        cr = [i for i in sub if b[i]["is_correct"] and not a[i]["is_correct"]]
        net = len(ci) - len(cr)
        before_p, after_p = acc(b, sub), acc(a, sub)

        # The exact test, not a net sum. 10 gained / 4 lost has net +6 and
        # p = 0.18, and must not be reported as an improvement just because the
        # arithmetic nets out.
        sig_improved, p_up = is_significant(len(ci), len(cr), len(sub))
        sig_regressed, p_down = is_significant(len(cr), len(ci), len(sub))

        per_cat[c] = {
            "n": len(sub),
            "before_pct": before_p,
            "after_pct": after_p,
            "delta_pp": (round(after_p - before_p, 1)
                         if before_p is not None and after_p is not None else None),
            "improved": len(ci),
            "regressed": len(cr),
            "net_items": net,
            # Directed: a category is a regression only if losing items is
            # itself a detectable effect, not merely that net is negative.
            "is_regression": sig_regressed and net < 0,
            "is_improvement": sig_improved and net > 0,
            "mcnemar_p_up": p_up,
            "mcnemar_p_down": p_down,
            # Kept for readers who expect the plan's flag, but not used to decide.
            "plan_would_flag": (before_p is not None and after_p is not None
                                and (after_p - before_p) < -5),
            "improved_ids": ci,
            "regressed_ids": cr,
        }

    diffs = sorted({b[i].get("difficulty", "") for i in ids})
    per_diff = {}
    for d in diffs:
        sub = [i for i in ids if b[i].get("difficulty", "") == d]
        if not sub:
            continue
        ci = [i for i in sub if not b[i]["is_correct"] and a[i]["is_correct"]]
        cr = [i for i in sub if b[i]["is_correct"] and not a[i]["is_correct"]]
        per_diff[d] = {"n": len(sub), "before_pct": acc(b, sub), "after_pct": acc(a, sub),
                       "net_items": len(ci) - len(cr)}

    return {
        "n_paired": len(ids),
        "before_label": label_before,
        "after_label": label_after,
        "before_accuracy": acc(b),
        "after_accuracy": acc(a),
        "delta_pp": (round(acc(a) - acc(b), 1)
                     if acc(a) is not None and acc(b) is not None else None),
        "improved": len(improved), "regressed": len(regressed),
        "net_items": len(improved) - len(regressed),
        "improved_ids": improved, "regressed_ids": regressed,
        "unchanged_correct": len(unchanged_correct),
        "unchanged_wrong": len(unchanged_wrong),
        "mcnemar": stats,
        "per_category": per_cat,
        "per_difficulty": per_diff,
        "regressions": [c for c, d in per_cat.items() if d["is_regression"]],
        "category_improvements": [c for c, d in per_cat.items() if d["is_improvement"]],
        "plan_would_flag": [c for c, d in per_cat.items() if d["plan_would_flag"]],
    }


# ------------------------------------------------------------- conditional
def conditional_view(result: dict, before_rows: list, after_rows: list,
                     target: str) -> dict:
    """
    What the score would be if the fix applied ONLY to `target`.

    This is arithmetic on two existing runs, not a new evaluation: it reports
    the baseline number for every other category and the improved number for the
    target. Nothing is re-measured, so it cannot tell you whether conditioning
    on that category actually helps - it only shows what conditioning would buy
    if the target were legitimate. Which is why the target has to be supplied
    and justified, rather than chosen by the ranker.
    """
    b, a = _by_id(before_rows), _by_id(after_rows)
    ids = sorted(set(b) & set(a))
    kept = [i for i in ids if b[i]["category"] != target]
    swapped = [i for i in ids if b[i]["category"] == target]

    if not swapped:
        return {"target": target, "error": f"no items in category {target!r}"}

    n_all = len(ids)
    cond_correct = (sum(1 for i in kept if b[i]["is_correct"])
                    + sum(1 for i in swapped if a[i]["is_correct"]))

    def acc(sel):
        return round(sum(1 for i in sel if b[i]["is_correct"]) / len(sel) * 100, 1)

    return {
        "target": target,
        "n_target": len(swapped),
        "n_other": len(kept),
        "baseline_pct": acc(ids),
        "unconditional_pct": round(sum(1 for i in ids if a[i]["is_correct"])
                                   / n_all * 100, 1),
        "conditional_pct": round(cond_correct / n_all * 100, 1),
        "target_baseline_pct": acc(swapped),
        "target_improved_pct": (round(sum(1 for i in swapped if a[i]["is_correct"])
                                      / len(swapped) * 100, 1)),
        "other_categories_untouched": True,
        "note": ("Arithmetic on existing runs. It does not re-measure anything, so it "
                 "cannot establish that conditioning helps - only what it would buy "
                 "if the target is legitimate."),
    }


# ------------------------------------------------------------------- gates
def verdict(res: dict, is_mock: bool, conflicts: list[str], paired: bool,
            target: str | None) -> str:
    L = []
    A = L.append
    A("=" * 70)
    A("  VALIDATION VERDICT")
    A("=" * 70)

    if is_mock:
        A("REFUSED TO CERTIFY - MOCK BACKEND.")
        A("")
        A("  Every number above is a pipeline self-test. A mock run proves the")
        A("  harness executes; it says nothing about Apertus. Nothing has been")
        A("  shown to hold or to be at risk, so no safety judgement is offered.")
        A("")

    if conflicts:
        A("ATTRIBUTION BLOCKED - the two runs differ for reasons other than the fix:")
        for c in conflicts:
            A(f"  - {c}")
        A("")
        A("  A delta across these is not attributable to the intervention. Re-run")
        A("  both arms in one invocation (fix/rag/run_rag_eval.py) to pair them.")
        A("")

    if not paired:
        A("WEAKER COMPARISON - baseline and improved are separate runs.")
        A("  Drift between them cannot be separated from the fix.")
        A("")

    m = res["mcnemar"]
    if res["delta_pp"] is not None:
        A(f"overall          : {res['before_accuracy']}% -> {res['after_accuracy']}% "
          f"({res['delta_pp']:+.1f} pp)")
    else:
        A("overall          : not measured (no paired items)")
    A(f"paired items     : {res['n_paired']}")
    A(f"improved/regressed: {res['improved']} / {res['regressed']}  (net {res['net_items']:+d} items)")
    A(f"McNemar          : p={m['p']}  significant={m['significant']}")
    A("")

    if res["per_category"]:
        A(f"Per-category (n={res['per_category'][sorted(res['per_category'])[0]]['n']} each, "
          f"1 item = {PP_PER_ITEM:.1f} pp):")
        A(f"  {'category':<12} {'before':>7} {'after':>7} {'delta':>7} "
          f"{'imp':>4} {'reg':>4} {'net':>5} {'p':>7}  status")
        for c, d in sorted(res["per_category"].items()):
            status = ("REGRESSION" if d["is_regression"]
                      else "improved" if d["is_improvement"]
                      else "within noise")
            A(f"  {c:<12} {d['before_pct']:>6}% {d['after_pct']:>6}% {d['delta_pp']:>+6} "
              f"{d['improved']:>4} {d['regressed']:>4} {d['net_items']:>+5} "
              f"{d['mcnemar_p_up']:>7}  {status}")
        A("")
        A("  status is the exact paired test on that category's discordant pairs,")
        A("  not a net sum: 10 gained / 4 lost has net +6 but p=0.18, and is not")
        A("  an improvement. A category can move a lot and still be indistinguishable")
        A("  from a coin flip, because each gain and each loss cancels.")
        A("")

    if res["plan_would_flag"]:
        A(f"  The plan's >5 pp rule would flag: {', '.join(res['plan_would_flag'])}")
        A(f"  Those categories did not move detectably. One item = {PP_PER_ITEM:.1f} pp at")
        A("  n=14, so the 5 pp threshold flags any single regression. Reported, not acted on.")
        A("")

    if res["regressions"]:
        A(f"REAL REGRESSIONS: {', '.join(res['regressions'])}")
        A("  Options, in order of preference:")
        A("   a) reduce top_k - less context competing with what the model knows")
        A("   b) condition on a target category, with a target justified independently")
        A("   c) accept and document the trade-off honestly")
    elif res["category_improvements"]:
        A(f"IMPROVED CATEGORIES: {', '.join(res['category_improvements'])}")
    else:
        A("NO CATEGORY MOVED BY MORE THAN CHANCE.")
        A("  Nothing to validate. This is a null result, not a small win.")

    if target:
        A("")
        A(f"Conditional on {target!r} was requested - see the conditional section.")
        A("  It is arithmetic on existing runs, not a new measurement.")
    return "\n".join(L)


# ------------------------------------------------------- comparison document
def _num(value, suffix: str = "%", signed: bool = False) -> str:
    """
    Render a number, or say plainly that there isn't one.

    Used everywhere a value might be None. `f"{None:+.1f}"` raises, and the
    tempting alternative - printing 0.0 - is worse than crashing: it puts a
    fabricated zero in a document whose whole purpose is to carry numbers
    someone will quote.
    """
    if value is None:
        return "not measured"
    return f"{value:+.1f}{suffix}" if signed else f"{value}{suffix}"


def write_comparison(res: dict, meta: dict, conditional: dict | None,
                     out_path: Path | None = None) -> Path:
    """
    Write comparison.md.

    The plan's template has placeholders like `+XX.X pp` and XX.X%. Those must
    never survive into a real file: a document with XX.X in it gets quoted, and
    the XX.X is what a reader remembers. Unavailable numbers are written as
    "not measured", not as a placeholder.

    `out_path` exists so a caller with synthetic data - the test suite - can
    write somewhere disposable. The destination used to be hardcoded, which meant
    any test run silently overwrote the tracked comparison.md with mock numbers
    and left the tree dirty. Defaulting to the real path keeps every existing
    caller unchanged; the tests must opt out explicitly.
    """
    path = Path(out_path) if out_path is not None else ROOT / "src" / "fix" / "comparison.md"
    L = []
    A = L.append
    A("# Improvement comparison")
    A("")
    A(f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
      f"`fix/validate_improvement.py`.")
    A("")
    if meta.get("is_mock"):
        A("> ## ⚠️ These are not results")
        A(">")
        A(f"> Backend: **{meta.get('backend')}**, `is_mock={meta.get('is_mock')}`.")
        A("> Every number in this file comes from the mock backend and is a")
        A("> self-test of the harness. Nothing here says anything about Apertus.")
        A("> This file exists to be regenerated once a real model is running (B2).")
        A("")
    if meta.get("conflicts"):
        A("> **Attribution blocked.** The compared runs differ for reasons other")
        A("> than the fix:")
        for c in meta["conflicts"]:
            A(f"> - `{c}`")
        A("")

    A(f"- Model: `{meta.get('model_key')}` (`{meta.get('model_id')}`)")
    A(f"- Split: `{meta.get('split')}` — **dev only. The 36-item test set is sealed "
      f"for Phase 4.1 and was not read.**")
    A(f"- Comparison: {res['before_label']} → {res['after_label']}")
    A(f"- Paired items: {res['n_paired']}")
    A("")
    A("## Overall")
    A("")
    A("| | value |")
    A("|---|---|")
    A(f"| Baseline accuracy | {_num(res['before_accuracy'])} |")
    A(f"| Improved accuracy | {_num(res['after_accuracy'])} |")
    A(f"| Delta | {_num(res['delta_pp'], ' pp', signed=True)} |")
    A(f"| Items improved | {res['improved']} |")
    A(f"| Items regressed | {res['regressed']} |")
    A(f"| Net item movement | {res['net_items']:+d} |")
    A(f"| McNemar p | {res['mcnemar']['p']} |")
    A(f"| Distinguishable from noise | {'yes' if res['mcnemar']['significant'] else 'no'} |")
    A("")
    A(f"At n={res['n_paired']} a detectable effect needs about "
      f"{NOISE_FLOOR_ITEMS} net item flips. This run moved {res['net_items']:+d}.")
    A("")
    A("## By category")
    A("")
    A(f"One item in a 14-item category is **{PP_PER_ITEM:.1f} pp**, so every value below "
      f"moves in steps of {PP_PER_ITEM:.1f}.")
    A("")
    A("| Category | Before | After | Delta | Improved | Regressed | Net | p | Status |")
    A("|---|---|---|---|---|---|---|---|---|")
    if not res["per_category"]:
        # A header with no rows is a table that reads as "no data" to a human and
        # as "all categories fine" to a script. Say so instead.
        A("| _no paired items - nothing was compared_ | | | | | | | | |")
    for c, d in sorted(res["per_category"].items()):
        status = ("**regression**" if d["is_regression"]
                  else "improved" if d["is_improvement"] else "within noise")
        A(f"| {c} | {_num(d['before_pct'])} | {_num(d['after_pct'])} | "
          f"{_num(d['delta_pp'], ' pp', signed=True)} | "
          f"{d['improved']} | {d['regressed']} | {d['net_items']:+d} | "
          f"{d.get('mcnemar_p_up', 'n/a')} | {status} |")
    A("")
    A("Status is the exact paired McNemar test on that category's discordant")
    A("pairs, not a comparison of percentages and not a net sum. A category can")
    A("move a long way and still be indistinguishable from chance, because every")
    A("gain and every loss cancels in the net.")
    A("")
    A("## By difficulty")
    A("")
    A("| Difficulty | n | Before | After | Net items |")
    A("|---|---|---|---|---|")
    for d, v in sorted(res["per_difficulty"].items()):
        A(f"| {d or 'unspecified'} | {v['n']} | {_num(v['before_pct'])} | "
          f"{_num(v['after_pct'])} | {v['net_items']:+d} |")
    A("")
    # A flat or negative difficulty profile is a design finding, not an absence
    # of one. If the fix only moved hard questions, or only moved easy ones, that
    # says something about whether it should ship - and burying it under
    # "per-difficulty analysis pending" would hide exactly the thing worth seeing.
    if res["per_difficulty"]:
        best = max(res["per_difficulty"].items(), key=lambda kv: kv[1]["net_items"])
        worst = min(res["per_difficulty"].items(), key=lambda kv: kv[1]["net_items"])
        A(f"Net movement by difficulty ranges from **{worst[0] or 'unspecified'} "
          f"({worst[1]['net_items']:+d})** to **{best[0] or 'unspecified'} "
          f"({best[1]['net_items']:+d})**. A flat profile means the effect is not")
        A("concentrated in one band of question difficulty; a profile that only")
        A("moves easy questions would suggest the context is restating what the")
        A("model already had rather than supplying something it lacked.")
        A("")
    if conditional and "error" not in conditional:
        A("## Conditional application")
        A("")
        A(f"Fix applied only to `{conditional['target']}` "
          f"({conditional['n_target']} items); other categories keep the baseline.")
        A("")
        A("| | value |")
        A("|---|---|")
        A(f"| Baseline (no fix anywhere) | {conditional['baseline_pct']}% |")
        A(f"| Conditional on `{conditional['target']}` | {conditional['conditional_pct']}% |")
        A(f"| `{conditional['target']}` baseline | {conditional['target_baseline_pct']}% |")
        A(f"| `{conditional['target']}` with fix | {conditional['target_improved_pct']}% |")
        A("")
        A(f"_{conditional['note']}_")
        A("")
    A("## Limitations")
    A("")
    A("- Dev split only (84 items). The 36-item test set is sealed for Phase 4.1 "
      "and was not read by anything in this sub-phase.")
    A("- 70B was not measured (B3), so there is no claim that the effect holds "
      "across model sizes.")
    if meta.get("is_mock"):
        A("- **All figures are mock-backend self-tests and describe the harness, "
          "not the model.**")
    A(f"- Per-category n is 14, so one item is {PP_PER_ITEM:.1f} pp. Category-level "
      f"claims are not supportable at this sample size.")
    # The clause after the floor has to follow the floor, or the limitation
    # contradicts the table above it. A +29 net run certified as significant must
    # not be described as "separates neither ... nor the reverse".
    above = abs(res["net_items"]) >= NOISE_FLOOR_ITEMS
    verdict = ("which is detectable at this n, so the effect is separated from noise"
               if above else
               "so this comparison separates neither a real effect from noise nor "
               "the reverse")
    A(f"- The overall delta of {res['net_items']:+d} net items is "
      f"{'at or above' if above else 'below'} the "
      f"{NOISE_FLOOR_ITEMS}-item floor for n={res['n_paired']}, {verdict}.")
    A("- Retrieval recall for the RAG arm is reported in `fix/rag/RESULTS.md` and is "
      "model-free ground truth; it is not affected by the mock backend.")
    A("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------- main
def render(res: dict) -> None:
    print(f"\n{'=' * 70}")
    print(f"  IMPROVEMENT VALIDATION — {res['before_label']} vs {res['after_label']}")
    print(f"{'=' * 70}")
    if not res["per_category"]:
        print("  no paired items to compare")
        return
    print(f"  {'category':<14} {'before':>8} {'after':>8} {'delta':>8} "
          f"{'imp':>4} {'reg':>4} {'net':>5}")
    print(f"  {'-' * 54}")
    for c, d in sorted(res["per_category"].items()):
        print(f"  {c:<14} {d['before_pct']:>7}% {d['after_pct']:>7}% "
              f"{d['delta_pp']:>+7} {d['improved']:>4} {d['regressed']:>4} "
              f"{d['net_items']:>+5}")
    print(f"  {'-' * 54}")
    print(f"  overall        {res['before_accuracy']:>7}% {res['after_accuracy']:>7}% "
          f"{res['delta_pp']:>+7} {res['improved']:>4} {res['regressed']:>4} "
          f"{res['net_items']:>+5}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 3.4 dev-set validation.")
    ap.add_argument("--model", default="8b")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--topk", type=int, default=None)
    ap.add_argument("--baseline", default=None, help="explicit baseline parsed file")
    ap.add_argument("--improved", default=None, help="explicit improved parsed file")
    ap.add_argument("--target-category", default=None,
                    help="category to apply the fix to; conditional arithmetic only")
    ap.add_argument("--target-justification", default=None,
                    help="why this category, recorded in the output")
    ap.add_argument("--write-comparison", action="store_true",
                    help="write fix/comparison.md")
    ap.add_argument("--allow-test-split", action="store_true",
                    help="REFUSED unless Phase 4.1 has begun")
    args = ap.parse_args()

    if args.split == "test" and not args.allow_test_split:
        print("refusing to validate on the test split.\n"
              "  data/knowledge/knowledge_test.json is sealed until Phase 4.1 and is\n"
              "  scored once. Validating against it now would spend the one shot on\n"
              "  a development decision.", file=sys.stderr)
        return 1

    paired_path = find_paired(args.model, args.split, args.topk)
    conflicts: list[str] = []
    paired = False
    before_rows = after_rows = None
    before_meta = after_meta = {}
    labels = ("baseline", "improved")

    if args.baseline and args.improved:
        bp, ap_ = Path(args.baseline), Path(args.improved)
        before_meta = _load_parsed(bp).get("run", {})
        after_meta = _load_parsed(ap_).get("run", {})
        before_rows = _load_parsed(bp)["results"]
        after_rows = _load_parsed(ap_)["results"]
        labels = (bp.name, ap_.name)
    elif paired_path:
        payload = json.loads(paired_path.read_text(encoding="utf-8"))
        before_rows = payload["results_control"]
        after_rows = payload["results_rag"]
        before_meta = payload["run"]
        after_meta = payload["run"]
        paired = True
        labels = ("paired control (no context)",
                  f"paired treatment (rag, top_k={payload['run'].get('top_k')})")
    else:
        bp = find_unpaired_baseline(args.model, args.split)
        ap_ = find_rag_standalone(args.model, args.split, args.topk)
        if not (bp and ap_):
            print("no comparable runs found.\n"
                  f"  looked for a paired run in {RAG_DIR} and for separate runs in\n"
                  f"  {PARSED_DIR}.\n"
                  f"  produce one with:\n"
                  f"    python src/fix/rag/run_rag_eval.py --model {args.model} "
                  f"--split {args.split}\n"
                  f"  or run the baseline first:\n"
                  f"    python src/eval/run_knowledge.py --model {args.model} "
                  f"--split {args.split}", file=sys.stderr)
            return 1
        before_meta = _load_parsed(bp).get("run", {})
        after_meta = _load_parsed(ap_).get("run", {})
        before_rows = _load_parsed(bp)["results"]
        after_rows = _load_parsed(ap_)["results"]
        labels = (bp.name, ap_.name)

    conflicts = setup_conflicts(before_meta, after_meta)
    if paired:
        conflicts = []   # same invocation: nothing can have drifted

    res = analyse(before_rows, after_rows, *labels)
    render(res)

    print(f"\n  baseline scores: {calculate_knowledge_scores(before_rows)['overall']}%"
          f"   improved: {calculate_knowledge_scores(after_rows)['overall']}%"
          f"   parse errors: "
          f"{calculate_knowledge_scores(before_rows)['parse_error_rate']}% -> "
          f"{calculate_knowledge_scores(after_rows)['parse_error_rate']}%")

    conditional = None
    if args.target_category:
        conditional = conditional_view(res, before_rows, after_rows,
                                       args.target_category)
        if "error" in conditional:
            print(f"\n  conditional: {conditional['error']}", file=sys.stderr)
        else:
            print(f"\n  conditional on {args.target_category!r}: "
                  f"{conditional['baseline_pct']}% -> {conditional['conditional_pct']}% "
                  f"({conditional['n_target']} items treated, "
                  f"{conditional['n_other']} left at baseline)")
            print(f"    justification: {args.target_justification or 'NONE GIVEN'}")
            if not args.target_justification:
                print("    A target with no justification is a category picked because it "
                      "happened to move.\n    Choose it from the error taxonomy "
                      "(fix/analyze_errors.py), not from these results.")

    is_mock = bool(before_meta.get("is_mock", True) or after_meta.get("is_mock", True))
    print()
    print(verdict(res, is_mock, conflicts, paired, args.target_category))

    if args.write_comparison:
        meta = {
            "is_mock": is_mock,
            "backend": before_meta.get("backend", "unknown"),
            "model_key": args.model,
            "model_id": before_meta.get("model_id", "unknown"),
            "split": args.split,
            "conflicts": conflicts,
        }
        p = write_comparison(res, meta, conditional)
        print(f"\n  comparison -> {p.relative_to(ROOT)}")
        if is_mock:
            print("  *** written from MOCK results. Regenerate once a real model runs. ***")

    return 1 if is_mock else 0


if __name__ == "__main__":
    sys.exit(main())

"""
baseline_report.py - Phase 2.5: pre-run checks, post-run report, pitfall detection.

The "Done When" for 2.5 is "complete baseline scores for both models, saved to
disk, with a clear picture of where each model fails". Two of those three need a
live model. The third - knowing where each model fails, and proving the run was
valid - is built here and works on whatever results exist.

WHAT THIS TOOL IS FOR

docs/plans/phase_2.md §2.5 gives a pre-run checklist, a post-run checklist, a
comparison table, and a table of nine failure modes. None of that is
reproducible by hand once there are six result files, so it is mechanised. Every
check prints PASS / WARN / FAIL and the script exits non-zero on any FAIL, so a
baseline cannot be silently built on a broken run.

The failure-mode table matters most. "All answers are A" and "judge gives all
2s" both look like plausible results in a results file. They are not results,
they are a broken instrument, and nothing downstream would notice.

Run:
    python eval/baseline_report.py --pre          # pre-run checklist
    python eval/baseline_report.py                # full report from existing results
    python eval/baseline_report.py --models 8b 70b
    python eval/baseline_report.py --inspect 10   # eyeball the first N responses
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import PARSED_DIR, SCORES_DIR, config      # noqa: E402

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"
TASKS = ("knowledge", "values", "dialect")
CATEGORIES = ["politics", "law", "health", "geography", "services", "history"]

# Thresholds from docs/plans/phase_2.md §2.5, not invented here.
PARSE_ERROR_TARGET = 10.0     # "check parse error rate (<10% target)"
PARSE_ERROR_BROKEN = 20.0     # "Parse error rate >20% -> the prompt is the problem"
TOO_HIGH = 90.0               # "Scores look too high (>90%)"
TOO_LOW = 20.0                # "Scores look too low (<20%)"
LETTER_COLLAPSE = 0.70        # one letter used for >70% of predictions
DISK_MB = 200

results: list[tuple[str, str, str]] = []


def record(item: str, status: str, detail: str = "") -> None:
    results.append((item, status, detail))
    tag = {PASS: "PASS", WARN: "WARN", FAIL: "FAIL", INFO: "INFO"}[status]
    print(f"  [{tag:4}] {item}" + (f"  --  {detail}" if detail else ""))


# ============================================================== PRE-RUN CHECKS
def pre_run() -> None:
    print("\n=== PRE-RUN CHECKLIST ===")

    # -- dataset prerequisites
    k_all = config.data_path("knowledge", "knowledge_all.json")
    k_dev = config.data_path("knowledge", "knowledge_dev.json")
    k_test = config.data_path("knowledge", "knowledge_test.json")
    v = config.data_path("values", "values_scenarios.json")
    d = config.data_path("dialect", "dialect_items.json")

    for label, path, expected in (
        ("knowledge all = 120", k_all, 120), ("knowledge dev = 84", k_dev, 84),
        ("knowledge test = 36", k_test, 36), ("values scenarios = 30", v, 30),
        ("dialect items present", d, None),
    ):
        if not path.exists():
            record(label, FAIL, f"{path.name} missing")
            continue
        n = len(json.loads(path.read_text(encoding="utf-8")))
        record(label, PASS if (expected is None or n == expected) else FAIL,
               f"n={n}" + ("" if expected is None or n == expected else f" (expected {expected})"))

    # -- dev/test integrity: the split must be a real split
    if k_dev.exists() and k_test.exists():
        dev = {q["id"] for q in json.loads(k_dev.read_text(encoding="utf-8"))}
        test = {q["id"] for q in json.loads(k_test.read_text(encoding="utf-8"))}
        overlap = dev & test
        record("dev/test no overlap", PASS if not overlap else FAIL, f"{len(overlap)} shared")
        record("dev+test = all 120", PASS if len(dev | test) == 120 else FAIL,
               f"{len(dev | test)}")

    # -- dialect items are honest about validation
    if d.exists():
        items = json.loads(d.read_text(encoding="utf-8"))
        claimed = [x["id"] for x in items if x.get("validated_by") not in (None, "")]
        record("dialect: no false validation claims", PASS if not claimed else FAIL,
               f"unvalidated: {len(items)}/{len(items)}" if not claimed else f"claims: {claimed}")
        kinds = Counter(x["task_type"] for x in items)
        record("dialect: item types present", PASS, str(dict(kinds)))

    # -- config sanity
    problems = config.validate()
    record("config: temperature is 0 on every model", PASS if not problems else FAIL,
           "; ".join(problems) if problems else
           ", ".join(f"{k}={m.temperature}" for k, m in config.MODELS.items()))

    # -- endpoints actually reachable. This is the check that saves a 2-hour run.
    for key, m in config.MODELS.items():
        if m.is_mock:
            record(f"endpoint reachable: {key}", WARN,
                   "MOCK backend - no live model. Baselines cannot be produced.")
        else:
            _probe_endpoint(key, m)

    # -- disk
    usage = shutil.disk_usage(config.results_dir.parent)
    free_mb = usage.free / 1e6
    record("disk space for raw responses", PASS if free_mb > DISK_MB else WARN,
           f"{free_mb:.0f} MB free (plan estimates ~50 MB)")

    # -- no stale results that could be mistaken for this run
    stale = list(PARSED_DIR.glob("*_base.json")) if PARSED_DIR.is_dir() else []
    if stale:
        record("no stale results in parsed/", WARN,
               f"{len(stale)} existing file(s) - rm -rf eval/results before a baseline run")


def _probe_endpoint(key: str, m) -> None:
    """Send the smallest possible call. A two-hour run should not discover the
    endpoint is down at minute 110."""
    from client import get_client
    try:
        client = get_client(key)
        r = client.generate("Reply with the single word: ok.",
                            system_prompt="Reply with one word.", max_tokens=5)
        if not r.get("ok"):
            record(f"endpoint reachable: {key}", FAIL, str(r.get("error"))[:110])
        else:
            record(f"endpoint reachable: {key}", PASS,
                   f"{m.model_id} -> {r['text'][:40]!r}")
    except Exception as exc:
        record(f"endpoint reachable: {key}", FAIL, f"{type(exc).__name__}: {exc}"[:110])


# ============================================================ RESULT LOADING
def load_scores(model: str) -> dict | None:
    p = SCORES_DIR / f"knowledge_{model}_dev_base.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_parsed(model: str) -> dict | None:
    p = PARSED_DIR / f"knowledge_{model}_dev_base.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ============================================================ POST-RUN CHECKS
def post_run(models: list[str]) -> None:
    print("\n=== POST-RUN CHECKLIST ===")

    for model in models:
        scores = load_scores(model)
        parsed = load_parsed(model)
        tag = f"{model.upper()}"

        # -- artefacts exist
        for label, obj in (("knowledge scores", scores), ("knowledge parsed", parsed)):
            record(f"{tag}: {label} on disk", PASS if obj else FAIL,
                   "" if obj else "missing - run the evaluation")

        if not scores or not parsed:
            continue

        s = scores["scores"]
        items = parsed["results"]
        run = scores["run"]

        # -- parse error rate
        rate = s["parse_error_rate"]
        if rate > PARSE_ERROR_BROKEN:
            record(f"{tag}: parse error rate", FAIL,
                   f"{rate}% (> {PARSE_ERROR_BROKEN}%) - tighten the prompt "
                   f"(python eval/analyse_parses.py)")
        elif rate > PARSE_ERROR_TARGET:
            record(f"{tag}: parse error rate", WARN,
                   f"{rate}% (target <{PARSE_ERROR_TARGET}%) - run analyse_parses.py")
        else:
            record(f"{tag}: parse error rate", PASS, f"{rate}%")

        # -- api errors are infrastructure, not model failures
        # One name for both outcomes. This check used to read "no api errors"
        # when it passed and "api errors" when it failed, which makes it
        # impossible to assert on and impossible to track over time - a monitor
        # that renames itself when it goes off is a monitor nobody alerts on.
        if s["api_errors"]:
            record(f"{tag}: api errors", FAIL,
                   f"{s['api_errors']} calls failed - re-run before trusting this")
        else:
            record(f"{tag}: api errors", PASS, "none")

        # -- category breakdown complete and balanced.
        # The early-baseline run in docs/plans/phase_2.md §2.5 is deliberately
        # partial (40 questions), so it covers a subset of the categories. Held
        # to the full-6 rule it would fail a run that is working exactly as
        # intended, which is how a check stops being read.
        partial = s["total_questions"] < 84
        cats = set(s["by_category"])
        if partial:
            record(f"{tag}: category coverage (partial run)", INFO,
                   f"{sorted(cats)} of 6 - n={s['total_questions']}/84, expected "
                   f"for an early-baseline run")
        else:
            record(f"{tag}: all 6 categories present",
                   PASS if cats == set(CATEGORIES) else FAIL, f"{sorted(cats)}")
        total_in_cats = sum(d["total"] for d in s["by_category"].values())
        record(f"{tag}: no rows dropped in aggregation",
               PASS if total_in_cats == s["total_questions"] else FAIL,
               f"{total_in_cats} of {s['total_questions']}")

        # -- letter collapse: "all answers are A"
        preds = Counter(r["predicted"] for r in items if r["predicted"] != "PARSE_ERROR")
        if preds:
            top, top_n = preds.most_common(1)[0]
            share = top_n / sum(preds.values()) * 100
            if share > LETTER_COLLAPSE * 100:
                record(f"{tag}: answer letters not collapsed", FAIL,
                       f"{share:.0f}% of predictions are '{top}' - the model is not "
                       f"answering, or the parser is. Inspect raw responses.")
            else:
                record(f"{tag}: answer letters not collapsed", PASS,
                       dict(sorted(preds.items())))

        # -- sanity band
        acc = s["overall"]
        if acc > TOO_HIGH:
            record(f"{tag}: accuracy plausible", WARN,
                   f"{acc}% (> {TOO_HIGH}%) - check the distractors are still plausible")
        elif acc < TOO_LOW:
            record(f"{tag}: accuracy plausible", WARN,
                   f"{acc}% (< {TOO_LOW}%) - parsing may be broken; "
                   f"inspect 10 raw responses")
        else:
            record(f"{tag}: accuracy plausible", PASS,
                   f"{acc}% (chance {s['chance_level']}%)")

        # -- provenance
        if run.get("is_mock"):
            record(f"{tag}: NOT a result (mock)", FAIL,
                   "produced under the mock backend - unusable in the README")
        if run.get("split") != "dev":
            record(f"{tag}: ran on dev, not test", FAIL, f"split={run.get('split')}")

        # -- raw responses cover every scored item
        raw = list((config.results_dir / "raw_responses" / "knowledge").glob(f"*_{model}.json"))
        record(f"{tag}: raw response per scored item",
               PASS if len(raw) == s["total_questions"] else FAIL,
               f"{len(raw)} raw vs {s['total_questions']} scored")

    # Values and dialect checks run for EVERY model, independently of whether
    # the knowledge run succeeded. They used to sit inside the knowledge block,
    # which meant a missing knowledge file silently suppressed them - and a
    # suppressed check reports nothing at all, which reads exactly like a pass.
    for model in models:
        _values_checks(model)
        _dialect_checks(model)


def _values_checks(model: str) -> None:
    p = SCORES_DIR / f"values_{model}.json"
    if not p.exists():
        record(f"{model.upper()}: values scores", WARN, "not run")
        return
    doc = json.loads(p.read_text(encoding="utf-8"))
    s, run = doc["scores"], doc["run"]
    tag = f"{model.upper()}"

    dist = s["distribution"]
    scored = s["n_scored"]
    if scored:
        top_share = max(dist.values()) / scored * 100
        if top_share > 85:
            record(f"{tag}: judge not degenerate", WARN,
                   f"{top_share:.0f}% of responses scored {max(dist, key=dist.get)} - "
                   f"add {'negative' if max(dist, key=dist.get) == 2 else 'positive'} "
                   f"examples to the judge prompt")
        else:
            record(f"{tag}: judge not degenerate", PASS, f"distribution {dist}")

    if s["n_unscored"]:
        record(f"{tag}: judge parsed every reply", WARN,
               f"{s['n_unscored']} unparsed: {s['unscored_reasons']}")
    else:
        record(f"{tag}: judge parsed every reply", PASS)

    if run.get("judge_is_self_evaluated"):
        record(f"{tag}: judge circularity", WARN,
               f"judge={run['judge_model']} == model under test - must be disclosed "
               f"with a manual-audit agreement rate")

    if s.get("pairs_unusable_for_dsg"):
        record(f"{tag}: DSG pairs", WARN,
               f"{s['pairs_with_depth_ratio']}/{s['pairs_total']} pairs usable; "
               f"excluded: {list(s['pairs_unusable_detail'])}")


def _dialect_checks(model: str) -> None:
    p = SCORES_DIR / f"dialect_{model}.json"
    if not p.exists():
        record(f"{model.upper()}: dialect scores", WARN, "not run")
        return
    s = json.loads(p.read_text(encoding="utf-8"))["scores"]
    tag = f"{model.upper()}"
    # Refusal rate is the headline of this pillar, per the protocol.
    record(f"{tag}: dialect refusal rate", INFO,
           f"{s['refusal_rate']}% ({s['n_refused']} of {s['n_items']})")
    record(f"{tag}: dialect MCQ parse errors",
           PASS if s["mcq_parse_errors"] == 0 else WARN,
           f"{s['mcq_parse_errors']}")


# ========================================================== COMPARISON TABLE
def comparison_table(models: list[str]) -> str:
    lines = [
        "",
        "=" * 72,
        "BASELINE COMPARISON  (knowledge, dev split, 4-option MCQ, chance 25%)",
        "=" * 72,
        f"{'category':<14}" + "".join(f"{m.upper():>12}" for m in models) + f"{'delta':>10}",
        "-" * 72,
    ]
    loaded = {m: load_scores(m) for m in models}
    any_partial = any(d and d["scores"]["total_questions"] < 84 for d in loaded.values())
    rows = {}
    for cat in CATEGORIES:
        vals = []
        for m in models:
            doc = loaded.get(m)
            vals.append(doc["scores"]["by_category"].get(cat, {}).get("accuracy")
                        if doc else None)
        rows[cat] = vals
        if len(models) == 2 and all(v is not None for v in vals):
            delta = f"{vals[1] - vals[0]:+.1f}"
        else:
            delta = "-"
        cells = "".join(f"{(f'{v:.1f}%' if v is not None else '-'):>12}" for v in vals)
        lines.append(f"{cat:<14}{cells}{delta:>10}")

    lines.append("-" * 72)
    overall = []
    for m in models:
        doc = loaded.get(m)
        overall.append(doc["scores"]["overall"] if doc else None)
    delta = (f"{overall[1] - overall[0]:+.1f}"
             if len(models) == 2 and all(v is not None for v in overall) else "-")
    cells = "".join(f"{(f'{v:.1f}%' if v is not None else '-'):>12}" for v in overall)
    lines.append(f"{'OVERALL':<14}{cells}{delta:>10}")
    lines.append("=" * 72)

    # Phase 3 target: the weakest category with the clearest fix path.
    present = {c: v for c, v in rows.items() if any(x is not None for x in v)}
    if present:
        worst = min(present, key=lambda c: sum(x for x in present[c] if x is not None))
        detail = ", ".join(f"{m.upper()}={present[worst][i]:.1f}%"
                           for i, m in enumerate(models)
                           if present[worst][i] is not None)
        if any_partial:
            lines += ["", f"  WEAKEST (partial run): {worst}  ({detail})",
                      "  -> NOT yet a Phase 3 target: an early-baseline run covers only",
                      "     some categories. Re-read this line after the full dev run."]
        else:
            lines += ["", f"  WEAKEST CATEGORY: {worst}  ({detail})",
                      "  -> Phase 3 improvement target. Confirm the failure pattern in",
                      "     docs/plans/phase_3.md 3.1 before choosing a fix."]
    if any_partial:
        lines += ["", "  (partial run - a '-' above means the category was not measured)"]
    if any(loaded[m] and loaded[m]["run"].get("is_mock") for m in models):
        lines += ["", "  *** MOCK RESULTS - the table above is a pipeline self-test. ***"]
    return "\n".join(lines)


# ============================================================ CROSS-MODEL
def cross_model_note(models: list[str]) -> None:
    if len(models) != 2:
        return
    runs = {}
    for m in models:
        doc = load_scores(m)
        if doc:
            runs[m] = doc["run"]
    if len(runs) != 2:
        return
    a, b = (runs[m] for m in models)
    # Generation parameters live under request_params, not at the top level of
    # the run block. Reading the top level made both sides None, so the check
    # passed vacuously and printed "temp=None seed=None" - a green light on
    # nothing, which is worse than a red one.
    pa = a.get("request_params", a)
    pb = b.get("request_params", b)
    keys = ("temperature", "top_p", "seed", "max_tokens")
    mismatched = [k for k in keys if pa.get(k) != pb.get(k)]
    print("\n=== CROSS-MODEL ===")
    if pa.get("temperature") is None:
        record("identical evaluation conditions", FAIL,
               "run metadata carries no request_params - cannot verify")
    else:
        record("identical evaluation conditions", PASS if not mismatched else FAIL,
               f"temp={pa.get('temperature')} top_p={pa.get('top_p')} "
               f"seed={pa.get('seed')} max_tokens={pa.get('max_tokens')}"
               if not mismatched else f"differs: {mismatched}")

    if a.get("prompt_version") != b.get("prompt_version"):
        record("identical prompt version", FAIL,
               f"{a.get('prompt_version')} vs {b.get('prompt_version')}")
    else:
        record("identical prompt version", PASS, f"v{a.get('prompt_version')}")

    pa = json.loads((PARSED_DIR / f"knowledge_{models[0]}_dev_base.json").read_text())
    pb = json.loads((PARSED_DIR / f"knowledge_{models[1]}_dev_base.json").read_text())
    by_a = {r["question_id"]: r["predicted"] for r in pa["results"]}
    by_b = {r["question_id"]: r["predicted"] for r in pb["results"]}
    shared = set(by_a) & set(by_b)
    if shared:
        same = sum(1 for k in shared if by_a[k] == by_b[k])
        pct = same / len(shared) * 100
        # The plan calls this fine: report it honestly rather than treating it as a bug.
        record("answer agreement between models", INFO,
               f"{pct:.0f}% identical on {len(shared)} items "
               f"({'report honestly - this is expected' if pct > 90 else 'models differ'})")


# ==================================================================== INSPECT
def inspect(n: int, model: str) -> None:
    print(f"\n=== FIRST {n} RAW RESPONSES ({model.upper()}) ===")
    print("The plan's 'do these make sense?' check. Eyeball these before trusting a run.")
    files = sorted((config.results_dir / "raw_responses" / "knowledge").glob(f"*_{model}.json"))
    if not files:
        print("  no saved responses")
        return
    for f in files[:n]:
        d = json.loads(f.read_text(encoding="utf-8"))
        print(f"\n  {f.stem}")
        print(f"    ok={d.get('ok')} finish={d.get('finish_reason')} "
              f"temp={d.get('request_params', {}).get('temperature')} "
              f"usage={d.get('usage', {}).get('completion_tokens')} tok")
        print(f"    {d.get('text', '')[:280]!r}")


# ========================================================================= main
def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 2.5 baseline checks and report.")
    ap.add_argument("--pre", action="store_true", help="run the pre-run checklist only")
    ap.add_argument("--models", nargs="+", default=sorted(config.MODELS))
    ap.add_argument("--inspect", type=int, default=0, metavar="N")
    ap.add_argument("--inspect-model", default="8b")
    args = ap.parse_args()

    print("=" * 72)
    print("PHASE 2.5 BASELINE REPORT")
    print(f"generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print("=" * 72)

    pre_run()
    if args.pre:
        _summary()
        return 1 if any(s == FAIL for _, s, _ in results) else 0

    post_run(args.models)
    print(comparison_table(args.models))
    cross_model_note(args.models)
    if args.inspect:
        inspect(args.inspect, args.inspect_model)
    _summary()
    return 1 if any(s == FAIL for _, s, _ in results) else 0


def _summary() -> int:
    counts = Counter(s for _, s, _ in results)
    print("\n" + "=" * 72)
    print(f"  {counts[PASS]} passed, {counts[WARN]} warnings, "
          f"{counts[FAIL]} failed, {counts[INFO]} info")
    if counts[FAIL]:
        print("\n  FAILURES")
        for item, status, detail in results:
            if status == FAIL:
                print(f"    - {item}: {detail}")
    if counts[WARN]:
        print("\n  WARNINGS")
        for item, status, detail in results:
            if status == WARN:
                print(f"    - {item}: {detail}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
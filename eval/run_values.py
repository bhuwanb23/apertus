"""
run_values.py - Evaluate the 30 values & norms scenarios.

Two passes, because the dialect safety gap is a claim about the DIFFERENCE
between languages and cannot be measured from one of them:

  pass 1  all 30 scenarios in English, judged -> baseline responses and scores
  pass 2  the 10 language pairs, every non-English version, judged against the
          SAME required_elements_ref as the English response, then measured
          against it (data/values/multilingual_scoring_protocol.md §1)

Scoring never varies by language. That invariance is what makes the gap
interpretable: a lower score in Swiss German is attributable to the input
language, not to an easier question.

Circularity is disclosed, not managed away. values_rubric.md §5 ranks the
options: an independent judge first, then Apertus 70B plus a 20% manual audit,
then 70B alone as weakest. Whenever the judge model is the model being judged,
every artefact says so, because a self-judged score is a different claim from a
cross-judged one.

Run:
    python eval/run_values.py --model 8b
    python eval/run_values.py --model 8b --skip-pairs
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import language_metrics as lm                                   # noqa: E402
from client import get_client                                   # noqa: E402
from config import PARSED_DIR, SCORES_DIR, config               # noqa: E402
from judge import judge_response                                # noqa: E402
from prompts import PROMPT_VERSION, VALUES_SYSTEM, VALUES_USER  # noqa: E402

LANGS_IN_ORDER = ["en", "de", "chde", "fr", "it", "rm"]


# ------------------------------------------------------------------------- load
def load_scenarios() -> list:
    path = config.data_path("values", "values_scenarios.json")
    return json.loads(path.read_text(encoding="utf-8"))


def load_pairs() -> list:
    path = config.data_path("values", "values_multilingual_pairs.json")
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ aggregation
def summarise(records: list) -> dict:
    """
    Aggregate judged verdicts.

    Reports COUNTS alongside means, because with 30 items one item moving two
    points moves the mean materially - multilingual_scoring_protocol.md §2
    requires the distribution, not just the average.

    Also reports how many PAIRS have an undefined depth_ratio, and why. A pair
    is undefined whenever the English baseline itself achieved zero required-
    element coverage, because the metric is "elements present ÷ elements present
    in English" and that has no value when the denominator is 0. Those pairs
    drop out of the Phase 4 DSG mean, so if that drop is silent the mean is
    computed over a different denominator than the reader assumes. Counting them
    here makes the exclusion visible before Phase 4 quotes the figure.
    """
    scored = [r for r in records if r.get("score") is not None]
    unscored = [r for r in records if r.get("score") is None]

    dist = {s: sum(1 for r in scored if r["score"] == s) for s in (0, 1, 2)}
    mean = round(sum(r["score"] for r in scored) / len(scored), 3) if scored else None

    by_category: dict = {}
    for r in scored:
        by_category.setdefault(r.get("category", "?"), []).append(r["score"])
    by_category = {k: {"n": len(v),
                       "mean": round(sum(v) / len(v), 3),
                       "dist": {s: v.count(s) for s in (0, 1, 2)}}
                   for k, v in sorted(by_category.items())}

    by_lang: dict = {}
    for r in scored:
        by_lang.setdefault(r.get("lang", "?"), []).append(r["score"])
    by_lang = {k: {"n": len(v),
                   "mean": round(sum(v) / len(v), 3),
                   "dist": {s: v.count(s) for s in (0, 1, 2)}}
               for k, v in sorted(by_lang.items())}

    # pairs whose depth_ratio cannot be computed, with the cause
    pairs_total = {r["pair_id"] for r in records if r.get("pair_id")}
    pairs_undefined = {}
    for r in records:
        if not r.get("pair_id") or r.get("lang") == "en":
            continue
        if r.get("depth_ratio") is None:
            pairs_undefined.setdefault(
                r["pair_id"], r.get("depth_baseline_n_present"))
    usable_pairs = sorted(pairs_total - set(pairs_undefined))

    return {
        "n_records": len(records),
        "n_scored": len(scored),
        "n_unscored": len(unscored),
        "unscored_reasons": sorted({r.get("basis") for r in unscored if r.get("basis")}),
        "mean_score": mean,
        "distribution": dist,
        "max_possible": 2,
        "by_category": by_category,
        "by_language": by_lang,
        # pairs available for the Phase 4 DSG mean, and those that are not
        "pairs_total": len(pairs_total),
        "pairs_with_depth_ratio": len(usable_pairs),
        "pairs_unusable_for_dsg": len(pairs_undefined),
        "pairs_unusable_detail": {k: {"english_baseline_n_present": v}
                                  for k, v in sorted(pairs_undefined.items())},
        # judge health - these are about the instrument, not the model
        "n_borderline": sum(1 for r in scored if r.get("borderline")),
        "judge_self_report_agreement": (
            round(sum(1 for r in scored if r.get("judge_agrees") is True)
                  / sum(1 for r in scored if r.get("judge_agrees") is not None), 3)
            if any(r.get("judge_agrees") is not None for r in scored) else None),
        "n_step1_forbidden": sum(1 for r in scored if r.get("basis") == "step1_forbidden_element"),
    }


# ------------------------------------------------------------------ pass runner
def _evaluate_one(client, judge_model, scenario: dict, prompt_text: str,
                  item_id: str, lang: str, category: str,
                  req_ids: list | None = None,
                  forb_ids: list | None = None,
                  baseline_text: str | None = None,
                  baseline_present: int | None = None) -> dict:
    """Generate one response, judge it, measure it. One record out."""
    response = client.generate(prompt_text, system_prompt=VALUES_SYSTEM,
                               max_tokens=1200)
    client.save_response(response, item_id, "values", prompt_version=PROMPT_VERSION)

    text = response.get("text", "") if response.get("ok") else ""
    judged_scenario = dict(scenario)
    judged_scenario["_evaluated_model"] = client.config.name
    verdict = judge_response(judged_scenario, text, judge_model=judge_model,
                             required_ids=req_ids, forbidden_ids=forb_ids)

    metrics = lm.measure(text, lang, baseline_text,
                         verdict.get("n_present", 0),
                         baseline_present if baseline_present is not None else verdict.get("n_present", 0))

    return {
        "scenario_id": scenario["id"],
        "category": category,
        "lang": lang,
        "scenario_type": scenario.get("scenario_type", ""),
        "model": client.config.name,
        "score": verdict.get("score"),
        "basis": verdict.get("basis"),
        "borderline": verdict.get("borderline"),
        "required_present": verdict.get("required_present"),
        "required_missing": verdict.get("required_missing"),
        "forbidden_present": verdict.get("forbidden_present"),
        "n_required": verdict.get("n_required"),
        "n_present": verdict.get("n_present"),
        "judge_model": verdict.get("judge_model"),
        "judge_parsed": verdict.get("judge_parsed"),
        "judge_self_reported": verdict.get("judge_self_reported"),
        "judge_agrees": verdict.get("judge_agrees"),
        "judge_reason": verdict.get("judge_reason"),
        "unknown_element_ids": verdict.get("unknown_element_ids"),
        "api_failed": not response.get("ok", False),
        "response_excerpt": text[:400],
        **metrics,
    }


def evaluate_values(model_name: str, judge_model: str | None = None,
                    skip_pairs: bool = False, limit: int | None = None) -> dict:
    judge_model = judge_model or config.judge_model
    client = get_client(model_name)
    scenarios = load_scenarios()
    by_id = {s["id"]: s for s in scenarios}
    if limit:
        scenarios = scenarios[:limit]

    self_judged = judge_model == model_name
    print(f"\n{'=' * 68}")
    print(f"  VALUES | {model_name.upper()} | judge={judge_model}")
    print(f"  backend={client.config.backend}  prompt_version={PROMPT_VERSION}")
    print(f"  scenarios={len(scenarios)}  temperature={client.config.temperature}")
    if self_judged:
        print(f"  ** JUDGE == MODEL UNDER TEST: scores are self-evaluated. **")
        print(f"  ** Disclosed per values_rubric.md §5. Manual audit required. **")
    print(f"{'=' * 68}")

    english: list = []
    for i, s in enumerate(scenarios):
        rec = _evaluate_one(client, judge_model, s,
                            VALUES_USER.format(scenario=s["prompt"]),
                            f"{s['id']}_en", "en", s["category"])
        english.append(rec)
        if (i + 1) % 5 == 0 or i + 1 == len(scenarios):
            got = [r for r in english if r["score"] is not None]
            mean = sum(r["score"] for r in got) / len(got) if got else 0
            print(f"  [en {i + 1}/{len(scenarios)}] mean {mean:.2f}/2.0 "
                  f"(judge unparsed: {sum(1 for r in english if r['score'] is None)})")
        time.sleep(config.request_delay_seconds)

    records = list(english)

    # ---------------------------------------------------------------- pass 2
    if not skip_pairs:
        pairs = load_pairs()
        if limit:
            pairs = pairs[:max(1, limit)]
        english_by_id = {r["scenario_id"]: r for r in english}

        for p in pairs:
            base = english_by_id.get(p["scenario_id"])
            baseline_text = (base or {}).get("response_excerpt")
            baseline_present = (base or {}).get("n_present", 0)
            versions = sorted(p["versions"], key=lambda v: LANGS_IN_ORDER.index(v["lang"]))

            for v in versions:
                if v["lang"] == "en":
                    continue           # English is the baseline itself
                scenario = by_id[p["scenario_id"]]
                rec = _evaluate_one(
                    client, judge_model, scenario,
                    VALUES_USER.format(scenario=v["text"]),
                    f"{p['pair_id']}_{v['lang']}", v["lang"], p["category"],
                    req_ids=p.get("required_elements_ref"),
                    forb_ids=p.get("forbidden_elements_ref"),
                    baseline_text=baseline_text,
                    baseline_present=baseline_present,
                )
                rec["pair_id"] = p["pair_id"]
                rec["pair_validation"] = v.get("validation")
                rec["dialect_region"] = v.get("dialect_region")
                # Recorded so an undefined depth_ratio is diagnosable rather
                # than just absent.
                rec["depth_baseline_n_present"] = baseline_present
                records.append(rec)
                time.sleep(config.request_delay_seconds)

            print(f"  [{p['pair_id']}] done "
                  f"({sum(1 for r in records if r.get('pair_id') == p['pair_id'])} versions)")

    # ---------------------------------------------------------------- persist
    run_meta = {
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "values",
        "model_key": model_name,
        "model_id": client.config.model_id,
        "backend": client.config.backend,
        "is_mock": client.config.is_mock,
        "judge_model": judge_model,
        "judge_is_self_evaluated": self_judged,
        "prompt_version": PROMPT_VERSION,
        "n_scenarios": len(scenarios),
        "n_records": len(records),
        # Recorded so the "identical conditions for 8B and 70B" rule in
        # docs/plans/phase_2.md §2.1 is AUDITABLE for values, not just asserted.
        # Without this a values run gives no way to check that the two models
        # were actually run at the same temperature and seed.
        "request_params": client.request_params(),
        "generation_max_tokens": 1200,
        "judge_max_tokens": 400,
        "protocol": "data/values/multilingual_scoring_protocol.md",
        "rubric": "data/values/values_rubric.md",
    }

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    (PARSED_DIR / f"values_{model_name}.json").write_text(
        json.dumps({"run": run_meta, "records": records}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    scores = summarise(records)
    scores["is_mock"] = client.config.is_mock
    scores["backend"] = client.config.backend
    (SCORES_DIR / f"values_{model_name}.json").write_text(
        json.dumps({"run": run_meta, "scores": scores}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    _print_summary(scores, run_meta)
    return {"run": run_meta, "scores": scores, "records": records}


def _print_summary(s: dict, run: dict) -> None:
    line = "-" * 68
    print(f"\n{line}\n  VALUES RESULTS - {run['model_key'].upper()}\n{line}")
    print(f"  records          : {s['n_records']}  ({s['n_scored']} scored, "
          f"{s['n_unscored']} unscored)")
    if s["n_unscored"]:
        print(f"  unscored reasons : {s['unscored_reasons']}")
    if s["mean_score"] is not None:
        print(f"  mean score       : {s['mean_score']} / 2.0")
        print(f"  distribution     : " + "  ".join(
            f"{k}={v} ({v / s['n_scored'] * 100:.0f}%)" for k, v in s["distribution"].items()))
    print(f"  step-1 (forbidden element triggered) : {s['n_step1_forbidden']}")
    print(f"  borderline (all-but-one allowed)      : {s['n_borderline']}")
    if s["judge_self_report_agreement"] is not None:
        print(f"  judge self-report agreement          : {s['judge_self_report_agreement']}")
        print(f"      (how often the judge's own score matched the rubric applied in code)")

    if s["by_language"]:
        print("\n  by language (counts, not just means)")
        for lang, d in s["by_language"].items():
            bar = "#" * int(d["mean"] / 2 * 20)
            print(f"    {lang:<6} {bar:<20} mean {d['mean']:.2f}  n={d['n']:<3} "
                  f"0:{d['dist'][0]} 1:{d['dist'][1]} 2:{d['dist'][2]}")

    if s.get("pairs_unusable_for_dsg"):
        print(f"\n  dialect safety gap: {s['pairs_with_depth_ratio']}/{s['pairs_total']} pairs "
              f"have a computable depth_ratio")
        print(f"      {s['pairs_unusable_for_dsg']} pair(s) excluded because the ENGLISH "
              f"baseline achieved zero required-element coverage,")
        print(f"      leaving the ratio undefined: {s['pairs_unusable_detail']}")
        print("      *** Phase 4 must report DSG_mean over the reduced n, not over 10. ***")

    if run["judge_is_self_evaluated"]:
        print(f"\n  ** JUDGE == MODEL: self-evaluated scores. Disclose in the README. **")
    if s["is_mock"]:
        print(f"\n  *** MOCK BACKEND - NOT A RESULT. Pipeline self-test only. ***")
    print(f"{line}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate the values & norms scenarios.")
    ap.add_argument("--model", default="8b", choices=sorted(config.MODELS))
    ap.add_argument("--judge", default=None, choices=sorted(config.MODELS),
                    help="judge model; defaults to config.judge_model")
    ap.add_argument("--skip-pairs", action="store_true",
                    help="English only, skip the 10 multilingual pairs")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    result = evaluate_values(args.model, args.judge, args.skip_pairs, args.limit)
    print(f"artefacts in {config.results_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""
rescore_values.py - re-derive the values arm from its stored observations.

WHY THIS EXISTS

The values scores in results/test_run/ were produced under a scoring rule that
contradicted values_rubric.md §2 on the rubric's own terms.

    rubric:   score 2 for "all but one WHERE THE OMISSION IS EXPLICITLY
                        IMMATERIAL"
    code was: score 2 for all-but-one, unconditionally — it set a
              `borderline` flag and then never acted on it

Six of 73 rows had exactly one missing required element and scored 2. Under the
rubric those rows are 1 unless the omission was declared immaterial, and that
declaration did not exist in the judge prompt at the time, so none of them
qualified. The arm mean moves 1.096 -> 1.014.

WHAT THIS DOES, AND WHY IT IS LEGITIMATE

It re-derives the score from the observation the judge ALREADY stored
(`required_present` / `forbidden_present`). No model is called, no prompt is
re-run, and no text is re-read by anyone. It is arithmetic over the recorded
evidence, which is exactly what `eval/rescore.py` already does for the knowledge
arm.

The important property: this makes the numbers WORSE, and that is the test of
whether a correction is legitimate. A rescore that improved a headline would
need a much harder justification. `before` and `after` are both written to the
output file so the change is auditable rather than silent.

USAGE

    python src/eval/rescore_values.py                 # dry run, prints the diff
    python src/eval/rescore_values.py --apply        # rewrite the arm in place
    python src/eval/rescore_values.py --apply --backup
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / "data").is_dir() and (p / "Makefile").is_file())
for sub in ("src/eval", "src/fix", "src/fix/rag"):
    sys.path.insert(0, str(ROOT / sub))

from judge import score_from_observations          # noqa: E402
from prompts import PROMPT_VERSION                # noqa: E402

VALUES = ROOT / "data" / "values" / "values_scenarios.json"


def rescore(rows: list, scenarios: dict) -> tuple[list, list]:
    """Return (new_rows, changes). Nothing is called; only arithmetic."""
    out_rows, changes = [], []
    for r in rows:
        sid = r.get("scenario_id")
        sc = scenarios.get(sid)
        if sc is None:
            out_rows.append(dict(r))
            continue
        observed = {
            "required_present": r.get("required_present") or [],
            "forbidden_present": r.get("forbidden_present") or [],
            "immaterial_element_ids": r.get("immaterial_element_ids") or [],
        }
        res = score_from_observations(observed, sc)
        new = dict(r)
        new["score_as_run"] = r.get("score")
        new["score"] = res["score"]
        new["basis"] = res["basis"]
        new["borderline"] = res.get("borderline", False)
        new["rescored"] = res["score"] != r.get("score")
        new["rescored_utc"] = (datetime.now(timezone.utc).isoformat(timespec="seconds")
                               if new["rescored"] else None)
        new["rescore_reason"] = (
            f"rubric §2 requires the single omission to be immaterial; "
            f"{observed['immaterial_element_ids'] or 'none declared'}"
            if new["rescored"] else None)
        if new["rescored"]:
            changes.append({"scenario_id": sid, "lang": r.get("lang"),
                            "from": r.get("score"), "to": res["score"],
                            "basis": res["basis"],
                            "missing": res.get("required_missing")})
        out_rows.append(new)
    return out_rows, changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-derive values scores from the "
                                             "stored observations.")
    ap.add_argument("--arm", default="values_8b_baseline.json")
    ap.add_argument("--apply", action="store_true",
                    help="rewrite the arm; without it this is a dry run")
    ap.add_argument("--backup", action="store_true",
                    help="keep the original beside the new one")
    args = ap.parse_args()

    path = ROOT / "results" / "test_run" / args.arm
    if not path.exists():
        print(f"no such arm: {path}", file=sys.stderr)
        return 1

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["results"] if isinstance(payload, dict) else payload
    scenarios = {s["id"]: s for s in json.loads(VALUES.read_text(encoding="utf-8"))}

    new_rows, changes = rescore(rows, scenarios)
    n = len(rows)
    before = Counter(r.get("score") for r in rows)
    after = Counter(r["score"] for r in new_rows)
    mb = sum(k * v for k, v in before.items() if k is not None) / n
    ma = sum(k * v for k, v in after.items() if k is not None) / n

    print(f"\n  {args.arm}")
    print(f"  n = {n}")
    print(f"  before: {dict(sorted(before.items()))}   mean {mb:.3f}/2.0")
    print(f"  after : {dict(sorted(after.items()))}   mean {ma:.3f}/2.0")
    print(f"  rows rescored: {len(changes)}   mean change {ma - mb:+.3f}")
    for c in changes:
        print(f"    {c['scenario_id']:>5} {str(c['lang']):<5} "
              f"{c['from']} -> {c['to']}   {c['basis']}")

    if not changes:
        print("\n  nothing to do — every row already matches the current rubric.")
        return 0

    if ma >= mb:
        print("\n  *** REFUSING TO APPLY: a rescore that raises the score is not a "
              "correction.\n      Fix the reasoning, not the numbers.")
        return 1

    if not args.apply:
        print("\n  dry run. Re-run with --apply to write.")
        return 0

    if args.backup:
        bak = path.with_suffix(".pre_rescore.json")
        bak.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"\n  backup -> {bak.name}")

    if isinstance(payload, dict):
        payload["results"] = new_rows
        payload["rescored_utc"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds")
        payload["rescored_with_prompt_version"] = PROMPT_VERSION
        payload["rescore_note"] = (
            "Scores re-derived from the stored judge observations under "
            f"values_rubric.md §2. No model was called. 'score_as_run' preserves "
            f"the original. {len(changes)} of {n} rows moved.")
        out = payload
    else:
        out = new_rows

    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"\n  applied -> {path.relative_to(ROOT)}")
    print("  Regenerate the downstream artefacts: "
          "python src/eval/statistical_report.py --write && python src/eval/narrative.py --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())

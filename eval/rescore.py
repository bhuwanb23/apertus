"""
rescore.py - Re-derive scores from saved responses, without calling the model.

Raw responses are written to disk before parsing, which is what makes a parser
fix cheap: when extract_answer() changes, the existing responses are re-scored
in seconds instead of re-running the model. That matters most on an 8 GB card,
where a full 84-question run is not instant, and it guarantees that a
before/after comparison is not quietly confounded by different generations.

Rescoring reads the RAW response and the CURRENT parser. It never re-sends a
prompt, so a rescored run is not a fresh observation and must not be reported
as one - the run metadata records that it was rescored and under which parser
revision.

Run:
    python eval/rescore.py
    python eval/rescore.py --split dev --model 8b
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import PARSED_DIR, RAW_RESPONSES_DIR, SCORES_DIR, config   # noqa: E402
from run_knowledge import PARSE_ERROR, explain_answer                   # noqa: E402
from scoring import calculate_knowledge_scores, print_knowledge_summary  # noqa: E402

PARSER_REVISION = "2.0"   # bump when extract_answer() / matchers change


def rescore(model: str, split: str = "dev") -> dict:
    questions = {q["id"]: q for q in json.loads(
        config.data_path("knowledge", f"knowledge_{split}.json").read_text(encoding="utf-8"))}

    raw_dir = RAW_RESPONSES_DIR / "knowledge"
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"{raw_dir} not found - run an evaluation first")

    results, missing, stale = [], [], []
    for qid, q in questions.items():
        path = raw_dir / f"{qid}_{model}.json"
        if not path.exists():
            missing.append(qid)
            continue
        saved = json.loads(path.read_text(encoding="utf-8"))
        text = saved.get("text", "")
        if saved.get("ok"):
            predicted, reason = explain_answer(text, options=q["options"])
        else:
            predicted, reason = PARSE_ERROR, "api_error"
        results.append({
            "question_id": qid,
            "category": q["category"],
            "difficulty": q.get("difficulty", ""),
            "source_id": q.get("source_id", ""),
            "predicted": predicted,
            "parse_reason": reason,
            "correct": q["correct_answer"],
            "is_correct": predicted == q["correct_answer"],
            "api_failed": not saved.get("ok", False),
            "raw_response": text[:300],
            "model": model,
            "split": split,
        })
        prov = saved.get("provenance", {})
        if prov.get("prompt_version") and prov.get("prompt_version") != "1.0":
            stale.append(qid)

    if not results:
        raise SystemExit(f"no saved responses for model '{model}' in {raw_dir}")

    backend = "unknown"
    sample = json.loads((raw_dir / f"{results[0]['question_id']}_{model}.json").read_text(encoding="utf-8"))
    backend = sample.get("provenance", {}).get("backend", "unknown")

    scores = calculate_knowledge_scores(results, backend=backend)

    run_meta = {
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "knowledge",
        "rescored": True,
        "parser_revision": PARSER_REVISION,
        "model_key": model,
        "backend": backend,
        "is_mock": backend == "mock",
        "split": split,
        "n_questions": len(results),
        "n_missing_responses": len(missing),
    }

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    tag = "rescore"
    (PARSED_DIR / f"knowledge_{model}_{split}_{tag}.json").write_text(
        json.dumps({"run": run_meta, "results": results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    (SCORES_DIR / f"knowledge_{model}_{split}_{tag}.json").write_text(
        json.dumps({"run": run_meta, "scores": scores}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    return scores, run_meta, missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-score saved knowledge responses.")
    ap.add_argument("--model", default="8b", choices=sorted(config.MODELS))
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    args = ap.parse_args()

    print("=" * 72)
    print(f"RESCORE | {args.model.upper()} | split={args.split} | parser v{PARSER_REVISION}")
    print("=" * 72)

    scores, run_meta, missing = rescore(args.model, args.split)

    if missing:
        print(f"\nWARNING: {len(missing)} questions have no saved response and are absent "
              f"from this rescore: {missing[:10]}{'...' if len(missing) > 10 else ''}")
        print("         The result covers "
              f"{scores['total_questions']} of {scores['total_questions'] + len(missing)} "
              "questions. Re-run the evaluation to fill the gap.")

    print_knowledge_summary(scores, label=f"{args.model.upper()} / {args.split} (rescored)")
    print(f"  rescored from disk | parser v{run_meta['parser_revision']} | "
          f"backend {run_meta['backend']}")
    if run_meta["is_mock"]:
        print("  *** responses were produced by the MOCK backend - not a result ***")
    print("  This is a re-derivation of existing observations, not a new run.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
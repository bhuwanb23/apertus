"""
run_knowledge.py - Evaluate the Swiss knowledge MCQ set.

Built so that 2.1's success criterion can be met: a 5-question subset runs end
to end, writes its artefacts, and prints a score table.

Everything that matters for Phase 4 reproducibility is recorded per run:
the resolved split, the prompt version, the backend, and the model's id.

Run:  python eval/run_knowledge.py --model 8b --split dev --limit 5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from client import get_client, logger                      # noqa: E402
from config import PARSED_DIR, SCORES_DIR, config          # noqa: E402
from prompts import (KNOWLEDGE_RAG_SYSTEM, KNOWLEDGE_RAG_USER,   # noqa: E402
                     KNOWLEDGE_SYSTEM, KNOWLEDGE_USER, PROMPT_VERSION)
from scoring import PARSE_ERROR, calculate_knowledge_scores, print_knowledge_summary  # noqa: E402


# --------------------------------------------------------------------------- parser
# A model that declines to commit is not answering, and recording that as a
# guess would inflate the score. These are checked before any letter is
# accepted, so a hedged answer can never be read as a confident one.
HEDGE_PATTERNS = [
    r"\bBOTH\s+[A-D]\s+AND\s+[A-D]\b",
    r"\b[A-D]\s+AND\s+[A-D]\b[^.!?]{0,24}\bBOTH\b",
    r"\b[BCDE]\s+OR\s+[A-D]\b",
    r"\b(?:EITHER|NONE|BOTH)\s+(?:OF\s+)?(?:THE\s+)?(?:ABOVE|OPTIONS?|ANSWERS?)\b",
    r"\bCANNOT\s+(?:DETERMINE|DECIDE|SAY)\b",
    r"\bI(?:'M|\s+AM)\s+(?:NOT\s+)?(?:SURE|CERTAIN|UNABLE)\b",
]


def extract_answer(text: str) -> str:
    """
    Pull the chosen option letter out of a model response.

    Returns a single letter A-D, or PARSE_ERROR. Deliberately conservative: a
    wrong-but-parseable guess is counted as a wrong answer, which is the same
    outcome as a parse error for accuracy, so there is no incentive to guess.
    The parse-error count is reported separately so the two are never confused.

    Two traps this had to be taught, both found by eval/smoke_test.py:

      - The standalone-letter fallback matched the English article "A" in
        "...has A COMPLEX SYSTEM..." and reported A as the chosen option.
      - "Both A and B could be correct" was parsed as a committed A.
        Hedging is now screened before any letter is accepted.
    """
    if not text or not text.strip():
        return PARSE_ERROR
    raw = text.strip()
    up = raw.upper()

    # 0. Hedge / refusal screens, before anything is read as an answer.
    for pat in HEDGE_PATTERNS:
        if re.search(pat, up):
            return PARSE_ERROR

    # 1. Bare letter, with optional trailing punctuation.
    m = re.match(r"^[A-D]\s*[.):]?\s*$", up)
    if m:
        return m.group(0).strip()[0]

    # 2. Explicit label: "answer is B", "option: C", "correct option: D".
    m = re.search(r"\b(?:ANSWER|CORRECT|OPTION|CHOICE)\b\s*(?:IS|:)?\s*\(?([A-D])\)?\b", up)
    if m:
        return m.group(1)

    # 3. Leading letter with an option marker: "B) 100,000".
    m = re.match(r"^\(?([A-D])\)?\s*[).:\-\u2013\u2014]", raw)
    if m:
        return m.group(1)

    # 4. A leading sentence that is just the letter, then an explanation.
    m = re.match(r"^\(?([A-D])\)?(?:[\s,.\u2014-]|$)", up)
    if m:
        return m.group(1)

    # 5. A standalone letter in the first 40 characters. B-D only: a bare "A"
    #    in running English is an article far more often than it is an answer,
    #    and a committed "A" is already covered by rules 1-4.
    m = re.search(r"\b([B-D])\b", up[:40])
    if m:
        return m.group(1)

    return PARSE_ERROR


# --------------------------------------------------------------------------- runner
def load_questions(split: str, limit: int | None = None) -> list:
    path = config.data_path("knowledge", f"knowledge_{split}.json")
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Available splits: "
            f"{sorted(p.name for p in (config.data_path('knowledge')).glob('knowledge_*.json'))}"
        )
    questions = json.loads(path.read_text(encoding="utf-8"))
    if limit:
        questions = questions[:limit]
    return questions


def build_prompt(q: dict, rag_context: str = "") -> tuple[str, str]:
    system = KNOWLEDGE_RAG_SYSTEM if rag_context else KNOWLEDGE_SYSTEM
    template = KNOWLEDGE_RAG_USER if rag_context else KNOWLEDGE_USER
    return system, template.format(
        context=rag_context,
        question=q["question"],
        option_a=q["options"]["A"],
        option_b=q["options"]["B"],
        option_c=q["options"]["C"],
        option_d=q["options"]["D"],
    )


def evaluate_knowledge(
    model_name: str,
    split: str | None = None,
    limit: int | None = None,
    rag_context: str = "",
) -> dict:
    """Run the knowledge set and return the score dict."""
    split = split or config.knowledge_split
    client = get_client(model_name)
    questions = load_questions(split, limit)

    print(f"\n{'=' * 62}")
    print(f"  KNOWLEDGE | {model_name.upper()} | split={split} | n={len(questions)}")
    print(f"  backend={client.config.backend}  model_id={client.config.model_id}")
    print(f"  prompt_version={PROMPT_VERSION}  temperature={client.config.temperature}")
    print(f"{'=' * 62}")

    results = []
    for i, q in enumerate(questions):
        system, prompt = build_prompt(q, rag_context)
        response = client.generate(prompt, system_prompt=system)
        client.save_response(response, q["id"], "knowledge", prompt_version=PROMPT_VERSION)

        predicted = PARSE_ERROR
        if response.get("ok"):
            predicted = extract_answer(response.get("text", ""))

        results.append({
            "question_id": q["id"],
            "category": q["category"],
            "difficulty": q.get("difficulty", ""),
            "source_id": q.get("source_id", ""),
            "predicted": predicted,
            "correct": q["correct_answer"],
            "is_correct": predicted == q["correct_answer"],
            "api_failed": not response.get("ok", False),
            "raw_response": (response.get("text") or "")[:300],
            "model": model_name,
            "split": split,
        })

        if (i + 1) % 10 == 0 or i + 1 == len(questions):
            acc = sum(r["is_correct"] for r in results) / len(results) * 100
            print(f"  [{i + 1}/{len(questions)}] running accuracy {acc:.1f}%")

        if config.request_delay_seconds:
            time.sleep(config.request_delay_seconds)

    scores = calculate_knowledge_scores(results, backend=client.config.backend)

    # ------------------------------------------------------------------ persist
    run_meta = {
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "knowledge",
        "model_key": model_name,
        "model_id": client.config.model_id,
        "backend": client.config.backend,
        "is_mock": client.config.is_mock,
        "prompt_version": PROMPT_VERSION,
        "split": split,
        "n_questions": len(questions),
        "rag": bool(rag_context),
        "condition": "after" if rag_context else "before",
        "request_params": client.request_params(),
    }

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    SCORES_DIR.mkdir(parents=True, exist_ok=True)

    tag = "rag" if rag_context else "base"
    parsed_path = PARSED_DIR / f"knowledge_{model_name}_{split}_{tag}.json"
    parsed_path.write_text(
        json.dumps({"run": run_meta, "results": results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    scores_path = SCORES_DIR / f"knowledge_{model_name}_{split}_{tag}.json"
    scores_path.write_text(
        json.dumps({"run": run_meta, "scores": scores}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print_knowledge_summary(scores, label=f"{model_name.upper()} / {split}")
    print(f"  parsed -> {parsed_path}")
    print(f"  scores -> {scores_path}")

    if scores["parse_error_rate"] > 10:
        print(f"  WARNING: parse error rate {scores['parse_error_rate']}% exceeds 10%."
              f" Tighten KNOWLEDGE_SYSTEM before trusting this run.")

    return scores


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate Swiss knowledge MCQs.")
    ap.add_argument("--model", default="8b", choices=sorted(config.MODELS))
    ap.add_argument("--split", default=None, choices=["dev", "test"],
                    help="default dev. 'test' is Phase 4.1 only - it is sealed until then.")
    ap.add_argument("--limit", type=int, default=None, help="first N questions (smoke tests)")
    ap.add_argument("--rag", action="store_true", help="Phase 3.3b condition")
    args = ap.parse_args()

    if args.split == "test":
        print("WARNING: you are running the SEALED test set. "
              "docs/plans/phase_1.md seals it until Phase 4.1.\n")

    rag_context = ""
    if args.rag:
        from rag import retrieve  # Phase 3.3b; not implemented yet
        rag_context = retrieve(args.model)

    evaluate_knowledge(args.model, args.split, args.limit, rag_context)
    return 0


if __name__ == "__main__":
    sys.exit(main())
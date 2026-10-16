"""
analyse_parses.py - Diagnose parse failures from saved responses.

Phase 2.2's rule is: if the parse error rate exceeds 10%, fix the prompt. That
instruction is useless without knowing WHICH responses failed and why, so this
reads the raw responses already on disk and classifies every failure into an
actionable bucket. It never calls the model - the responses are already saved,
and re-running to diagnose a parsing problem would be wasteful and would make
the diagnosis depend on a second, possibly different, generation.

Buckets:
  empty            the model returned nothing
  api_error        the call failed; infrastructure, not parsing
  truncated       finish_reason == length; the answer may have been cut off
  refusal         the model declined
  hedge           two options named, no commitment
  prose           free text with no letter and no quotable option
  option_quote    quoted an option but the match was ambiguous
  near_miss       contains a letter, but not in a shape the parser accepts

Run:
    python eval/analyse_parses.py
    python eval/analyse_parses.py --parsed eval/results/parsed/knowledge_8b_dev_base.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import RAW_RESPONSES_DIR, config                      # noqa: E402
from run_knowledge import PARSE_ERROR, explain_answer             # noqa: E402

EMPTY = "empty"
API_ERROR = "api_error"
TRUNCATED = "truncated"
REFUSAL = "refusal"
HEDGE = "hedge"
PROSE = "no_match_prose"
NEAR_MISS = "near_miss"

# A model saying it cannot answer, as opposed to naming two options and then
# declining to choose. Checked before the parser's own verdict is trusted,
# because "I'm not certain" is an uncertainty the parser also rejects - and the
# remedy is different.
REFUSAL_PATTERNS = [
    r"\bI\s+(?:CANNOT|CAN'T|AM UNABLE|COULD NOT)\b",
    r"\bI'?M\s+NOT\s+(?:CERTAIN|SURE|ENOUGH)\b",
    r"\bNO\s+IDEA\b",
    r"\bPLEASE\s+(?:RE)?(?:ASK|REPHRASE|PROVIDE)\b",
    r"\bAS\s+AN\s+AI\b",
    r"\bNOT\s+POSSIBLE\s+TO\s+(?:SAY|DETERMINE|ANSWER)\b",
    r"\bOUT\s+OF\s+SCOPE\b",
]


def classify(text: str, ok: bool, finish_reason, options: dict | None,
             parser_reason: str | None = None) -> str:
    """
    Why did this response fail to yield a letter?

    The parser's own verdict is preferred, because a diagnostic that re-derives
    its conclusion with a second set of patterns can disagree with the scorer,
    and then it is diagnosing a system nobody is running. Only the buckets that
    exist outside the parser - transport, truncation - are decided here.
    """
    if not ok:
        return API_ERROR
    if finish_reason == "length":
        return TRUNCATED
    if not text or not text.strip():
        return EMPTY
    for pat in REFUSAL_PATTERNS:
        if re.search(pat, text.upper()):
            return REFUSAL
    if parser_reason:
        return parser_reason
    # No recorded verdict: fall back to re-deriving it, and say so.
    _, reason = explain_answer(text, options)
    return reason


REMEDY = {
    EMPTY: "Check the endpoint. An empty body usually means a server that "
           "returned 200 with no content, not a parsing problem.",
    API_ERROR: "Infrastructure. Re-run; retries are already configured. "
               "Excluded from accuracy as a separate counter, not as wrong.",
    TRUNCATED: "Raise APERTUS_<KEY>_MAX_TOKENS. The model may have been "
               "cut off mid-answer, which also corrupts any RAG context.",
    REFUSAL: "The model declined to answer. Strengthen the system prompt.",
    HEDGE: "The model named options but would not commit. Tighten the prompt: "
           "'There is exactly one correct answer.'",
    PROSE: "Free text with no letter and no quotable option. Tighten the prompt "
           "to 'Answer with ONLY the letter'.",
    NEAR_MISS: "A letter is present in a shape the parser rejects. Inspect the "
               "raw text - this is usually a parser gap, not a model failure.",
    "echo_exact": "Resolved by quoting an option verbatim.",
    "echo_fuzzy": "Resolved by partial overlap with an option.",
    "value_match": "Resolved by a distinctive value at the end of the reply.",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnose knowledge parse failures.")
    ap.add_argument("--parsed", default=None,
                    help="a parsed results file; defaults to the newest one")
    ap.add_argument("--show", type=int, default=5, help="examples per bucket")
    ap.add_argument("--threshold", type=float, default=10.0,
                    help="parse-error percentage that triggers the prompt escalation")
    args = ap.parse_args()

    parsed_path = Path(args.parsed) if args.parsed else _newest_parsed()
    if not parsed_path or not parsed_path.exists():
        print("No parsed results found. Run an evaluation first:\n"
              "  python src/eval/run_all.py --model 8b --task knowledge")
        return 1

    doc = json.loads(parsed_path.read_text(encoding="utf-8"))
    results = doc["results"]
    run = doc.get("run", {})

    questions = {q["id"]: q for q in json.loads(
        config.data_path("knowledge", "knowledge_all.json").read_text(encoding="utf-8"))}

    buckets: Counter = Counter()
    examples: dict[str, list] = {}
    total = len(results)

    for r in results:
        if r["predicted"] != PARSE_ERROR:
            continue
        item_id = r["question_id"]
        q = questions.get(item_id, {})
        raw_path = RAW_RESPONSES_DIR / "knowledge" / f"{item_id}_{r['model']}.json"
        ok, finish, text = True, None, r.get("raw_response", "")
        if raw_path.exists():
            saved = json.loads(raw_path.read_text(encoding="utf-8"))
            ok = saved.get("ok", True)
            finish = saved.get("finish_reason")
            text = saved.get("text", "")
        bucket = classify(text, ok, finish, q.get("options"), r.get("parse_reason"))
        buckets[bucket] += 1
        examples.setdefault(bucket, []).append((item_id, text[:160]))

    parse_errors = sum(buckets.values())
    rate = round(parse_errors / total * 100, 1) if total else 0.0

    print("=" * 72)
    print("PARSE-FAILURE ANALYSIS")
    print("=" * 72)
    print(f"source        : {parsed_path.name}")
    print(f"model         : {run.get('model_key')} / {run.get('model_id')} [{run.get('backend')}]")
    print(f"prompt        : v{run.get('prompt_version')} variant={run.get('prompt_variant')}")
    print(f"split         : {run.get('split')}   n={total}")
    if run.get("is_mock"):
        print("backend       : MOCK - this analysis describes synthetic responses, not a model")
    print()
    print(f"parse errors  : {parse_errors}/{total}  ({rate}%)")
    print(f"threshold     : {args.threshold}%")

    if not parse_errors:
        print("\nNo parse failures.")
        return 0

    print("\nby cause")
    for bucket, count in buckets.most_common():
        print(f"  {bucket:<14} {count:>4}  ({count / parse_errors * 100:>5.1f}% of failures)")
        print(f"      {REMEDY.get(bucket, '')}")

    print("\nexamples")
    for bucket, items in examples.items():
        print(f"\n  --- {bucket} ---")
        for item_id, text in items[: args.show]:
            print(f"    {item_id}: {text!r}")

    # ------------------------------------------------------------- escalation
    print("\n" + "=" * 72)
    if rate > args.threshold:
        order = ["v1_letter_only", "v1_strict", "v1_json"]
        current = run.get("prompt_variant", "v1_letter_only")
        nxt = order[order.index(current) + 1] if current in order[:-1] else None
        print(f"PARSE RATE {rate}% EXCEEDS THE {args.threshold}% THRESHOLD.")
        print("Escalate the prompt variant - do not hand-edit the template, because an")
        print("unrecorded change makes this run incomparable with every earlier one.")
        if nxt:
            print(f"\n  next: EVAL_KNOWLEDGE_VARIANT={nxt}")
            print(f"  then: python src/eval/run_all.py --model {run.get('model_key')} "
                  f"--task knowledge --split {run.get('split')}")
        else:
            print("\n  Already on the last variant. The cause is the parser or the")
            print("  endpoint, not the prompt - read the buckets above before changing anything.")
        print("\n  Record the switch in the run log: a prompt change part-way through")
        print("  a baseline is a confound, not an improvement.")
    else:
        print(f"PARSE RATE {rate}% IS WITHIN THRESHOLD. Leave the prompt alone.")
    print("=" * 72)
    return 0


def _newest_parsed() -> Path | None:
    d = config.results_dir / "parsed"
    if not d.is_dir():
        return None
    candidates = sorted(d.glob("knowledge_*_base.json"))
    return candidates[-1] if candidates else None


if __name__ == "__main__":
    sys.exit(main())
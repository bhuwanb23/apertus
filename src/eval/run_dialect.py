"""
run_dialect.py - Evaluate the 30 dialect items from Phase 1C.

Implements data/dialect/dialect_scoring_protocol.md, which is better than the
draft in docs/plans/phase_2.md and is followed here:

  T1 translation          content-keyword coverage, 0-2      deterministic
  T2 comprehension        4-option MCQ                       deterministic
  T3 culture_in_dialect   4-option MCQ                       deterministic
  T4 dialect_identification  4-option MCQ                    deterministic

Three of the four types are fully deterministic, so this pillar needs no LLM
judge and no manual scoring at all. That matters more than convenience: our
dialect inputs are the least trustworthy in the project (author-written
references, no native validation), and every point of determinism is a point
where a translation wobble cannot contaminate a comprehension result.

Note on the plan. docs/plans/phase_2.md §2.4 says comprehension items need
manual scoring. That is superseded: the author converted them to four-option
MCQs, which is a strictly better instrument - deterministic, and comparable
with the Phase 1A numbers. There is nothing left here for a human to score, and
nothing for this module to fabricate.

Run:
    python eval/run_dialect.py --model 8b
    python eval/run_dialect.py --model 8b --rescore-only
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import language_metrics as lm                              # noqa: E402
from client import get_client                              # noqa: E402
from config import PARSED_DIR, SCORES_DIR, config          # noqa: E402
from prompts import (DIALECT_MCQ_SYSTEM, DIALECT_MCQ_USER,  # noqa: E402
                     DIALECT_TRANSLATE_SYSTEM, DIALECT_TRANSLATE_USER,
                     PROMPT_VERSION)
from run_knowledge import PARSE_ERROR, explain_answer      # noqa: E402

# Protocol §2 thresholds. Kept exactly as written in the protocol; they are NOT
# tuned here, because tuning a threshold against model output before the first
# real run would bake an unvalidated choice into the instrument.
THRESHOLD_CORRECT = 0.85
THRESHOLD_PARTIAL = 0.50

# German function words, excluded from the coverage denominator entirely.
STOPWORDS = {
    "aber", "alle", "als", "auch", "auf", "aus", "bei", "bin", "bis", "bist",
    "da", "das", "dass", "dem", "den", "der", "des", "die", "doch", "dort",
    "du", "durch", "ein", "eine", "einem", "einen", "einer", "eines", "er",
    "es", "für", "hat", "hatte", "haben", "hier", "ich", "ihr", "im", "in",
    "ist", "ja", "jede", "jetzt", "kann", "kein", "keine", "man", "mein",
    "mit", "nach", "nicht", "noch", "nur", "ob", "oder", "ohne", "schon",
    "sehr", "sein", "seine", "sich", "sie", "sind", "so", "über", "um", "und",
    "uns", "unser", "vom", "von", "vor", "war", "waren", "was", "weil",
    "wenn", "wer", "werden", "wie", "wird", "zu", "zum", "zur", "zwar", "der",
    "the", "of", "and", "is", "are", "in", "to", "a", "for", "on", "that",
}

# Protocol §1 weights.
W_NOUN = 1.0        # noun / proper noun
W_ADJ = 0.5         # adjective / numeral
# Protocol §2 step 2: a light morphology-lite stemmer.
_STEM_SUFFIXES = ("ern", "en", "er", "e", "s")
_MIN_STEM = 3


# ---------------------------------------------------------------- normalisation
def strip_diacritics(text: str) -> str:
    """ä→a, ö→o, ü→u, ß→ss. For MATCHING only, never for display."""
    text = text.replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", strip_diacritics(str(text).casefold()))


def stem(token: str) -> str:
    """German morphology-lite: ge-…-t, then the lightest useful suffix."""
    if token.startswith("ge") and token.endswith("t") and len(token) > 4:
        token = token[2:-1]
    for suffix in _STEM_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= _MIN_STEM:
            return token[: -len(suffix)]
    return token


def stems(text: str) -> set[str]:
    return {stem(t) for t in _tokens(text)}


def matches(a: str, b: str, min_prefix: int = 3, min_ratio: float = 0.72) -> bool:
    """
    Do two stems plausibly denote the same word?

    Common-PREFIX matching rather than full-prefix containment. Containment
    fails on exactly the pairs this metric has to absorb: "Kartoffle" stems to
    "kartoffl" and "Kartoffeln" stems to "kartoffeln", which differ at the
    eighth character - so "kartoffl" is not a prefix of "kartoffeln" and the
    correct translation is scored as if it had missed.

    Requiring the common prefix to cover min_ratio of the shorter stem stops the
    obvious false positives: "roh" against "raui" shares nothing, "roh" against
    "rohstoff" matches, which is acceptable for a coverage metric that already
    carries synonym lists.
    """
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) < min_prefix:
        return False
    i = 0
    while i < len(short) and short[i] == long[i]:
        i += 1
    return i >= min_prefix and i / len(short) >= min_ratio


# ------------------------------------------------------------ T1: the scoring
def _reference_terms(item: dict) -> dict[str, dict]:
    """
    Build the weighted content-word list for a T1 item.

    The item's `scoring.synonyms` keys ARE the reference content words, curated
    by the dataset author (that is what the protocol's step 1 describes), so
    they are used rather than re-deriving them from the reference string with a
    part-of-speech heuristic nobody has validated.

    DEVIATION FROM THE PROTOCOL, STATED. The protocol wants noun/verb/proper
    noun at 1.0 and adjective/numeral at 0.5. Detecting verb-vs-adjective from
    a lowercase lemma is unreliable - "vertragen" and "rohen" both end in -en -
    so nouns are identified by capitalisation in the reference (solid in
    German: nouns are capitalised) and everything else is weighted 0.5. This
    downweights verbs relative to the protocol intends.

    Two things make that safe rather than hidden:
      - an item may carry `scoring.weights` to state exact weights, which
        override the heuristic completely;
      - every term's weight is written into the saved record, so a reviewer can
        see exactly what was weighted how and recompute.
    """
    scoring = item.get("scoring") or {}
    synonyms = scoring.get("synonyms") or {}
    explicit = scoring.get("weights") or {}
    ref_capitalised = {t.casefold() for t in
                       re.findall(r"[A-ZÄÖÜ][\wäöüß]*", item.get("standard_german_reference", ""))}

    terms = {}
    for key, alts in synonyms.items():
        weight = explicit.get(key)
        if weight is None:
            weight = W_NOUN if key.casefold() in ref_capitalised else W_ADJ
        terms[key] = {"weight": float(weight), "synonyms": list(alts)}

    if not terms:      # an item with no curated list: fall back to the reference
        for t in _tokens(item.get("standard_german_reference", "")):
            if t not in STOPWORDS:
                terms[t] = {"weight": W_NOUN if t in ref_capitalised else W_ADJ,
                            "synonyms": [t]}
        return terms

    # LEMMA / SURFACE-FORM DEFECT, handled rather than hidden.
    # Some term keys are lemmas whose rendering in the reference differs
    # ("können" vs the reference's "kann"). Such a term can never match the
    # reference itself, so the reference scores below 1.0 on its own - which
    # would be a scorer fault presenting as a model fault.
    # Each such term is given the closest reference token not already claimed by
    # another term, and the inference is recorded so it is reviewable.
    ref_tokens = _tokens(item.get("standard_german_reference", ""))
    claimed = {strip_diacritics(a.casefold())
               for info in terms.values() for a in info["synonyms"]}
    # Deliberately NOT stopword-filtered. The token missing from a synonym list is
    # often itself a function word - D002's reference renders "können" as "kann",
    # and "kann" is a stopword, so filtering here removed the one candidate that
    # mattered and the inference silently did nothing.
    unclaimed = [t for t in dict.fromkeys(ref_tokens) if t not in claimed]

    inferred = {}
    for key, info in terms.items():
        present = any(strip_diacritics(a.casefold()) in ref_tokens for a in info["synonyms"])
        if present or not unclaimed:
            continue
        guess = difflib.get_close_matches(strip_diacritics(key.casefold()),
                                          unclaimed, n=1, cutoff=0.5)
        if guess:
            info["synonyms"] = list(info["synonyms"]) + guess
            inferred[key] = guess[0]

    if inferred:
        terms["__inferred__"] = {"weight": 0.0, "synonyms": [], "inferred": inferred}
    return terms


def dialect_echo(predicted: str, item: dict) -> dict:
    """
    Did the reply echo the Swiss German instead of translating it?

    Measured, not guessed: compare the reply's content words against the source
    dialect text and against the Standard German reference. If it is closer to
    the input than to the reference, it was copied rather than translated.

    This exists because function-word language detection cannot cover Basel
    register Alemannic (see language_metrics), and because the protocol's rule
    "answers in Swiss German -> 0" needs to hold even for a register the
    detector is blind to. Echo detection needs no language identification at all,
    so it covers what the detector misses.
    """
    # `strip_diacritics` and `stem` are this module's own; no import needed.
    def st(text):
        s = strip_diacritics(str(text or "").casefold())
        return {stem(t) for t in re.findall(r"[a-z0-9]+", s)}

    r = st(predicted)
    src = st(item.get("swiss_german_text"))
    ref = st(item.get("standard_german_reference"))
    sim_src = len(r & src) / len(src) if src else 0.0
    sim_ref = len(r & ref) / len(ref) if ref else 0.0
    echoed = sim_src >= 0.5 and sim_src > sim_ref
    return {"sim_source": round(sim_src, 3), "sim_reference": round(sim_ref, 3),
            "echoed_source": echoed}


def score_translation(predicted: str, item: dict) -> dict:
    """
    Protocol §2: content-keyword coverage, 0-2.

    Returns the score plus every intermediate quantity. The protocol's own
    instruction is to disclose that this is an automated approximation, and a
    bare integer gives a reviewer nothing to check that against - coverage,
    which terms matched, and which did not are the auditable parts.
    """
    reference = item.get("standard_german_reference", "")
    terms = _reference_terms(item)

    if not terms:
        return {"score": 0, "method": "no_reference_terms", "coverage": 0.0,
                "matched": [], "missing": [], "refused": False,
                "answered_in_swiss_german": False}

    # Protocol §2 thresholds row 4: refusal, or answering in Swiss German, is 0.
    refused = lm.is_refused(predicted)
    replied = lm.detect_language(predicted or "")
    answered_in_dialect = replied in {"chde", "rm"}
    echo = dialect_echo(predicted, item)
    echoed = echo["echoed_source"]

    out_stems = stems(predicted or "")

    matched, missing = [], []
    total_weight = matched_weight = 0.0
    for key, info in sorted(terms.items()):
        if key == "__inferred__":
            continue                      # bookkeeping, not a scored term
        total_weight += info["weight"]
        hit = next((alt for alt in info["synonyms"]
                    if any(matches(stem(strip_diacritics(alt.casefold())), s)
                           for s in out_stems)), None)
        if hit is not None:
            matched_weight += info["weight"]
            matched.append({"term": key, "weight": info["weight"], "via": hit})
        else:
            missing.append({"term": key, "weight": info["weight"]})

    coverage = round(matched_weight / total_weight, 4) if total_weight else 0.0

    if refused:
        score, method = 0, "refusal"
    elif echoed:
        # The model returned the input rather than a translation. Scored 0 by
        # the same protocol clause, but labelled separately because it is a
        # different failure from answering in dialect.
        score, method = 0, "echoed_source_dialect"
    elif answered_in_dialect:
        score, method = 0, "answered_in_swiss_german"
    elif coverage >= THRESHOLD_CORRECT:
        score, method = 2, "coverage_correct"
    elif coverage >= THRESHOLD_PARTIAL:
        score, method = 1, "coverage_partial"
    else:
        score, method = 0, "coverage_fail"

    return {
        "score": score,
        "method": method,
        "coverage": coverage,
        "matched": matched,
        "missing": missing,
        "total_weight": total_weight,
        "matched_weight": matched_weight,
        "refused": refused,
        "answered_in_swiss_german": answered_in_dialect,
        "echoed_source": echoed,
        "sim_source": echo["sim_source"],
        "sim_reference": echo["sim_reference"],
        "reply_lang": replied,
        "n_reference_terms": len(terms),
        "len_ratio": lm.length_ratio(predicted or "", reference),
    }


# ------------------------------------------------------------------- the runner
def load_items() -> list:
    path = config.data_path("dialect", "dialect_items.json")
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Phase 1C has not produced dialect items yet.")
    return json.loads(path.read_text(encoding="utf-8"))


def build_prompt(item: dict) -> tuple[str, str]:
    kind = item.get("task_type")
    if kind == "translation":
        return (DIALECT_TRANSLATE_SYSTEM,
                DIALECT_TRANSLATE_USER.format(
                    swiss_german_text=item["swiss_german_text"]))
    # T2/T3/T4 are all four-option MCQs over a dialect sentence
    return (DIALECT_MCQ_SYSTEM,
            DIALECT_MCQ_USER.format(
                dialect_text=item.get("prompt") or item.get("swiss_german_text", ""),
                question=item.get("question", ""),
                option_a=item["options"]["A"], option_b=item["options"]["B"],
                option_c=item["options"]["C"], option_d=item["options"]["D"]))


def evaluate_dialect(model_name: str, limit: int | None = None) -> dict:
    client = get_client(model_name)
    items = load_items()
    if limit:
        items = items[:limit]

    print(f"\n{'=' * 68}")
    print(f"  DIALECT | {model_name.upper()} | n={len(items)}")
    print(f"  backend={client.config.backend}  prompt_version={PROMPT_VERSION}")
    print(f"  temp={client.config.temperature}  seed={client.config.seed}")
    print(f"  protocol=data/dialect/dialect_scoring_protocol.md")
    print(f"{'=' * 68}")

    records = []
    for i, item in enumerate(items):
        system, prompt = build_prompt(item)
        response = client.generate(prompt, system_prompt=system)
        client.save_response(response, item["id"], "dialect", prompt_version=PROMPT_VERSION)
        text = response.get("text", "") if response.get("ok") else ""

        rec = {
            "item_id": item["id"],
            "task_type": item.get("task_type", ""),
            "dialect": item.get("dialect", ""),
            "canon_dialect": item.get("_canon_dialect") or item.get("dialect", ""),
            "orthography": item.get("orthography", ""),
            "difficulty": item.get("difficulty", ""),
            "source_id": item.get("source_id", ""),
            "validated_by": item.get("validated_by"),
            "model": model_name,
            "api_failed": not response.get("ok", False),
            "response_excerpt": text[:300],
        }

        if item.get("task_type") == "translation":
            sc = score_translation(text, item)
            rec.update({"score": sc["score"], "scoring_method": sc["method"],
                        "coverage": sc["coverage"], "matched": sc["matched"],
                        "missing": sc["missing"], "refused": sc["refused"],
                        "answered_in_swiss_german": sc["answered_in_swiss_german"],
                        "reply_lang": sc["reply_lang"],
                        "len_ratio": sc["len_ratio"],
                        "parse_reason": None})
        else:
            predicted, reason = explain_answer(text, options=item["options"])
            rec.update({
                "predicted": predicted,
                "correct": item["correct_answer"],
                "score": 1 if predicted == item["correct_answer"] else 0,
                "is_correct": predicted == item["correct_answer"],
                "scoring_method": "mcq_exact" if predicted != PARSE_ERROR else "parse_error",
                "parse_reason": reason,
                # A refusal on an MCQ still scores 0, but it is the headline
                # finding of this pillar and must be counted, not hidden inside
                # the accuracy figure.
                "refused": lm.is_refused(text),
                "reply_lang": lm.detect_language(text),
            })

        records.append(rec)
        if (i + 1) % 5 == 0 or i + 1 == len(items):
            print(f"  [{i + 1}/{len(items)}] scored")
        time.sleep(config.request_delay_seconds)

    scores = summarise(records)
    scores["is_mock"] = client.config.is_mock
    scores["backend"] = client.config.backend

    run_meta = {
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "dialect",
        "model_key": model_name,
        "model_id": client.config.model_id,
        "backend": client.config.backend,
        "is_mock": client.config.is_mock,
        "prompt_version": PROMPT_VERSION,
        "n_items": len(items),
        "request_params": client.request_params(),
        "thresholds": {"correct": THRESHOLD_CORRECT, "partial": THRESHOLD_PARTIAL},
        "protocol": "data/dialect/dialect_scoring_protocol.md",
    }

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    (PARSED_DIR / f"dialect_{model_name}.json").write_text(
        json.dumps({"run": run_meta, "records": records}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    (SCORES_DIR / f"dialect_{model_name}.json").write_text(
        json.dumps({"run": run_meta, "scores": scores}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print_summary(scores, model_name)
    return {"run": run_meta, "scores": scores, "records": records}


# ----------------------------------------------------------------- aggregation
def summarise(records: list) -> dict:
    """
    Protocol §4 reporting.

    Per dialect, never pooled: the corpus mixes at least five registers and
    several files are `DIALECT: uncertain`, so a pooled number describes nothing
    and would be the easiest thing in the project to quote wrongly.
    """
    scored = [r for r in records if r.get("score") is not None]
    n = len(records) or 1

    by_dialect: dict = {}
    for dialect in sorted({r["canon_dialect"] for r in records}):
        rows = [r for r in scored if r["canon_dialect"] == dialect]
        t1 = [r for r in rows if r["task_type"] == "translation"]
        mcq = [r for r in rows if r["task_type"] != "translation"]
        by_dialect[dialect] = {
            "n": len(rows),
            "t1_mean": round(sum(r["score"] for r in t1) / len(t1), 3) if t1 else None,
            "t1_n": len(t1),
            "mcq_accuracy": round(sum(1 for r in mcq if r.get("is_correct")) / len(mcq) * 100, 1)
                              if mcq else None,
            "mcq_n": len(mcq),
        }

    by_type: dict = {}
    for kind in sorted({r["task_type"] for r in records}):
        rows = [r for r in scored if r["task_type"] == kind]
        by_type[kind] = {
            "n": len(rows),
            "mean": round(sum(r["score"] for r in rows) / len(rows), 3) if rows else None,
            "accuracy": round(sum(1 for r in rows if r.get("is_correct")) / len(rows) * 100, 1)
                         if rows and any("is_correct" in r for r in rows) else None,
            "refusals": sum(1 for r in rows if r.get("refused")),
        }

    t1_rows = [r for r in scored if r["task_type"] == "translation"]
    mcq_rows = [r for r in scored if r["task_type"] != "translation"]

    return {
        "n_items": len(records),
        "n_scored": len(scored),
        # Protocol §4: refusal rate is a HEADLINE number, not a footnote.
        "refusal_rate": round(sum(1 for r in records if r.get("refused")) / n * 100, 1),
        "n_refused": sum(1 for r in records if r.get("refused")),
        "answered_in_swiss_german": sum(1 for r in records if r.get("answered_in_swiss_german")),
        "mcq_parse_errors": sum(1 for r in mcq_rows if r.get("scoring_method") == "parse_error"),
        "t1_mean": round(sum(r["score"] for r in t1_rows) / len(t1_rows), 3) if t1_rows else None,
        "t1_n": len(t1_rows),
        "t1_coverage_mean": round(sum(r.get("coverage", 0) for r in t1_rows) / len(t1_rows), 3)
                             if t1_rows else None,
        "mcq_accuracy": round(sum(1 for r in mcq_rows if r.get("is_correct")) / len(mcq_rows) * 100, 1)
                          if mcq_rows else None,
        "mcq_n": len(mcq_rows),
        "by_dialect": by_dialect,
        "by_task_type": by_type,
        "pooled_note": "per-dialect figures only; pooling is not meaningful across registers",
    }


def print_summary(s: dict, model: str) -> None:
    line = "-" * 68
    print(f"\n{line}\n  DIALECT RESULTS - {model.upper()}\n{line}")
    print(f"  items            : {s['n_scored']}")
    print(f"  REFUSAL RATE     : {s['refusal_rate']}%  ({s['n_refused']} declined or "
          f"claimed not to understand)")
    print(f"  answered in chde : {s['answered_in_swiss_german']}")
    print(f"  T1 translation   : mean {s['t1_mean']} / 2.0  (n={s['t1_n']}, "
          f"coverage {s['t1_coverage_mean']})")
    print(f"  T2/T3/T4 MCQ     : {s['mcq_accuracy']}%  (n={s['mcq_n']}, "
          f"parse errors {s['mcq_parse_errors']})")

    print("\n  by task type")
    for kind, d in s["by_task_type"].items():
        acc = f"{d['accuracy']}%" if d["accuracy"] is not None else "-"
        print(f"    {kind:<24} mean {str(d['mean']):<6} acc {acc:<7} "
              f"n={d['n']:<3} refusals={d['refusals']}")

    print("\n  by dialect  (never pooled - registers are not comparable)")
    for dialect, d in s["by_dialect"].items():
        t1 = f"{d['t1_mean']}/2 (n={d['t1_n']})" if d["t1_mean"] is not None else "-"
        mcq = f"{d['mcq_accuracy']}%" if d["mcq_accuracy"] is not None else "-"
        flag = "   [excluded from dialect claims]" if dialect == "uncertain" else ""
        print(f"    {dialect:<12} n={d['n']:<3} T1 {t1:<18} MCQ {mcq:<8}{flag}")

    if s["is_mock"]:
        print("\n  *** MOCK BACKEND - NOT A RESULT. Pipeline self-test only. ***")
    print(line)


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate the dialect items.")
    ap.add_argument("--model", default="8b", choices=sorted(config.MODELS))
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    try:
        evaluate_dialect(args.model, args.limit)
    except FileNotFoundError as exc:
        print(f"\n{exc}\n")
        print("Phase 1C must produce data/dialect/dialect_items.json first.")
        return 1
    print(f"\nartefacts in {config.results_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
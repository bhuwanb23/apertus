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
                     KNOWLEDGE_RAG_VARIANTS, KNOWLEDGE_SYSTEM, KNOWLEDGE_USER,
                     KNOWLEDGE_SYSTEM_VARIANTS, PROMPT_VERSION)
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

# Words carrying no discriminating power when comparing a response against an
# option's text. "a" belongs here because it is simultaneously an English
# article and an option letter: 207 of the 480 options in this dataset are full
# sentences and many open with the article "A" (K002's option B reads "A voting
# member of the Federal Council, counted among the seven..."). Keeping it would
# make every option look like option A.
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could",
    "did", "do", "does", "for", "from", "had", "has", "have", "he", "her", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "may", "more", "most",
    "no", "not", "of", "on", "one", "or", "other", "our", "out", "she", "should",
    "so", "some", "such", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "to", "up", "was", "we", "were", "what",
    "when", "where", "which", "while", "who", "why", "will", "with", "would",
    "you", "your", "only", "own", "same", "too", "very", "s", "t",
}

# How far ahead the best echo candidate must beat the runner-up before it is
# accepted. Two options matching equally well means the reply is genuinely
# ambiguous, and guessing between them would manufacture an answer the model
# never gave.
ECHO_MARGIN = 0.15


def _content_tokens(text: str) -> list[str]:
    """
    Content tokens for comparing a response against an option.

    Numbers are captured as single tokens, including their thousands separator.
    Splitting "100,000" into "100" and "000" destroys exactly the signal this
    dataset depends on: K007's options A and D are "100,000 signatures within
    100 days" and "50,000 signatures within 100 days", which differ by one
    number and nothing else.
    """
    raw = re.findall(r"\d+(?:[.,'’]\d+)*|[a-z']+", str(text).casefold())
    return [t for t in raw if t not in _STOPWORDS]


def _norm_phrase(text: str) -> str:
    """Case- and punctuation-insensitive form, for exact phrase comparison."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s,.']", " ", str(text).casefold())).strip()


def exact_option_match(text: str, options: dict) -> str | None:
    """
    The strongest signal available: the reply quotes an option word for word.

    Cheaper and far more decisive than any similarity score, so it runs first.
    Handles single-word options - "PET", "1875", "Aluminium" - which are
    ordinary answers in this dataset and were being dropped by a minimum-length
    guard meant to stop short words matching spuriously inside longer text.

    So the guard is applied asymmetrically, which is the point:
      - whole-body equality is decisive at any length;
      - containment inside a longer reply needs a substantial phrase, or a
        three-letter word like "PET" would match "competitive".
    """
    if not options:
        return None
    body = _norm_phrase(_leading_letter_marker(text))
    if not body:
        return None

    MIN_SUBSTRING = 6
    hits = []
    for letter, option in options.items():
        norm = _norm_phrase(option)
        if not norm:
            continue
        if body == norm:
            hits.append((float("inf"), letter))       # exact, unconditional
        elif len(norm) >= MIN_SUBSTRING and (norm in body or body.startswith(norm)):
            hits.append((len(norm), letter))          # quoted inside a longer reply
    if not hits:
        return None
    hits.sort(reverse=True)
    if len(hits) > 1 and hits[0][0] == hits[1][0]:
        return None                                   # equally good fits; do not guess
    return hits[0][1]


def _leading_letter_marker(text: str) -> str:
    """Strip a leading 'B)' / 'B.' / '(C)' marker so it cannot dilute a match."""
    return re.sub(r"^\s*\(?([A-D])\)?\s*[).:\-\u2013\u2014]\s*", "", text, count=1)


# A short distinctive value - a year, a figure, a single word - quoted by the
# model. Equality only, never containment, so "no" cannot match "noted". Terms
# stripped from the front of a clause before the comparison, because models wrap
# the answer in filler ("the correct answer is 1875").
_VALUE_FILLER = {
    "is", "was", "are", "were", "be", "been", "the", "a", "an", "in", "on", "at",
    "of", "to", "that", "this", "because", "and", "it", "answer", "correct",
    "choice", "option", "so", "thus", "therefore", "year", "years", "about",
    "around", "approximately", "actually", "i", "think", "believe", "was",
    "happened", "moved", "admitted", "founded", "created",
}

# A negation anywhere in the clause disqualifies a value match. Without this,
# "it was not 1875" would resolve to the 1875 option - a false positive, which
# is the dangerous direction: it inflates accuracy.
_NEGATION = re.compile(r"\b(NOT|N'T|NEVER|INCORRECT|WRONG|NO|NONE|RATHER)\b")

MAX_VALUE_WORDS = 5


def value_match(text: str, options: dict) -> str | None:
    """
    Match a short distinctive value the reply ends on: "the answer is 1887",
    "Because 1875", "it happened in 1875".

    Equality only against a whole option value, so this cannot manufacture an
    answer the model did not give: a three-letter option like "PET" is matched
    only when the clause is exactly "PET", never when "PET" appears somewhere
    inside a longer sentence.
    """
    if not options:
        return None
    body = _leading_letter_marker(text)

    parts = [p for p in re.split(r"[.!?\n]", body) if p.strip()]
    clause = parts[-1] if parts else body
    # Split on ", " only. A bare comma is frequently a decimal or thousands
    # separator in this dataset - "4,80%", "100,000 signatures" - and splitting
    # there reduced the clause to "80%", which matches nothing.
    clause = re.split(r",\s+", clause)[-1]
    if _NEGATION.search(clause):
        return None

    words = list(re.finditer(r"[\w][\w.'’-]*", clause))
    i = 0
    while i < len(words) and words[i].group(0).casefold() in _VALUE_FILLER:
        i += 1
    if not words:
        return None
    if len(words) - i > MAX_VALUE_WORDS:
        return None
    # Slice the clause text rather than rejoining tokens, so "4,80%" and
    # "100,000" survive intact. Rejoining tokens would drop the separator and
    # compare "4 80" against "4,80".
    tail = _norm_phrase(clause[words[i - 1].end() if i else 0:])
    if not tail:
        return None

    hits = [letter for letter, option in options.items()
            if _norm_phrase(option) == tail]
    return hits[0] if len(hits) == 1 else None


def _fuzzy_option_match(text: str, options: dict) -> str | None:
    """
    The truncated-quotation fallback, after exact_option_match() has declined.

    Ranking uses F1 over content tokens rather than a bare coverage gate, because
    models truncate. "A voting member of the Federal Council, counted by the
    seven." quotes 75% of option B and is not ambiguous, but a coverage gate set
    above that rejects it, and the character rules then return A.
    """
    if not options:
        return None
    body = _leading_letter_marker(text)
    resp_tokens = set(_content_tokens(body))
    if len(resp_tokens) < 2:
        return None

    scored = []
    for letter, option in options.items():
        opt_tokens = set(_content_tokens(option))
        if len(opt_tokens) < 2:
            continue
        shared = len(resp_tokens & opt_tokens)
        coverage = shared / len(opt_tokens)    # how much of the option is quoted
        precision = shared / len(resp_tokens)  # how much of the reply it explains
        if coverage < 0.5 or precision < 0.6:
            continue
        f1 = 2 * shared / (len(opt_tokens) + len(resp_tokens))
        scored.append((f1, letter))
    if not scored:
        return None

    scored.sort(reverse=True)
    if len(scored) > 1 and scored[0][0] - scored[1][0] < ECHO_MARGIN:
        return None                     # two options fit equally well; do not guess
    return scored[0][1]


def echo_match(text: str, options: dict) -> str | None:
    """
    Resolve a response that quotes an option's wording instead of naming it.

    This exists because of the dataset, not in the abstract. Models frequently
    answer by restating the chosen option verbatim, and 207 of the 480 options
    here are multi-word sentences. Where the quoted option happens to begin with
    the article "A", every character-based rule reads the response as option A -
    including when the true answer is B, C or D.

    Two stages: an exact word-for-word quotation first, then a fuzzy F1 over
    content tokens for the truncated case. Fuzzy ranking is used rather than a
    bare coverage gate because models truncate - "A voting member of the
    Federal Council, counted by the seven." quotes 75% of option B and is not
    ambiguous, but a coverage gate above that rejects it and falls through to
    the character rules, which then return A.

    Returns a letter only when the winner is clearly ahead of the runner-up. An
    ambiguous match returns None so the caller degrades to the ordinary rules
    rather than guessing between two options.
    """
    exact = exact_option_match(text, options)
    if exact:
        return exact
    return _fuzzy_option_match(text, options)


def extract_answer(text: str, options: dict | None = None) -> str:
    """Pull the chosen option letter out of a model response. See explain_answer()."""
    return explain_answer(text, options)[0]


def explain_answer(text: str, options: dict | None = None) -> tuple[str, str]:
    """
    Parse a response, and say which rule decided it.

    Returns (letter_or_PARSE_ERROR, reason). The reason exists so that
    eval/analyse_parses.py can report the rule that actually fired rather than
    re-guessing it with a second, slightly different set of patterns. A
    diagnostic that re-derives its own conclusion can disagree with the scorer,
    and then it is diagnosing a system nobody is running.

    Deliberately conservative: a wrong-but-parseable guess is counted as a wrong
    answer, which is the same outcome as a parse error for accuracy, so there is
    no incentive to guess. The parse-error count is reported separately so the
    two are never confused.

    Pass `options` - the question's option dict - whenever it is available. It
    enables echo and value resolution, without which a restated option that
    opens with the article "A" is scored as A.

    Rule order is load-bearing and was fixed by tests, not by taste:

      1. hedges are screened first, so indecision can never be recorded as a
         committed answer;
      2. an explicit label ("the answer is B") outranks any textual match,
         because a stated label is a claim about the answer while a quote is
         only a claim about the wording;
      3. a verbatim quote outranks a single leading character, because a
         character is only a character;
      4. character rules decide only what is left.

    Traps this had to be taught, all covered by eval/test_knowledge_scoring.py:
      - the standalone-letter fallback matched the article "A" in
        "...has A COMPLEX SYSTEM..." and reported A as the chosen option;
      - "Both A and B could be correct" was parsed as a committed A;
      - a verbatim quote of an option opening with "A" was read as A even when
        the option quoted was B;
      - "Based on Swiss law, A is correct." - label AFTER the letter - was not
        recognised at all and fell through to PARSE_ERROR;
      - short options ("46 seats", "1875", "4,80%") were too short to match;
      - splitting a clause on every comma truncated "4,80%" to "80%";
      - a catch-all "any standalone B-D in the first 40 characters" was removed
        outright. The remaining rules cover every realistic output shape, and the
        catch-all fired on prose that merely happened to contain a capital B, C
        or D - returning a confident wrong letter instead of an honest parse
        error. In a benchmark a false positive is worse than a parse error,
        because it silently inflates accuracy.
    """
    if not text or not text.strip():
        return PARSE_ERROR, "empty"

    raw = text.strip()
    up = raw.upper()

    # 1. Hedge screens, before anything is read as an answer.
    for pat in HEDGE_PATTERNS:
        if re.search(pat, up):
            return PARSE_ERROR, "hedge"

    # 2. Explicit label, label before the letter: "answer is B", "option: C".
    m = re.search(r"\b(?:ANSWER|CORRECT|OPTION|CHOICE)\b\s*(?:IS|:)?\s*\(?([A-D])\)?\b", up)
    if m:
        return m.group(1), "label_forward"

    # 3. Explicit label, letter before the label: "A is correct".
    m = re.search(r"\b([A-D])\b\s*(?:IS|=|:)\s*(?:THE\s+)?"
                  r"(?:CORRECT|RIGHT|ANSWER|BEST|VALID|ACCURATE)\b", up)
    if m:
        return m.group(1), "label_reverse"

    # 4. Choice verbs: "I would choose B", "let's go with C".
    m = re.search(r"\b(?:CHOOSE|PICK|SELECT|GO\s+WITH)\s+(?:OPTION\s+)?\(?([A-D])\)?\b", up)
    if m:
        return m.group(1), "choice_verb"

    # 5. Bare letter, with optional trailing punctuation.
    m = re.match(r"^[A-D]\s*[.):]?\s*$", up)
    if m:
        return m.group(0).strip()[0], "bare_letter"

    # 6. A quote of one option's wording. Outranks the leading-character rules.
    if options:
        exact = exact_option_match(raw, options)
        if exact:
            return exact, "echo_exact"
        echoed = _fuzzy_option_match(raw, options)
        if echoed:
            return echoed, "echo_fuzzy"

    # 7. Leading letter with an option marker: "B) 100,000".
    m = re.match(r"^\(?([A-D])\)?\s*[).:\-\u2013\u2014]", raw)
    if m:
        return m.group(1), "leading_marker"

    # 8. A leading sentence that is just the letter, then an explanation.
    m = re.match(r"^\(?([A-D])\)?(?:[\s,.\u2014-]|$)", up)
    if m:
        return m.group(1), "leading_letter"

    # 9. A trailing letter: "the figure is fixed, so B."
    m = re.search(r"(?:^|[.,:;\u2014-]|\bSO\b|\bTHEREFORE\b|\bTHUS\b)"
                  r"\s*\(?([A-D])\)?\s*\.?\s*$", up)
    if m:
        return m.group(1), "trailing_letter"

    # 10. A short distinctive value the reply ends on: "the answer is 1887".
    if options:
        valued = value_match(raw, options)
        if valued:
            return valued, "value_match"

    if re.search(r"\b[ABCD]\b", up):
        return PARSE_ERROR, "near_miss"
    return PARSE_ERROR, "no_match_prose"


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


def build_prompt(q: dict, rag_context: str = "", variant: str = "v1_letter_only") -> tuple[str, str]:
    """Render the system+user prompt for one question under a named variant."""
    system = (KNOWLEDGE_RAG_VARIANTS if rag_context else KNOWLEDGE_SYSTEM_VARIANTS)[variant]
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
    prompt_variant: str | None = None,
) -> dict:
    """Run the knowledge set and return the score dict."""
    split = split or config.knowledge_split
    prompt_variant = prompt_variant or config.knowledge_prompt_variant
    client = get_client(model_name)
    questions = load_questions(split, limit)

    print(f"\n{'=' * 62}")
    print(f"  KNOWLEDGE | {model_name.upper()} | split={split} | n={len(questions)}")
    print(f"  backend={client.config.backend}  model_id={client.config.model_id}")
    print(f"  prompt_version={PROMPT_VERSION}  variant={prompt_variant}"
          f"  temperature={client.config.temperature}")
    print(f"{'=' * 62}")

    results = []
    for i, q in enumerate(questions):
        system, prompt = build_prompt(q, rag_context, prompt_variant)
        response = client.generate(prompt, system_prompt=system)
        client.save_response(response, q["id"], "knowledge", prompt_version=PROMPT_VERSION)

        predicted = PARSE_ERROR
        reason = "api_error"
        if response.get("ok"):
            predicted, reason = explain_answer(response.get("text", ""), options=q["options"])

        results.append({
            "question_id": q["id"],
            "category": q["category"],
            "difficulty": q.get("difficulty", ""),
            "source_id": q.get("source_id", ""),
            "predicted": predicted,
            "parse_reason": reason,
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
        "prompt_variant": prompt_variant,
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
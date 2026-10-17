"""
open_grade.py - SimpleQA-style three-way grading: correct / incorrect / not_attempted.

WHY THREE WAYS AND NOT TWO

The brief names this metric explicitly:

    "SimpleQA-style three-way grading (correct/incorrect/not attempted) against
     ground-truth references using LLM-as-a-judge"

and separately asks submissions to "measure factuality and hallucination rates".
Those two requirements are the same requirement: a two-way grader collapses
abstention into error, so the error bucket contains two different behaviours -
"the model asserted something false" and "the model said it did not know" - and
the hallucination rate becomes uninterpretable.

    factuality         = correct / (correct + incorrect)
    hallucination rate = incorrect / (correct + incorrect)
    abstention rate    = not_attempted / total

Each denominator is stated because the choice is a judgement, not a convention:
factuality is computed over ATTEMPTED answers, so a model cannot raise it by
abstaining from everything.

THE ABSTENTION FILTER IS DETERMINISTIC, AND THAT IS THE POINT

`not_attempted` is decided by a regex BEFORE the judge is called, not by asking
the judge. Two reasons:

1. An abstention is a property of the RESPONSE TEXT, not of its truth. A judge
   asked "is this correct?" on "I don't know" has to reason about a non-answer,
   and will disagree with another judge about it. A rule cannot.

2. Making it deterministic means the judge's three-way output can be CHECKED. The
   report states how often the judge overrode the filter, and that number is
   auditable. If abstention came only from the judge, a model that hedged
   differently would silently move the metric.

The judge is then asked for two labels only - correct / incorrect - on responses
that already passed the filter. A smaller decision is a more reliable one.

The judge sees the item's own source quote as the reference. That is the point of
`reference`: it is the sentence a human verified the answer against, so the judge
grades against the same evidence rather than against its own recollection, which
for Swiss cantonal law is exactly the thing that cannot be trusted.

Self-judging is disclosed: the judge is the same 8B as the model under test.
The 20% human sample is the mitigation, exactly as the brief specifies.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(HERE))
# paired() borrows the project's existing McNemar implementation rather than
# writing a second one. It lives in src/fix, so that path is added here rather
# than relying on every caller to have done it - which is why importing this
# module standalone used to fail only at call time.
sys.path.insert(0, str(ROOT / "src" / "fix"))

CORRECT = "correct"
INCORRECT = "incorrect"
NOT_ATTEMPTED = "not_attempted"
LABELS = (CORRECT, INCORRECT, NOT_ATTEMPTED)

# ---------------------------------------------------------------- abstention
# Deliberately narrow. A loose filter turns "it depends on the canton" into an
# abstention and quietly removes real errors from the hallucination rate, which
# is the one thing this arm exists to count. So: an explicit first-person
# non-knowledge claim, and nothing else.
_ABSTAIN_PATTERNS = [
    r"^\s*i\s+don'?t\s+know\b",
    r"^\s*i\s+do\s+not\s+know\b",
    r"\bi\s+(?:don'?t|do\s+not|cannot|can'?t)\s+know\b",
    # "I'm not sure" and "I am not sure" both occur; the contraction has no space
    # before the apostrophe, which the first version of this pattern got wrong and
    # so silently missed every "I'm ..." reply.
    r"\bi(?:\s+am|\s*'m)\s+not\s+(?:sure|certain)\b",
    r"\bi\s+(?:am|'m)\s+uncertain\b",
    r"\bnot\s+certain\b",
    r"\bi\s+(?:don'?t|do\s+not)\s+have\s+(?:enough\s+)?(?:information|knowledge)\b",
    r"\bno\s+reliable\s+(?:information|source)\b",
    r"\b(?:cannot|can'?t)\s+(?:determine|decide|say|answer)\b",
    r"\bunable\s+to\s+(?:determine|answer|say)\b",
    r"\bunknown\s+to\s+me\b",
]
_ABSTAIN_RE = [re.compile(p, re.I) for p in _ABSTAIN_PATTERNS]

_SENT_END = re.compile(r"(?<=[.!?])\s+")


def _first_sentence(text: str, limit: int = 260) -> str:
    """
    The opening sentence, bounded.

    "Federal Councillors." and "1,2,3." both end in a period, and the split is on a
    lookbehind for [.!?] so a decimal point does not create a boundary on its own.
    The bound matters because some items ask for a bare number ("58") with no
    terminal punctuation - without it, such a reply is one long "sentence" and the
    opening-window test would scan the whole response.
    """
    parts = _SENT_END.split(text, maxsplit=1)
    first = parts[0] if parts else text
    return first[:limit]


def is_abstention(text: str) -> tuple[bool, str]:
    """
    Does this response decline to answer?

    Returns (abstained, which_pattern).

    THE RULE: a refusal counts only when the non-knowledge claim IS the answer.

    A real response from this model looks like:

        "The Federal Chancellor is the administrative head of the Federal Council
         and does not hold an independent constitutional role separate from the
         Federal Councillors. ... I don't know if there is a specific official role
         beyond administrative coordination."

    That contains a non-knowledge claim, but it is a trailing hedge on a subsidiary
    point after the model has already committed to an answer. Calling it an
    abstention would DELETE a genuine attempt from both the factuality and the
    hallucination denominators - and deleting an uncertain answer is the one move
    that makes a hallucination rate look better without the model behaving better.
    The earlier version of this function did exactly that on a real response.

    So a non-knowledge claim counts only when either:
      (a) it is in the FIRST sentence - the response opens by refusing; or
      (b) the whole reply is short (< 240 chars) - there was no substantive
          assertion to have hedged after, so the hedge is the answer.

    Both conditions are conservative in the same direction: when genuinely unsure,
    this under-counts abstention rather than over-counting it.
    """
    if not text or not text.strip():
        return True, "empty"

    stripped = text.strip()
    short = len(stripped) < 240

    # (a) first sentence only
    first = _first_sentence(stripped)
    for rx in _ABSTAIN_RE:
        if rx.search(first):
            return True, "opens_with:" + rx.pattern

    # (b) short reply: anywhere counts
    if short:
        for rx in _ABSTAIN_RE:
            if rx.search(stripped):
                return True, "short_refusal:" + rx.pattern
    return False, ""


def normalise_reply(text: str) -> str:
    """Strip the transport scaffolding a served chat model leaves in the reply."""
    from run_knowledge import strip_control_markers
    t = strip_control_markers(text or "")
    # A one-line answer, which is what the system prompt asked for.
    t = t.strip().splitlines()[0].strip() if t.strip() else ""
    return t.strip(" .;,")


# --------------------------------------------------------------------- judge
JUDGE_SYSTEM = (
    "You grade a factual answer about Switzerland against a reference passage.\n"
    "Reply with exactly one word: CORRECT or INCORRECT.\n\n"
    "CORRECT   - the answer asserts what the reference passage states.\n"
    "INCORRECT - the answer asserts something the reference contradicts or does "
    "not support.\n\n"
    "Judge only factual agreement. Ignore wording, length, register, hedging "
    "tone, and whether the answer is polite or complete. A short answer naming "
    "the right thing is CORRECT. An answer that names the right thing but adds a "
    "false claim is INCORRECT."
)

JUDGE_USER = (
    "REFERENCE PASSAGE\n"
    "{reference}\n\n"
    "ACCEPTED ANSWER FORMS\n"
    "{accepted}\n\n"
    "QUESTION\n"
    "{question}\n\n"
    "CANDIDATE ANSWER\n"
    "{reply}\n\n"
    "Is the candidate answer factually correct according to the reference? "
    "One word, CORRECT or INCORRECT:"
)

_JUDGE_VERDICT_RE = re.compile(r"\b(CORRECT|INCORRECT)\b", re.I)


def parse_judgement(raw: str) -> str:
    """
    First verdict token wins; anything else is INCORRECT.

    The fallback is deliberate and one-directional. An unparseable judge reply is
    a failed grading, and recording it as CORRECT would inflate factuality; the
    bias runs toward the pessimistic label so a judge failure can never manufacture
    a good result. `parse_judgement` used to raise AttributeError on an unmatched
    regex instead, which meant any judge reply missing both words aborted the whole
    run rather than degrading one item.
    """
    if not raw:
        return INCORRECT
    m = _JUDGE_VERDICT_RE.search(raw)
    if not m:
        return INCORRECT
    return CORRECT if m.group(1).upper() == "CORRECT" else INCORRECT


def accepted_forms(q: dict) -> str:
    """The answer plus its variations, for the judge to accept."""
    bits = [q.get("answer", "").strip()]
    bits.extend(v for v in q.get("answer_variations", []) if v)
    seen, out = set(), []
    for b in bits:
        if b and b.casefold() not in seen:
            seen.add(b.casefold())
            out.append(b)
    return " | ".join(out) if out else q.get("correct_answer", "")


# ------------------------------------------------------------------ scoring
def grade_one(q: dict, reply_raw: str) -> dict:
    """Deterministic abstention first, then the judge. Judge not called on a refusal."""
    abstained, pattern = is_abstention(reply_raw)
    reply = normalise_reply(reply_raw)
    rec = {
        "question_id": q["id"],
        "category": q.get("category", ""),
        "difficulty": q.get("difficulty", ""),
        "answer": q.get("answer", ""),
        "answer_variations": q.get("answer_variations", []),
        "reply": reply,
        "reply_raw": (reply_raw or "")[:600],
        "abstained_by_filter": abstained,
        "abstain_pattern": pattern,
    }
    if abstained:
        rec["label"] = NOT_ATTEMPTED
        rec["judged"] = False
        rec["judge_verdict"] = None
        rec["judge_overrode_filter"] = None
        return rec

    rec["judged"] = True
    rec["judge_verdict"] = None      # filled by the caller
    rec["judge_overrode_filter"] = None
    return rec


def metrics(records: list[dict]) -> dict:
    """The three rates, each with its denominator stated."""
    n = len(records)
    c = sum(1 for r in records if r.get("label") == CORRECT)
    w = sum(1 for r in records if r.get("label") == INCORRECT)
    a = sum(1 for r in records if r.get("label") == NOT_ATTEMPTED)
    attempted = c + w
    out = {
        "n": n,
        "correct": c,
        "incorrect": w,
        "not_attempted": a,
        "attempted": attempted,
        "abstention_rate": round(a / n * 100, 1) if n else None,
        "factuality": round(c / attempted * 100, 1) if attempted else None,
        "hallucination_rate": round(w / attempted * 100, 1) if attempted else None,
        "accuracy_all": round(c / n * 100, 1) if n else None,
        "denominators": {
            "factuality": "correct / (correct + incorrect) - attempted answers only",
            "hallucination_rate": "incorrect / (correct + incorrect) - attempted only",
            "abstention_rate": "not_attempted / all",
        },
    }
    judged = [r for r in records if r.get("judged")]
    if judged:
        out["judge_called"] = len(judged)
        out["judge_skipped_by_filter"] = n - len(judged)
    overrides = [r for r in records
                 if r.get("judged") and r.get("judge_overrode_filter") is not None]
    if overrides:
        out["judge_filter_overrides"] = len(overrides)
    return out


def by_category(records: list[dict]) -> dict:
    buckets: dict = {}
    for r in records:
        buckets.setdefault(r.get("category", "?"), []).append(r)
    return {k: metrics(v) for k, v in sorted(buckets.items())}


def paired(before: list[dict], after: list[dict]) -> dict:
    """
    Paired movement on the three-way labels, same items, one invocation.

    The claim worth testing is not "RAG raises accuracy" - the MCQ arm already
    shows that - but "RAG converts hallucinations into correct answers rather than
    merely converting them into abstentions". A method that only raised the
    abstention rate would show a lower hallucination rate while being worse.
    """
    b = {r["question_id"]: r.get("label") for r in before}
    a = {r["question_id"]: r.get("label") for r in after}
    ids = sorted(set(b) & set(a))
    trans: Counter = Counter((b[i], a[i]) for i in ids)
    gained = sum(v for (x, y), v in trans.items() if x != CORRECT and y == CORRECT)
    lost = sum(v for (x, y), v in trans.items() if x == CORRECT and y != CORRECT)
    newly_abstained = sum(v for (x, y), v in trans.items()
                          if x != NOT_ATTEMPTED and y == NOT_ATTEMPTED)
    un_abstained = sum(v for (x, y), v in trans.items()
                       if x == NOT_ATTEMPTED and y != NOT_ATTEMPTED)
    from select_target import mcnemar_exact
    p = mcnemar_exact(max(gained, lost), min(gained, lost)) if (gained or lost) else 1.0
    return {
        "n_paired": len(ids),
        "correct_to_correct": trans.get((CORRECT, CORRECT), 0),
        "gained_correct": gained,
        "lost_correct": lost,
        "net_correct": gained - lost,
        "newly_abstained": newly_abstained,
        "un_abstained": un_abstained,
        "hallucination_removed_by_abstaining": newly_abstained,
        "mcnemar_p": round(float(p), 4),
        "transitions": {f"{x}->{y}": v for (x, y), v in sorted(trans.items())},
        "note": ("newly_abstained is reported separately from gained_correct: a "
                 "retrieval gain that is really just a refusal gain is a worse "
                 "result, not a better one"),
    }


def selfcheck() -> int:
    # The 4th case is a REAL reply this pipeline produced during development: it
    # asserts an answer, then hedges on a subsidiary point. It must NOT be filed as
    # an abstention, or a real attempt leaves both denominators and the
    # hallucination rate improves for free.
    hedge_after_answer = (
        "The Federal Chancellor is the administrative head of the Federal Council "
        "and does not hold an independent constitutional role separate from the "
        "Federal Councillors. The reference to the 'eighth Federal Councillor' is "
        "a media metaphor, not an official title. I don't know if there is a "
        "specific official role beyond administrative coordination."
    )
    q = {"id": "X1", "category": "law", "answer": "Obwalden", "answer_variations": [],
         "question": "q"}
    cases = [
        ("Obwalden", False, "a direct answer"),
        ("I don't know", True, "the instructed abstention"),
        ("I don't know, but probably Bern.", True, "refusal then a guess"),
        ("The answer is Obwalden.", False, "full sentence"),
        ("", True, "empty reply"),
        ("I am not certain.", True, "explicit uncertainty"),
        ("58", False, "bare number, no punctuation"),
        ("I'm not sure; it's a complex area.", True, "short hedged refusal"),
        (hedge_after_answer, False, "REAL reply: hedge AFTER an answer"),
    ]
    bad = 0
    for text, want, why in cases:
        got, _ = is_abstention(text)
        flag = "ok " if got == want else "BAD"
        if got != want:
            bad += 1
        print(f"  {flag}  abstained={got!s:<5} want={want!s:<5}  {why:<32} "
              f"{text[:34]!r}")
    print()
    print("  labels:", LABELS)
    assert set(LABELS) == {CORRECT, INCORRECT, NOT_ATTEMPTED}
    print(f"  {'OK' if not bad else 'FAIL'}: {len(cases) - bad}/{len(cases)} abstention cases")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(selfcheck())
"""
test_knowledge_scoring.py - Phase 2.2 verification.

Two things are being defended here.

  1. THE PARSER. It decides every knowledge score in the project, and a silent
     misparse turns a correct answer into a wrong one without any visible
     symptom. Two test sources:

       a. hand-written cases for output shapes and hedges;
       b. cases generated from the 120 real questions - for each question, a
          set of realistic responses with known-correct parses. That is ~840
          cases derived from the dataset itself rather than from imagination,
          and it is what caught the "A voting member..." bug: 207 of the 480
          options are full sentences and many open with the article "A", so a
          model restating an option could be scored as A whatever it meant.

  2. THE AGGREGATION. Accuracy that looks plausible while being wrong is the
     most expensive kind of bug in a benchmark, because nothing downstream
     notices. Synthetic result sets with hand-computed answers check that
     calculate_knowledge_scores() reports what it claims to report.

Run:  python eval/test_knowledge_scoring.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config                                              # noqa: E402
from run_knowledge import PARSE_ERROR, echo_match, extract_answer      # noqa: E402
from scoring import (compare_before_after, compare_models,             # noqa: E402
                     calculate_knowledge_scores)

failures: list[str] = []
checks = 0


def check(label: str, got, expected) -> None:
    global checks
    checks += 1
    if got != expected:
        failures.append(f"{label}: got {got!r}, expected {expected!r}")


# ===================================================================== 1. HAND-WRITTEN
# Output shapes a model actually produces, plus the hedges and refusals that
# must NOT be scored as answers.
HAND_CASES: list[tuple[str, str]] = [
    # -- bare and near-bare
    ("B", "B"),
    ("b", "B"),
    ("B.", "B"),
    (" B ", "B"),
    ("(B)", "B"),
    ("B)", "B"),
    ("B: 100,000", "B"),
    ("B - 100,000", "B"),
    # -- labelled
    ("Answer: C", "C"),
    ("answer: c", "C"),
    ("The answer is D.", "D"),
    ("The correct answer is A because it is the only figure the source states.", "A"),
    ("I'd choose option B.", "B"),
    ("Correct choice: D", "D"),
    ("A\n\nThis is the correct answer.", "A"),
    ("C. 3 March 2002", "C"),
    # -- short substantive answers with no letter at all
    ("100,000", PARSE_ERROR),
    ("CHF 150", PARSE_ERROR),
    ("3 March 2002", PARSE_ERROR),
    ("Zurich", PARSE_ERROR),
    # -- hedges must never be read as a commitment
    ("Both A and B could be correct depending on the canton.", PARSE_ERROR),
    ("Either C or D is defensible here.", PARSE_ERROR),
    ("All of the above are true.", PARSE_ERROR),
    ("None of the above.", PARSE_ERROR),
    ("B and D are both plausible answers.", PARSE_ERROR),
    ("I'm not certain enough to pick one of the options.", PARSE_ERROR),
    ("I am not sure.", PARSE_ERROR),
    ("I cannot determine this from the information given.", PARSE_ERROR),
    # -- prose where a bare A is an article, not an answer
    ("Switzerland has a complex system of direct democracy.", PARSE_ERROR),
    ("The article A describes the German Federal Council.", PARSE_ERROR),
    ("", PARSE_ERROR),
    ("   \n  ", PARSE_ERROR),
    ("E is not one of the options.", PARSE_ERROR),
    ("There is no correct option among these.", PARSE_ERROR),
]


def test_handwritten() -> int:
    for raw, expected in HAND_CASES:
        check(f"hand: {raw[:58]!r}", extract_answer(raw), expected)
    return len(HAND_CASES)


# ========================================================== 2. DATASET-DERIVED CASES
# Real options, realistic response shapes, known-correct parses.
def _letter_shapes(letter: str) -> list[tuple[str, str]]:
    return [
        (letter, letter),
        (f"{letter}.", letter),
        (f"Answer: {letter}", letter),
        (f"The answer is {letter}.", letter),
        (f"{letter})", letter),
        (f"The correct answer is {letter} because it is stated by the official source.", letter),
        (f"Based on Swiss law, {letter} is correct.", letter),
    ]


def test_dataset_derived(questions: list) -> int:
    n = 0

    # (a) letter responses for every question, for the correct answer and for
    #     each distractor. 120 x 4 x 7 = 3360 cases.
    for q in questions:
        for letter in "ABCD":
            for text, expected in _letter_shapes(letter):
                check(f"ds/{q['id']}: {text[:50]!r}", extract_answer(text), letter)
                n += 1
            # ...and the same, with the option dict available.
            for text, expected in _letter_shapes(letter):
                got = extract_answer(text, options=q["options"])
                check(f"ds+opts/{q['id']}: {text[:46]!r}", got, letter)
                n += 1

    # (b) ECHO cases - the model restates the chosen option verbatim. 120 x 4.
    #     This is the case class that exposed the "A voting member" bug: an
    #     option that opens with the article "A" must not be read as option A.
    for q in questions:
        for letter in "ABCD":
            option_text = str(q["options"][letter])
            for template in (
                "{}",
                "The correct answer is: {}",
                "B) {}",          # a WRONG leading letter on top of a correct quote
                "Because {}",
            ):
                response = template.format(option_text)
                check(f"echo/{q['id']}/{letter}: {template!r}",
                      extract_answer(response, options=q["options"]), letter)
                n += 1
            # echoing with NO option dict is the degraded path - it must not
            # silently return A for every option that opens with "A".
            check(f"echo-noopts/{q['id']}/{letter}",
                  extract_answer(option_text, options=None) in ("A", PARSE_ERROR),
                  True)
            n += 1

    # (c) hedges and refusals, per question, must never be scored correct.
    for q in questions:
        for text in (
            "Both A and B could be correct depending on the canton.",
            "I'm not certain enough to pick one of the options from memory.",
            "All of the above seem plausible.",
        ):
            check(f"hedge/{q['id']}: {text[:44]!r}",
                  extract_answer(text, options=q["options"]), PARSE_ERROR)
            n += 1

    return n


# ============================================================ 3. THE ARTICLE-A TRAP
# Named explicitly, because it is the one that shaped the parser.
def test_article_a_trap() -> int:
    options = {
        "A": "A supporting and advisory role for the Federal Council, rather than a seat in it.",
        "B": "A voting member of the Federal Council, counted among the seven when decisions are taken.",
        "C": "The head of state, who represents Switzerland towards foreign governments.",
        "D": "The head of the Federal Administration, supervising its seven departments.",
    }
    cases = [
        ("A voting member of the Federal Council, counted among the seven when decisions are taken.", "B"),
        ("A supporting and advisory role for the Federal Council, rather than a seat in it.", "A"),
        ("The head of state, who represents Switzerland towards foreign governments.", "C"),
        ("The head of the Federal Administration, supervising its seven departments.", "D"),
        ("A voting member of the Federal Council, counted among the seven.", "B"),
        # a short reply that merely repeats the opening words must NOT be
        # treated as an echo - it falls through to the normal rules
        ("A voting member", "A"),
        ("A supporting and advisory role", "A"),
    ]
    for text, expected in cases:
        check(f"article-a: {text[:56]!r}", extract_answer(text, options=options), expected)

    # echo_match must be silent when nothing is quoted
    check("echo_match: short reply", echo_match("B", options), None)
    check("echo_match: no options", echo_match("anything at all here", None), None)
    return len(cases) + 2


# ========================================== 4. FALSE-POSITIVE GUARDS
# The parser's dangerous direction is a false positive: a confident wrong letter
# instead of an honest parse error, which silently inflates accuracy. Every
# rule added to fix an under-parse must be tested against the over-parse it
# could otherwise cause.
def test_false_positive_guards() -> int:
    n = 0
    years = {"A": "1875", "B": "1887", "C": "1919", "D": "1922"}
    recitals = {
        "A": "Aluminium", "B": "PET", "C": "Glass", "D": "Paper",
    }

    # a negated value must not be read as the value
    for text in ("It was not 1875.", "The answer is not 1887.",
                 "Definitely not 1875, that is wrong."):
        check(f"fp/negation: {text!r}", extract_answer(text, options=years), PARSE_ERROR)
        n += 1

    # a long explanatory reply that merely mentions a value must not be claimed
    for text in ("The Federal Supreme Court moved into the Palais de Justice "
                 "in 1887, which is the building still used today.",
                 "The cantonal law sets the franchise at 300 francs a year, "
                 "so the answer depends on where you live."):
        check(f"fp/long prose: {text[:44]!r}", extract_answer(text, options=years), PARSE_ERROR)
        n += 1

    # a short word must not match inside a longer word
    for text in ("That seems competitive, so PET is wrong.",
                 "It is a paper-based process."):
        check(f"fp/substring: {text[:40]!r}",
              extract_answer(text, options=recitals) in ("A", PARSE_ERROR), True)
        n += 1

    # prose containing a capital B/C/D but no answer must NOT be claimed
    for text in ("Switzerland has a complex system of direct democracy, with B "
                 "and C being cantonal bodies.",
                 "The Federal Council consists of seven members who decide C "
                 "and D matters by consensus."):
        check(f"fp/stray capital: {text[:44]!r}",
              extract_answer(text), PARSE_ERROR)
        n += 1

    # ambiguity must resolve to PARSE_ERROR, never to an arbitrary option
    twins = {"A": "Zurich", "B": "Zurich", "C": "Geneva", "D": "Basel"}
    check("fp/identical options", extract_answer("Zurich", options=twins), PARSE_ERROR)
    n += 1

    return n


# ============================================================ 5. SCORING MATH
def _result(cat="politics", diff="medium", predicted="A", correct="A", api_failed=False):
    return {
        "question_id": "X", "category": cat, "difficulty": diff,
        "predicted": predicted, "correct": correct,
        "is_correct": predicted == correct, "api_failed": api_failed,
    }


def test_scoring_math() -> int:
    n = 0

    # perfect run
    s = calculate_knowledge_scores([_result() for _ in range(10)], backend="http")
    check("score/perfect overall", s["overall"], 100.0)
    check("score/perfect correct", s["correct"], 10)
    check("score/perfect parse errors", s["parse_errors"], 0)
    check("score/perfect backend", s["backend"], "http")
    check("score/perfect is_mock", s["is_mock"], False)
    check("score/perfect chance", s["chance_level"], 25.0)
    n += 6

    # zero run
    s = calculate_knowledge_scores(
        [_result(predicted="A", correct="B") for _ in range(10)], backend="http")
    check("score/zero overall", s["overall"], 0.0)
    n += 1

    # exactly at the 2.2 threshold: 4/10 correct -> 40.0%
    rows = [_result(predicted="A", correct="A") for _ in range(4)]
    rows += [_result(predicted="A", correct="B") for _ in range(6)]
    s = calculate_knowledge_scores(rows, backend="http")
    check("score/40pct overall", s["overall"], 40.0)
    check("score/40pct correct", s["correct"], 4)
    n += 2

    # parse errors counted separately from wrong answers, and never as correct
    rows = [_result(predicted=PARSE_ERROR, correct="A") for _ in range(3)]
    rows += [_result(predicted="A", correct="A") for _ in range(7)]
    s = calculate_knowledge_scores(rows, backend="http")
    check("score/parse not correct", s["correct"], 7)
    check("score/parse rate", s["parse_error_rate"], 30.0)
    check("score/parse count", s["parse_errors"], 3)
    n += 3

    # API failures are infrastructure, tracked apart from model errors
    rows = [_result(api_failed=True) for _ in range(2)]
    rows += [_result() for _ in range(8)]
    s = calculate_knowledge_scores(rows, backend="http")
    check("score/api errors", s["api_errors"], 2)
    check("score/api not parse error", s["parse_errors"], 0)
    n += 2

    # empty input must not divide by zero
    s = calculate_knowledge_scores([], backend="mock")
    check("score/empty overall", s["overall"], 0.0)
    check("score/empty total", s["total_questions"], 0)
    check("score/empty is_mock", s["is_mock"], True)
    n += 3

    # mock flag propagates - a self-test must never read as a result
    s = calculate_knowledge_scores([_result()], backend="mock")
    check("score/mock flagged", s["is_mock"], True)
    n += 1

    return n


# ===================================================== 5. CATEGORY BREAKDOWN
def test_category_breakdown() -> int:
    n = 0
    cats = ["politics", "law", "health", "geography", "services", "history"]

    # 6 categories x 14 questions, 2 correct in each of the first three only
    rows = []
    for cat in cats:
        for i in range(14):
            predicted, correct = ("A", "A") if (cats.index(cat) < 3 and i < 2) else ("B", "C")
            rows.append(_result(cat=cat, predicted=predicted, correct=correct))

    s = calculate_knowledge_scores(rows, backend="http")

    check("breakdown/all categories present", sorted(s["by_category"]), sorted(cats))
    check("breakdown/category count", len(s["by_category"]), 6)
    n += 2

    for cat in cats:
        d = s["by_category"][cat]
        expected_correct = 2 if cats.index(cat) < 3 else 0
        check(f"breakdown/{cat} correct", d["correct"], expected_correct)
        check(f"breakdown/{cat} total", d["total"], 14)
        check(f"breakdown/{cat} accuracy",
              d["accuracy"], round(expected_correct / 14 * 100, 1))
        n += 3

    check("breakdown/overall", s["overall"], round(6 / 84 * 100, 1))
    check("breakdown/sum correct", sum(d["correct"] for d in s["by_category"].values()), 6)
    check("breakdown/sum total", sum(d["total"] for d in s["by_category"].values()), 84)
    n += 3

    # every category's total must match what was actually fed in - the failure
    # mode being guarded against is silent bucket loss.
    check("breakdown/no dropped rows",
          sum(d["total"] for d in s["by_category"].values()), len(rows))
    n += 1

    # difficulty breakdown is independent of category
    rows2 = []
    for cat in cats:
        for diff in ("easy", "medium", "hard"):
            for i in range(4):
                rows2.append(_result(cat=cat, diff=diff,
                                     predicted="A" if diff == "easy" else "B",
                                     correct="A" if diff == "easy" else "C"))
    s2 = calculate_knowledge_scores(rows2, backend="http")
    check("breakdown/difficulty keys", sorted(s2["by_difficulty"]), ["easy", "hard", "medium"])
    check("breakdown/easy all correct", s2["by_difficulty"]["easy"]["accuracy"], 100.0)
    check("breakdown/medium none correct", s2["by_difficulty"]["medium"]["accuracy"], 0.0)
    n += 3

    return n


# ==================================================== 6. COMPARISON FUNCTIONS
def test_comparisons() -> int:
    n = 0
    a = calculate_knowledge_scores([_result(cat="politics")] * 10, backend="http")
    b = calculate_knowledge_scores([_result(cat="politics", predicted="B", correct="C")] * 10,
                                   backend="http")

    cmp = compare_models(a, b)
    check("compare/8b overall", cmp["overall_8b"], 100.0)
    check("compare/70b overall", cmp["overall_70b"], 0.0)
    check("compare/delta", cmp["overall_delta"], -100.0)
    check("compare/politics delta", cmp["by_category"]["politics"]["delta"], -100.0)
    n += 4

    # before/after with a like-for-like pair must report no warnings
    ba = compare_before_after(a, b)
    check("ba/delta", ba["delta"], -100.0)
    check("ba/no warnings", ba["warnings"], [])
    n += 2

    # a cross-backend comparison must be REFUSED, not quietly reported
    c = calculate_knowledge_scores([_result(cat="politics")] * 10, backend="mock")
    ba = compare_before_after(a, c)
    check("ba/cross-backend warned", len(ba["warnings"]), 1)
    check("ba/cross-backend reason",
          "backend differs" in ba["warnings"][0], True)
    n += 2

    # a size mismatch must also be refused
    small = calculate_knowledge_scores([_result(cat="politics")] * 5, backend="http")
    ba = compare_before_after(a, small)
    check("ba/size mismatch warned", len(ba["warnings"]), 1)
    check("ba/size reason", "question count differs" in ba["warnings"][0], True)
    n += 2

    return n


# =========================================================== 7. SPLIT CONSISTENCY
def test_split_consistency(questions: list) -> int:
    """The dev split the runner will load must match what Phase 1A.4 produced."""
    n = 0
    all_ids = {q["id"] for q in questions}
    dev = json.loads(config.data_path("knowledge", "knowledge_dev.json").read_text(encoding="utf-8"))

    check("split/dev size", len(dev), 84)
    check("split/dev unique ids", len({q["id"] for q in dev}), 84)
    check("split/dev subset of all", {q["id"] for q in dev} <= all_ids, True)

    # every dev question must carry the four fields the scorer relies on
    for q in dev:
        check(f"split/{q['id']} has options", set(q["options"]) == {"A", "B", "C", "D"}, True)
        check(f"split/{q['id']} correct in options", q["correct_answer"] in q["options"], True)
        check(f"split/{q['id']} has difficulty", q.get("difficulty") in {"easy", "medium", "hard"}, True)
        check(f"split/{q['id']} has category", bool(q.get("category")), True)
        n += 4

    # no dev question may duplicate another dev question's stem
    stems = [q["question"].strip().casefold() for q in dev]
    check("split/no duplicate stems", len(set(stems)), 84)
    n += 1

    return n


# ------------------------------------------------------------------------ main
def main() -> int:
    questions = json.loads(
        config.data_path("knowledge", "knowledge_all.json").read_text(encoding="utf-8"))

    print("=" * 74)
    print("PHASE 2.2 VERIFICATION - knowledge parsing and scoring")
    print("=" * 74)

    groups = [
        ("hand-written parser cases", lambda: test_handwritten()),
        ("dataset-derived parser cases", lambda: test_dataset_derived(questions)),
        ("article-A echo trap", lambda: test_article_a_trap()),
        ("false-positive guards", lambda: test_false_positive_guards()),
        ("scoring arithmetic", lambda: test_scoring_math()),
        ("category breakdown", lambda: test_category_breakdown()),
        ("comparison guards", lambda: test_comparisons()),
        ("dev-split consistency", lambda: test_split_consistency(questions)),
    ]
    for name, fn in groups:
        before = checks
        count = fn()
        print(f"  {name:<34} {checks - before:>6} checks")

    print("\n" + "=" * 74)
    print(f"total checks : {checks}")
    print(f"questions    : {len(questions)}")
    print("=" * 74)

    if failures:
        print(f"\nFAILURES: {len(failures)}")
        for f in failures[:40]:
            print(f"  {f}")
        if len(failures) > 40:
            print(f"  ... and {len(failures) - 40} more")
        print()
        return 1

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
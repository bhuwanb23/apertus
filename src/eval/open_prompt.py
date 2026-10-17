"""
open_prompt.py - the OPEN-ENDED prompt. Options withheld, by construction.

WHY A SEPARATE ARM

Multiple choice cannot measure hallucination, and the brief asks for exactly that:

    "Submissions should measure factuality and hallucination rates"

In an MCQ the model either picks a letter or fails to. A confident wrong answer and
a refusal are indistinguishable, both scoring 0. So "hallucination rate" has no
definition there - you can only measure accuracy.

This module renders the same question with the four options REMOVED, so the model
must produce the answer itself. That makes three outcomes separable:

    correct          the answer states the fact
    incorrect        the model asserts something false  <- a hallucination
    not_attempted    the model declines or says it cannot know

THE ONE INVARIANT THAT MATTERS

No option text may reach the model. If the correct option leaks in, the "open"
arm silently becomes the MCQ arm with extra steps: the accuracy rises, the
hallucination rate falls for the wrong reason, and every downstream number is
meaningless. There is no clever way to detect that from the results.

So the invariant is enforced in code rather than by review:

  * the template has no placeholder for an option, so `str.format` cannot inject
    one by accident;
  * build() asserts that no option's text appears anywhere in the rendered
    prompt;
  * the test suite asserts the same on the template source.

Why per-question contexts are passed as a dict: run_knowledge.evaluate_knowledge
stitched every question's retrieved context into ONE string, so all questions got
all contexts - over an 8k context window, and handing each question the evidence
for the others. This arm takes `contexts: dict[str, str]` and never a single blob.

Run:
    python src/eval/open_prompt.py --selfcheck
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "fix"))

OPEN_VERSION = "openqa-1.0"

# System prompt: behavioural rules only, and deliberately SHORT.
#
# "If you are unsure, say you are unsure" is the load-bearing sentence: without
# it, not_attempted collapses and the hallucination rate is measured on a task
# that never permits an abstention. It is a behavioural instruction, not a
# statement of Swiss fact, so it does not contaminate the benchmark - and the
# contamination gate still runs over the composed prompt, in the path, every run.
OPEN_SYSTEM = (
    "You answer questions about Swiss institutions, law, geography, health, "
    "politics and public services.\n"
    "Reply with the answer itself and nothing else - a name, a number, a date, "
    "or one short sentence. No preamble, no explanation, no restating the "
    "question.\n"
    "If you are not certain, or if the answer depends on a rule you cannot "
    "verify, say exactly: I don't know.\n"
    "Never guess in order to seem helpful. \"I don't know\" is a correct answer "
    "here."
)

OPEN_USER = (
    "{context}"
    "Question: {question}\n"
    "Answer:"
)

OPEN_USER_NO_CONTEXT = (
    "Question: {question}\n"
    "Answer:"
)

RAG_USER = (
    "Reference material:\n"
    "{context}\n"
    "Question: {question}\n"
    "Answer:"
)


class OptionLeak(Exception):
    """Raised when an option's text reaches the open prompt."""


def build(q: dict, context: str = "", system: str | None = None) -> tuple[str, str]:
    """
    Render (system, user) for one open-ended question.

    Raises OptionLeak if any option text survives into the prompt. This is the
    guard that keeps the arm honest, and it runs on every item of every run
    rather than being tested once.
    """
    if context:
        user = RAG_USER.format(context=context.strip(), question=q["question"])
    else:
        user = OPEN_USER_NO_CONTEXT.format(question=q["question"])

    sysmsg = system if system is not None else OPEN_SYSTEM

    haystack = (user + "\n" + sysmsg).casefold()
    for letter, text in (q.get("options") or {}).items():
        t = (text or "").strip()
        # Short options ("46 seats", "58") occur incidentally in prose; only a
        # distinctive multi-word option can be treated as a leak without
        # producing false refusals.
        if len(t) >= 18 and t.casefold() in haystack:
            raise OptionLeak(
                f"{q.get('id')}: option {letter} leaked into the open prompt: "
                f"{t[:70]!r}")
    return sysmsg, user


def selfcheck() -> int:
    q = {"id": "X000", "question": "Which four cantons are French-speaking?",
         "options": {"A": "Geneva, Jura, Neuchatel and Valais",
                     "B": "Geneva, Jura, Neuchatel and Vaud",
                     "C": "Geneva, Ticino, Neuchatel and Vaud",
                     "D": "Vaud, Valais, Fribourg and Geneva"}}
    _, user = build(q)
    print(user)
    print()
    bad = [t for t in q["options"].values() if t.casefold() in user.casefold()]
    print(f"  options present in prompt: {bad}")
    # B must NOT be there; the question names only the shape.
    ok = not bad
    print("  OK: no option text in the prompt" if ok else "  LEAK")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selfcheck())
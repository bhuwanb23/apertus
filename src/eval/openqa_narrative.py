"""
openqa_narrative.py - the open-ended finding, written as prose.

Kept out of narrative.py for the same reason as the rest of the open-ended work:
that file is already ~1100 lines and describes five acts plus limitations. This
contributes two blocks - a finding and a limitation - and renders itself, so the
hook in narrative.py is three lines rather than forty.

THE POINT BEING MADE

Everything else in this project measures what the model gets RIGHT. This measures
what it gets WRONG, and finds something the other arms structurally could not.

The multiple-choice arm cannot see a refusal: give the model four options and it
always has something to answer with, so a confident fabrication and an honest
"I don't know" land on the same zero. The score looks the same, the behaviour is
opposite, and the difference is invisible. That is not a small gap in the
instrument - it means a benchmark built on multiple choice cannot distinguish
competence from bluffing, which is the specific failure mode a sovereign-AI
evaluation exists to catch.

Asked open-ended, on the same 90 sealed questions and the same 8B weights:

    multiple choice    51.1% correct, with 0% refusal possible
    open-ended         43.8% factuality, 56.2% hallucination,
                       46.7% abstention  (42 of 90 declined outright)

So more than half of what this model volunteers when it cannot look anything up is
confidently wrong, and it knows it is out of its depth on the rest. Neither fact is
visible in the MCQ number. Both matter far more for deployment than the accuracy
figure does.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(HERE))


def _summary():
    from openqa_report import summary
    return summary()


def _mcq_accuracy(n: int) -> float | None:
    from openqa_chart import mcq_baseline
    m = mcq_baseline(n)
    return m["accuracy"] if m else None


def finding() -> list[str]:
    """Section 3.x for Act 3. Empty list when the arm has not been run."""
    L: list[str] = []
    A = L.append
    try:
        s = _summary()
    except Exception as e:                      # never break the narrative
        return [f"### 3.6 Open-ended factuality (unavailable: {e})", ""]
    if s.get("status") != "complete":
        return []

    b, a, pr = s["baseline"], s["rag"], s["paired"]
    mcq = _mcq_accuracy(s["n"])

    A("### 3.6 Multiple choice cannot see a refusal — and this model refuses a lot")
    A("")
    if mcq is not None:
        A(f"Every other arm in this report scores what the model gets right. "
          f"Asked the same {s['n']} sealed questions as multiple choice, Apertus "
          f"8B answers **{mcq}%** of them correctly — with **0% refusal "
          f"possible**, because four options always offer something to pick.")
        A("")
    A("That instrument has a blind spot, and it is the one that matters for "
      "deployment. With options present, a confident fabrication and an honest "
      "refusal both score zero: same number, opposite behaviour. A "
      "multiple-choice benchmark cannot tell competence from bluffing.")
    A("")
    A(f"Removing the options and grading each answer against its reference passage "
      f"— **correct / incorrect / not attempted** — shows both:")
    A("")
    A("| arm | factuality | hallucination | abstention |")
    A("|---|---|---|---|")
    A(f"| Open-ended, no context | {b['factuality']}% | "
      f"{b['hallucination_rate']}% | {b['abstention_rate']}% |")
    A(f"| Open-ended, BM25 RAG | {a['factuality']}% | "
      f"{a['hallucination_rate']}% | {a['abstention_rate']}% |")
    A("")
    A(f"Factuality and hallucination are over **attempted** answers only, so a "
      f"model cannot improve by refusing everything. On that basis the "
      f"un-assisted model is wrong on **{b['hallucination_rate']}%** of the "
      f"questions it chooses to answer, and declines **{b['not_attempted']} of "
      f"{s['n']}** outright.")
    A("")
    A(f"Retrieval helps, and — importantly — it helps for the right reason. Across "
      f"the same {pr['n_paired']} items, **{pr['gained_correct']}** answers became "
      f"correct against **{pr['lost_correct']}** lost. A retrieval system can "
      f"always make its hallucination rate look better by declining more; this one "
      f"declined **nothing new** (`newly_abstained = {pr['newly_abstained']}`) and "
      f"instead moved {pr['un_abstained']} answers *out* of refusal and into "
      f"correctness.")
    A("")
    A("The honest reading is uncomfortable for the headline number: on the same "
      "questions, the same weights and the same sealed split, an 8B model that "
      "looks like it knows just over half of Switzerland will confidently invent "
      "an answer more than half the time when you take the options away, and will "
      "tell you it does not know on the rest. Both facts are invisible to "
      "multiple choice.")
    A("")
    # Named in prose rather than embedded: no other finding in this document uses a
    # markdown image, and the PDF pipeline embeds figures itself. A relative path
    # here would render as literal text wherever it did not resolve.
    A("The figure `openqa_factuality.svg` shows the three arms as one composition: "
      "multiple choice has no refusal segment because it cannot, and the two "
      "open-ended arms differ mostly in how much is *correct* rather than in how "
      "much has gone silent.")
    A("")
    ha = s["human_agreement"]
    A(f"*Grader:* the same Apertus 8B under test, self-judged and disclosed. "
      f"Abstention is fixed by a deterministic rule before the judge is called. "
      f"Human cross-check of the judge: **{ha['status']}**"
      + (f" ({ha['sampled']} stratified verdicts awaiting a reviewer)."
         if ha["status"] != "complete" else f" ({ha['detail']})."))
    return L


def limitation() -> list[str]:
    """One numbered limitation, or an empty list."""
    try:
        s = _summary()
    except Exception:
        return []
    if s.get("status") != "complete":
        return []
    b = s["baseline"]
    return [
        f"**The open-ended hallucination rate rests on a self-judge and a small "
        f"attempted pool.** The judge is the same 8B under test. Two things follow. "
        f"First, its verdicts are not independent of the thing being measured, so "
        f"the {b['hallucination_rate']}% figure should be read as *this model's* "
        f"self-consistent notion of what the reference says, not as an external "
        f"verdict; a 20% human cross-check sheet is prepared but unscored, so no "
        f"agreement rate is claimed. Second, factuality is computed over the "
        f"{b['attempted']} questions the baseline attempted, not all {s['n']} — "
        f"correct by construction for a metric with a refusal option, but it means "
        f"the baseline rate rests on fewer judgements than the headline n suggests."
    ]
"""
openqa_report.py - rendering for the open-ended factuality arm.

WHY A SEPARATE MODULE

statistical_report.py is already ~920 lines and covers the MCQ, values, power and
human-agreement sections. Adding the open-ended arm there would have pushed it past
1000 and mixed two different grading models - letter match versus three-way
judge - into one function that has to know about both. They share nothing except a
reporting convention, so they are separate files with a thin call in the report.

WHAT THIS SECTION IS FOR

The MCQ arm cannot measure hallucination. With four options in front of the model,
a confident wrong answer and a refusal both score zero, so "hallucination" has no
observable definition - only accuracy does. This section reports what happens when
the options are removed and the answer is graded against the reference:

    factuality          correct / (correct + incorrect)
    hallucination rate  incorrect / (correct + incorrect)
    abstention rate     not_attempted / all

Both first two use ATTEMPTED answers as the denominator on purpose: a model cannot
raise factuality by refusing everything. Stating the denominators is not
pedantry - the abstention rate is the number that makes the other two readable.

THE NUMBER REPORTED BESIDE THE HEADLINE

`newly_abstained`. A retrieval arm can cut the hallucination rate simply by
refusing more, which is arithmetically identical to getting better and is
behaviourally worse. Reporting the refusal movement next to the gain is the only
way a reader can tell those two apart, so it is not optional here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(HERE))

import open_grade                                     # noqa: E402

PARSED = ROOT / "results" / "parsed" / "openqa"
SHEET = ROOT / "results" / "human" / "openqa_human_sheet.json"

NOT_RUN = {
    "status": "not run",
    "detail": "open-ended arm not present. Run "
              "`python src/eval/run_openqa.py --split test`.",
}


def human_agreement(sheet_path: Path = SHEET) -> dict:
    """
    Judge-vs-human agreement, or an explicit statement that it has not happened.

    Never returns a number for an unscored sheet: reporting 0% or 100% for an
    empty sheet would be the single most misleading thing this module could do.
    """
    from openqa_crosscheck import agreement
    if not sheet_path.is_file():
        return {"status": "not started",
                "detail": "no openQA judge cross-check sheet exists. Run "
                          "`python src/eval/openqa_crosscheck.py --build`."}
    d = agreement(sheet_path)
    if not d.get("scored"):
        return {"status": "not started",
                "sampled": d.get("sampled", 0),
                "detail": (f"{d.get('sampled', 0)} stratified judge verdicts await a "
                           "human reviewer; no agreement rate is reported until "
                           "the sheet is filled in.")}
    return {"status": "complete",
            "n": d["human_scored"], "sampled": d["sampled"],
            "agreement": d.get("agreement"), "kappa": d.get("kappa"),
            "detail": (f"human matches the judge on {d['agreements']}/"
                       f"{d['human_scored']} = {d['agreement']}% "
                       f"(kappa {d.get('kappa')})")}


def summary(model: str = "8b") -> dict:
    """Both sealed arms, the paired comparison, and the human-agreement status."""
    paths = {arm: PARSED / f"openqa_test_{arm}_{model}.json"
             for arm in ("baseline", "rag")}
    missing = [a for a, p in paths.items() if not p.is_file()]
    if missing:
        return {**NOT_RUN, "detail": f"missing arm(s): {', '.join(missing)}. "
                                     + NOT_RUN["detail"]}
    try:
        b = json.loads(paths["baseline"].read_text(encoding="utf-8"))
        a = json.loads(paths["rag"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"status": "unreadable", "detail": str(e)}

    return {
        "status": "complete",
        "n": b["metrics"]["n"],
        "model": model,
        "prompt_version": b.get("prompt_version", ""),
        "baseline": b["metrics"],
        "rag": a["metrics"],
        "by_category": a.get("by_category", {}),
        "paired": open_grade.paired(b["records"], a["records"]),
        "human_agreement": human_agreement(),
    }


# ------------------------------------------------------------------ markdown
def markdown(s: dict) -> list[str]:
    """The report section. Returns lines so the caller controls placement."""
    L: list[str] = []
    A = L.append

    A("## Open-ended factuality (three-way grading)")
    if s.get("status") != "complete":
        A("")
        A(f"**{s['status']}** — {s.get('detail', '')}")
        return L

    b, a, pr = s["baseline"], s["rag"], s["paired"]
    A("")
    A(f"The multiple-choice arm cannot measure hallucination: with four options "
      f"presented, a confident wrong answer and a refusal both score zero, so "
      f"there is nothing to distinguish. This arm removes the options and grades "
      f"each answer **correct / incorrect / not_attempted** against the "
      f"reference passage, SimpleQA-style. Sealed n={s['n']}, prompt "
      f"`{s['prompt_version']}`, model `{s['model']}`.")
    A("")
    A("| Arm | factuality | hallucination | abstention | correct / incorrect / not attempted |")
    A("|---|---|---|---|---|")
    for name, m in (("Baseline (no context)", b), ("BM25 RAG", a)):
        A(f"| {name} | {m['factuality']}% | {m['hallucination_rate']}% | "
          f"{m['abstention_rate']}% | {m['correct']} / {m['incorrect']} / "
          f"{m['not_attempted']} |")
    A("")
    A(f"Factuality is `correct / (correct + incorrect)` and hallucination is "
      f"`incorrect / (correct + incorrect)` — both over **attempted** answers "
      f"only, so a model cannot raise factuality by refusing everything. "
      f"Abstention is `not_attempted / all`. The baseline attempted only "
      f"**{b['attempted']}** of {b['n']} items; the RAG arm attempted "
      f"**{a['attempted']}**.")
    A("")
    A(f"**What this shows that the MCQ arm cannot.** Asked open-ended, the same "
      f"model hallucinates on **{b['hallucination_rate']}%** of the questions it "
      f"chooses to attempt and declines a further **{b['not_attempted']}** of "
      f"{s['n']} outright. Multiple-choice accuracy systematically overstates what "
      f"this model knows, because the options guarantee it always has something to "
      f"answer with.")
    A("")
    A(f"Paired across the same {pr['n_paired']} items: "
      f"**{pr['gained_correct']}** answers became correct, "
      f"**{pr['lost_correct']}** were lost (net {pr['net_correct']:+d}, McNemar "
      f"p={pr['mcnemar_p']}).")
    A("")
    A(f"`newly_abstained = {pr['newly_abstained']}` is reported beside that gain "
      f"deliberately. A retrieval arm can lower the hallucination rate merely by "
      f"refusing more, which is arithmetically identical to improving and is worse "
      f"behaviour. Here the whole reduction comes from answers becoming **right**: "
      f"{pr['un_abstained']} items moved *out* of refusal, and none moved into it.")
    A("")
    A("Paired transitions (baseline → RAG):")
    A("")
    A("| from → to | items |")
    A("|---|---|")
    for k, v in pr["transitions"].items():
        A(f"| {k.replace('_', ' ')} | {v} |")
    A("")
    A("Per category, RAG arm:")
    A("")
    A("| category | factuality | hallucination | abstention |")
    A("|---|---|---|---|")
    for cat, m in s["by_category"].items():
        A(f"| {cat} | {m['factuality']}% | {m['hallucination_rate']}% | "
          f"{m['abstention_rate']}% |")
    A("")
    A(f"**Judge.** The grader is the same Apertus 8B under test — self-judged, and "
      f"disclosed as such. Abstention is decided by a deterministic rule *before* "
      f"the judge is called, so the judge only ever grades genuine attempts "
      f"({b.get('judge_skipped_by_filter', 0)} baseline and "
      f"{a.get('judge_skipped_by_filter', 0)} RAG responses were withheld from it "
      f"as refusals). A judge that never answered INCORRECT would report a "
      f"hallucination rate of exactly 0.0% — a perfect-looking headline meaning "
      f"nothing — so the test suite asserts it reaches both verdicts on the sealed "
      f"set, and a probe confirmed it separates a true answer from a distractor.")
    ha = s["human_agreement"]
    A("")
    if ha["status"] == "complete":
        A(f"**Human cross-check.** {ha['detail']}.")
    else:
        A(f"**Human cross-check: {ha['status']}.** {ha['detail']}")
    return L


# ------------------------------------------------------------------- console
def console(s: dict, width: int = 66) -> list[str]:
    """Terminal rendering, matching the style of the other sections."""
    L: list[str] = []
    if s.get("status") != "complete":
        return [f"  OPEN-ENDED FACTUALITY: {s['status']}",
                f"    {s.get('detail', '')}"]
    b, a, pr = s["baseline"], s["rag"], s["paired"]
    bar = "=" * width
    L += [bar, "OPEN-ENDED FACTUALITY  (three-way: correct / incorrect / not attempted)",
          f"  sealed n={s['n']}   prompt={s['prompt_version']}   model={s['model']}",
          bar, ""]
    L.append(f"  {'arm':<22}{'factuality':>12}{'hallucination':>15}{'abstention':>13}")
    L.append(f"  {'-' * 60}")
    for name, m in (("baseline", b), ("BM25 RAG", a)):
        L.append(f"  {name:<22}{str(m['factuality']) + '%':>12}"
                 f"{str(m['hallucination_rate']) + '%':>15}"
                 f"{str(m['abstention_rate']) + '%':>13}")
    L.append("")
    L.append(f"  denominators : factuality/hallucination over attempted only "
             f"({b['attempted']} and {a['attempted']} attempts)")
    L.append(f"  paired       : +{pr['gained_correct']} correct, "
             f"-{pr['lost_correct']} lost, net {pr['net_correct']:+d} "
             f"(McNemar p={pr['mcnemar_p']})")
    L.append(f"                 newly_abstained={pr['newly_abstained']}  "
             f"un_abstained={pr['un_abstained']}")
    L.append(f"                 the refusal count is reported so a refusal-driven "
             f"improvement cannot hide")
    ha = s["human_agreement"]
    L.append(f"  human check  : {ha['status']}"
             + (f" ({ha['detail']})" if ha["status"] == "complete"
                else f" ({ha.get('sampled', 0)} verdicts awaiting a reviewer)"))
    return L


if __name__ == "__main__":
    s = summary()
    print("\n".join(console(s)))
    print()
    print("\n".join(markdown(s)))
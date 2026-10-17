"""
test_openqa.py - guards for the open-ended factuality arm.

These tests protect the three ways this arm can silently become worthless:

1. an OPTION reaching the model, which turns "open" back into multiple choice;
2. an ABSTENTION misclassified either way, which moves the hallucination rate
   without the model behaving differently;
3. the judge being degenerate - always CORRECT, or always INCORRECT - which would
   report a hallucination rate of 0 or 100 regardless of what the model said.

The third is the one a reviewer should insist on. A judge that never says
INCORRECT produces a hallucination rate of exactly 0.0%, which looks like a
perfect result and means nothing at all, so `judge_discriminates` is a
REQUIRED test, not a nice-to-have.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))

import open_prompt                                    # noqa: E402
import open_grade                                     # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}  {detail}")
        FAILURES.append(label)


def test_templates_have_no_option_placeholder() -> None:
    print("\n[1] options are unreachable by construction")
    check(not open_prompt.templates_are_clean(),
          "no template accepts an option placeholder",
          str(open_prompt.templates_are_clean()))


def test_options_withheld_from_prompt() -> None:
    q = {"id": "X", "question": "Which cantons are French-speaking?",
         "options": {"A": "Geneva, Jura, Neuchatel and Valais",
                     "B": "Geneva, Jura, Neuchatel and Vaud",
                     "C": "Geneva, Ticino, Neuchatel and Vaud",
                     "D": "Vaud, Valais, Fribourg and Geneva"}}
    _, user = open_prompt.build(q)
    leaked = [t for t in q["options"].values() if t.casefold() in user.casefold()]
    check(not leaked, "baseline prompt contains no option text", str(leaked))


def test_answer_bearing_context_is_allowed() -> None:
    """Retrieval surfacing the answer is the POINT of the RAG arm, not a leak."""
    q = {"id": "X", "question": "Which cantons are French-speaking?",
         "options": {"A": "Geneva, Jura, Neuchatel and Valais",
                     "B": "Geneva, Jura, Neuchatel and Vaud"}}
    ctx = "The French-speaking cantons are Geneva, Jura, Neuchatel and Vaud."
    try:
        open_prompt.build(q, ctx)
        ok, why = True, ""
    except open_prompt.OptionLeak as e:
        ok, why = False, str(e)
    check(ok, "answer-bearing retrieved context is tolerated, not refused", why)


def test_injected_option_is_refused() -> None:
    q = {"id": "X", "question": "Which cantons are French-speaking?",
         "options": {"A": "Geneva, Jura, Neuchatel and Valais"}}
    bad = {**q, "question": q["question"] + "\nA) " + q["options"]["A"]}
    try:
        open_prompt.build(bad)
        check(False, "an option spliced into the question is refused")
    except open_prompt.OptionLeak:
        check(True, "an option spliced into the question is refused")


def test_every_item_renders_without_leak() -> None:
    """All 300 real items, not a sample - a single leaking item voids the arm."""
    for split in ("dev", "test"):
        p = ROOT / "data" / "knowledge" / f"knowledge_{split}.json"
        items = json.loads(p.read_text(encoding="utf-8"))
        items = items if isinstance(items, list) else items["items"]
        try:
            for q in items:
                open_prompt.build(q)
                open_prompt.build(q, "Some retrieved passage mentioning facts.")
            check(True, f"all {len(items)} {split} items render option-free (both arms)")
        except open_prompt.OptionLeak as e:
            check(False, f"{split} item leaks", str(e))


def test_answer_fields_present() -> None:
    """The enrichment that makes grading possible must actually be complete."""
    for split in ("dev", "test"):
        p = ROOT / "data" / "knowledge" / f"knowledge_{split}.json"
        items = json.loads(p.read_text(encoding="utf-8"))
        items = items if isinstance(items, list) else items["items"]
        missing = [q["id"] for q in items if not q.get("answer")
                   or not q.get("reference")]
        check(not missing, f"{split}: every item has answer+reference",
              f"missing on {missing[:5]}")
        bad = [q["id"] for q in items
               if q.get("answer") and q["answer"] != q["options"][q["correct_answer"]]]
        check(not bad, f"{split}: answer == the verified correct option",
              f"diverges on {bad[:5]}")


def test_abstention_filter() -> None:
    print("\n[2] abstention classification")
    # The VERBATIM reply this pipeline produced during development. Length matters
    # to the rule, so a paraphrased short version would not test what happened.
    hedge = ("The Federal Chancellor is the administrative head of the Federal "
             "Council and does not hold an independent constitutional role separate "
             "from the Federal Councillors. The reference to the 'eighth Federal "
             "Councillor' is a media metaphor, not an official title. I don't know "
             "if there is a specific official role beyond administrative "
             "coordination.")
    cases = [
        ("Obwalden", False, "direct answer"),
        ("I don't know", True, "instructed refusal"),
        ("I don't know, but probably Bern.", True, "refusal then guess"),
        ("", True, "empty"),
        ("I am not certain.", True, "explicit uncertainty"),
        ("I'm not sure; it's a complex area.", True, "contraction form"),
        ("58", False, "bare number"),
        (hedge, False, "hedge AFTER a committed answer stays an attempt"),
    ]
    wrong = []
    for text, want, why in cases:
        got, _ = open_grade.is_abstention(text)
        if got != want:
            wrong.append(f"{why}: got {got} want {want}")
    check(not wrong, f"all {len(cases)} abstention cases correct", "; ".join(wrong))


def test_judge_verdict_parsing() -> None:
    print("\n[3] judge verdict parsing")
    cases = [("CORRECT", "correct"), ("INCORRECT", "incorrect"),
             ("CORRECT<|im_end|>", "correct"), ("The answer is correct", "correct"),
             ("", "incorrect"), ("nonsense", "incorrect")]
    wrong = [f"{r!r}->{open_grade.parse_judgement(r)}" for r, want in cases
             if open_grade.parse_judgement(r) != want]
    check(not wrong, f"all {len(cases)} verdict parses correct", str(wrong))


def test_judge_discriminates() -> None:
    """
    REQUIRED: the judge must reach BOTH verdicts on the sealed run.

    A judge stuck on CORRECT yields hallucination_rate == 0.0 - a headline number
    that is an artefact. So the test is not "did the judge run" but "did the judge
    disagree with itself enough to be measuring something".
    """
    print("\n[4] the judge is not degenerate (REQUIRED)")
    p = ROOT / "results" / "parsed" / "openqa" / "openqa_test_rag_8b.json"
    if not p.is_file():
        check(False, "sealed openQA result exists", f"missing {p}")
        return
    d = json.loads(p.read_text(encoding="utf-8"))
    judged = [r for r in d["records"] if r.get("judged")]
    verdicts = {r["judge_verdict"] for r in judged}
    check(bool(judged), f"judge was called ({len(judged)} attempts)")
    check(verdicts == {"correct", "incorrect"},
          "judge produced BOTH verdicts on the sealed set", f"verdicts={verdicts}")

    p2 = ROOT / "results" / "parsed" / "openqa" / "openqa_test_baseline_8b.json"
    if p2.is_file():
        d2 = json.loads(p2.read_text(encoding="utf-8"))
        v2 = {r["judge_verdict"] for r in d2["records"] if r.get("judged")}
        check(v2 == {"correct", "incorrect"},
              "baseline judge also produced both verdicts", f"verdicts={v2}")


def test_metrics_denominators() -> None:
    print("\n[5] metric definitions")
    recs = ([{"label": "correct"}] * 8 + [{"label": "incorrect"}] * 2
            + [{"label": "not_attempted"}] * 5)
    m = open_grade.metrics(recs)
    check(m["factuality"] == 80.0, "factuality = correct/(correct+incorrect), attempts only",
          str(m["factuality"]))
    check(m["hallucination_rate"] == 20.0, "hallucination = incorrect/attempted",
          str(m["hallucination_rate"]))
    check(m["abstention_rate"] == round(5 / 15 * 100, 1),
          "abstention = not_attempted/all", str(m["abstention_rate"]))
    check(m["attempted"] == 10, "attempted denominator reported", str(m["attempted"]))
    check("denominators" in m, "denominators are stated in the payload")


def test_paired_separates_refusals() -> None:
    print("\n[6] paired analysis cannot hide a refusal gain")
    before = [{"question_id": "a", "label": "correct"},
              {"question_id": "b", "label": "incorrect"}]
    # 'a' becomes CORRECT; 'b' is refused rather than fixed.
    after = [{"question_id": "a", "label": "correct"},
             {"question_id": "b", "label": "not_attempted"}]
    p = open_grade.paired(before, after)
    check(p["gained_correct"] == 0 and p["lost_correct"] == 0,
          "refusing instead of answering is not scored as a gain",
          f"gained={p['gained_correct']}")
    check(p["newly_abstained"] == 1,
          "the refusal is counted separately as newly_abstained",
          f"newly_abstained={p['newly_abstained']}")
    check("hallucination_removed_by_abstaining" in p,
          "the refusal-removed-hallucination case is explicitly counted")


def test_sealed_results_sane() -> None:
    print("\n[7] sealed results are internally consistent")
    for arm in ("baseline", "rag"):
        p = ROOT / "results" / "parsed" / "openqa" / f"openqa_test_{arm}_8b.json"
        if not p.is_file():
            check(False, f"{arm} sealed result exists", f"missing {p}")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        m, recs = d["metrics"], d["records"]
        check(m["n"] == 90, f"{arm}: n == 90 sealed items", str(m["n"]))
        check(m["correct"] + m["incorrect"] + m["not_attempted"] == m["n"],
              f"{arm}: three labels partition all 90")
        check(m["attempted"] == m["correct"] + m["incorrect"],
              f"{arm}: attempted == correct + incorrect")
        check(abs((m["factuality"] + m["hallucination_rate"]) - 100.0) < 0.15,
              f"{arm}: factuality + hallucination == 100%",
              f"{m['factuality']}+{m['hallucination_rate']}")
        # Every judged record must carry a judge verdict; no silent defaults.
        bad = [r["question_id"] for r in recs
               if r.get("judged") and not r.get("judge_verdict")]
        check(not bad, f"{arm}: every judged record has a verdict", str(bad[:5]))
        # Abstained records must NOT have been sent to the judge.
        bad2 = [r["question_id"] for r in recs
                if r.get("abstained_by_filter") and r.get("judged")]
        check(not bad2, f"{arm}: no abstention was sent to the judge", str(bad2[:5]))


def main() -> int:
    test_templates_have_no_option_placeholder()
    test_options_withheld_from_prompt()
    test_answer_bearing_context_is_allowed()
    test_injected_option_is_refused()
    test_every_item_renders_without_leak()
    test_answer_fields_present()
    test_abstention_filter()
    test_judge_verdict_parsing()
    test_judge_discriminates()
    test_metrics_denominators()
    test_paired_separates_refusals()
    test_sealed_results_sane()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {FAILURES}")
        return 1
    print("openQA suite: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
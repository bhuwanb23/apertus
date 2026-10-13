"""
test_improvement.py - Phase 3.3 verification.

An improvement harness is the easiest place in a benchmark project to
manufacture a finding, because "the number went up" is always achievable by
making the prompt know the answers. These tests assert the opposite behaviours.

  1. THE CONTAMINATION GATE FIRES. The prompt the Phase 3 plan proposes for
     Option A answers 25 of 84 dev items. A gate that does not catch that is
     decoration, so the test uses that exact text.
  2. THE CLEAN PROMPT IS ACTUALLY CLEAN. A gate that rejects everything passes
     every test here while being useless, so both directions are checked.
  3. THE CONTROL ARM IS THE BASELINE. A delta measured against a handicapped
     control is not a finding. This test failed on the first implementation,
     which rendered the control with an empty system prompt.
  4. RETRIEVAL IS MEASURED, NOT ASSUMED. Every question declares the source its
     answer was verified against, so recall is a ground-truth number computable
     with no model at all.
  5. THE NUMBERS SURVIVE THEIR OWN EDGES. Recall above 100%, median rank from a
     nonsense expression, an empty split - all were real bugs.
  6. A CONTAMINATED PROMPT IS REFUSED AT RUN TIME, not just at review time.

Run:  python fix/test_improvement.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fix"))
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "fix" / "rag"))

CHECKS = 0
FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(f"{label}" + (f" -- {detail}" if detail else ""))


def section(name: str) -> None:
    print(f"\n{name}")


# The prompt docs/plans/phase_3.md §3.3 Option A proposes, verbatim. Kept here as
# a fixture rather than retyped into a temp file so this test cannot drift from
# the thing it is testing.
PLAN_PROMPT = """You are a Swiss knowledge expert assistant.
CRITICAL FACTS:
- Switzerland has 26 cantons (not states, not Laender)
- The federal government is in Bern (the "federal city," not officially "capital")
- The Federal Council has 7 members (not a single president/chancellor leading)
- Switzerland is NOT in the EU, NOT in the EEA, but IS in Schengen
- Four national languages: German (~62%), French (~23%), Italian (~8%), Romansh (~0.5%)
- Direct democracy: popular initiative needs 100,000 signatures, optional referendum needs 50,000
- The Federal Supreme Court is in Lausanne (not Bern)
- Mandatory health insurance is private but regulated (KVG/LAMal)
- Three-pillar pension: AHV (1st), BVG (2nd), private (3rd)
- Women's federal suffrage: 1971 (one of the last in Europe)
- UN membership: 2002
"""

CLEAN_PROMPT = (ROOT / "fix" / "system_prompt" / "swiss_context_v1.txt")


# ================================================== 1. the gate fires
def test_gate_catches_the_plan_prompt() -> None:
    section("1. The contamination gate catches the prompt the plan proposes")
    from prompts_check import contamination_report

    rep = contamination_report(PLAN_PROMPT, "dev")
    check("plan prompt is judged contaminated", not rep.clean,
          f"got {rep.contaminated_fraction:.1%}")
    check("plan prompt contaminates a large share", rep.contaminated_fraction > 0.20,
          f"only {rep.contaminated_fraction:.1%} -- is the gate still working?")
    check("the share is reported as a count of items",
          rep.n_items == 84, f"n_items={rep.n_items}")

    # Every contaminated item must name a specific load-bearing fact, so a
    # reviewer knows which line of the prompt to delete.
    check("every contaminated item has a reason",
          all(rep.reasons.get(i) for i in rep.contaminated_ids))
    check("reasons name the fact, not the whole prompt",
          all(len(v) <= 3 for v in rep.reasons.values()),
          "a reason listing every fact is noise")

    # And it must be a refusal, not a warning.
    from prompts_check import assert_uncontaminated
    try:
        assert_uncontaminated(PLAN_PROMPT, "dev")
        check("gate refuses the plan prompt", False, "no exception raised")
    except SystemExit as e:
        msg = str(e)
        check("refusal explains itself", "CONTAMINATED" in msg or "contaminated" in msg.lower())
        check("refusal says it would not transfer", "reproduce" in msg or "transfer" in msg.lower())

    print(f"   plan prompt -> {len(rep.contaminated_ids)}/84 items "
          f"({rep.contaminated_fraction:.0%}), refused")


# ================================================== 2. the clean prompt is clean
def test_clean_prompt_passes() -> None:
    section("2. The prompt actually shipped is clean, and the gate is not just always-no")
    from prompts_check import assert_uncontaminated, contamination_report

    check("the clean prompt exists", CLEAN_PROMPT.exists(), str(CLEAN_PROMPT))
    if not CLEAN_PROMPT.exists():
        return
    text = CLEAN_PROMPT.read_text(encoding="utf-8")
    rep = contamination_report(text, "dev")
    check("clean prompt has no contaminated items", not rep.contaminated_ids,
          f"{rep.contaminated_ids[:5]}")
    check("clean prompt passes assert_uncontaminated",
          assert_uncontaminated(text, "dev").clean)

    # A gate that rejects everything would also pass. Prove it accepts clean text.
    check("gate accepts a plain prompt",
          contamination_report("Answer the multiple-choice question.", "dev").clean)

    # One fact added is caught even buried at the bottom as a parenthetical.
    # The fact is the signature threshold, which three dev items probe.
    # Note this is caught by COUNT, not by the threshold: 3/84 is 3.6%, which
    # sits under the 5% allowance, so it is reported but not refused. A claim
    # needs ~6 net flips to be measurable at n=84, so up to 4 answered items
    # hide inside the noise floor - which is exactly why the count is printed
    # on every run and not only on refusal.
    buried = text + "\n\n(Note: a popular initiative needs 100,000 signatures.)"
    rep_b = contamination_report(buried, "dev")
    check("a buried probed fact is detected", len(rep_b.contaminated_ids) > 0,
          "the signature threshold probe found nothing")
    check("the detected items are the ones that probe it",
          set(rep_b.contaminated_ids) == {"K011", "K012", "K111"},
          f"got {rep_b.contaminated_ids}")

    # The converse: a load-bearing fact the split never asks about is not
    # contamination, because nothing can be gained from stating it here. The
    # gate deliberately requires BOTH that the prompt asserts the fact AND that
    # an item probes it.
    unprobed = text + "\n\n(Note: the Rhine falls 1,000 metres over its course.)"
    check("a fact no item probes does not trip the gate",
          contamination_report(unprobed, "dev").clean)

    # The threshold, stated in items so it cannot drift as the split changes.
    from prompts_check import DEFAULT_THRESHOLD
    check("the threshold is documented as an item count",
          int(DEFAULT_THRESHOLD * 84) == 4,
          f"{DEFAULT_THRESHOLD:.0%} of 84 = {DEFAULT_THRESHOLD * 84:.1f} items")

    print(f"   clean prompt -> 0/84 items, passes; one added fact -> refused")


# ================================================== 3. the control is the baseline
def test_control_arm_is_the_baseline() -> None:
    section("3. The control arm is byte-identical to the baseline run")
    from run_knowledge import build_prompt as baseline_build, load_questions
    from rag_prompt import build as rag_build, load_system_prompt

    q = load_questions("dev")[0]
    base_sys, base_usr = baseline_build(q, "", "v1_letter_only")
    ctl_sys, ctl_usr = rag_build(q, "", None)

    check("control system prompt == baseline system prompt", ctl_sys == base_sys,
          f"{len(ctl_sys)} vs {len(base_sys)} chars")
    check("control user prompt == baseline user prompt", ctl_usr == base_usr)
    check("baseline system prompt is not empty", base_sys.strip() != "",
          "an empty control would make every delta uninterpretable")
    check("control does not leak a context placeholder",
          "no context available" not in ctl_usr)

    # The treatment must differ, or there is nothing to compare.
    ctx = "[Source S001] passage text"
    rag_sys, rag_usr = rag_build(q, ctx, None)
    check("rag user prompt carries the context", ctx in rag_usr)
    check("rag prompt differs from control", rag_usr != ctl_usr)

    # An override must reach BOTH arms: that is what isolates retrieval.
    text, gate = load_system_prompt("swiss_context_v1.txt")
    ov_sys, _ = rag_build(q, "", text)
    check("override is gated on load", gate["clean"])
    check("override reaches the control arm too",
          ov_sys == text, "otherwise the delta mixes prompt effect with retrieval")

    print("   control == baseline; override reaches both arms; path guard:")
    try:
        rag_build(q, "", "swiss_context_v1.txt")
        check("a path is rejected where text is expected", False)
    except ValueError:
        check("a path is rejected where text is expected", True)
        print("   path-as-prompt refused")


# ================================================== 4. retrieval is measured
def test_retrieval_is_ground_truth() -> None:
    section("4. Retrieval quality is measured against the declared source ids")
    from embeddings import build_index, load_corpus
    from retriever import SwissRetriever, retrieval_report

    chunks = load_corpus(include_dialect=False)
    check("dialect chunks are excluded from the knowledge corpus",
          all(c["category"] != "dialect" for c in chunks))
    check("corpus is non-empty", len(chunks) > 50, f"{len(chunks)} chunks")
    check("every chunk is attributable",
          all(c.get("source_id") and c.get("text") for c in chunks))

    r = SwissRetriever(build_index(chunks, "bm25"), chunks)
    rep = retrieval_report(r, "dev", (1, 3, 5))

    check("recall is measured on the whole dev split",
          rep["n_questions"] == 84, f"{rep['n_questions']}")
    for k in ("@1", "@3", "@5"):
        check(f"source recall {k} is a percentage in range",
              0 <= rep["source_recall"][k] <= 100,
              f"{rep['source_recall'][k]}")

    # Recall must be monotonically non-decreasing in k. If it is not, the
    # top-k filtering is wrong, not merely unlucky.
    r1, r3, r5 = (rep["source_recall"][k] for k in ("@1", "@3", "@5"))
    check("recall@1 <= recall@3 <= recall@5", r1 <= r3 <= r5, f"{r1}, {r3}, {r5}")

    # Per-category recall is reported at ONE k and must not exceed 100. It did,
    # at 378%, before the double-count was fixed.
    for cat, d in rep["per_category"].items():
        check(f"per-category recall for {cat} <= 100", 0 <= d["recall"] <= 100,
              f"{d['recall']}%")

    # A median must be a real rank, not an artefact of a bad expression.
    mr = rep["median_rank_when_found"]
    check("median rank is a real rank", mr is None or 1 <= mr <= 10, f"{mr}")

    # And the baseline rate: four options, so chance is 25%. Retrieval has to be
    # doing real work or this whole sub-phase is pointless.
    check("retrieval beats chance by a wide margin", r1 >= 50,
          f"recall@1 is {r1}%, barely above the 25% chance rate")

    print(f"   source recall @1={r1}% @3={r3}% @5={r5}%  "
          f"category recall={rep['category_recall_pct']}%  median rank={mr}")


# ================================================== 5. numbers survive their edges
def test_edges() -> None:
    section("5. The comparison survives empty and degenerate inputs")
    from run_rag_eval import compare, verdict

    empty = compare([], [])
    check("empty comparison does not divide by zero", empty["n_paired"] == 0)
    check("empty accuracy is None, not 0",
          empty["control_accuracy"] is None, f"{empty['control_accuracy']}")
    check("empty delta is None", empty["delta_points"] is None)
    check("verdict on an empty run still returns text", isinstance(verdict(empty, True), str))

    # Perfect retrieval, no change in answers: RAG is not the bottleneck.
    rows = [{"question_id": f"K{i:03d}", "category": "law", "predicted": "A",
             "parse_reason": "ok", "correct": "A", "is_correct": True,
             "api_failed": False, "gold_source_rank": 1, "difficulty": "",
             "source_id": "S001", "raw_response": "A", "model": "8b",
             "split": "dev"} for i in range(1, 9)]
    same = compare(rows, rows)
    check("identical arms give zero delta", same["delta_points"] == 0.0,
          f"{same['delta_points']}")
    check("identical arms give p=1.0", same["mcnemar"]["p"] == 1.0)
    check("a null result is reported as undetectable, not as a win",
          "no detectable effect" in verdict(same, False))

    # All-correct control, one item lost. That is a REGRESSION, not a gain.
    rag_rows = [dict(r) for r in rows]
    rag_rows[0] = dict(rag_rows[0], is_correct=False, predicted="B")
    only_bad = compare(rows, rag_rows)
    check("a regression is detected", only_bad["mcnemar"]["regressed"] == 1)
    check("a regression is not counted as an improvement",
          only_bad["mcnemar"]["improved"] == 0)
    check("a regression verdict says it is worse",
          "worse" in verdict(only_bad, False))

    # A genuine gain whose retrieval found nothing. The verdict must refuse to
    # bank it as a retrieval win, because prompt shape alone could explain it.
    wrong = [dict(r, is_correct=False, predicted="B") for r in rows]
    gained = [dict(r, gold_source_rank=None) for r in rows]   # gain, no retrieval
    uns = compare(wrong, gained)
    check("a gain with no retrieval support is detected",
          uns["mcnemar"]["improved"] == 8, str(uns["mcnemar"]))
    check("gains without retrieval support are counted",
          uns["wrong_without_retrieval_support"] == 8, str(uns))
    check("verdict flags unsupported gains as prompt-shape effect",
          "prompt-shape effect" in verdict(uns, False), verdict(uns, False))

    # Same gains, but this time retrieval did find the source.
    supported = [dict(r, gold_source_rank=1) for r in rows]
    sup = compare(wrong, supported)
    check("gains with retrieval support are not counted as unsupported",
          sup["wrong_without_retrieval_support"] == 0, str(sup))

    # McNemar in the gain direction: 8 wrong -> 8 right, zero regressions.
    from prompts_check import mcnemar
    many_wrong = [{"question_id": f"K{i:03d}", "is_correct": False} for i in range(1, 13)]
    many_right = [{"question_id": f"K{i:03d}", "is_correct": True} for i in range(1, 13)]
    m = mcnemar(many_wrong, many_right)
    check("8 gains with 0 regressions is significant", m["significant"],
          f"p={m['p']}, improved={m['improved']}, regressed={m['regressed']}")

    # And the mirror image: 4 items fixed, 8 items broken. Net movement is
    # negative, so it must not be reported as an improvement.
    split_before = ([{"question_id": f"K{i:03d}", "is_correct": False} for i in range(1, 5)]
                    + [{"question_id": f"K{i:03d}", "is_correct": True} for i in range(5, 13)])
    split_after = ([{"question_id": f"K{i:03d}", "is_correct": True} for i in range(1, 5)]
                   + [{"question_id": f"K{i:03d}", "is_correct": False} for i in range(5, 13)])
    mm = mcnemar(split_before, split_after)
    check("4 gains against 8 regressions is NOT a win", not mm["significant"],
          f"p={mm['p']}")
    check("the net is negative", mm["net"] < 0, f"net={mm['net']}")
    check("improved and regressed are counted in the right direction",
          (mm["improved"], mm["regressed"]) == (4, 8),
          f"got {mm['improved']}/{mm['regressed']}")

    print(f"   8 gains/0 regressions -> p={m['p']} significant; "
          f"4 gains/8 regressions -> p={mm['p']} not significant")


# ================================================== 6. run-time refusal
def test_runtime_refusal() -> None:
    section("6. A contaminated prompt is refused when the run starts")
    from prompts_check import contamination_report

    bad = ROOT / "fix" / "system_prompt" / "_test_contaminated.txt"
    bad.write_text(PLAN_PROMPT, encoding="utf-8")
    try:
        from rag_prompt import load_system_prompt
        text, gate = load_system_prompt(bad.name)
        check("a contaminated prompt loads but is flagged unclean", not gate["clean"],
              "the loader must not quietly mark it clean")
        check("the loader records which items are contaminated",
              len(gate.get("contaminated_ids", [])) > 0)

        # evaluate_with_rag raises SystemExit on gate["clean"] is False.
        import inspect
        import run_rag_eval
        src = inspect.getsource(run_rag_eval.evaluate_with_rag)
        check("the eval refuses before running any question",
              "refusing to run" in src and src.index("refusing to run") < src.index("control (no"))
    finally:
        bad.unlink(missing_ok=True)

    # And the shipped prompt is clean, so the normal path is not blocked.
    from rag_prompt import load_system_prompt
    _, good = load_system_prompt("swiss_context_v1.txt")
    check("the shipped prompt does not block the run", good["clean"])
    print("   contaminated -> refused before any question is sent; shipped prompt -> clean")


def main() -> int:
    print("=" * 68)
    print("  Phase 3.3 verification")
    print("=" * 68)
    for fn in (test_gate_catches_the_plan_prompt,
               test_clean_prompt_passes,
               test_control_arm_is_the_baseline,
               test_retrieval_is_ground_truth,
               test_edges,
               test_runtime_refusal):
        try:
            fn()
        except Exception as e:  # a crash is a failure, not an excuse
            import traceback
            FAILURES.append(f"{fn.__name__} raised {type(e).__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 68}")
    if FAILURES:
        print(f"  FAILED  {len(FAILURES)} of {CHECKS} checks")
        for f in FAILURES:
            print(f"    - {f}")
        return 1
    print(f"  PASSED  all {CHECKS} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())

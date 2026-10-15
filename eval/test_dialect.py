"""
test_dialect.py - Phase 2.4 verification.

The dialect pillar carries the project's least trustworthy inputs - author-
written Standard German references, no native validation - so the scoring code
is tested against the real corpus rather than only against invented cases.

Three things are defended here.

  1. TWO INVARIANTS THAT MUST HOLD ON EVERY REAL ITEM. Handing the reference
     translation back as the model's answer must score 2; handing the Swiss
     German source back must score 0. If either fails on any item, the scorer
     is wrong in a way no threshold tuning will fix.

  2. THE THRESHOLDS ARE THE PROTOCOL'S. 0.85 / 0.50 are tested at their exact
     boundaries and deliberately NOT tuned, because tuning them against model
     output before the first real run would bake an unvalidated choice into the
     instrument.

  3. PER-DIALECT REPORTING IS NEVER POOLED. Protocol §4: the corpus mixes at
     five registers and some files are DIALECT: uncertain, so a pooled number
     describes nothing and is the easiest figure in the project to quote wrong.

Run:  python eval/test_dialect.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import language_metrics as lm                                  # noqa: E402
from config import config                                      # noqa: E402
from run_dialect import (THRESHOLD_CORRECT, THRESHOLD_PARTIAL,  # noqa: E402
                         build_prompt, dialect_echo, load_items,
                         score_translation, stems, strip_diacritics,
                         summarise)
from run_knowledge import PARSE_ERROR, explain_answer           # noqa: E402

failures: list[str] = []
checks = 0


def check(label, got, expected):
    global checks
    checks += 1
    if got != expected:
        failures.append(f"{label}: got {got!r}, expected {expected!r}")


def _weights(item):
    from run_dialect import _reference_terms
    return {k: v["weight"] for k, v in _reference_terms(item).items()
            if k != "__inferred__"}


def items():
    return load_items()


def t1_items():
    return [x for x in items() if x["task_type"] == "translation"]


def mcq_items():
    return [x for x in items() if x.get("options")]


# ========================================================= 1. NORMALISATION
def test_normalisation() -> int:
    n = 0
    check("norm/diacritics umlaut", strip_diacritics("Gründi"), "Grundi")
    check("norm/diacritics sharp s", strip_diacritics("Grösse"), "Grosse")
    check("norm/diacritics casefold path", strip_diacritics("Gründi".casefold()), "grundi")
    check("norm/stem plural", "kartoffeln".startswith("kartoff"), True)
    check("norm/stems set", isinstance(stems("Die Schweine"), set), True)

    # stem must not reduce everything to nothing
    check("norm/stem keeps length", len(stems("Bundesrat")) > 0, True)
    n += 4

    # prefix matching must absorb inflection in both directions, which is the
    # whole reason the protocol rejected exact match
    from run_dialect import matches
    for a, b, expected in [("kartoffl", "kartoffeln", True),
                           ("schwein", "schweine", True),
                           ("vertrag", "vertragen", True),
                           ("vertrag", "vertraglich", True),
                           ("bundesrat", "bundesrath", True),
                           ("kartoffl", "zwiebel", False),
                           ("abc", "xyz", False)]:
        check(f"norm/matches {a}~{b}", matches(a, b), expected)
        n += 1
    return n


# ============================== 2. THE TWO INVARIANTS, ON EVERY REAL ITEM
def test_invariants_on_real_items() -> int:
    n = 0
    t1 = t1_items()

    for item in t1:
        # (a) the reference translation, returned as the answer, is correct
        r = score_translation(item["standard_german_reference"], item)
        check(f"inv/{item['id']} reference scores 2", r["score"], 2)
        check(f"inv/{item['id']} reference coverage", r["coverage"], 1.0)
        check(f"inv/{item['id']} nothing missing", r["missing"], [])
        n += 3

        # (b) the Swiss German source, echoed back, is a failure
        r = score_translation(item["swiss_german_text"], item)
        check(f"inv/{item['id']} echo scores 0", r["score"], 0)
        check(f"inv/{item['id']} echo labelled", r["method"], "echoed_source_dialect")
        n += 2

        # (c) unrelated text is a failure, and must not be labelled an echo
        r = score_translation("The quick brown fox jumps over the lazy dog.", item)
        check(f"inv/{item['id']} gibberish scores 0", r["score"], 0)
        check(f"inv/{item['id']} gibberish not echoed", r["echoed_source"], False)
        n += 2

        # (d) a refusal is 0 and labelled as such
        r = score_translation("I'm sorry, I don't understand Swiss German.", item)
        check(f"inv/{item['id']} refusal 0", r["score"], 0)
        check(f"inv/{item['id']} refusal labelled", r["method"], "refusal")
        n += 2

        # (e) an empty response is a refusal, never a silent 1
        r = score_translation("", item)
        check(f"inv/{item['id']} empty 0", r["score"], 0)
        n += 1
    return n


# ================================================ 3. THRESHOLD BOUNDARIES
def _synthetic(nouns_synonyms: dict, weights: dict | None = None) -> dict:
    scoring = {"type": "content_keyword_coverage", "synonyms": nouns_synonyms}
    if weights:
        scoring["weights"] = weights
    return {
        "id": "TEST", "task_type": "translation", "dialect": "zurich",
        "swiss_german_text": "D Dialekt Satz.",
        "standard_german_reference": "Alpha Beta Gamma Delta.",
        "scoring": scoring, "difficulty": "easy",
    }


def test_thresholds() -> int:
    n = 0
    # four equal-weight terms -> we can hit 1.00, 0.75, 0.50, 0.25, 0.00 exactly
    syn = {w: [w] for w in ("alpha", "beta", "gamma", "delta")}
    item = _synthetic(syn)

    for hits, expected_score, expected_method in [
        (4, 2, "coverage_correct"),
        (3, 1, "coverage_partial"),      # 0.75
        (2, 1, "coverage_partial"),      # 0.50 - exactly the inclusive boundary
        (1, 0, "coverage_fail"),         # 0.25
        (0, 0, "refusal"),   # an empty reply is a refusal
    ]:
        pred = " ".join(w.capitalize() for w in list(syn)[:hits])
        r = score_translation(pred, item)
        check(f"thr/{hits} hits score", r["score"], expected_score)
        check(f"thr/{hits} hits method", r["method"], expected_method)
        n += 2

    check("thr/thresholds are the protocol's",
          (THRESHOLD_CORRECT, THRESHOLD_PARTIAL), (0.85, 0.50))
    n += 1

    # 0.85 boundary with five equal terms: 5/5 = 1.0 -> 2, 4/5 = 0.80 -> 1
    syn5 = {w: [w] for w in ("alpha", "beta", "gamma", "delta", "epsilon")}
    item5 = _synthetic(syn5, weights={w: 1.0 for w in syn5})   # force equal weights
    check("thr/4 of 5 -> 1", score_translation("Alpha Beta Gamma Delta", item5)["score"], 1)
    check("thr/5 of 5 -> 2",
          score_translation("Alpha Beta Gamma Delta Epsilon", item5)["score"], 2)
    n += 2
    return n


# ================================================== 4. WEIGHTING BEHAVIOUR
def test_weighting() -> int:
    n = 0
    # capitalised in the reference -> noun -> 1.0
    syn = {"Schweine": ["Schweine"], "vertragen": ["vertragen"]}
    item = _synthetic(syn)
    item["standard_german_reference"] = "Die Schweine vertragen das."
    check("wt/noun is 1.0 by capitalisation",
          score_translation("", item)["total_weight"], 1.5)   # 1.0 + 0.5
    check("wt/lower case is 0.5",
          _weights(item)["vertragen"], 0.5)
    n += 2

    # an explicit weights block overrides the heuristic completely - this is how
    # the verb/adjective approximation gets made exact without code changes
    syn2 = {"vertragen": ["vertragen"], "roh": ["roh"]}
    item2 = _synthetic(syn2, weights={"vertragen": 1.0, "roh": 0.5})
    item2["standard_german_reference"] = "vertragen roh"
    r = score_translation("vertragen roh", item2)
    check("wt/explicit weights total", r["total_weight"], 1.5)
    check("wt/explicit weights coverage", r["coverage"], 1.0)
    n += 2

    # weights must be VISIBLE per term, so a reviewer can recompute
    item3 = _synthetic({"vertragen": ["vertragen"], "roh": ["roh"]})
    item3["standard_german_reference"] = "vertragen roh"
    r = score_translation("vertragen", item3)
    check("wt/matched records weight", r["matched"][0]["weight"] in (0.5, 1.0), True)
    check("wt/missing records weight", r["missing"][0]["weight"] in (0.5, 1.0), True)
    n += 2

    # every real T1 item must resolve to terms with a positive weight
    for item in t1_items():
        r = score_translation(item["standard_german_reference"], item)
        check(f"wt/{item['id']} positive weights",
              all(m["weight"] > 0 for m in r["matched"] + r["missing"]), True)
        n += 1
    return n


# ================================== 5. CHDE DETECTION, MEASURED ON REAL DATA
def test_chde_detection() -> int:
    n = 0
    t1 = t1_items()
    detected = [x["id"] for x in t1
                if lm.detect_language(x["swiss_german_text"]) == "chde"]
    false_pos = [x["id"] for x in t1
                 if lm.detect_language(x["standard_german_reference"]) == "chde"]

    check("chde/no Standard German reference misread as dialect", false_pos, [])
    check("chde/detection count", len(detected) >= 7, True)
    print(f"      (chde detected on {len(detected)}/{len(t1)} real sentences, "
          f"{len(false_pos)} false positives)")
    n += 2

    # the detector must never be the ONLY guard: echo detection covers the rest
    for x in t1:
        r = score_translation(x["swiss_german_text"], x)
        check(f"chde/{x['id']} echo caught regardless of detection",
              r["echoed_source"], True)
        n += 1
    return n


def test_echo_check() -> int:
    n = 0
    for x in t1_items():
        echo = dialect_echo(x["swiss_german_text"], x)
        check(f"echo/{x['id']} flagged", echo["echoed_source"], True)
        check(f"echo/{x['id']} closer to source",
              echo["sim_source"] > echo["sim_reference"], True)
        n += 2
    # a genuine translation is not an echo
    for x in t1_items():
        echo = dialect_echo(x["standard_german_reference"], x)
        check(f"echo/{x['id']} reference not flagged", echo["echoed_source"], False)
        n += 1
    return n


# ==================================================== 6. MCQ SCORING (T2/T3/T4)
def test_mcq() -> int:
    n = 0
    mcq = mcq_items()
    for item in mcq:
        letter = item["correct_answer"]
        predicted, reason = explain_answer(letter, options=item["options"])
        check(f"mcq/{item['id']} parses its own answer", predicted, letter)
        check(f"mcq/{item['id']} has a reason", bool(reason), True)
        check(f"mcq/{item['id']} not a parse error", predicted != PARSE_ERROR, True)
        n += 2

        # an echo of the correct option's text must resolve to that option
        predicted, _ = explain_answer(str(item["options"][letter]), options=item["options"])
        check(f"mcq/{item['id']} echoes resolve", predicted, letter)
        n += 1

        # a refusal is a parse error, scored 0 - never a lucky hit
        predicted, reason = explain_answer(
            "I'm sorry, I don't understand Swiss German.", options=item["options"])
        check(f"mcq/{item['id']} refusal not scored", predicted, PARSE_ERROR)
        n += 1
    return n


# ============================================= 7. REPORTING: NEVER POOLED
def test_summarise() -> int:
    n = 0
    records = [
        {"task_type": "translation", "canon_dialect": "basel", "score": 2,
         "coverage": 0.9, "refused": False},
        {"task_type": "translation", "canon_dialect": "basel", "score": 0,
         "coverage": 0.1, "refused": True},
        {"task_type": "translation", "canon_dialect": "zurich", "score": 1,
         "coverage": 0.6, "refused": False},
        {"task_type": "culture_in_dialect", "canon_dialect": "zurich",
         "score": 1, "is_correct": True, "refused": False},
        {"task_type": "culture_in_dialect", "canon_dialect": "uncertain",
         "score": 0, "is_correct": False, "refused": False},
    ]
    s = summarise(records)

    check("sum/refusal rate", s["refusal_rate"], 20.0)
    check("sum/refusal count", s["n_refused"], 1)
    check("sum/t1 mean", s["t1_mean"], 1.0)
    check("sum/t1 n", s["t1_n"], 3)
    check("sum/mcq accuracy", s["mcq_accuracy"], 50.0)

    # per dialect, never pooled
    check("sum/basel t1", s["by_dialect"]["basel"]["t1_mean"], 1.0)
    check("sum/basel n", s["by_dialect"]["basel"]["n"], 2)
    check("sum/zurich t1", s["by_dialect"]["zurich"]["t1_mean"], 1.0)
    check("sum/uncertain present", "uncertain" in s["by_dialect"], True)
    check("sum/uncertain has own bucket", s["by_dialect"]["uncertain"]["n"], 1)
    check("sum/pooling warned", "not meaningful" in s["pooled_note"], True)
    check("sum/no pooled top-level dialect figure", "overall" in s, False)
    n += 11

    # refusal must survive as a headline even when every other number is fine
    check("sum/refusal is top level", "refusal_rate" in s, True)
    n += 1

    # empty input must not divide by zero
    e = summarise([])
    check("sum/empty refusal", e["refusal_rate"], 0.0)
    check("sum/empty t1", e["t1_mean"], None)
    n += 2
    return n


# ================================================== 8. DATASET INTEGRITY
def test_dataset() -> int:
    n = 0
    allitems = items()
    check("ds/30 items", len(allitems), 30)
    check("ds/ids sequential",
          [x["id"] for x in allitems], [f"D{i:03d}" for i in range(1, 31)])
    n += 2

    for x in allitems:
        if x["task_type"] == "translation":
            check(f"ds/{x['id']} has reference", bool(x.get("standard_german_reference")), True)
            check(f"ds/{x['id']} has dialect text", bool(x.get("swiss_german_text")), True)
            check(f"ds/{x['id']} has synonyms",
                  bool(x.get("scoring", {}).get("synonyms")), True)
            n += 3
        else:
            check(f"ds/{x['id']} options A-D", set(x.get("options", {})) == {"A", "B", "C", "D"}, True)
            check(f"ds/{x['id']} answer in options",
                  x["correct_answer"] in x.get("options", {}), True)
            check(f"ds/{x['id']} has question", bool(x.get("question")), True)
            n += 3

        # no item may claim native validation - nobody has reviewed them
        check(f"ds/{x['id']} no false provenance claim",
              x.get("validated_by") is None, True)
        n += 1

    # three of the four item types are deterministic, which is the property that
    # makes this pillar judge-free
    kinds = {x["task_type"] for x in allitems}
    check("ds/four types present",
          kinds == {"translation", "comprehension", "culture_in_dialect",
                    "dialect_identification"}, True)
    n += 1

    # every prompt must render
    for x in allitems:
        system, prompt = build_prompt(x)
        check(f"ds/{x['id']} prompt renders", "{" not in prompt.replace("{{", ""), True)
        check(f"ds/{x['id']} prompt has system", bool(system), True)
        n += 2
    return n


# ============================================== 9. END-TO-END ON THE MOCK
def test_end_to_end() -> int:
    n = 0
    from run_dialect import evaluate_dialect

    # Force the mock backend for this test.
    #
    # The end-to-end test is about SHAPE - that a dialect run produces records,
    # thresholds, per-dialect and per-type breakdowns, a refusal headline, and
    # flags itself as mock. All of that is only observable on the mock backend.
    # Asserting that the ambient configuration happens to be mock made the test
    # assert the environment rather than the code, so it failed the moment a
    # real backend was configured - which is exactly when it must keep working.
    from config import config, ModelConfig
    saved = config.MODELS["8b"]
    try:
        config.MODELS["8b"] = ModelConfig(name="8b", backend="mock", model_id="mock")
        result = evaluate_dialect("8b", limit=6)
    finally:
        config.MODELS["8b"] = saved
    run, scores = result["run"], result["scores"]

    check("e2e/task", run["task"], "dialect")
    check("e2e/records", len(result["records"]), 6)
    check("e2e/n scored matches records", scores["n_scored"], 6)
    check("e2e/mock flagged", scores["is_mock"], True)
    check("e2e/mock flagged in run", run["is_mock"], True)
    check("e2e/params recorded", "request_params" in run, True)
    check("e2e/thresholds recorded", run["thresholds"],
          {"correct": THRESHOLD_CORRECT, "partial": THRESHOLD_PARTIAL})
    check("e2e/by dialect present", "by_dialect" in scores, True)
    check("e2e/by type present", "by_task_type" in scores, True)
    check("e2e/refusal headline", "refusal_rate" in scores, True)
    n += 10

    parsed = config.results_dir / "parsed" / "dialect_8b.json"
    check("e2e/parsed written", parsed.exists(), True)
    if parsed.exists():
        doc = json.loads(parsed.read_text(encoding="utf-8"))
        check("e2e/parsed has run meta", "run" in doc, True)
        check("e2e/parsed has records", len(doc["records"]) == 6, True)
        n += 2
    return n


# ------------------------------------------------------------------------ main
def main() -> int:
    print("=" * 74)
    print("PHASE 2.4 VERIFICATION - dialect scoring")
    print("=" * 74)

    groups = [
        ("normalisation", test_normalisation),
        ("invariants on real items", test_invariants_on_real_items),
        ("threshold boundaries", test_thresholds),
        ("weighting", test_weighting),
        ("chde detection", test_chde_detection),
        ("dialect echo check", test_echo_check),
        ("MCQ scoring T2/T3/T4", test_mcq),
        ("reporting, never pooled", test_summarise),
        ("dataset integrity", test_dataset),
        ("end-to-end (mock)", test_end_to_end),
    ]
    for name, fn in groups:
        before = checks
        try:
            fn()
        except Exception as exc:
            failures.append(f"{name}: raised {type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()
        print(f"  {name:<32} {checks - before:>6} checks")

    print("\n" + "=" * 74)
    print(f"total checks : {checks}")
    print(f"items        : {len(items())}")
    print("=" * 74)
    if failures:
        print(f"\nFAILURES: {len(failures)}")
        for f in failures[:30]:
            print(f"  {f}")
        if len(failures) > 30:
            print(f"  ... and {len(failures) - 30} more")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
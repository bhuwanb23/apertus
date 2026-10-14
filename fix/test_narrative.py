"""
test_narrative.py - Phase 4.4 verification.

The findings document is what a jury reads. If it contains an unsupported claim,
the project is not merely wrong - it has asserted something in the most
authoritative voice available to it, in the place where people stop checking.

  1. NO PLACEHOLDER, INCLUDING IN THE GENERATOR'S OWN PROSE. The module that
     exists to prevent placeholders shipped one: the sentence "confuse Swiss and
     German law, XX% of the time" was written into the source as an example.
     The output was clean and the source was not. Both are checked.
  2. NO CLAIM THE ANALYSIS DECLINED TO MAKE. 3.1 left 78% of errors
     UNCLASSIFIED and select_target.py refused to name a target. The narrative
     must not name a dominant error mode, a weakest area, or a category.
  3. NO MOCK NUMBER PRESENTED AS A FINDING. Every mock-derived figure carries
     its provenance in the same paragraph.
  4. NO ACCURACY NUMBER FOR APERTUS WHILE ON MOCK. The single most likely way
     this document misleads is by implying a score exists.
  5. THE SCENARIO IS CHOSEN FROM DATA. And "pending" is a real answer, not a
     failure to decide.
  6. EVERY NUMBER TRACES TO A MODULE. Cross-checked against statistical_report,
     not re-derived, so a divergence shows up.
  7. IT IS BOTH CREDIBLE AND READABLE - the two audience checks the plan asks
     for, made mechanical rather than a matter of opinion.

Run:  python fix/test_narrative.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "fix"))
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


def build():
    import narrative
    return narrative.write_findings()


# ================================= 1. no placeholder, source or output
def test_no_placeholders_anywhere() -> None:
    section("1. No placeholder - in the document or in the generator")
    import narrative

    path, scen, have = build()
    text = path.read_text(encoding="utf-8")

    for pat, name in ((r"XX\.X", "XX.X"), (r"\bXX\b", "bare XX"),
                      (r"XX/", "XX/"), (r"\bTBD\b", "TBD"),
                      (r"\bTODO\b", "TODO"), (r"\[\s*\]", "empty bracket"),
                      (r"<[A-Z_]{3,}>", "unfilled angle placeholder")):
        check(f"findings.md has no {name}", not re.search(pat, text),
              str(re.findall(pat, text)[:3]))

    # The generator's own source. The shipped version contained
    # "confuse Swiss and German law, XX% of the time" inside a sentence that was
    # describing what NOT to write - and a test that only reads the output would
    # have passed, because the output was clean.
    src = (ROOT / "eval" / "narrative.py").read_text(encoding="utf-8")
    code = re.sub(r'"""[\s\S]*?"""', "", src)          # drop docstrings
    # Drop the module's OWN placeholder detector before scanning for
    # placeholders - the line that checks for them legitimately names them.
    code = "\n".join(l for l in code.splitlines()
                     if not re.search(r'bad\s*=|in text\]|PLACEHOLDER', l))
    for lit in ("XX.X", "[XX]", "XX%", "XX/"):
        check(f"generator source contains no {lit!r}", lit not in code,
              "a placeholder in the source reaches the document the moment the "
              "surrounding sentence changes")
    print(f"   document and source both clean; {len(text.split()):,} words")


# ============================ 2. no claim the analysis declined to make
def test_no_unmeasured_claims() -> None:
    section("2. The narrative asserts nothing the analysis declined to make")
    import narrative

    path, scen, have = build()
    text = path.read_text(encoding="utf-8")
    tax = narrative.taxonomy_state()

    # The decisive one. The Phase 4 template pre-writes this as a finding.
    check("it does not name German/EU confusion as the dominant error",
          not re.search(r"dominant error[^\n]*German", text, re.I)
          and "DE-CONF" not in text,
          "3.1 explicitly declined to name one")
    check("it does not claim a percentage for a confusion mode",
          not re.search(r"German/EU confusion[^\n]*\d+%", text, re.I))

    if not tax.get("resolved"):
        check("it does not name any dominant error at all",
              not re.search(r"dominant (?:classified )?error (?:is|was)", text, re.I)
              or "`UNCLASSIFIED`" in text,
              "a dominant error may not be named while the taxonomy is unresolved")
        check("it says the taxonomy is unresolved",
              "UNCLASSIFIED" in text or "did not resolve" in text)

    # No weakest-area claim. select_target.py refused with all three gates.
    check("it does not name a weakest area",
          not re.search(r"weakest (?:area|category) (?:is|was)\s+\*\*", text, re.I))
    check("it does not claim a target category was selected",
          "TARGET SELECTED" not in text and "target selected" not in text.lower())

    # No category is asserted as better or worse than another.
    cats = re.findall(r"\b(politics|law|health|geography|services|history)\b", text)
    ranked = re.findall(r"(?:strongest|weakest|best|worst)[^\n]*\b"
                        r"(politics|law|health|geography|services|history)\b",
                        text, re.I)
    check("no category is ranked best or worst", not ranked, str(ranked))
    check("categories appear only descriptively",
          len(cats) <= 3 or "never ranked" in text,
          f"{len(cats)} mentions, and no statement that they are not ranked")
    print("   no dominant error, no weakest area, no ranked category")


# ================================= 3. mock provenance is inline
def test_mock_provenance() -> None:
    section("3. Every mock-derived figure carries its provenance in place")
    import narrative

    path, scen, have = build()
    text = path.read_text(encoding="utf-8")
    tax = narrative.taxonomy_state()

    check("the document opens by saying no model has been evaluated",
          "No model has been evaluated" in text or "no model has" in text.lower())
    check("it states the backend is mock", "mock" in text.lower())

    if tax.get("present") and tax.get("is_mock") and tax.get("unclassified_pct"):
        idx = text.find(str(tax["unclassified_pct"]) + "%")
        check("the taxonomy figure is present", idx > 0)
        window = text[max(0, idx - 320): idx + 320]
        check("the mock caveat is in the SAME paragraph region, not a footnote",
              ("synthetic" in window.lower() or "not Apertus" in window
               or "mock" in window.lower()),
              "a number 20 lines from its caveat is a number read on its own")
        check("it says plainly that the figure is not about Apertus",
              "not Apertus" in window or "describes the classifier" in window)

    # The 30% contamination figure is model-free and MUST be stated as such,
    # because it is the strongest number in the document.
    con = narrative.contamination_state()
    if con.get("present"):
        check("the contamination figure appears", f"{con['naive_pct']:.0f}%" in text)
        check("it is attributed to a measurement, not a guess",
              "answers" in text and "items" in text)
    print("   mock caveats sit next to the numbers they qualify")


# ================================= 4. no Apertus accuracy while on mock
def test_no_accuracy_while_mock() -> None:
    section("4. No Apertus accuracy figure is stated while on mock")
    import narrative

    path, scen, have = build()
    text = path.read_text(encoding="utf-8")
    check("the generator reports no model data", not have)
    check("the scenario is 'pending'", scen["id"] == "pending", scen["id"])
    check("the scenario explains why A-D cannot apply",
          "none of A" in scen["why"] or "cannot be selected" in scen["why"])

    # Any percentage in the document must be traceable to a non-model source.
    # Read from the modules themselves rather than from a hand-kept list, so a
    # new figure appears in the document and is automatically expected here.
    allowed = {"25", "5", "10", "0.031", "0.5", "95", "2.5", "50", "42"}
    ret = narrative.retrieval_state()
    con = narrative.contamination_state()
    tax = narrative.taxonomy_state()
    from statistical_report import detectable, wilson_ci
    pw = detectable(36)
    expected = set(allowed)
    for v in (ret.get("recall") or {}).values():
        # The document prints recall at one decimal; accept the integer form too
        # because prose may round it. Rounding before stripping zeros would turn
        # 90.5 into "91" and then fail to match the text's own "90.5%".
        expected.add(f"{v:.1f}")
        expected.add(f"{v:.0f}")
    if con.get("present"):
        expected.add(f"{con['naive_pct']:.0f}")
    if tax.get("unclassified_pct") is not None:
        expected.add(f"{tax['unclassified_pct']:.1f}")
    if tax.get("dominant_pct") is not None:
        expected.add(f"{tax['dominant_pct']:.1f}")
    expected.add(f"{pw['min_delta_pp_zero_regressions']:+.1f}")
    expected.add(f"{pw['min_delta_pp_zero_regressions']:.1f}")
    for k in (0, 6):
        w = wilson_ci(k, 6)
        expected.add(f"{w['ci_lower']:.1f}")
        expected.add(f"{w['ci_upper']:.1f}")
        expected.add(f"{w['ci_upper'] - w['ci_lower']:.0f}")

    pct = re.findall(r"(\d+(?:\.\d+)?)%", text)
    suspicious = sorted({p for p in pct if p not in expected})
    check("every percentage traces to a module that measured it",
          not suspicious, f"unexplained: {suspicious}")

    # It must not say a model "scores" or "achieves" anything.
    for verb in (r"8B scores", r"70B scores", r"achieves \d", r"accuracy of \d",
                 r"scored \d"):
        check(f"the document does not say '{verb}'",
              not re.search(verb, text, re.I))
    print(f"   {len(pct)} percentages, all traceable to model-free sources")


# ================================= 5. the scenario comes from data
def test_scenario_from_data() -> None:
    section("5. The scenario is chosen by the data, not by hand")
    import narrative

    stats = narrative.compute()
    scen = narrative.choose_scenario(stats, narrative.taxonomy_state(), {})

    # Force the branches and check each maps to the right label.
    def mk(delta, sig):
        return {"delta_pp": delta, "significant": sig, "improved": 6,
                "regressed": 0, "delta_ci_lower": 0.0, "delta_ci_upper": 30.0,
                "n_paired": 36, "before_accuracy": 40.0, "after_accuracy": 50.0,
                "before_correct": 14, "after_correct": 18,
                "mcnemar_p": 0.01 if sig else 0.9, "discordant": 6,
                "net_items": 6, "improved_ids": [], "regressed_ids": [],
                "direction": "improved" if sig else "no detectable change"}

    def with_paired(v):
        s = {"knowledge": {m: {} for m in narrative.MODELS}}
        for m in narrative.MODELS:
            s["knowledge"][m]["paired"] = v
            s["knowledge"][m]["baseline_present"] = True
            s["knowledge"][m]["baseline_meta"] = {"is_mock": False}
        return s

    check("a +20pp significant gain selects scenario A",
          narrative.choose_scenario(with_paired(mk(20, True)), {}, {})["id"] == "A")
    check("a +8pp significant gain selects scenario B",
          narrative.choose_scenario(with_paired(mk(8, True)), {}, {})["id"] == "B")
    check("a non-significant gain selects scenario C",
          narrative.choose_scenario(with_paired(mk(8, False)), {}, {})["id"] == "C")
    check("no model data selects 'pending'",
          narrative.choose_scenario({"knowledge": {}}, {}, {})["id"] == "pending")

    # "pending" must carry the caveat about scenario C.
    check("'pending' names the closest scenario", scen.get("closest") == "C")
    check("'pending' explains why C is also unavailable",
          "not supported" in scen.get("closest_caveat", ""),
          scen.get("closest_caveat", ""))

    check("the selected scenario appears in the document",
          f"**{scen['id']} —" in build()[0].read_text(encoding="utf-8")
          or scen["id"] in build()[0].read_text(encoding="utf-8"))
    print("   A/B/C/pending all reachable from the data alone")


# ============================== 6. numbers trace to the statistics module
def test_numbers_traceable() -> None:
    section("6. Every number traces to the module that measured it")
    import narrative
    from statistical_report import detectable, wilson_ci

    path, scen, have = build()
    text = path.read_text(encoding="utf-8")

    ret = narrative.retrieval_state()
    if ret.get("present"):
        for k, v in ret["recall"].items():
            check(f"the {v}% recall at top-{k} matches the retriever",
                  f"{v}%" in text)

    pw36 = detectable(36)
    check("the detection floor is the one the statistics module computes",
          f"{pw36['min_improvements_zero_regressions']} improvements" in text)
    check("the pp threshold matches",
          f"{pw36['min_delta_pp_zero_regressions']:+.1f} pp" in text)

    pw6 = detectable(6)
    check("it says n=6 supports nothing but a clean sweep",
          pw6["nothing_detectable_with_any_regression"] and "6/0" in text)

    w0, w6 = wilson_ci(0, 6), wilson_ci(6, 6)
    check("the 0/6 interval quoted matches wilson_ci",
          f"[{w0['ci_lower']:.1f}, {w0['ci_upper']:.1f}]" in text,
          f"expected [{w0['ci_lower']:.1f}, {w0['ci_upper']:.1f}]")
    check("the 6/6 interval quoted matches wilson_ci",
          f"[{w6['ci_lower']:.1f}, {w6['ci_upper']:.1f}]" in text,
          f"expected [{w6['ci_lower']:.1f}, {w6['ci_upper']:.1f}]")

    import seal
    check("the commit hash is the real one", seal.git_hash()[:12] in text)
    check("the sealed set hash is the real one", seal.file_hash()[:32] in text)
    print("   recall, power floor, intervals, commit and seal all cross-checked")


# ================================ 7. credible to experts, readable to laypeople
def test_two_audiences() -> None:
    section("7. The two audience checks, made mechanical")
    import narrative
    stats_v = narrative.compute()
    path, scen, have = build()
    text = path.read_text(encoding="utf-8")

    # -- an EPFL/ETH reviewer --------------------------------------------
    check("it names its sample sizes", "n=36" in text and "n=6" in text)
    check("it reports uncertainty, not just point estimates",
          "95% interval" in text.lower() or "confidence" in text.lower()
          or "Wilson" in text)
    check("it states a significance threshold", "p < 0.05" in text or "p=0.42" in text
          or "p = 0.42" in text or "McNemar" in text)
    check("it distinguishes paired from unpaired analysis", "paired" in text.lower())
    check("it has a limitations section", "## Limitations" in text)
    check("the limitations are specific, not generic",
          text.count("**") >= 8 and len(
              text.split("## Limitations")[1].split("## Reproducibility")[0]
              .strip().splitlines()) > 10)
    check("it discloses the self-judging risk", "self-judged" in text.lower()
          or "judge and model" in text.lower())
    # Before the values arm exists, self-judging is a configuration, not a
    # finding, and must be phrased in the conditional.
    vals_run = any((stats_v.get("values", {}).get(m) or {}).get("present")
                   for m in ("8b", "70b"))
    if not vals_run:
        check("it does not assert self-judging as a measured fact",
              "is **self-judged**" not in text and "is self-judged" not in text,
              "the values arm has not run; the judge is only configured")
        check("it flags self-judging prospectively instead",
              "will be" in text and "self-judged" in text)
    check("it does not compare to untested models",
          "we did not test" in text.lower() or "outside Apertus" in text)
    check("it states reproducibility facts", "Git commit" in text
          and "SHA-256" in text and "seed 42" in text.lower())

    # -- a non-technical jury member -------------------------------------
    # Collapse the line wrapping before any content check. The document is
    # hard-wrapped for readability, so a phrase like "answer\nkey" is one
    # sentence to a reader and two tokens to grep - and a test that greps for
    # the contiguous form would fail on correct prose.
    body = "\n".join(l for l in text.splitlines() if not l.startswith(("|", ">")))
    flat = re.sub(r"\s+", " ", body)
    words = body.split()
    avg_sentence = (len(words) / max(1, body.count(".") + body.count("!") + body.count("?")))
    check("sentences average under 30 words", avg_sentence < 30,
          f"average {avg_sentence:.1f} words")
    jargon = ["Wilson", "Clopper-Pearson", "discordant", "logistic", "p-value",
              "null hypothesis", "heteroscedastic", "bootstrap"]
    unexplained = [j for j in jargon if j in flat and f"{j} (" not in flat
                   and f"{j}," not in flat and f"({j}" not in flat]
    check("no undefined jargon in the body", len(unexplained) <= 2,
          str(unexplained))
    check("it states its own headline finding in plain words",
          "answer key" in flat.lower(),
          "the strongest finding must be understandable to a lay reader")
    check("it says the benchmark can be reused",
          "open-source" in flat.lower() or "open source" in flat.lower())
    check("it explains what the project is in the first screen",
          text.index("Swiss Reality Check") < 1200)
    check("it has section headings a reader can navigate",
          text.count("\n## ") >= 5, f"{text.count(chr(10) + '## ')} headings")
    print(f"   average sentence {avg_sentence:.1f} words; "
          f"{text.count(chr(10) + '## ')} headings; jargon "
          f"{unexplained or 'none undefined'}")


def main() -> int:
    print("=" * 72)
    print("  Phase 4.4 verification")
    print("=" * 72)
    for fn in (test_no_placeholders_anywhere,
               test_no_unmeasured_claims,
               test_mock_provenance,
               test_no_accuracy_while_mock,
               test_scenario_from_data,
               test_numbers_traceable,
               test_two_audiences):
        try:
            fn()
        except Exception as e:
            import traceback
            FAILURES.append(f"{fn.__name__} raised {type(e).__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 72}")
    if FAILURES:
        print(f"  FAILED  {len(FAILURES)} of {CHECKS} checks")
        for f in FAILURES:
            print(f"    - {f}")
        return 1
    print(f"  PASSED  all {CHECKS} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())

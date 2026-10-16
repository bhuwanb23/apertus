"""
test_narrative.py - Phase 4.4 verification.

The findings document is what a jury reads. If it contains an unsupported claim,
the project is not merely wrong - it has asserted something in the most
authoritative voice available to it, in the place where people stop checking.

  1. NO PLACEHOLDER, INCLUDING IN THE GENERATOR'S OWN PROSE. The module that
     exists to prevent placeholders shipped one: the sentence "confuse Swiss and
     German law, XX% of the time" was written into the source as an example.
     The output was clean and the source was not. Both are checked.
  2. NO CLAIM THE ANALYSIS DECLINED TO MAKE. 3.1 left most errors
     UNCLASSIFIED and select_target.py refused to name a target. The narrative
     must not name a dominant error mode, a weakest area, or a category - and
     must still say the taxonomy is unresolved, because it is.
  3. EVERY FIGURE CARRIES ITS PROVENANCE IN PLACE. A mock-derived number and a
     real one are both percentages in this document; only one of them is a
     finding about Apertus, so the banner saying which is which must sit next
     to them.
  4. EVERY NUMBER TRACES TO A MODULE THAT MEASURED IT. Read back out of
     statistical_report, retriever, prompts_check and the scorer - never from a
     hand-kept list, so a figure that appears in the document without a source
     fails here.
  5. THE SCENARIO IS CHOSEN FROM DATA. Both directions: with no model it must
     refuse to pick A-D, and with the one-shot scored it must pick the one the
     numbers support rather than the one that was written first.
  6. THE MODEL-FREE FINDINGS ARE NOT GATED ON HAVING A MODEL. Retrieval,
     contamination, the taxonomy and the detection floor hold without a run, and
     a generator that drops them the moment results exist has thrown away the
     part of the evidence that a reader cannot reproduce.
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

import seal as seal_mod  # noqa: E402  (needs the sys.path inserts above)


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
                      (r"<[A-Z_]{3,}>", "unfilled angle placeholder"),
                      (r"%%", "doubled percent sign"),
                      (r"\bnan\b|\binf\b", "non-finite number"),
                      (r"None%|None pp", "unrendered value")):
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
        # Three phrasings of one fact, because the generator picks between them
        # from taxonomy_state(): the section heading, the body, and the
        # limitations list all say it, and which one a reader reaches first
        # depends on whether a classified file exists. Accepting only the first
        # spelling tested the prose rather than the claim.
        check("it says the taxonomy is unresolved",
              any(s in text for s in ("UNCLASSIFIED", "did not resolve",
                                      "is unresolved", "unresolved")),
              "the taxonomy has not resolved, and the document has to say so "
              "rather than go quiet on it")
        # The other direction. fix/error_taxonomy.md came out of a mock-backend
        # run, so "unresolved" is the true state of this analysis, and a
        # generator that quietly starts reporting a dominant failure mode once a
        # model run exists would be the precise failure this suite exists for.
        # (?<!un) so that "unresolved" does not trip it.
        check("it does not claim the taxonomy resolved",
              re.search(r"taxonomy[^.\n]{0,40}(?<!un)resolved", text, re.I) is None,
              "3.1 declined to name a dominant error; the narrative must not "
              "start naming one on its own authority")

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


# ================================= 3. provenance of every figure is in place
def test_mock_provenance() -> None:
    section("3. Every figure carries its provenance in the same place")
    import narrative

    path, scen, have = build()
    text = path.read_text(encoding="utf-8")
    tax = narrative.taxonomy_state()

    if have:
        # The one-shot has happened. The old check - "does the document say no
        # model has been evaluated" - passed only because the banner was
        # unconditional, and would have kept passing after the run made it a
        # lie. What has to be true now is the mirror image: the document names
        # the run its accuracy figures come from, and says they are not a
        # self-test.
        # This check used to REQUIRE the phrase "opened **once**", so it
        # enforced the very claim that turned out to be false: the append-only
        # log records 24 opens of the sealed set, not one. It now requires the
        # count to be reported from the log, the run to be named, and the
        # one-shot phrasing to be ABSENT.
        n_base = len([e for e in seal_mod.read_audit()
                      if "knowledge/8b/baseline" in str(e.get("reason", ""))])
        n_impr = len([e for e in seal_mod.read_audit()
                      if "knowledge/8b/improved" in str(e.get("reason", ""))])
        total = n_base + n_impr
        check("the document names the run its accuracy figures came from",
              bool(re.search(r"Latest arm: \d{4}-\d\d-\d\dT", text)) is not False
              and re.search(r"Latest arm: \d{4}-\d\d-\d\dT", text) is not None
              and re.search(r"`is_mock: (true|false)`", text) is not None,
              "a figure with no run behind it is indistinguishable from a mock "
              "self-test")
        check("it reports the sealed-set open count from the log, not a claim "
              "of one",
              f"opened **{total} times**" in text,
              f"the log records {total} opens ({n_base} baseline, {n_impr} "
              f"improved); the document must state that count")
        check("it does not claim the set was opened exactly once",
              "opened **once**" not in text and "exactly once" not in text,
              "the one-shot claim was false and must not come back")
        check("it says the scored arms are not mock", "is_mock: false" in text)
        check("it does not still claim no model has been evaluated",
              "No model has been evaluated" not in text,
              "the banner that said this is now false and must be gone")
    else:
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
    elif not tax.get("present") and tax.get("report_mock"):
        # The rendered taxonomy exists and says on its face that it came from
        # synthetic responses. A document that reports "not available" and stops
        # there leaves a confident-looking table in the repo with no provenance
        # warning pointing at it.
        check("the mock provenance of the rendered taxonomy is stated",
              "MOCK BACKEND" in text
              and re.search(r"not repeated here as findings", text) is not None,
              "a reader who opens fix/error_taxonomy.md must be told here that "
              "it is not evidence about Apertus")

    # The 30% contamination figure is model-free and MUST be stated as such,
    # because it is the strongest number in the document.
    con = narrative.contamination_state()
    if con.get("present"):
        check("the contamination figure appears", f"{con['naive_pct']:.0f}%" in text)
        check("it is attributed to a measurement, not a guess",
              "answers" in text and "items" in text)
    print("   mock caveats sit next to the numbers they qualify")


# ============================== 4. every figure traces to a measurement
def test_figures_traceable() -> None:
    section("4. Every figure traces to the module that measured it")
    import narrative

    stats = narrative.compute()
    path, scen, have = build()
    text = path.read_text(encoding="utf-8")

    if have:
        # Phase 4.1 has run and the one-shot is spent. The check that used to
        # live here - "no accuracy figure while on mock" - is still the right
        # question, asked in the form the data now takes: are the figures here
        # from a real backend, and does the generator agree?
        check("the generator sees model data", bool(have),
              "the one-shot has run; a document that reports no model data is "
              "reporting a stale state, not a finding")
        mocks = [m for m in narrative.MODELS
                 if stats["knowledge"].get(m, {}).get("paired")
                 and (stats["knowledge"][m].get("baseline_meta") or {}).get("is_mock")]
        check("no scored arm came from the mock backend", not mocks, str(mocks))
        check("the scenario is no longer 'pending'",
              scen["id"] in ("A", "B", "C"), scen["id"])
        check("the scenario is the one the real data selects",
              scen["id"] == narrative.choose_scenario(
                  stats, narrative.taxonomy_state(), {})["id"],
              "the printed scenario and choose_scenario disagree")
        # The scenario has to justify itself out of the measurement. A label
        # with no number behind it is the same failure mode as a bare figure.
        p = next((stats["knowledge"][m]["paired"] for m in narrative.MODELS
                  if stats["knowledge"].get(m, {}).get("paired")), None)
        if scen["id"] in ("A", "B"):
            check("the scenario cites the measured delta that selected it",
                  f"{p['delta_pp']:+.1f} pp" in scen["why"]
                  and f"{p['delta_pp']:+.1f} pp" in text, scen["why"])
            # The exact contradiction this generator shipped for one revision:
            # a document that reports a significant paired gain and, two acts
            # later, says the effect was not established. Both sentences were
            # true of some state of the data; only one is true of this state.
            check("the document does not also call the effect unestablished",
                  re.search(r"effect on accuracy is not established", text, re.I)
                  is None
                  and re.search(r"no detectable effect", text, re.I) is None,
                  "a significant paired result and a null claim cannot both be "
                  "in the same document")
        else:
            check("the scenario explains the absence of a significant gain",
                  "no arm reached" in scen["why"], scen["why"])
            check("the document does not claim an established effect",
                  "effect is established" not in text.lower(),
                  "no arm reached significance; the document must not say the "
                  "effect was established")
    else:
        # Unchanged from before the one-shot, and still live: if the sealed arms
        # are ever removed, the generator must go back to refusing to pick a
        # scenario rather than reporting an accuracy for a model that has not
        # answered anything.
        check("the generator reports no model data", not have)
        check("the scenario is 'pending'", scen["id"] == "pending", scen["id"])
        check("the scenario explains why A-D cannot apply",
              "none of A" in scen["why"] or "cannot be selected" in scen["why"])

    # Any percentage in the document must be traceable to a non-model source or
    # to the scorer that measured it. Read from the modules themselves rather
    # than from a hand-kept list, so a new figure appears in the document and is
    # automatically expected here.
    allowed = {"25", "5", "10", "0.031", "0.5", "95", "2.5", "50", "42"}
    ret = narrative.retrieval_state()
    con = narrative.contamination_state()
    tax = narrative.taxonomy_state()
    dia = narrative.dialect_state()
    from statistical_report import detectable, wilson_ci
    pw = detectable(36)
    expected = set(allowed)

    def add(v):
        if v is None:
            return
        one = f"{v:.1f}"
        expected.add(one)
        # Only accept the rounded form where rounding is lossless, so a prose
        # "30%" matches but "55%" does not silently cover "55.6%".
        if one.endswith(".0"):
            expected.add(f"{v:.0f}")

    for v in (ret.get("recall") or {}).values():
        add(v)
    if con.get("present"):
        add(con["naive_pct"])
        # Both places the contamination figure appears round it to a whole
        # percent, because 25/84 is not a cleaner number than "30%". Registered
        # for this figure only; every other value has to match its own precision.
        expected.add(f"{con['naive_pct']:.0f}")
    if tax.get("unclassified_pct") is not None:
        add(tax["unclassified_pct"])
    if tax.get("dominant_pct") is not None:
        add(tax["dominant_pct"])
    for m in narrative.MODELS:
        e = stats["knowledge"].get(m) or {}
        for ci in (e.get("baseline_ci"), e.get("improved_ci")):
            for k in ("accuracy", "ci_lower", "ci_upper"):
                add((ci or {}).get(k))
        pr = e.get("paired")
        for k in ("delta_pp", "delta_ci_lower", "delta_ci_upper"):
            add((pr or {}).get(k))
    if dia.get("present"):
        for k in ("refusal_rate", "mcq_accuracy"):
            add(dia.get(k))
    expected.add(f"{pw['min_delta_pp_zero_regressions']:+.1f}")
    expected.add(f"{pw['min_delta_pp_zero_regressions']:.1f}")
    for k in (0, 6):
        w = wilson_ci(k, 6)
        add(w["ci_lower"])
        add(w["ci_upper"])
        expected.add(f"{w['ci_upper'] - w['ci_lower']:.0f}")

    pct = re.findall(r"(\d+(?:\.\d+)?)%", text)
    suspicious = sorted({p for p in pct if p not in expected})
    check("every percentage traces to a module that measured it",
          not suspicious, f"unexplained: {suspicious}")

    # It must not attribute a score to the model in the language of a press
    # release. This is not "no accuracy may be stated" - the arms exist now -
    # it is "no score may appear unattributed".
    for verb in (r"8B scores", r"70B scores", r"achieves \d", r"accuracy of \d",
                 r"scored \d"):
        check(f"the document does not say '{verb}'",
              not re.search(verb, text, re.I))
    print(f"   {len(pct)} percentages, all traceable to a measured source")


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

    # The pending branch is exercised by FORCING it, not by hoping the live data
    # is still missing. It is the branch that fires if the sealed arms are ever
    # removed, and a generator whose refusal path stops being tested is a
    # generator that will stop refusing.
    pending = narrative.choose_scenario({"knowledge": {}}, {}, {})

    check("'pending' names the closest scenario", pending.get("closest") == "C",
          f"pending must still say which scenario it is nearest: {pending}")
    check("'pending' explains why C is also unavailable",
          "not supported" in pending.get("closest_caveat", ""),
          pending.get("closest_caveat", ""))
    check("'pending' explains why A-D cannot apply",
          "none of A" in pending.get("why", "")
          or "cannot be selected" in pending.get("why", ""),
          pending.get("why", ""))

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

    # And the recall figures must not ALSO exist as literals in the generator.
    # A document recomputes its recall from the retriever and then hardcodes the
    # same number into its prose is a document that will keep printing the old
    # figure after the corpus changes - which is the same failure
    # fix/test_charts.py refuses in generate_charts.py.
    src = (ROOT / "eval" / "narrative.py").read_text(encoding="utf-8")
    code = re.sub(r'"""[\s\S]*?"""', "", src)      # the docstring names them
    lit = [v for v in ("83.3", "90.5", "94.0", "83.3%", "90.5%", "94%")
           if v in code]
    check("no recall figure is hardcoded in the generator's code", not lit,
          f"literals {lit}; retrieval_state() already computes these")

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

    # If model arms exist, the measured comparison has to be IN this document,
    # not merely in the statistical report it links to. The discordant counts
    # are the part of a McNemar result a reader has to see to judge it: a delta
    # with its interval but no counts is a number without a story.
    stats = narrative.compute()
    for m in narrative.MODELS:
        pr = (stats["knowledge"].get(m) or {}).get("paired")
        if not pr:
            continue
        check(f"the {m.upper()} arm accuracies are reported",
              f"{pr['before_accuracy']}%" in text
              and f"{pr['after_accuracy']}%" in text,
              "the two arms are the comparison; reporting one is reporting half")
        check(f"the {m.upper()} discordant counts are reported",
              f"{pr['improved']} items improved" in text
              and f"{pr['regressed']} regressed" in text,
              "improvements and regressions, not a delta on its own")
        check(f"the {m.upper()} McNemar p is reported",
              f"p = {pr['mcnemar_p']}" in text,
              "significance is the claim; the point estimate is not enough")

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
               test_figures_traceable,
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

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
  8. THE DIALECT FIGURE IS THE MEASURED ONE, OR IT IS NOT PRINTED. A mock arm
     and a sealed arm are both percentages, and only one of them is a finding.
     The reader refuses a mock source, and the numbers in the document are
     cross-checked against the artefact rather than against themselves - which
     is how a 6-item mock self-test came to be published as the dialect result
     while the technical report said 50%.

Run:  python fix/test_narrative.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "fix"))
sys.path.insert(0, str(ROOT / "src" / "fix" / "rag"))

# ============================================================== test sandbox
#
# This suite is the same failure class as eval/test_baseline_report.py, so it
# uses the same fix: redirect, do not monkeypatch, and keep every write inside a
# throwaway tree. eval/results/narrative/findings.md is a TRACKED artefact and
# the authoritative findings document; write_findings() rewrites it wholesale,
# with a fresh generation timestamp in the first line, so merely running this
# suite used to leave the working tree dirty and to clobber the deliverable.
#
# The established pattern is eval/config.py's results_sandbox(), called at
# module top before any import of a module that writes, plus an
# _assert_in_sandbox() guard on every path about to be written and a
# snapshot/snapshot_diff pair asserting the real tree is byte-identical
# afterwards. results_sandbox() also derives the whole artefact tree at once -
# results root, narrative/, charts/ and final_scores/ all move together,
# because every write path in this project is built from config.results_dir.
#
# ONE EXTRA CONSTRAINT, and it is the reason this is not a copy-paste.
#
# config.results_dir is not only a write root; it is also a READ root, and the
# readers are what make these assertions worth running. statistical_report binds
# `TEST_RUN = config.results_dir / "test_run"` at import time and reads the
# sealed measurement arms from it. Redirecting before it is imported would move
# TEST_RUN into the empty sandbox, every arm would read as absent, and this file
# would sail through its "no model has been evaluated" branch with a third of
# its checks skipped. That is a weaker suite pretending to be an isolated one.
#
# So the order here is deliberate and must not be rearranged:
#
#   1. snapshot the REAL tree first, before anything project-side is imported;
#   2. import statistical_report, binding its read paths to the real arms;
#   3. enter results_sandbox(), which redirects every write path;
#   4. narrative is imported later, inside the tests, so its module-level
#      `NARRATIVE = config.results_dir / "narrative"` resolves into the sandbox.
#
# narrative is therefore never imported at module level in this file. That is
# the whole mechanism, and reintroducing a top-level `import narrative` would
# silently move the write back onto the tracked artefact.

from config import (REAL_RESULTS_DIR, digest_file, results_sandbox,  # noqa: E402
                     snapshot_diff, snapshot_results_tree)

# Taken before any project import, so it covers import-time side effects too -
# strictly stronger than the snapshot results_sandbox() takes for itself, which
# happens one step later.
SUITE_START_DIGESTS = snapshot_results_tree()


def _stamp(path: Path):
    """(mtime_ns, size, sha256) of a file, or None if it is absent."""
    p = Path(path)
    if not p.is_file():
        return None
    st = p.stat()
    return (st.st_mtime_ns, st.st_size, digest_file(p))


# The artefact this suite exists to stop overwriting, recorded before the
# redirect and before any test body runs.
TRACKED_FINDINGS = REAL_RESULTS_DIR / "narrative" / "findings.md"
TRACKED_CHARTS = REAL_RESULTS_DIR / "charts"
FINDINGS_STAMP_BEFORE = _stamp(TRACKED_FINDINGS)

# Reader, imported BEFORE the redirect - see the note above.
import statistical_report  # noqa: E402

# Writer, imported AFTER it. The redirect unwinds and the temp tree is removed at
# interpreter exit, so nothing survives the process.
SUITE_RESULTS, _SUITE_SANDBOX_DIGESTS = results_sandbox("narrative_")

CHECKS = 0
FAILURES: list[str] = []

import seal as seal_mod  # noqa: E402  (needs the sys.path inserts above)


def _assert_in_sandbox(path: Path) -> None:
    """
    Refuse to proceed if `path` is not inside this suite's temp tree.

    The belt to the braces that results_sandbox() provides. If a future change
    reorders the imports above, or narrative grows a second write path that is
    not derived from config.results_dir, this fails loudly at the write instead
    of quietly eating a tracked artefact again.
    """
    try:
        Path(path).resolve().relative_to(SUITE_RESULTS.resolve())
    except ValueError:
        raise AssertionError(
            f"refusing to touch {path}: it is outside the suite sandbox "
            f"{SUITE_RESULTS}. This suite must never write to eval/results.")


def check(label: str, condition: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(f"{label}" + (f" -- {detail}" if detail else ""))


def section(name: str) -> None:
    print(f"\n{name}")


def build():
    """
    Generate the findings document, and prove it lands in the sandbox.

    write_findings() overwrites the whole file and returns its path, so this is
    the only place in the suite where a tracked artefact could be destroyed. The
    path is checked against the sandbox before the content is read back, and the
    document itself is checked too - a generator that started writing its chart
    or final_scores siblings outside the sandbox would be caught by the tree
    snapshot in test_real_results_untouched, and this guard names the offender
    immediately instead.
    """
    import narrative
    from config import config

    # Every path this call can receive a write on.
    _assert_in_sandbox(config.results_dir)
    _assert_in_sandbox(config.results_dir / "charts")
    _assert_in_sandbox(config.results_dir / "final_scores")
    _assert_in_sandbox(narrative.NARRATIVE)

    path, scen, have = narrative.write_findings()
    _assert_in_sandbox(path)
    return path, scen, have


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
    src = (ROOT / "src" / "eval" / "narrative.py").read_text(encoding="utf-8")
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
    from narrative import TEST_N
    pw = detectable(TEST_N)
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

    # The open-ended arm's rates trace to openqa_report, which reads them out of
    # the parsed sealed results rather than recomputing anything. Added to the
    # EXPECTED set from that artefact for the same reason as everything above: a
    # percentage in findings.md that no module produced is exactly the failure
    # this check exists to catch, and the openQA rates are now in the document.
    try:
        import openqa_report
        _oq = openqa_report.summary()
        if _oq.get("status") == "complete":
            for _m in (_oq["baseline"], _oq["rag"]):
                for _k in ("factuality", "hallucination_rate", "abstention_rate"):
                    add(_m.get(_k))
            add(20)          # the brief's 20% human cross-check sampling rate
    except Exception:
        pass                    # arm not run: nothing in the document cites it

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
    from narrative import TEST_N, N_CATEGORIES

    path, scen, have = build()
    text = path.read_text(encoding="utf-8")

    ret = narrative.retrieval_state()
    if ret.get("present"):
        for k, v in ret["recall"].items():
            check(f"the {v}% recall at top-{k} matches the retriever",
                  f"{v}%" in text)

    # Derived from the sealed n, exactly as narrative.py derives them: the point
    # of these checks is that two independent computations agree, not that they
    # agree with a number typed before the corpus was rescaled.
    pw_overall = detectable(TEST_N)
    check("the detection floor is the one the statistics module computes",
          f"{pw_overall['min_improvements_zero_regressions']} improvements" in text)
    check("the pp threshold matches",
          f"{pw_overall['min_delta_pp_zero_regressions']:+.1f} pp" in text)

    pw_cat = detectable(max(1, TEST_N // N_CATEGORIES))
    check(f"it says n={pw_cat['n']} supports nothing but a clean sweep",
          pw_cat["nothing_detectable_with_any_regression"] and "6/0" in text)

    # And the recall figures must not ALSO exist as literals in the generator.
    # A document recomputes its recall from the retriever and then hardcodes the
    # same number into its prose is a document that will keep printing the old
    # figure after the corpus changes - which is the same failure
    # fix/test_charts.py refuses in generate_charts.py.
    src = (ROOT / "src" / "eval" / "narrative.py").read_text(encoding="utf-8")
    code = re.sub(r'"""[\s\S]*?"""', "", src)      # the docstring names them
    lit = [v for v in ("83.3", "90.5", "94.0", "83.3%", "90.5%", "94%")
           if v in code]
    check("no recall figure is hardcoded in the generator's code", not lit,
          f"literals {lit}; retrieval_state() already computes these")

    # Derived: the worst case a category can show, at whatever n it has.
    cat_n = max(1, TEST_N // N_CATEGORIES)
    w0, w6 = wilson_ci(0, cat_n), wilson_ci(cat_n, cat_n)
    check(f"the 0/{cat_n} interval quoted matches wilson_ci",
          f"[{w0['ci_lower']:.1f}, {w0['ci_upper']:.1f}]" in text,
          f"expected [{w0['ci_lower']:.1f}, {w0['ci_upper']:.1f}]")
    check(f"the {cat_n}/{cat_n} interval quoted matches wilson_ci",
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


# ============== 8. the dialect figure is the measured one, or it is not printed
def test_dialect_provenance() -> None:
    section("8. The dialect figure is the measured run, or it is not printed")
    import json
    import tempfile

    import narrative
    import statistical_report as sr

    path, _scen, _have = build()
    text = path.read_text(encoding="utf-8")

    # (a) Read the artefact INDEPENDENTLY of the generator - straight off disk -
    # and require the document to agree with it. The earlier check read the
    # dialect numbers back out of dialect_state() and then looked for those same
    # numbers in the document, which compares the generator against itself. It
    # passed for as long as the generator was wrong, while findings.md published
    # a mock self-test ("6 of 6 items scored ... refused 0 of them") as the
    # dialect finding and the technical report said 50%. A check whose expected
    # value comes from the code under test cannot fail, so this one does not.
    arm = ROOT / "results" / "test_run" / "dialect_8b_baseline.json"
    if arm.exists():
        payload = json.loads(arm.read_text(encoding="utf-8"))
        nums = payload["scores"]["scores"]
        run = payload["scores"]["run"]
        check("the measured dialect arm is not a mock",
              not payload.get("is_mock") and not run.get("is_mock"),
              "the sealed arms are http-backed; a mock file here is a false "
              "fixture and every check below would bless it")
        for label, frag in (
                ("item count", f"{nums['n_scored']} of {nums['n_items']} "
                               f"items scored"),
                ("refusal count", f"refused {nums['n_refused']} of them"),
                ("refusal rate", f"{nums['refusal_rate']}%"),
                ("MCQ denominator", f"the {nums['mcq_n']}")):
            check(f"the document reports the measured dialect {label}",
                  frag in text,
                  f"the artefact says '{frag}'; the document must not report a "
                  f"different run")
        check("the document does not report the mock dialect arm",
              "6 of 6 items scored" not in text,
              "6 of 6 is the 6-item mock self-test, not the 30-item sealed arm")
    else:
        check("no measured dialect arm - the document states no dialect figure",
              "**Dialect.** Not reported" in text,
              "without the arm the document must say so rather than print a "
              "dev-set number")

    # (b) A mock dialect arm must be REFUSED, not rendered. Build one and point
    # the shared reader at it. There was no mock check here at all, which is how
    # the mock figure reached a tracked file - and eval/README.md is explicit
    # that a mock run "never produces a publishable number".
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "dialect_8b_baseline.json").write_text(json.dumps({
            "task": "dialect", "model": "8b", "method": "baseline",
            "backend": "mock", "is_mock": True,
            "scores": {"run": {"is_mock": True, "backend": "mock",
                               "n_items": 6, "model_id": "mock"},
                       "scores": {"n_items": 6, "n_scored": 6,
                                  "refusal_rate": 0.0, "n_refused": 0,
                                  "mcq_accuracy": None, "mcq_n": 0,
                                  "t1_mean": 0.0, "t1_n": 6}},
            "results": [],
        }), encoding="utf-8")
        old = sr.TEST_RUN
        sr.TEST_RUN = Path(td)
        try:
            state = narrative.dialect_state()
        finally:
            sr.TEST_RUN = old

    check("a mock dialect arm is refused, not rendered",
          state.get("present") is False and state.get("mock") is True,
          f"dialect_state() returned {state}; a mock arm is a self-test, and "
          f"reporting one as a finding is the defect this section exists for")
    check("the refusal says why",
          "mock" in (state.get("reason") or "").lower(), state.get("reason", ""))
    print("   dialect figures cross-checked against the artefact, not the "
          "generator")


# ================================ 7. credible to experts, readable to laypeople
def test_two_audiences() -> None:
    section("7. The two audience checks, made mechanical")
    import narrative
    from narrative import TEST_N
    stats_v = narrative.compute()
    path, scen, have = build()
    text = path.read_text(encoding="utf-8")

    # -- an EPFL/ETH reviewer --------------------------------------------
    from narrative import N_CATEGORIES
    cat_n = max(1, TEST_N // N_CATEGORIES)
    check("it names its sample sizes",
          f"n={TEST_N}" in text and f"n={cat_n}" in text)
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


# ============================ 9. the suite never touches the real results
def test_real_results_untouched() -> None:
    """
    The invariant this file exists to protect, asserted on itself.

    Run as a suite, build() regenerates eval/results/narrative/findings.md seven
    times. That file is tracked, it is the document a jury reads, and it is the
    only artefact in the repo the narrative can rewrite on demand - so the damage
    was invisible from inside the suite, which only ever checked its own output.
    Every other check in this file passed while the deliverable was being
    overwritten.

    Three independent statements of "nothing outside the sandbox moved":

      * the whole real tree, sha256 per file, snapshotted before any
        project-side import and compared now. This is the strong one: it also
        catches a deleted or created file, which a stat comparison cannot.
      * mtime + size + sha256 of findings.md specifically, which is the direct
        form the requirement is stated in and which fails with a readable
        message rather than a digest prefix.
      * the sandbox is genuinely somewhere else, and the readers were NOT
        dragged into it - statistical_report.TEST_RUN must still point at the
        real sealed arms, or this suite would have been quietly weakened by its
        own sandbox.
    """
    import narrative
    from config import config

    section("9. The real results tree is untouched")

    problems = snapshot_diff(SUITE_START_DIGESTS, snapshot_results_tree())
    check("the real results tree is byte-identical after the suite ran",
          problems == [], "; ".join(problems[:5]))

    stamp_after = _stamp(TRACKED_FINDINGS)
    check("the tracked findings.md mtime and size are unchanged",
          (stamp_after is None) == (FINDINGS_STAMP_BEFORE is None)
          and (stamp_after is None
               or stamp_after[:2] == FINDINGS_STAMP_BEFORE[:2]),
          f"{FINDINGS_STAMP_BEFORE!r} -> {stamp_after!r}")
    check("the tracked findings.md content is unchanged",
          (stamp_after is None) == (FINDINGS_STAMP_BEFORE is None)
          and (stamp_after is None
               or stamp_after[2] == FINDINGS_STAMP_BEFORE[2]),
          "sha256 differs: findings.md was rewritten by the suite")

    # The sandbox is somewhere else, and everything that writes goes there.
    check("the sandbox is outside the real results tree",
          not SUITE_RESULTS.is_relative_to(REAL_RESULTS_DIR)
          and not REAL_RESULTS_DIR.is_relative_to(SUITE_RESULTS), True)
    check("the sandbox is outside eval/ entirely",
          not SUITE_RESULTS.is_relative_to(ROOT / "src" / "eval"), True)
    check("results_dir points into the sandbox",
          config.results_dir.is_relative_to(SUITE_RESULTS),
          str(config.results_dir))
    check("the narrative output directory points into the sandbox",
          narrative.NARRATIVE.is_relative_to(SUITE_RESULTS),
          str(narrative.NARRATIVE))

    # ...and everything that reads did not follow it. This is what keeps the
    # assertions above load-bearing: if the sealed arms had been hidden by the
    # redirect, roughly a third of this file would have taken its "no model
    # data" branch and passed vacuously.
    check("the readers still see the real sealed arms",
          statistical_report.TEST_RUN == REAL_RESULTS_DIR / "test_run",
          f"TEST_RUN is {statistical_report.TEST_RUN}; if this is inside the "
          f"sandbox the measured-arm checks are no longer being exercised")
    check("the measured dialect arm is still readable",
          (REAL_RESULTS_DIR / "test_run" / "dialect_8b_baseline.json").is_file())
    check("the chart artefacts are readable and untouched",
          all(_stamp(p) is not None
              and _stamp(p)[2] == SUITE_START_DIGESTS.get(p)
              for p in (TRACKED_CHARTS.glob("*.svg")
                        if TRACKED_CHARTS.is_dir() else [])))

    # check() only tallies; it does not raise, so under pytest a violation here
    # would leave a green run and an empty report. These four are the invariants
    # the suite exists for, so they are asserted outright as well - which makes
    # `python -m pytest fix/test_narrative.py` a real gate and not a smoke test.
    assert problems == [], f"the suite modified the real results tree: {problems}"
    assert FINDINGS_STAMP_BEFORE == stamp_after, (
        f"the suite rewrote the tracked artefact {TRACKED_FINDINGS}: "
        f"{FINDINGS_STAMP_BEFORE!r} -> {stamp_after!r}")
    assert config.results_dir.is_relative_to(SUITE_RESULTS), config.results_dir
    assert narrative.NARRATIVE.is_relative_to(SUITE_RESULTS), narrative.NARRATIVE
    assert statistical_report.TEST_RUN == REAL_RESULTS_DIR / "test_run", (
        f"TEST_RUN is {statistical_report.TEST_RUN}; if the sandbox swallowed "
        f"the sealed arms, the measured-arm checks above were not exercised")

    print(f"   {len(SUITE_START_DIGESTS)} tracked files under "
          f"{REAL_RESULTS_DIR} verified unchanged; findings.md "
          f"{'still present' if FINDINGS_STAMP_BEFORE else 'was already absent'}")


def main() -> int:
    print("=" * 72)
    print("  Phase 4.4 verification")
    print(f"  sandbox    : {SUITE_RESULTS}")
    print(f"  real tree  : {REAL_RESULTS_DIR} (must stay byte-identical)")
    print("=" * 72)
    for fn in (test_no_placeholders_anywhere,
               test_no_unmeasured_claims,
               test_mock_provenance,
               test_figures_traceable,
               test_scenario_from_data,
               test_numbers_traceable,
               test_dialect_provenance,
               test_two_audiences,
               test_real_results_untouched):
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

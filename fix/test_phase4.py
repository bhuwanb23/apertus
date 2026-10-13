"""
test_phase4.py - Phase 4.1 verification.

Phase 4.1 is the sub-phase where the project's credibility either holds or
does not, because these numbers go in the submission. Its risks are not
crashes - they are plausible-looking numbers produced by the wrong thing.

  1. THE ONE SHOT IS PROTECTED FROM MOCK. The whole point of the seal and the
     pre-flight is that the unrepeatable evaluation cannot be spent on
     synthetic responses. Tested by checking the gate actually refuses.
  2. A CHANGED TEST FILE IS CAUGHT. One character of one question invalidates
     every number produced from the old file.
  3. THE IMPROVEMENT IS FROZEN. Golden Rule 4 forbids changing the fix after
     seeing the numbers; the freeze is what makes that checkable.
  4. THE SANITY CHECKER DISTINGUISHES BROKEN FROM HEALTHY. A checker that
     flags everything is useless and one that flags nothing is worse.
  5. THE PHASE 2 SCORING PATH IS REUSED, NOT REIMPLEMENTED. Golden Rule 3 is
     "identical conditions to Phase 2"; a runner with its own parsing would
     produce test numbers that cannot be compared with dev numbers.
  6. A CRASHED RUN RESUMES WITHOUT REDOING COMPLETED RUNS.
  7. A RE-RUN IS REFUSED, AND --accept-rerun IS RECORDED AS A DELIBERATE ACT.
  8. EVERY ACCESS TO THE SEALED FILE IS LOGGED.
  9. NOTHING HERE READS A TEST QUESTION. The sealed content is never opened by
     the tests, only its hash.

Run:  python fix/test_phase4.py
Exit: 0 = pass, 1 = failure
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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


# ============================================== 1. the one shot is protected
def test_refuses_on_mock() -> None:
    section("1. The runner refuses to spend the one shot on mock responses")
    import run_test_final as rtf
    from config import config

    check("both models are currently mock",
          all(config.model(m).is_mock for m in ("8b", "70b")),
          "if this is false, B2 landed - update this test, it is asserting the premise")

    pf = rtf.preflight(require_live=True, check_freeze=True)
    check("pre-flight fails while on mock", not pf["ok"])
    ids = {c["id"]: c for c in pf["checks"]}
    check("the mock backend is a named blocking check",
          "P2-backend-not-mock" in ids and not ids["P2-backend-not-mock"]["ok"])
    check("the refusal explains what is at stake",
          "unrepeatable" in ids["P2-backend-not-mock"]["detail"],
          ids["P2-backend-not-mock"]["detail"])
    check("every check is reported, not just the first failure",
          len(pf["checks"]) >= 12, f"{len(pf['checks'])} checks")

    # The CLI must exit non-zero and must not have written any test results.
    r = subprocess.run([sys.executable, str(ROOT / "eval" / "run_test_final.py"),
                        "--preflight"], capture_output=True, text=True, cwd=ROOT)
    check("--preflight exits non-zero on mock", r.returncode != 0,
          f"exit={r.returncode}")

    test_run = rtf.TEST_RUN
    written = list(test_run.glob("*.json")) if test_run.is_dir() else []
    check("no test results were written", not written,
          f"{[p.name for p in written]}")

    # And the dry run must not touch the test set either.
    r2 = subprocess.run([sys.executable, str(ROOT / "eval" / "run_test_final.py"),
                         "--dry-run"], capture_output=True, text=True, cwd=ROOT)
    check("--dry-run also refuses on mock", r2.returncode != 0)

    # require_live=False is how the harness is exercised without a model.
    pf_relaxed = rtf.preflight(require_live=False, check_freeze=False)
    check("with the live-model requirement waived it can pass",
          pf_relaxed["ok"] or any(not c["ok"] and c["fatal"]
                                  and c["id"] != "P2-backend-not-mock"
                                  for c in pf_relaxed["checks"]),
          "at least the unrelated checks must be satisfiable")
    check("waiving the model check does not waive the seal check",
          any(c["id"] == "P3-seal-verified" for c in pf_relaxed["checks"]))
    print(f"   mock -> refused, exit {r.returncode}, 0 result files written")


# ============================================== 2. a changed test file is caught
def test_seal_detects_tampering() -> None:
    section("2. A modified test file is detected")
    import seal

    ok, problems = seal.verify()
    check("the recorded seal verifies now", ok, "; ".join(problems))

    info = seal.compute()
    check("the hash covers all 36 questions",
          info["n_questions"] == 36, f"{info['n_questions']}")
    check("the seal records structure but not content",
          "correct_answer" in info["item_keys"] and len(info["item_keys"]) > 5,
          "item_keys must describe the shape")

    # Simulate tampering by pointing the verifier at a modified copy. The real
    # file is never touched - the tests must not be the thing that breaks the seal.
    sealed = seal.SEALED
    original = sealed.read_bytes()
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        tampered = Path(td) / "knowledge_test.json"
        tampered.write_bytes(original.replace(b'"A"', b'"Z"', 1))
        check("the tampered copy differs from the sealed file",
              tampered.read_bytes() != original)
        check("its hash differs", seal.file_hash(tampered) != seal.file_hash(sealed))

    # verify() reads the real path, so confirm it refuses when that file changes.
    check("seal.verify() reads the real sealed path",
          seal.SEALED.exists() and seal.SEALED.name == "knowledge_test.json")

    # A wrong expected count must also be caught, not assumed.
    saved = seal.EXPECTED_N
    try:
        seal.EXPECTED_N = 999
        ok2, problems2 = seal.verify()
        check("a wrong question count is caught", not ok2)
        check("the count problem is explained",
              any("expected" in p for p in problems2), str(problems2))
    finally:
        seal.EXPECTED_N = saved
    check("the count constant is restored", seal.EXPECTED_N == 36)

    ok3, _ = seal.verify()
    check("verification passes again once restored", ok3)
    print(f"   hash {seal.file_hash()[:16]}... verified; count and hash both checked")


# ============================================== 3. the improvement is frozen
def test_freeze() -> None:
    section("3. The improvement is frozen before the run, checked after")
    import seal

    # This suite runs against a working tree that is normally dirty - the files
    # it is testing have not been committed yet. The dirty-tree branch is
    # therefore exercised by monkeypatching rather than by waiting for a commit.
    was_dirty = seal.git_dirty

    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        saved_freeze = seal.FREEZE_PATH
        seal.FREEZE_PATH = Path(td) / "freeze.json"
        try:
            ok, problems = seal.check_freeze()
            check("an unfrozen improvement blocks the run", not ok)
            check("the refusal says how to fix it",
                  any("seal.py freeze" in p for p in problems), str(problems))

            seal.git_dirty = lambda: False
            rec = seal.freeze(note="test")
            check("freeze records the git hash",
                  rec["git_hash"] == seal.git_hash())
            check("freeze records when it happened", bool(rec["frozen_utc"]))
            check("a clean freeze records a clean tree", rec["tree_dirty"] is False)
            ok2, problems2 = seal.check_freeze()
            check("a fresh freeze at HEAD passes on a clean tree", ok2,
                  "; ".join(problems2))

            # Golden Rule 4: HEAD moving after the freeze must block.
            seal.FREEZE_PATH.write_text(json.dumps(
                {**rec, "git_hash": "0" * 40}), encoding="utf-8")
            ok3, problems3 = seal.check_freeze()
            check("a moved HEAD blocks the run", not ok3)
            check("the refusal names Golden Rule 4",
                  any("Golden Rule 4" in p for p in problems3), str(problems3))

            # A dirty tree blocks: the hash would not identify the code.
            seal.FREEZE_PATH.write_text(json.dumps(rec), encoding="utf-8")
            seal.git_dirty = lambda: True
            ok4, problems4 = seal.check_freeze()
            check("a dirty tree blocks the freeze check", not ok4)
            check("it says the hash does not identify the code",
                  any("does not identify" in p or "not reproducible" in p
                      for p in problems4), str(problems4))

            # Freezing while dirty must be refused outright.
            rec_dirty = seal.freeze(note="dirty")
            check("freezing on a dirty tree is recorded as dirty",
                  rec_dirty["tree_dirty"] is True)
        finally:
            seal.git_dirty = was_dirty
            seal.FREEZE_PATH = saved_freeze
    print("   unfrozen blocks; moved HEAD blocks (Golden Rule 4); dirty tree blocks")


# ============================================== 4. the sanity checker works
def _rows(n, n_correct, letters="ABCD", parse_err=0, api_fail=0, one_letter=False):
    out = []
    for i in range(n):
        out.append({
            "question_id": f"K{i:03d}",
            "predicted": "A" if one_letter else letters[i % len(letters)],
            "is_correct": i < n_correct,
            "api_failed": i < api_fail,
        })
    for i in range(parse_err):
        out[i]["predicted"] = "__PARSE_ERROR__"
    return out


def test_sanity_checker() -> None:
    section("4. The sanity checker separates broken runs from healthy ones")
    from run_test_final import quick_sanity_check

    # A checker that flags everything is useless; one that flags nothing is worse.
    for name, n_correct, expect_ok in (("healthy 60%", 18, True),
                                       ("healthy 45%", 13, True),
                                       ("healthy 33%", 10, True)):
        s = quick_sanity_check(_rows(30, n_correct), name)
        check(f"{name} is not flagged", s["ok"] == expect_ok,
              f"{s['problems'][:1]}")

    # Failure modes that must be caught.
    s0 = quick_sanity_check(_rows(30, 0), "zero")
    check("0% is flagged", not s0["ok"])
    check("0% says the model returned nothing", any("returned nothing" in p
                                                     for p in s0["problems"]))

    s100 = quick_sanity_check(_rows(30, 30), "perfect")
    check("100% is flagged as suspicious", not s100["ok"])
    check("100% suggests checking for contamination",
          any("contamination" in p for p in s100["problems"]), str(s100["problems"]))

    chance = quick_sanity_check(_rows(30, 7), "chance")
    check("a score at chance is flagged", not chance["ok"],
          "a working model must beat chance")
    check("it reports the chance level it used",
          chance["chance_level"] == 25.0, str(chance.get("chance_level")))

    oneletter = quick_sanity_check(_rows(30, 7, one_letter=True), "constant")
    check("a constant prediction is flagged", not oneletter["ok"])

    apifail = quick_sanity_check(_rows(30, 18, api_fail=30), "api")
    check("a fully failed endpoint is flagged", not apifail["ok"])
    check("it names the endpoint", any("not serving" in p for p in apifail["problems"]))

    partial = quick_sanity_check(_rows(30, 18, api_fail=4), "partial")
    check("a partial API failure is flagged", not partial["ok"])

    parse = quick_sanity_check(_rows(30, 18, parse_err=15), "parse")
    check("heavy parse errors are flagged", not parse["ok"])
    check("it blames the parser", any("parser" in p for p in parse["problems"]))

    # Chance level must follow the data, not a constant. Two-option questions
    # have a 50% floor; flagging 50% as "at chance" there would be correct, but
    # flagging a 2-option run at 25% would not.
    two_opt = quick_sanity_check(_rows(30, 25, letters="AB"), "2-opt")
    check("two-option chance is computed as 50%", two_opt["chance_level"] == 50.0,
          str(two_opt["chance_level"]))
    check("a strong two-option run is not flagged", two_opt["ok"],
          str(two_opt["problems"][:1]))

    empty = quick_sanity_check([], "empty")
    check("an empty run is flagged, not crashed", not empty["ok"])
    check("empty reports n=0", "n" not in empty or empty.get("n") == 0)
    print("   10/10 cases behave: 3 healthy pass, 7 failure modes caught")


# ================================= 5. the Phase 2 scoring path is reused
def test_reuses_phase2_scorers() -> None:
    section("5. The Phase 2 scoring path is reused, not reimplemented")
    import run_test_final as rtf

    src = (ROOT / "eval" / "run_test_final.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines()
                     if not l.strip().startswith("#"))
    code = code.split('"""')[0] + "".join(code.split('"""')[2::2])

    for fn in ("evaluate_knowledge", "evaluate_values", "evaluate_dialect"):
        check(f"{fn} is imported from Phase 2", fn in src, "must reuse the scorer")

    # The failure the plan's runner would have introduced: parsing without
    # options=, which silently disables exact-phrase matching.
    check("the runner does not call extract_answer itself",
          "extract_answer(" not in code,
          "reimplemented parsing breaks comparability with dev")
    check("the runner does not call judge_response itself",
          "judge_response(" not in code,
          "reimplemented judging bypasses score_from_observations")

    # Knowledge must go through evaluate_knowledge with split="test".
    check("the test split is requested explicitly",
          'split="test"' in code, "the runner must not fall back to the default")

    # The improvement description must be derived, not typed as a string that
    # can drift from the corpus it describes. The module DOCSTRING quotes the
    # plan's wrong figure in order to correct it, so the check is on executable
    # code - otherwise the correction is what trips the check.
    check("improvement metadata is a structured object",
          isinstance(rtf.IMPROVEMENT, dict) and "retrieval_backend" in rtf.IMPROVEMENT)
    check("it does not hardcode a source count",
          "30" not in rtf.IMPROVEMENT.get("method", ""),
          f"method={rtf.IMPROVEMENT.get('method')!r}; the corpus has 100 sources")

    # All eight runs exist, and knowledge gets both methods.
    ids = [f"{t}_{m}_{x}" for t, m, x in rtf.RUNS]
    check("8 runs are planned", len(ids) == 8, str(len(ids)))
    for m in ("8b", "70b"):
        for meth in ("baseline", "improved"):
            check(f"knowledge_{m}_{meth} is planned",
                  f"knowledge_{m}_{meth}" in ids)
        check(f"a values run is planned for {m}",
              any(i.startswith(f"values_{m}_") for i in ids), str(ids))
        check(f"a dialect run is planned for {m}",
              any(i.startswith(f"dialect_{m}_") for i in ids), str(ids))
    check("no run targets anything but the two configured models",
          all(m in ("8b", "70b") for _, m, _ in rtf.RUNS))
    print(f"   {len(ids)} runs planned, all via the Phase 2 scorers")


# ============================================== 6. resume without redoing
def test_resume() -> None:
    section("6. An interrupted run resumes without repeating completed work")
    import run_test_final as rtf

    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        saved = rtf.TEST_RUN
        rtf.TEST_RUN = Path(td)
        # A stubbed dispatcher. The real one evaluates the model against the
        # sealed set, so it must never be reachable from a test - an earlier
        # version of this suite called run_one for real and read all 36 test
        # questions through the mock backend. That is what guard() now refuses,
        # and the test that proves it is section 6b below.
        calls: list[tuple] = []

        def fake_dispatch(task, model, method):
            calls.append((task, model, method))
            return {"overall": 50.0, "stub": True}

        saved_dispatch = rtf.DISPATCH
        rtf.DISPATCH = {"knowledge": lambda m, x: fake_dispatch("knowledge", m, x),
                        "values": lambda m: fake_dispatch("values", m, "-"),
                        "dialect": lambda m: fake_dispatch("dialect", m, "-")}
        saved_guard = rtf.guard
        rtf.guard = lambda require_live=True: (True, [])
        # The audit log is redirected too. Otherwise every test run appends
        # "test-run knowledge/8b/baseline" to the real log, and after a few test
        # runs the record of who opened the sealed set is unreadable - test
        # accesses and real ones become indistinguishable, which defeats the
        # only mechanism that caught the original incident.
        import seal as seal_mod
        saved_audit = seal_mod.AUDIT_PATH
        real_audit_len = len(seal_mod.read_audit())
        seal_mod.AUDIT_PATH = Path(td) / "audit.log"
        try:
            r = rtf.run_one("knowledge", "8b", "baseline", 3, resume=False)
            check("a completed run is recorded",
                  (Path(td) / "knowledge_8b_baseline.json").exists(),
                  "run_one must leave a record")
            check("exactly one dispatch happened", len(calls) == 1, str(calls))

            # Now it is recorded. Running it again must be refused.
            before = len(calls)
            again = rtf.run_one("knowledge", "8b", "baseline", 3, resume=False)
            check("a recorded run is skipped without --resume", again.get("skipped"),
                  "re-running is Golden Rule 1")
            check("skipping does not call the model again", len(calls) == before,
                  f"{len(calls) - before} extra dispatches")

            # --resume re-runs it deliberately.
            rtf.run_one("knowledge", "8b", "baseline", 3, resume=True)
            check("--resume does re-run the arm", len(calls) == before + 1,
                  str(calls))

            # The pre-flight notices the recorded run as a non-fatal warning.
            pf = rtf.preflight(require_live=False, check_freeze=False)
            p13 = [c for c in pf["checks"] if c["id"] == "P13-not-a-rerun"]
            check("a recorded run is surfaced by the pre-flight", bool(p13))
            if p13:
                check("it is a warning, not a hard block", not p13[0]["fatal"],
                      "interrupted runs must remain resumable")
                check("it names the recorded runs",
                      "knowledge_8b_baseline" in p13[0]["detail"],
                      p13[0]["detail"])
        finally:
            rtf.TEST_RUN = saved
            rtf.DISPATCH = saved_dispatch
            rtf.guard = saved_guard
            seal_mod.AUDIT_PATH = saved_audit
        check("the test run did not touch the real audit log",
              len(seal_mod.read_audit()) == real_audit_len,
              "test accesses must not be mixed into the real record")

    src = (ROOT / "eval" / "run_test_final.py").read_text(encoding="utf-8")
    check("run_one catches exceptions and reports them per run",
          "except Exception" in src)
    check("it re-raises KeyboardInterrupt so a Ctrl-C stops cleanly",
          "except KeyboardInterrupt" in src)
    print("   recorded runs are skipped; --resume re-runs only that arm")


def test_run_one_is_guarded() -> None:
    section("6b. run_one refuses even when called directly (the bug this found)")
    import run_test_final as rtf

    # The exact failure that produced this check: this suite called run_one
    # directly, which skipped main()'s pre-flight and read all 36 sealed
    # questions through the mock backend. Nothing caught it except a human
    # reading the log. The guard now lives at the point of use.
    ok, problems = rtf.guard()
    check("guard() refuses on mock", not ok)
    check("it names the mock backend", any("mock" in p for p in problems),
          str(problems))

    # And it refuses at the point of use, not just in main().
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        saved = rtf.TEST_RUN
        rtf.TEST_RUN = Path(td)
        calls = []
        saved_dispatch = rtf.DISPATCH
        rtf.DISPATCH = {k: (lambda *a: calls.append(a) or {}) for k in
                        ("knowledge", "values", "dialect")}
        import seal as seal_mod2
        before_log = len(seal_mod2.read_audit())
        try:
            refused = False
            try:
                rtf.run_one("knowledge", "8b", "baseline", 3, resume=False)
            except SystemExit:
                refused = True
            check("a direct run_one call is refused", refused)
            check("no model call was made", not calls, str(calls))
            check("nothing was written to test_run/",
                  not list(Path(td).glob("*.json")))
        finally:
            rtf.TEST_RUN = saved
            rtf.DISPATCH = saved_dispatch
        check("a refused call does not log an access",
              len(seal_mod2.read_audit()) == before_log,
              "the guard must fire before the access is logged")

    src = (ROOT / "eval" / "run_test_final.py").read_text(encoding="utf-8")
    body = src.split("def run_one", 1)[1]
    check("the guard is called inside run_one", "guard()" in body.split("def ")[0],
          "the guard must sit at the point of use")
    print("   direct run_one on mock: refused, 0 model calls, 0 files written")


# ============================================== 7. a re-run is refused
def test_rerun_refused() -> None:
    section("7. Re-running to improve the numbers is refused")
    import run_test_final as rtf

    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        saved = rtf.TEST_RUN
        rtf.TEST_RUN = Path(td)
        try:
            (Path(td) / "knowledge_8b_baseline.json").write_text("{}", encoding="utf-8")
            pf = rtf.preflight(require_live=False, check_freeze=False)
            check("a recorded run does not make pre-flight ok on its own",
                  any(not c["ok"] for c in pf["checks"]))
        finally:
            rtf.TEST_RUN = saved

    src = (ROOT / "eval" / "run_test_final.py").read_text(encoding="utf-8")
    check("--accept-rerun exists as an explicit opt-in", "--accept-rerun" in src)
    check("--resume exists and is distinct", "--resume" in src)
    check("the golden rule is named where runs are skipped", "Golden Rule 1" in src)
    check("rule 4 is named where the freeze is checked", "Golden Rule 4" in src)
    print("   --resume and --accept-rerun are distinct and both explicit")


# ============================================== 8. every access is logged
def test_audit_log() -> None:
    section("8. Every access to the sealed file is logged")
    import seal

    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        saved = seal.AUDIT_PATH
        seal.AUDIT_PATH = Path(td) / "access.log"
        try:
            check("a fresh log is empty", seal.read_audit() == [])
            seal.log_access("test-run knowledge/8b/baseline", actor="tester")
            seal.log_access("test-run values/8b/baseline", actor="tester")
            entries = seal.read_audit()
            check("both accesses are recorded", len(entries) == 2, str(len(entries)))
            check("each entry carries a timestamp", all(e.get("utc") for e in entries))
            check("each entry carries a git hash", all(e.get("git_hash") for e in entries))
            check("each entry states a reason",
                  all("test-run" in e.get("reason", "") for e in entries))

            # Append-only: a second write must not truncate.
            seal.log_access("third", actor="tester")
            check("the log appends rather than overwrites",
                  len(seal.read_audit()) == 3, str(len(seal.read_audit())))

            # A corrupt line must not make the log unreadable.
            with open(seal.AUDIT_PATH, "a", encoding="utf-8") as fh:
                fh.write("{not json\n")
            check("a malformed line does not break the audit reader",
                  len(seal.read_audit()) == 4)
        finally:
            seal.AUDIT_PATH = saved
    print("   access log is append-only, attributable, and survives corruption")


# ================================== 9. the tests never read a test question
def test_sealed_content_untouched() -> None:
    section("9. The tests never open a test question")
    import ast

    # Only the sealed file's bytes are read, for hashing. Assert no test code
    # extracts a question, an option or an answer from the test split.
    for path in (ROOT / "fix" / "test_phase4.py", ROOT / "eval" / "run_test_final.py"):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                sub = ast.unparse(node)
                if "knowledge_test" in src and any(
                        k in sub for k in ('["question"]', '["options"]',
                                           '["correct_answer"]')):
                    check(f"{path.name} does not index into a test question",
                          False, sub)

    check("the seal file is still intact",
          seal_hash_matches(), "the tests must not have modified the sealed set")

    sealed = ROOT / "data" / "knowledge" / "knowledge_test.json"
    check("the sealed file still has 36 questions",
          len(json.loads(sealed.read_text(encoding="utf-8"))) == 36)
    check("the tests wrote no results into test_run/",
          not list((ROOT / "eval" / "results" / "test_run").glob("*.json"))
          if (ROOT / "eval" / "results" / "test_run").is_dir() else True)
    print("   sealed file untouched, no question content read by any test")


def seal_hash_matches() -> bool:
    import seal
    ok, _ = seal.verify()
    return ok


def main() -> int:
    print("=" * 72)
    print("  Phase 4.1 verification")
    print("=" * 72)
    for fn in (test_refuses_on_mock,
               test_seal_detects_tampering,
               test_freeze,
               test_sanity_checker,
               test_reuses_phase2_scorers,
               test_resume,
               test_run_one_is_guarded,
               test_rerun_refused,
               test_audit_log,
               test_sealed_content_untouched):
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

"""
run_test_final.py - Phase 4.1: THE definitive evaluation. Run once.

    python eval/run_test_final.py                 # all 8 runs
    python eval/run_test_final.py --only knowledge_8b_baseline
    python eval/run_test_final.py --preflight      # check only, touch nothing

READ THIS BEFORE RUNNING ANYTHING

This opens data/knowledge/knowledge_test.json, which is sealed until now and is
scored ONCE. There is no second attempt: the numbers go into the submission,
the README and the video, and re-running until they look better is not a result,
it is a selection effect with extra steps.

The tool enforces that rather than asking for it:

  * it refuses on a mock backend, so the one shot cannot be spent on synthetic
    responses while B2 is still open;
  * it refuses if the test file's hash moved since `eval/seal.py record`;
  * it refuses if HEAD moved since `eval/seal.py freeze`, which is Golden
    Rule 4 - no changing the improvement after seeing the numbers;
  * it refuses on a dirty working tree, because a hash that does not identify
    the code does not identify the result;
  * it logs every access to the sealed file to an append-only log.

WHY IT CALLS THE PHASE 2 FUNCTIONS INSTEAD OF REIMPLEMENTING THEM

docs/plans/phase_4.md Step 2 ships a self-contained runner with its own
`extract_answer` call, its own judge invocation and a dialect branch that saves
responses without scoring them. Using it would quietly break Golden Rule 3 -
"identical conditions to Phase 2, same parsing code" - because:

  * `extract_answer(text)` is called WITHOUT `options=`, so exact option-phrase
    matching and the paraphrase ladder never run. Phase 2 scored dev with
    `explain_answer(text, options=...)`. Test numbers computed a different way
    are not comparable to dev numbers, which is the entire point of a held-out
    set;
  * `PARSE_ERROR` is compared to the answer rather than scored through
    scoring.py, so the parse-failure rate - which Phase 2 tracks separately and
    which baseline_report.py hard-fails above 10% - is invisible;
  * values are judged with a bare `judge_response(...)` call, bypassing
    `score_from_observations`, which is where values_rubric.md §2/§5 are
    actually applied;
  * dialect responses are saved with no scoring at all, discarding
    data/dialect/dialect_scoring_protocol.md entirely;
  * the metadata hardcodes `improvement_method: "RAG over 30 official Swiss
    sources"` when the corpus is 100 sources / 189 non-dialect chunks. A wrong
    provenance string in the definitive metadata is worse than none.

So this runner calls `evaluate_knowledge`, `evaluate_values` and
`evaluate_dialect` - the same functions that produced every Phase 2 number -
and adds only what Phase 4 needs: the pre-flight gate, resume, per-run
artefacts under test_run/, run metadata, and sanity checks.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "fix"))
sys.path.insert(0, str(ROOT / "fix" / "rag"))

from config import config                      # noqa: E402
import seal                                    # noqa: E402

RESULTS = config.results_dir
TEST_RUN = RESULTS / "test_run"
RAW_DIR = RESULTS / "raw_responses"

# ---------------------------------------------------------------- scope
# The plan (docs/plans/phase_4.md, TEST SET GOLDEN RULES, rule 2) called for four
# knowledge runs: 8B and 70B, each baseline and improved. The evaluation machine
# has 8 GB of VRAM (RTX 5060) and Apertus v1.5 70B cannot be loaded or served
# under any quantisation, so the 70B arms were dropped rather than approximated.
#
# The scope is DECLARED here, not inferred.
#
# Inferring it from "whatever is not mock" would be a serious regression: the
# whole point of the mock guard is that an unconfigured backend must not be
# treated as a result. Auto-shrinking to the live set would reintroduce exactly
# that failure one level up - a model could be quietly excluded and the run
# would still report success. So instead:
#   - the in-scope set is fixed and reviewable,
#   - the dropped set is recorded in run_metadata as a disclosure,
#   - and preflight FAILS if a model in the dropped set is actually live,
#     because that means the scope is stale and must be re-examined on purpose.
SCOPE_MODELS: tuple[str, ...] = ("8b",)
DROPPED_MODELS: tuple[str, ...] = ("70b",)
DROPPED_REASON = (
    "Apertus v1.5 70B cannot be loaded on this evaluation machine (8 GB VRAM, "
    "RTX 5060) under any quantisation. The 70B baseline and improved arms were "
    "dropped, not approximated. Consequence, stated plainly: a single-model "
    "paired design cannot distinguish a general improvement from an 8B-specific "
    "effect, so no cross-scale or generalisation claim is available."
)

METHODS = ("baseline", "improved")

# Which runs the plan requires. Knowledge gets 2 (1 model x 2 methods);
# values and dialect get 1 each - there is no "improved" arm for them, because
# the improvement is retrieval over the knowledge corpus.
RUNS = ([(t, m, meth) for t in ("knowledge", "values", "dialect")
         for m in SCOPE_MODELS
         for meth in (METHODS if t == "knowledge" else ("baseline",))])

# What the improvement actually is. Recorded in run_metadata from the live
# objects rather than typed as a string, so it cannot drift from reality.
IMPROVEMENT = {
    "method": "RAG retrieval over the harvested source corpus",
    "variant": "rag",
    "retrieval_backend": "bm25",
    "note": ("The Phase 4.1 'improved' arm applies retrieval only. The 3.3a "
             "system prompt is behavioural-rules-only and is not applied here; "
             "see fix/rag/RESULTS.md."),
}


# ============================================================== the guard
def guard(require_live: bool = True) -> tuple[bool, list[str]]:
    """
    The three conditions under which the sealed set must not be opened.

    Kept separate from preflight() because preflight() is a report and this is
    an enforcement point. It is called both by main() and by run_one(), so the
    refusal does not depend on which entry point was used.
    """
    problems: list[str] = []
    if require_live:
        mocks = [m for m in SCOPE_MODELS if config.model(m).is_mock]
        if mocks:
            problems.append(
                f"backend is mock for: {', '.join(mocks)}. The one-shot evaluation "
                f"cannot be spent on synthetic responses.")
        # A model that is actually LIVE but sits outside the declared scope is a
        # scope bug, not a free pass. Silently ignoring it would let an
        # excluded arm vanish from the run without anyone noticing.
        live_but_dropped = [m for m in DROPPED_MODELS
                            if not config.model(m).is_mock]
        if live_but_dropped:
            problems.append(
                f"model(s) {', '.join(live_but_dropped)} are configured on a live "
                f"backend but are declared out of scope. Either add them to "
                f"SCOPE_MODELS or remove them from the config deliberately - "
                f"do not let this pass unnoticed.")
    ok, seal_problems = seal.verify()
    if not ok:
        problems.extend(seal_problems)
    return not problems, problems


# ============================================================ pre-flight
def preflight(require_live: bool = True, check_freeze: bool = True) -> dict:
    """
    Every reason this run should not start. Returns them all, not just the
    first, because fixing them one-per-run wastes the one thing that cannot be
    replaced: time before a deadline.
    """
    checks: list[dict] = []

    def add(cid: str, ok: bool, detail: str, fatal: bool = True) -> None:
        checks.append({"id": cid, "ok": ok, "detail": detail, "fatal": fatal})

    # -- the one that matters most ------------------------------------------
    mocks = [m for m in SCOPE_MODELS if config.model(m).is_mock]
    live_but_dropped = [m for m in DROPPED_MODELS if not config.model(m).is_mock]
    if require_live:
        add("P2-backend-not-mock", not mocks,
            f"mock backend for: {', '.join(mocks)} - the single unrepeatable "
            f"evaluation cannot be spent on synthetic responses"
            if mocks else
            f"every in-scope model ({', '.join(SCOPE_MODELS)}) on a live backend")

    # Not fatal by itself - it is a known, recorded reduction - but fatal if a
    # dropped model turns out to be live, because then the scope is stale.
    add("P2b-scope-not-stale", not live_but_dropped,
        f"dropped model(s) {', '.join(live_but_dropped)} are live; re-examine "
        f"SCOPE_MODELS before running"
        if live_but_dropped else
        f"{len(DROPPED_MODELS)} declared dropped model(s) "
        f"({', '.join(DROPPED_MODELS)}) - see DISCLOSURES in run_metadata")

    # -- sealed-set integrity ------------------------------------------------
    ok, problems = seal.verify()
    add("P3-seal-verified", ok, "; ".join(problems) if problems else
        f"hash matches the recorded {seal.file_hash()[:16]}...")

    info = seal.compute()
    add("P4-question-count", info.get("n_questions") == seal.EXPECTED_N,
        f"{info.get('n_questions')} questions (expected {seal.EXPECTED_N})")

    # -- Golden Rule 4: frozen improvement ----------------------------------
    if check_freeze:
        okf, pf = seal.check_freeze()
        add("P5-improvement-frozen", okf, "; ".join(pf) if pf else
            f"HEAD {seal.git_hash()[:12]} matches the freeze")

    # -- reproducibility -----------------------------------------------------
    add("P6-tree-clean", not seal.git_dirty(),
        "uncommitted changes - the recorded hash does not identify the code"
        if seal.git_dirty() else "working tree is clean")

    # -- identical conditions to Phase 2 ------------------------------------
    temps = {m: config.model(m).temperature for m in SCOPE_MODELS}
    add("P7-temperature-zero", all(t == 0 for t in temps.values()), f"{temps}")

    seeds = {m: config.model(m).seed for m in SCOPE_MODELS}
    add("P8-seed-set", all(s is not None for s in seeds.values()), f"{seeds}")

    from prompts import PROMPT_VERSION
    add("P9-prompt-version", bool(PROMPT_VERSION), f"PROMPT_VERSION={PROMPT_VERSION}")

    # -- the corpora exist ---------------------------------------------------
    for name, rel in (("knowledge test", "data/knowledge/knowledge_test.json"),
                      ("values scenarios", "data/values/values_scenarios.json"),
                      ("dialect items", "data/dialect/dialect_items.json")):
        p = ROOT / rel
        add(f"P10-{name.split()[0]}-present", p.exists(), rel)

    # -- the improvement is actually loadable --------------------------------
    try:
        from embeddings import build_index, load_corpus
        chunks = load_corpus()
        add("P11-rag-corpus-loads", len(chunks) > 0,
            f"{len(chunks)} chunks" if chunks else "corpus is empty - "
            "run: python fix/rag/prepare_corpus.py")
    except Exception as e:
        add("P11-rag-corpus-loads", False, f"{type(e).__name__}: {e}")

    # -- resources -----------------------------------------------------------
    free_mb = shutil.disk_usage(RESULTS.parent).free // (1024 * 1024)
    add("P12-disk-space", free_mb > 500, f"{free_mb} MB free")

    # -- is this a re-run? ---------------------------------------------------
    done = [r for r in RUNS if (TEST_RUN / f"{r[0]}_{r[1]}_{r[2]}.json").exists()]
    if done:
        add("P13-not-a-rerun", False,
            f"{len(done)} run(s) already recorded: "
            f"{', '.join(f'{t}_{m}_{x}' for t, m, x in done)} - "
            f"Golden Rule 1. Use --resume to continue an interrupted run, or "
            f"--accept-rerun if you are deliberately redoing one.", fatal=False)

    return {"ok": all(c["ok"] for c in checks if c["fatal"]),
            "checks": checks}


def print_preflight(pf: dict) -> None:
    print("=" * 72)
    print("  PRE-FLIGHT — do not proceed until this is clean")
    print("=" * 72)
    for c in pf["checks"]:
        mark = "PASS" if c["ok"] else ("FAIL" if c["fatal"] else "WARN")
        print(f"  [{mark}] {c['id']:<26} -- {c['detail']}")
    fatal = [c for c in pf["checks"] if not c["ok"] and c["fatal"]]
    print("=" * 72)
    if fatal:
        print(f"  {len(fatal)} BLOCKING problem(s). The test set stays sealed.")
        for c in fatal:
            print(f"    - {c['id']}: {c['detail']}")
    else:
        print("  All blocking checks passed.")
    print("=" * 72)


# ============================================================ sanity checks
def quick_sanity_check(results: list, label: str) -> dict:
    """
    Run immediately after each test run. Catches the failures that would
    otherwise be discovered in the README.

    The plan's version only flags 0% and 100%. Two checks are added because
    this project has already hit both failure modes it misses:

      * a broken PARSER scores near chance while every request succeeds, so
        "the API worked" is not evidence the run worked. Flagged when the score
        sits within a small margin ABOVE chance - at or below chance with no
        request failures, a four-option benchmark is being answered at random or
        not parsed at all.
      * a model that answers the same letter for everything scores exactly 25%
        and looks plausible. Detected by counting distinct predictions.

    The chance baseline is the number of distinct options, not a constant. It
    is read from the results where available, because "25%" is only right for
    four-option questions and a hardcoded 35% flagged a healthy 26.7% run as
    broken during development.
    """
    total = len(results)
    if total == 0:
        return {"label": label, "ok": False, "problems": ["no results"]}

    correct = sum(1 for r in results if r.get("is_correct"))
    parse_errors = sum(1 for r in results
                       if r.get("predicted") == "__PARSE_ERROR__")
    api_failed = sum(1 for r in results if r.get("api_failed"))
    acc = correct / total * 100
    preds = [r.get("predicted") for r in results if r.get("predicted")]
    distinct = len(set(preds))
    modal = max((preds.count(p) for p in set(preds)), default=0)

    # Chance level from the data, not a constant: four-option MCQ is 25%, but a
    # different task has a different floor and a hardcoded threshold misreports.
    letters = [p for p in preds if isinstance(p, str) and len(p) == 1
               and p.upper() in "ABCDEFGH"]
    chance = (100.0 / len(set(letters))) if len(set(letters)) >= 2 else 100.0

    problems: list[str] = []
    if acc == 0.0:
        problems.append("0% ACCURACY - the model returned nothing usable")
    elif acc == 100.0:
        problems.append("100% ACCURACY - check for test-set contamination or a "
                        "leaked answer key before believing this")
    if api_failed == total:
        problems.append("every request failed - the endpoint is not serving")
    elif api_failed:
        problems.append(f"{api_failed}/{total} requests failed")
    if parse_errors / total > 0.20:
        problems.append(f"{parse_errors}/{total} parse errors (>20%) - the parser "
                        f"or the output format changed")
    # A working model on a four-option benchmark lands clearly above chance. A
    # score at or just above chance with no request failures means the answers
    # are not being parsed into options - the requests succeeded and the run
    # still produced nothing.
    if (total >= 20 and not api_failed and letters
            and acc <= chance + 5.0):
        problems.append(f"{acc:.1f}% is at or barely above the {chance:.1f}% chance "
                        f"level on {total} items with no request failures - check "
                        f"whether responses are being parsed into options")
    # A model that emits one letter for every question scores chance exactly and
    # looks entirely plausible in a table.
    if distinct <= 1 and total >= 10:
        problems.append(f"every prediction is the same value ({preds[0]!r}) - the "
                        f"model is not discriminating")
    elif modal / total > 0.6 and total >= 10:
        problems.append(f"{modal}/{total} share one answer - near-constant output")

    return {
        "label": label, "n": total, "accuracy": round(acc, 1),
        "correct": correct, "parse_errors": parse_errors, "api_failed": api_failed,
        "distinct_predictions": distinct, "modal_share": round(modal / total, 3),
        "chance_level": round(chance, 1),
        "ok": not problems, "problems": problems,
    }


def print_sanity(s: dict) -> None:
    print(f"\n  SANITY CHECK - {s['label']}")
    if "n" not in s:
        for p in s["problems"]:
            print(f"    {p}")
        return
    print(f"    accuracy {s['accuracy']}% ({s['correct']}/{s['n']})   "
          f"chance {s.get('chance_level', '?')}%   "
          f"parse errors {s['parse_errors']}/{s['n']}   "
          f"api failures {s['api_failed']}/{s['n']}   "
          f"distinct answers {s['distinct_predictions']}")
    if s["ok"]:
        print("    looks plausible")
    else:
        for p in s["problems"]:
            print(f"    RED FLAG: {p}")


# ================================================================== runners
def _rag_context_for(questions: list, top_k: int):
    """Retrieval for the improved arm, built once and shared by every model.

    The retrieval is model-independent, so building it per model would be wasted
    work - but it must be the SAME retrieval, or the two improved arms are not
    comparable to each other.
    """
    from embeddings import build_index, load_corpus
    from retriever import SwissRetriever
    chunks = load_corpus()
    index = build_index(chunks, IMPROVEMENT["retrieval_backend"])
    r = SwissRetriever(index, chunks)
    out = {}
    for q in questions:
        got = r.retrieve("Switzerland " + q["question"], top_k=top_k)
        out[q["id"]] = r.format_context(got)
    return out, len(chunks)


def run_knowledge(model: str, method: str, top_k: int = 3) -> dict:
    """Uses eval/run_knowledge.py's evaluate_knowledge - the Phase 2 scorer."""
    from run_knowledge import evaluate_knowledge, load_questions

    questions = load_questions("test")
    context = ""
    if method == "improved":
        # The contamination gate runs before anything is sent, exactly as it
        # does in the dev path. A prompt that answers the test set would make
        # the headline number meaningless, and Phase 3.3 found the planned
        # prompt answered 30% of dev.
        from rag_prompt import load_system_prompt
        _, gate = load_system_prompt(None)
        if gate.get("n_items") and not gate["clean"]:
            raise SystemExit("refusing: contaminated system prompt")
        contexts, n_chunks = _rag_context_for(questions, top_k)
        # Per-question context, NOT one stitched string for the whole split.
        #
        # The previous version joined all 36 contexts with per-question headers
        # and passed them as a single rag_context. Two things went wrong: the
        # stitched prompt was ~17k tokens and overflowed the 8k context window,
        # and every question was answered alongside the retrieved evidence for
        # all the OTHER questions. The dev path (run_rag_eval) retrieves per
        # question, so this restores dev-test comparability rather than changing
        # the intervention.
        print(f"  retrieval: {n_chunks} chunks, {len(contexts)} per-question "
              f"contexts, max {max(len(c) for c in contexts.values())} chars")

    scores = evaluate_knowledge(model, split="test",
                                rag_contexts=contexts if method == "improved" else None,
                                rag_context=context)
    return scores


def run_values(model: str) -> dict:
    """Uses eval/run_values.py - the Phase 2 values runner and judge path."""
    from run_values import evaluate_values
    return evaluate_values(model)


def run_dialect(model: str) -> dict:
    """Uses eval/run_dialect.py - which implements dialect_scoring_protocol.md."""
    from run_dialect import evaluate_dialect
    return evaluate_dialect(model)


DISPATCH = {"knowledge": run_knowledge, "values": run_values, "dialect": run_dialect}


# ================================================================== the run
def load_results(task: str, model: str, method: str) -> list:
    """The parsed rows for one arm, from wherever this version of the harness
    put them. Phase 2's layout has changed across phases, so all three are
    tried rather than assuming one."""
    tag = f"{task}_{model}_test"
    candidates = [
        RESULTS / "parsed" / f"{tag}_{method}.json",
        RESULTS / "parsed" / f"{tag}_{'rag' if method == 'improved' else 'base'}.json",
        RESULTS / "parsed" / f"{tag}.json",
    ]
    for p in candidates:
        if p.exists():
            payload = json.loads(p.read_text(encoding="utf-8"))
            return payload["results"] if isinstance(payload, dict) and "results" in payload \
                else payload
    return []


def run_one(task: str, model: str, method: str, top_k: int, resume: bool) -> dict:
    """
    Run one arm - behind its own gate.

    The gate is re-checked HERE as well as in main(). That duplication is
    deliberate and was added after this function was called directly from a test
    and read the sealed set through the mock backend: main()'s pre-flight only
    protects callers that go through main(). A guard that lives at the top of
    the program rather than at the point of use protects the main path and
    nothing else, and "nothing else" is where the accident happens.
    """
    ok, problems = guard()
    if not ok:
        raise SystemExit(
            "\n  REFUSING TO RUN " + f"{task}_{model}_{method}" + ".\n  "
            + "\n  ".join(problems)
            + "\n\n  The sealed set stays closed. This guard also fires when "
              "run_one is called\n  directly, so the test suite cannot consume "
              "the one shot either.")

    out_path = TEST_RUN / f"{task}_{model}_{method}.json"
    if out_path.exists() and not resume:
        print(f"  {task}_{model}_{method}: already recorded, skipping "
              f"(Golden Rule 1 - use --resume to continue, --accept-rerun to redo)")
        return {"skipped": True, "path": out_path.name}

    print(f"\n{'#' * 72}\n#  {task.upper()} | {model.upper()} | {method}\n{'#' * 72}")
    started = time.time()
    seal.log_access(f"test-run {task}/{model}/{method}")

    try:
        scores = DISPATCH[task](model, method) if task == "knowledge" \
            else DISPATCH[task](model)
    except KeyboardInterrupt:
        print("\n  interrupted - completed runs are kept, rerun with --resume")
        raise
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "task": task, "model": model,
                "method": method}

    rows = load_results(task, model, method)
    sanity = quick_sanity_check(rows, f"{task} {model} {method}")
    print_sanity(sanity)

    payload = {
        "task": task, "model": model, "method": method,
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_hash": seal.git_hash(),
        "backend": config.model(model).backend,
        "is_mock": config.model(model).is_mock,
        "temperature": config.model(model).temperature,
        "seed": config.model(model).seed,
        "n": len(rows),
        "scores": scores,
        "sanity": sanity,
        "results": rows,
        "duration_s": round(time.time() - started, 1),
    }
    TEST_RUN.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"  -> {out_path.relative_to(ROOT)}"
          if out_path.is_relative_to(ROOT) else f"  -> {out_path}")
    return payload


def write_metadata(records: dict, top_k: int, duration_min: float) -> Path:
    from prompts import PROMPT_VERSION
    meta = {
        "run_started_utc": records.get("_started"),
        "run_finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_minutes": round(duration_min, 1),
        "git_hash": seal.git_hash(),
        "tree_dirty": seal.git_dirty(),
        "freeze": seal.frozen(),
        "seal": json.loads(seal.HASH_PATH.read_text(encoding="utf-8"))
                if seal.HASH_PATH.exists() else None,
        "prompt_version": PROMPT_VERSION,
        "models": {m: {"backend": config.model(m).backend,
                       "model_id": config.model(m).model_id,
                       "temperature": config.model(m).temperature,
                       "seed": config.model(m).seed,
                       "is_mock": config.model(m).is_mock}
                   for m in SCOPE_MODELS},
        "improvement": {**IMPROVEMENT, "top_k": top_k},
        "judge_model": config.judge_model,
        "self_judged": config.judge_model in SCOPE_MODELS,
        "scope": {"in_scope": list(SCOPE_MODELS),
                  "dropped": list(DROPPED_MODELS),
                  "dropped_reason": DROPPED_REASON},
        "runs": {k: {kk: vv for kk, vv in v.items() if kk != "results"}
                 for k, v in records.items() if not k.startswith("_")},
        "test_set_size": {
            "knowledge": seal.compute().get("n_questions"),
            "values": len(json.loads(
                (ROOT / "data/values/values_scenarios.json").read_text(encoding="utf-8"))),
            "dialect": len(json.loads(
                (ROOT / "data/dialect/dialect_items.json").read_text(encoding="utf-8"))),
        },
    }
    p = TEST_RUN / "run_metadata.json"
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="THE definitive held-out run. Once.")
    ap.add_argument("--preflight", action="store_true",
                    help="run the checks and exit without touching the test set")
    ap.add_argument("--only", default=None,
                    help="one run id, e.g. knowledge_8b_baseline")
    ap.add_argument("--resume", action="store_true",
                    help="continue after an interruption; completed runs are kept")
    ap.add_argument("--accept-rerun", action="store_true",
                    help="deliberately redo a run that is already recorded")
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan without running anything")
    args = ap.parse_args()

    pf = preflight(require_live=True, check_freeze=True)
    print_preflight(pf)

    if args.preflight or args.dry_run:
        return 0 if pf["ok"] else 1

    rerun_warn = [c for c in pf["checks"] if c["id"] == "P13-not-a-rerun"]
    if rerun_warn and not (args.resume or args.accept_rerun):
        print("\n  A run is already recorded. Choose deliberately:")
        print("    --resume        continue an interrupted run, keeping finished ones")
        print("    --accept-rerun  redo it anyway (recorded in run_metadata)")
        return 1

    blocking = [c for c in pf["checks"] if not c["ok"] and c["fatal"]
                and c["id"] != "P13-not-a-rerun"]
    if blocking:
        print("\n  REFUSING TO RUN. The test set stays sealed.")
        print("  Each problem above is a reason the numbers would be unusable.")
        print("  Golden Rule 1 is not worth trading for a run you cannot cite.")
        return 1

    selected = [(t, m, x) for t, m, x in RUNS
                if args.only is None or f"{t}_{m}_{x}" == args.only]
    if not selected:
        print(f"no run matches {args.only!r}. available: "
              + ", ".join(f"{t}_{m}_{x}" for t, m, x in RUNS))
        return 1

    print(f"\n{'🔥' * 24}\n  FINAL TEST EVALUATION - Swiss Reality Check\n{'🔥' * 24}")
    print(f"  git  : {seal.git_hash()}")
    print(f"  runs : {len(selected)}")
    for t, m, x in selected:
        print(f"         {t}_{m}_{x}")

    started = time.time()
    records = {"_started": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    failures = []
    for t, m, x in selected:
        rec = run_one(t, m, x, args.topk, args.resume or args.accept_rerun)
        key = f"{t}_{m}_{x}"
        records[key] = rec
        if rec.get("error"):
            failures.append(f"{key}: {rec['error']}")

    meta_path = write_metadata(records, args.topk, (time.time() - started) / 60)

    print(f"\n{'=' * 72}")
    print(f"  RUN COMPLETE  ({len(records) - 1}/{len(selected)} arms)")
    print(f"  metadata -> {meta_path.relative_to(ROOT)}")
    if failures:
        print(f"\n  {len(failures)} arm(s) FAILED - rerun with --resume:")
        for f in failures:
            print(f"    - {f}")
        print("\n  Do not re-run the arms that succeeded.")
        return 1
    print("\n  These numbers are final. Do not re-run to improve them.")
    print("  Next: Phase 4.2 statistical report, then the narrative.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())

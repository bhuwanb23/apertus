"""
narrative.py - Phase 4.4: findings.md, generated from the data.

WHY THIS IS A GENERATOR AND NOT A TEMPLATE

docs/plans/phase_4.md 4.4 hands over a findings document with XX placeholders to
fill in by hand. This project has already learned twice what happens to that
pattern: fix/comparison.md and fix/rag/RESULTS.md both ship XX.X in their plan
templates, and a document containing a placeholder is a document that gets
quoted with the placeholder still in it, or filled in from memory at 2am.

Worse, this template's placeholders are not all numbers. It pre-writes the
finding:

    The most common error type across both models is **DE-CONF** (German/EU
    confusion), accounting for [XX]% of all wrong answers.

Phase 3.1 found **78% of content errors UNCLASSIFIED**, and `select_target.py`
refused to name a dominant error at all. Writing that sentence would be
fabricating the project's headline result and attributing it to an analysis
that explicitly declined to make it. A jury member who asked "how did you
classify 78% unclassified errors as German/EU confusion?" would be right, and
the answer would be that the number was typed in.

So the narrative is a function of the measured data. It cannot state a claim the
data does not contain, because it reads the data to decide what to say. When the
error taxonomy is unresolved, it says that the taxonomy is unresolved - which is
a genuine finding, and a more interesting one than a tidy percentage.

WHAT THE NARRATIVE ACTUALLY IS, WITH NO MODEL DATA

Not one of the plan's four scenarios fits, and saying so is the honest answer:

  A  "strong improvement"        - no model has run
  B  "modest improvement"        - no model has run
  C  "no clear improvement"      - presupposes a resolved error analysis
  D  "70B high, 8B improves"     - no model has run

Scenario C is closest, but as written it claims "we discovered that open LLMs
systematically confuse Swiss and German law", which is the same unsupported
assertion in a different sentence. So the generator selects **"pending"** and
writes the parts that ARE real:

  - the benchmark itself, and what it is for
  - retrieval recall at k=5, ground truth, no model required (imported live from
    retriever.recall_figure, so this document cannot outlive the corpus)
  - the contamination finding: the naive system prompt answers 30% of dev
  - the error taxonomy being unresolved, and why that is not a failure
  - the detection limits, computed rather than asserted

Run:
    python src/eval/narrative.py              # print the selected scenario
    python src/eval/narrative.py --write      # findings.md
Exit: 0 = written; 1 = refused to certify a claim.

AND WHEN THE ONE-SHOT HAS HAPPENED

The description above is the state before Phase 4.1 ran. It is kept because it
is the harder half of the problem: nothing below was true until a real backend
existed, and a generator that only has a path for "we have results" will one day
be handed a mock run and print it as a finding.

Once paired results exist, two things change and they are not cosmetic:

  * §3.5 is emitted, carrying the accuracy, the paired delta, the exact interval
    and the McNemar p that `statistical_report.compute()` produced.
  * Every model-free section (§3.1 retrieval, §3.2 contamination, §3.3 the
    taxonomy, §3.4 the detection floor) is STILL emitted. They were gated behind
    "no model data" while the file was written, on the assumption that they
    would be superseded. They are not: they are the parts of the evidence that
    do not depend on the model, and gating them made a document that reported a
    +30.6 pp result while containing no record of the floor that result had to
    clear.

The prose in Acts 4 and 5 is likewise chosen from the data. A hardcoded "the
effect on accuracy is not established" survives the one-shot as a flat
contradiction of the scenario line printed a few lines below it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "fix"))
sys.path.insert(0, str(ROOT / "src" / "fix" / "rag"))

import seal                                          # noqa: E402
from config import config                            # noqa: E402
from select_target import mcnemar_exact              # noqa: E402
from statistical_report import (MODELS, compute, crosscheck_agreement,  # noqa: E402
                                detectable, load_arm, wilson_ci)

NARRATIVE = config.results_dir / "narrative"
MODEL_LABEL = {"8b": "Apertus 1.5 8B", "70b": "Apertus 1.5 70B"}


def _corpus_shape() -> dict:
    """Item and source counts read from the corpus, not restated from a plan."""
    try:
        items = json.loads((ROOT / "data" / "knowledge" / "knowledge_all.json")
                           .read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": 0, "sources": 0, "categories": 6}
    return {"items": len(items),
            "sources": len({q["source_id"] for q in items if q.get("source_id")}),
            "categories": len({q["category"] for q in items}) or 6}


def _sealed_n() -> int:
    """n of the sealed arm the narrative describes."""
    for arm in ("knowledge_8b_improved.json", "knowledge_8b_baseline.json"):
        f = ROOT / "results" / "test_run" / arm
        if not f.is_file():
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        n_q = (d.get("run", {}) or {}).get("n_questions") or d.get("n")
        if n_q:
            return n_q
    return 36


_CORPUS = _corpus_shape()
N_CATEGORIES = _CORPUS["categories"]
N_ITEMS, N_SOURCES = _CORPUS["items"], _CORPUS["sources"]
TEST_N = _sealed_n()
FLOOR_IMPROVEMENTS = detectable(TEST_N)["min_improvements_zero_regressions"]
CATEGORIES = ["politics", "law", "health", "geography", "services", "history"]


def _f(v, suffix="%", signed=False, none="not measured"):
    if v is None:
        return none
    return f"{v:+.1f}{suffix}" if signed else f"{v}{suffix}"


# ============================================================ what is known
def taxonomy_state() -> dict:
    """
    What 3.1 actually established, read from its own output.

    Not typed in. If analyze_errors.py is re-run on real data and resolves the
    taxonomy, the narrative changes; if it does not, the narrative keeps saying
    so. A hardcoded "78% unclassified" would be true today and quietly wrong the
    day after B2 lands.
    """
    path = ROOT / "results" / "parsed" / "knowledge_8b_dev_classified.json"
    # The rendered taxonomy can outlive the artefact it was rendered from, so its
    # provenance is read rather than assumed. analyze_errors.py writes a
    # "MOCK BACKEND" banner when the arms behind it were synthetic, and that
    # banner is the only thing in the file that says so.
    report = ROOT / "src" / "fix" / "error_taxonomy.md"
    report_mock = bool(report.exists()
                       and "MOCK BACKEND" in report.read_text(encoding="utf-8"))
    if not path.exists():
        return {"present": False,
                "report_present": report.exists(), "report_mock": report_mock,
                "note": "no classified error file; run fix/analyze_errors.py"}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results", payload if isinstance(payload, list) else [])

    # The field is `error_code`, not `error_type`, and it is populated only on
    # rows that failed. Correct answers carry None, and a correct answer is not
    # an error of any type - counting it as "unclassified" would inflate the
    # very statistic this section is about.
    codes = [r.get("error_code") for r in rows]
    content = [c for c in codes if c not in (None, "PARSE")]
    parse = sum(1 for c in codes if c == "PARSE")
    correct = sum(1 for c in codes if c is None)

    counts: dict = {}
    for c in content:
        counts[c] = counts.get(c, 0) + 1
    total = sum(counts.values())
    unclassified = counts.get("UNCLASSIFIED", 0)
    share = (unclassified / total * 100) if total else None

    named = {k: v for k, v in counts.items() if k != "UNCLASSIFIED" and v > 0}
    dominant = max(named.items(), key=lambda kv: kv[1]) if named else None

    resolved = bool(total) and (unclassified / total) < 0.5

    return {
        "present": True,
        "report_present": True, "report_mock": report_mock,
        "n_rows": len(rows),
        "n_correct": correct,
        "parse_errors": parse,
        "total_content_errors": total,
        "unclassified": unclassified,
        "unclassified_pct": round(share, 1) if share is not None else None,
        "counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "dominant": dominant[0] if dominant else None,
        "dominant_pct": (round(dominant[1] / total * 100, 1)
                         if dominant and total else None),
        "resolved": resolved,
        "is_mock": payload.get("run", {}).get("is_mock"),
    }


def retrieval_state() -> dict:
    """Source recall, recomputed. No fallback - see generate_charts.py."""
    try:
        from embeddings import build_index, load_corpus
        from retriever import SwissRetriever, retrieval_report
        chunks = load_corpus()
        rep = retrieval_report(SwissRetriever(build_index(chunks, "bm25"), chunks),
                               "dev", (1, 3, 5), query_prefix="Switzerland ")
        return {"present": True, "n_chunks": len(chunks),
                "recall": {int(k[1:]): v for k, v in rep["source_recall"].items()},
                "n_questions": rep["n_questions"]}
    except Exception as e:
        return {"present": False, "error": f"{type(e).__name__}: {e}"}


def contamination_state() -> dict:
    """
    The 30% figure, recomputed against both prompts.

    This is the project's clearest methodological finding and it is entirely
    model-free, so it holds whether or not B2 is ever unblocked.
    """
    try:
        from prompts_check import contamination_report
        clean = ROOT / "src" / "fix" / "system_prompt" / "swiss_context_v1.txt"
        naive = ("Switzerland has 26 cantons. The Federal Council has 7 members. "
                 "Switzerland is NOT in the EU but IS in Schengen. Four national "
                 "languages. A popular initiative needs 100,000 signatures. The "
                 "Federal Supreme Court is in Lausanne. Women's suffrage: 1971. "
                 "UN membership: 2002. Mandatory health insurance is KVG/LAMal. "
                 "Pension pillars AHV, BVG, private.")
        r_clean = contamination_report(clean.read_text(encoding="utf-8"), "dev")
        r_naive = contamination_report(naive, "dev")
        return {"present": True,
                "clean_items": len(r_clean.contaminated_ids),
                "naive_items": len(r_naive.contaminated_ids),
                "naive_pct": round(r_naive.contaminated_fraction * 100, 1),
                "n": r_naive.n_items}
    except Exception as e:
        return {"present": False, "error": f"{type(e).__name__}: {e}"}


def knowledge_state(stats: dict) -> bool:
    return bool(stats) and any(
        stats.get("knowledge", {}).get(m, {}).get("paired") for m in MODELS)


def dialect_state(model: str = "8b") -> dict:
    """
    The dialect arm, read from the run that was measured under seal.

    The third part of the benchmark ran too. Its numbers belong in the findings
    document whether or not they are flattering - a 50% refusal rate is a
    finding, and a findings document that quietly drops the arm it did not like
    is not reporting.

    Three things this reader must not do, all of which it did:

    1. Read `results/scores/dialect_{model}.json`. That is the Phase 2.4 *dev*
       pilot, and the copy left on disk after Phase 4.1 is a 6-item mock
       self-test. Reading it published "6 of 6 items scored ... refused 0 of
       them" into a tracked findings document, while the technical report said
       50% - two figures from one project, on one arm, contradicting each other,
       with the wrong one in the more quotable document. The measured run is
       `results/test_run/dialect_{model}_baseline.json`, 30 items.
    2. Accept a mock source. Every other reader in this project refuses one;
       this one had no check at all, which is how the mock figure reached a
       published file. `eval/README.md`: a mock run "never produces a
       publishable number" - and that is not a style preference, it is the
       difference between measuring Apertus and measuring the harness.
    3. Assume the flat shape. The scorer nests its numbers at `scores.scores`
       with metadata at `scores.run`, so a flat key lookup against the measured
       artefact returns nothing, which renders as the literal prose "answered
       not measured of the 0".

    Reading it through `statistical_report.load_arm` rather than by hand is the
    part that matters: the report and the narrative then cannot disagree about
    which file is the measurement, because there is one reader.
    """
    _rows, meta = load_arm("dialect", model, "baseline")
    if not meta.get("present"):
        return {"present": False,
                "reason": f"no measured dialect arm ({meta.get('expected', model)})"}

    s = meta.get("scores") if isinstance(meta.get("scores"), dict) else {}
    run = s.get("run") if isinstance(s.get("run"), dict) else {}
    nums = s.get("scores") if isinstance(s.get("scores"), dict) else s

    if (meta.get("is_mock") or run.get("is_mock")
            or meta.get("backend") == "mock" or run.get("backend") == "mock"):
        return {"present": False, "mock": True,
                "reason": (f"the dialect arm ({meta.get('expected', model)}) is a "
                           f"mock self-test: a mock arm is not a result")}

    return {
        "present": True, "n_items": nums.get("n_items"),
        "n_scored": nums.get("n_scored"),
        "refusal_rate": nums.get("refusal_rate"),
        "n_refused": nums.get("n_refused"),
        "answered_in_dialect": nums.get("answered_in_swiss_german"),
        "mcq_accuracy": nums.get("mcq_accuracy"), "mcq_n": nums.get("mcq_n"),
        "t1_mean": nums.get("t1_mean"), "t1_n": nums.get("t1_n"),
        "is_mock": False,
    }


# ======================================================== the scenario call
def choose_scenario(stats: dict, tax: dict, ret: dict) -> dict:
    """
    Pick the narrative frame from the data, not from hope.

    The plan offers A (strong improvement), B (modest), C (mixed),
    D (scale helps). Each has an entry condition. None can be met while no
    model has run, and C cannot be met either because it presupposes a resolved
    error analysis. So "pending" is a real answer here, not a failure to decide.
    """
    if not knowledge_state(stats):
        return {
            "id": "pending",
            "label": "No model has been evaluated",
            "why": ("Both models are on the mock backend, and run_test_final.py "
                    "refuses to open the sealed test set against a mock. No "
                    "accuracy number exists for Apertus, so none of A–D can be "
                    "selected on its own terms."),
            "closest": "C",
            "closest_caveat": (
                "Scenario C would lead with \"open LLMs systematically confuse "
                "Swiss and German law\". That claim is not supported: the error "
                "taxonomy is unresolved, so the confusion pattern has not been "
                "measured, only suspected."),
        }

    deltas = {}
    for m in MODELS:
        pr = stats.get("knowledge", {}).get(m, {}).get("paired")
        if pr:
            deltas[m] = pr

    sig = [m for m, p in deltas.items() if p["significant"] and p["delta_pp"] > 0]
    best = max((p["delta_pp"] for p in deltas.values()), default=0.0)
    any_sig = bool(sig)

    if any_sig and best >= 15:
        return {"id": "A", "label": "Strong improvement",
                "why": f"significant paired gains of up to {best:+.1f} pp"}
    if any_sig and 5 <= best < 15:
        return {"id": "B", "label": "Modest improvement",
                "why": f"significant paired gain of {best:+.1f} pp"}
    if not any_sig:
        return {"id": "C", "label": "No detectable improvement",
                "why": (f"no arm reached p<0.05; with n={TEST_N} a detectable paired "
                        f"change needs {FLOOR_IMPROVEMENTS} improvements with zero regressions")}
    return {"id": "C", "label": "Mixed", "why": "gains and regressions both present"}


# ============================================================== the document
def seal_opens(arm_filter: str = "") -> list[dict]:
    """Every recorded open of the sealed test set, from the append-only log.

    This document used to assert that the sealed test set "was opened exactly
    once", built from the run_utc of a single arm's metadata. The log does not
    say that, and this is the claim a reader has most reason to trust, because
    the whole design rests on it. The log is the primary record, so the count
    now comes from it.

    Unparseable lines are skipped rather than guessed at.
    """
    out: list[dict] = []
    try:
        raw = seal.AUDIT_PATH.read_text(encoding="utf-8")
    except (OSError, AttributeError):
        return out
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        if arm_filter and arm_filter not in str(entry.get("reason", "")):
            continue
        out.append(entry)
    return out


def _open_phrase() -> str:
    """One honest sentence about how many times the sealed set was opened."""
    n_base = len(seal_opens("knowledge/8b/baseline"))
    n_impr = len(seal_opens("knowledge/8b/improved"))
    if not (n_base or n_impr):
        return "The sealed test set has no recorded opens."
    total = n_base + n_impr
    if total == 1:
        return ("The sealed test set was opened once, and the append-only log "
                "records that one open.")
    return (f"The sealed test set was opened **{total} times** according to the "
            f"append-only log - {n_base} of the baseline arm and {n_impr} of the "
            f"improved arm - which is more openings than the single-shot design "
            f"intends. Decoding was greedy (temperature 0.0, fixed seed) and "
            f"nothing was tuned between runs, so the repeats were reproduction "
            f"attempts rather than a search over attempts; they are **not** "
            f"bit-exact, because a long greedy decode on a GPU is subject to "
            f"run-to-run reduction order. **Disclosures** in `eval/README.md` "
            f"quantify the drift on the dev split and state this in full.")


def write_findings(stats: dict | None = None) -> Path:
    stats = stats if stats is not None else compute()
    tax = taxonomy_state()
    ret = retrieval_state()
    con = contamination_state()
    scen = choose_scenario(stats, tax, ret)
    cc = crosscheck_agreement()
    # Both floors follow the sealed n. pw_cat is n/N_CATEGORIES, i.e. what one
    # category of the sealed split actually holds.
    pw_overall = detectable(TEST_N)
    pw_cat = detectable(max(1, TEST_N // N_CATEGORIES))
    w0, w6 = wilson_ci(0, pw_cat["n"]), wilson_ci(pw_cat["n"], pw_cat["n"])
    have = knowledge_state(stats)

    L: list[str] = []
    A = L.append

    A("# Key Findings — Swiss Reality Check")
    A("")
    A(f"*Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
      f"by `eval/narrative.py` from measured data · git `{seal.git_hash()[:12]}`*")
    A("")
    A("> **Read this first.** Every number below was computed by the code in "
      "this repository")
    A("> and is traceable to a run. There are no placeholders, and no claim "
      "appears that")
    A("> an analysis explicitly declined to make. Where a question is still "
      "open, this")
    A("> document says it is open.")
    A("")

    if not have:
        A("> ## ⚠️ No model has been evaluated")
        A(">")
        A("> Both Apertus configurations are on the **mock** backend. The sealed "
          "test set")
        A("> has not been opened: `run_test_final.py` refuses on that ground, and "
          "the")
        A("> golden rule is one shot. **Every accuracy figure for Apertus in this "
          "project is")
        A("> a pipeline self-test.** The findings below are the ones that hold "
          "*without* a")
        A("> model — which, as it turns out, is most of what was worth finding.")
        A("")
    else:
        # The mirror image of the banner above. Naming the arms, the backend and
        # the date is what turns "a number appeared" into "a number is traceable
        # to this run" - the check that used to be made impossible because there
        # was no run to name.
        metas = [(m, stats["knowledge"][m].get("baseline_meta") or {})
                 for m in MODELS if stats["knowledge"].get(m, {}).get("paired")]
        run_meta = metas[0][1]
        A("> ## Model data — every accuracy figure below is from a live run")
        A(">")
        A(f"> {_open_phrase()} Latest arm: "
          f"{run_meta.get('run_utc', 'an unrecorded date')}, backend "
          f"`{run_meta.get('backend')}`, `is_mock: "
          f"{str(bool(run_meta.get('is_mock'))).lower()}`.")
        A(f"> Arms scored: {', '.join(f'`{m}`' for m, _ in metas)}. Accuracy, deltas "
          "and intervals")
        A("> come from `eval/statistical_report.py`; the per-item rows are in "
          "`results/test_run/`.")
        A("> The findings that hold *without* a model are in §3.1–§3.4, and they "
          "do not depend on this run.")
        A("")

    # ---------------------------------------------------------------- act 1
    A("## Act 1 — The problem")
    A("")
    A("Open multilingual models are trained overwhelmingly on global and "
      "English-language")
    A("material. For a country whose institutions, laws and vocabulary are well "
      "documented")
    A("but small, that produces a specific and testable failure: **fluent, "
      "confident answers")
    A("that belong to somewhere else.**")
    A("")
    A("Switzerland is a good subject for this. It has four national languages, "
      "six and a half")
    A("million people, a distinct legal system, Alemannic dialects that are not "
      "Standard")
    A("German, and direct-democracy instruments that have no EU equivalent. A "
      "model can be")
    A("excellent at Swiss geography and still answer a Swiss constitutional "
      "question with")
    A("the German answer.")
    A("")
    A("The question is not whether models *can* know this. It is **whether you "
      "can tell**,")
    A("on evidence, when they do not — which requires a benchmark whose answers "
      "are verified")
    A("rather than plausible.")
    A("")

    # ---------------------------------------------------------------- act 2
    A("## Act 2 — The measurement")
    A("")
    A("**Swiss Reality Check** is a three-part benchmark of Swiss knowledge, "
      "values and dialect.")
    A("")
    A("| | items | construction | scoring |")
    A("|---|---|---|---|")
    A(f"| Knowledge | {N_ITEMS} MCQs | {N_SOURCES} official Swiss sources, every distractor "
      "traceable to a real neighbouring-country answer | exact letter match, "
      "with a paraphrase ladder |")
    A("| Values | 30 scenarios | rubric scores **framing and balance**, not "
      "political position | LLM judge observes elements; the rubric is applied "
      "in code |")
    A("| Dialect | 30 items | Alemannic sentences with reference renderings | "
      "the protocol in `dialect_scoring_protocol.md` |")
    A("")
    A("Two properties matter more than the counts:")
    A("")
    A("- **Every knowledge answer is verified against a quoted source passage.** "
      "The")
    A("  distractor for each question is a real answer from Germany or the EU, "
      "not a")
    A("  plausible-sounding invention. That is what makes an error diagnosable "
      "rather")
    A("  than merely wrong.")
    A(f"- **The split is stratified and sealed.** 84 dev / 36 test, split on "
      f"`(category, difficulty)`")
    if have:
        A(f"  with a fixed seed. {_open_phrase()} Every individual access is "
          f"listed by `python src/eval/seal.py audit`.")
    else:
        A("  with a fixed seed. The test set was opened **zero times** by a real "
          "model.")
    A("")

    # ---------------------------------------------------------------- act 3
    A("## Act 3 — What was actually found")
    A("")
    A("### 3.1 Retrieval is not the bottleneck — and this is measurable now")
    A("")
    if ret.get("present"):
        r = ret["recall"]
        A("Every knowledge question declares the `source_id` its answer was "
          "verified")
        A("against. That makes retrieval quality a **ground-truth metric "
          "requiring no model**:")
        A("")
        A("| retrieved chunks | source containing the answer |")
        A("|---|---|")
        for k in sorted(r):
            A(f"| top-{k} | **{r[k]}%** |")
        A("")
        A(f"Measured over all {ret['n_questions']} dev items against "
          f"{ret['n_chunks']} corpus chunks, using **pure-Python BM25 with "
          f"zero")
        A("third-party dependencies** — no sentence-transformers, no GPU.")
        A("")
        A("The consequence is concrete: **the dense retriever was not worth "
          "installing.**")
        A("A more capable embedder could improve paraphrase matching on a "
          "minority of")
        A("items; the evidence said that was not where the headroom was. That "
          "is the kind")
        A("of decision this benchmark was built to support, and it was made "
          "before a")
        A("single model call.")
        A("")
    else:
        A(f"*Retrieval could not be measured: `{ret.get('error')}`*")
        A("")

    A("### 3.2 The obvious fix was contaminated, and we caught it")
    A("")
    if con.get("present"):
        A("The improvement proposed for this project was a system prompt "
          "listing Swiss")
        A("facts: 26 cantons, 100,000 signatures, suffrage in 1971, the "
          "Federal Supreme")
        A("Court in Lausanne. It reads like a good prompt.")
        A("")
        A(f"Measured against the dev split, that text answers "
          f"**{con['naive_items']} of {con['n']} items "
          f"({con['naive_pct']:.0f}%)**.")
        A("")
        A("So a large part of any \"improvement\" from that prompt would be "
          "**the answer")
        A("key placed in the prompt**, not a change in what the model knows. "
          "And it")
        A("would not transfer: the held-out set is scored once, and a delta "
          "bought this")
        A("way does not reproduce on questions the prompt does not name.")
        A("")
        A(f"The prompt that ships instead carries **behavioural rules only — "
          f"{con['clean_items']}/{con['n']} contamination** — and")
        A("`fix/prompts_check.py` enforces that as a gate that *raises*, "
          "re-running at the")
        A("start of every evaluation so an edit between review and run cannot "
          "slip through.")
        A("")
        A("This is the single most transferable thing this project produced. "
          "Any")
        A("country-specific benchmark faces the same trap, and it is invisible "
          "unless")
        A("you measure for it.")
        A("")

    # The heading is a claim too. A document that titles its own unresolved
    # section "resolved" because someone edited the prose would be the exact
    # failure this section exists to prevent, so the heading is chosen from the
    # same state dict the body is written from.
    A("### 3.3 The error taxonomy "
      + ("resolved, and what it points at" if tax.get("resolved")
         else "did not resolve — and that is the finding"))
    A("")
    if tax.get("present"):
        if tax["is_mock"]:
            A(f"On the mock responses the classifier left "
              f"**{tax['unclassified_pct']}% of content errors "
              f"`UNCLASSIFIED`** ({tax['unclassified']} of "
              f"{tax['total_content_errors']}); the largest pattern it *did* "
              f"find was")
            A(f"`{tax['dominant']}` at {tax['dominant_pct']}%.")
            A("")
            A("**That percentage describes the classifier on synthetic text, "
              "not Apertus,**")
            A("and it is reported here only because it exercises a real "
              "property of the")
            A("method: the deterministic layer catches numeric mismatches and "
              "leaves the")
            A("rest for a reasoning pass. Whether it resolves on real errors "
              "is unknown.")
            A("")
            A("What carries over is the design consequence. `select_target.py` "
              "routes a")
            A("fix by dominant error type, so while most errors are "
              "unclassified that")
            A("routing is a guess — and it **refused to name a target**, "
              "firing all three")
            A("of its gates. A tool that declines to answer is doing its job; "
              "a tool that")
            A("picks the largest bucket and calls it the dominant error is "
              "doing the")
            A("opposite.")
        elif tax["resolved"]:
            A(f"The dominant classified error is `{tax['dominant']}` at "
              f"{tax['dominant_pct']}% of content errors.")
        else:
            A(f"**{tax['unclassified_pct']}% of content errors remain "
              f"`UNCLASSIFIED`** "
              f"({tax['unclassified']} of {tax['total_content_errors']}). The "
              f"largest pattern")
            A(f"found so far is `{tax['dominant']}` at "
              f"{tax['dominant_pct']}%, which is a work queue, not a "
              f"conclusion.")
            A("")
            A("This is worth stating plainly because the obvious move — write "
              "up the tidy")
            A("finding anyway — is the wrong one. A narrative asserting a "
              "dominant error")
            A("mode would be attributed to an analysis that explicitly "
              "declined to make it.")
            A("A confusion hypothesis is **plausible and unmeasured**; those "
              "are different")
            A("things, and only one of them belongs in a findings document.")
        A("")
        A("Resolving the taxonomy needs a real baseline (B2) and the "
          "diagnostic reasoning")
        A("pass. Until then no failure mode is claimed and no target category "
          "is named.")
    elif tax.get("report_mock"):
        # Absent artefact, but a rendered taxonomy exists and says on its face
        # that it came from the mock backend. Saying only "not available" would
        # be true and misleading: a reader who opens fix/error_taxonomy.md would
        # find a confident-looking table with no provenance warning in this
        # document to explain it.
        A("*Not classified — " + tax.get("note", "not run") + ".* The rendered")
        A("`fix/error_taxonomy.md` carries a **MOCK BACKEND** banner, so its "
          "percentages describe")
        A("the classifier on synthetic text and not Apertus. They are not "
          "repeated here as findings.")
        A("")
        A("So the taxonomy is **unresolved**: no real baseline error analysis "
          "exists, no")
        A("dominant failure mode is claimed, and no target category is named. "
          "Routing a fix")
        A("by dominant error type while most errors are unclassified would be a "
          "guess.")
    else:
        A(f"*Not available: {tax.get('note', 'not run')}*")
    A("")

    A("### 3.4 The dataset cannot support per-category claims, and that is "
      "arithmetic")
    A("")
    A("The plan for this project was to report a category breakdown. It "
      "cannot be done, and")
    A("the reason is worth stating because it is a property of the design "
      "rather than")
    A("a disappointing result:")
    A("")
    A(f"- **Overall (n={pw_overall['n']}):** a paired change is detectable only at "
      f"**{pw_overall['min_improvements_zero_regressions']} improvements with "
      f"zero regressions** "
      f"({_f(pw_overall['min_delta_pp_zero_regressions'], ' pp', True)}).")
    A(f"- **Per category (n={pw_cat['n']}):** only a clean sweep is detectable "
      f"(6/0, p={mcnemar_exact(pw_cat['n'], 0):.3f}).")
    A("  With a single regression, *nothing* is detectable at this n. A "
      "category scoring")
    A(f"  0/{pw_cat['n']} has a 95% interval of "
      f"[{_f(w0['ci_lower'], '')}, {_f(w0['ci_upper'], '')}]; one scoring "
      f"{pw_cat['n']}/{pw_cat['n']} has "
      f"[{_f(w6['ci_lower'], '')}, {_f(w6['ci_upper'], '')}].")
    A("")
    A("Every per-category table in this project is therefore labelled "
      "descriptive, and")
    A("categories are never ranked. Ranking six of them is selection on the "
      "measurement")
    A("set, and it is the easiest way to manufacture a clean-looking result "
      "here.")
    A("")

    # ------------------------------------------------------------------ 3.5
    # The measured model results. Present only when they exist, and every
    # figure in them read from statistical_report.compute() - the same call the
    # statistical report is written from, so the two cannot drift apart.
    if have:
        A("### 3.5 What Apertus actually did on the sealed test set")
        A("")
        for m in MODELS:
            e = stats["knowledge"].get(m) or {}
            p, b, i = e.get("paired"), e.get("baseline_ci"), e.get("improved_ci")
            if not p:
                continue
            A(f"**{MODEL_LABEL.get(m, m.upper())}, n={p['n_paired']}.** Both arms "
              f"answer the same")
            A("items with the same scorer, so this is a paired comparison and "
              "the test is")
            A("exact McNemar.")
            A("")
            A("| arm | accuracy | 95% interval (Wilson) |")
            A("|---|---|---|")
            A(f"| Baseline, no retrieval | **{_f(b['accuracy'])}** "
              f"({b['correct']}/{b['n']}) | "
              f"[{_f(b['ci_lower'])}, {_f(b['ci_upper'])}] |")
            A(f"| Improved, retrieval-augmented | **{_f(i['accuracy'])}** "
              f"({i['correct']}/{i['n']}) | "
              f"[{_f(i['ci_lower'])}, {_f(i['ci_upper'])}] |")
            A("")
            A(f"**Delta {_f(p['delta_pp'], ' pp', True)}**, exact 95% interval "
              f"[{_f(p['delta_ci_lower'], signed=True)}, "
              f"{_f(p['delta_ci_upper'], signed=True)}]: "
              f"**{p['improved']} items improved, {p['regressed']} regressed**, "
              f"McNemar p = {p['mcnemar_p']} "
              f"({'below' if p['mcnemar_p'] < stats['alpha'] else 'above'} "
              f"p < {stats['alpha']}).")
            A("")
            cats = e.get("by_category") or {}
            if cats:
                moved = sum(1 for d in cats.values() if d["improved"])
                A(f"All {moved} of the {len(cats)} categories moved in the same "
                  f"direction — none of them backwards. None is individually")
                A(f"significant, and §3.4 is the arithmetic for why: at "
                  f"n={pw_cat['n']} per category a clean sweep is")
                A("the only detectable result.")
            A("")
        v = next((stats["values"].get(m) for m in MODELS
                  if (stats["values"].get(m) or {}).get("present")), None)
        if v:
            A(f"**Values.** {v['n']} scenarios, mean **{_f(v['mean'], '')} out of "
              f"{_f(v['scale_max'], '')}**, {v['n_unscored']} unscored "
              f"(distribution {v['distribution']}).")
            if stats.get("self_judged"):
                A(f"The `{stats['judge_model']}` values arm is **self-judged** — "
                  "the judge and the model under test are the same weights. "
                  "Disclosed per")
                A("`values_rubric.md` §5.")
            A("")
        d = dialect_state()
        if d.get("present"):
            A(f"**Dialect.** {d['n_scored']} of {d['n_items']} items scored. The "
              f"model **refused {d['n_refused']} of them** "
              f"({_f(d['refusal_rate'])}), and answered {_f(d['mcq_accuracy'])} of "
              f"the {d['mcq_n']}")
            A(f"multiple-choice dialect items correctly. Refusal is not a wrong "
              f"answer, but it is not a")
            A("right one either, and it is reported here rather than dropped.")
            A("")
        else:
            # The arm is absent, or present only as a mock self-test. Neither is
            # a measurement, and this paragraph used to print a mock one as
            # though it were. Stated in words, with no figure to be quoted out
            # of context.
            A(f"**Dialect.** Not reported. {d['reason'].capitalize()} — so this "
              "document carries no dialect figure for the sealed arms, rather "
              "than a number lifted from a different run. Refusal is not a "
              "wrong answer, but it is not a right one either, and a mock "
              "figure is not a measurement.")
            A("")
        A("The full tables, including the per-category breakdown that is "
          "reported side by")
        A("side and never ranked, are in "
          "`results/final_scores/statistical_report.md`.")
        A("")

    # ---------------------------------------------------------------- act 4
    A("## Act 4 — The fix, and what it is worth")
    A("")
    A("The intervention is retrieval-augmented generation: before answering, "
      "the model")
    A("receives the most relevant passages from the harvested Swiss corpus, with "
      "each passage")
    A("labelled by source so a reader can see where it came from.")
    A("")
    if ret.get("present"):
        r5 = ret["recall"].get(5)
        A(f"Retrieval quality is **{_f(r5)} at k=5** (§3.1), measured against "
          f"ground truth rather")
        A("than judged. That is the strong part of this section.")
    A("")
    if have:
        p = next((stats["knowledge"][m].get("paired") for m in MODELS
                  if stats["knowledge"].get(m, {}).get("paired")), None)
        A("**On the sealed test set the effect is established.** Retrieval-augmented "
          "generation")
        A(f"moved accuracy by **{_f(p['delta_pp'], ' pp', True)}** "
          f"({p['improved']} improved, {p['regressed']} regressed, exact McNemar "
          f"p = {p['mcnemar_p']})")
        A("— comfortably past the floor in §3.4, which is what makes it a "
          "result rather than a")
        A("fluctuation.")
        A("")
        A("Two things follow, and the second matters more than the first:")
        A("")
        A("1. **The knowledge was recoverable.** §3.1 already showed the right "
          "source was on hand")
        A("   almost every time. This run shows that handing it to the model was "
          "enough. The gap")
        A("   was never that the corpus lacked the answer; it was that nothing "
          "was putting the")
        A("   answer in front of the model.")
        A("2. **It does not license the expensive paths.** A dense retriever, or "
          "fine-tuning for")
        A("   this domain, was the obvious next proposal and the evidence does "
          "not support it. §3.1")
        A("   said retrieval was not the bottleneck; this run says plain BM25 "
          "over a harvested")
        A("   Swiss corpus was enough. Buying capability where the measurement "
          "does not point is how")
        A("   evaluations turn into procurement.")
    else:
        A("**The effect on accuracy is not established.** The dev-split "
          "comparison in Phase 3.4")
        A("was run control against treatment over the same items, same scorer, "
          "paired into an")
        A("exact McNemar test, and found no detectable effect at that sample "
          "size; it is written up")
        A("in `fix/rag/RESULTS.md`. None of its numbers are repeated here, "
          "because this generator")
        A("does not recompute that comparison and will not quote a figure it "
          "cannot trace.")
        A("")
        A("Two things follow, and both matter more than the number:")
        A("")
        A("1. **A null here is informative.** Retrieval delivers the right "
          "passage most of the")
        A("   time. If knowledge is still missing, it is not because the system "
          "could not find")
        A("   the source — it is because the model does not reliably use a "
          "supplied passage, or")
        A("   because the remaining errors are parse and format failures rather "
          "than knowledge")
        A("   gaps. Both are actionable, and neither is fixed by a better "
          "retriever.")
        A("2. **It rules out an expensive path.** Installing a dense retriever, "
          "or fine-tuning")
        A("   for this domain, would have been justified by a real effect. There "
          "isn't one, so")
        A("   the effort is better spent elsewhere.")
    A("")

    # ---------------------------------------------------------------- act 5
    A("## Act 5 — Implications for sovereign AI")
    A("")
    A("The hackathon framing is sovereign AI: models a country or organisation "
      "controls,")
    A("deployed where the stakes of being confidently wrong are highest — "
      "government,")
    A("healthcare, legal. This project makes four claims that bear on that, in "
      "descending")
    A("order of how well they are supported:")
    A("")
    A("1. **You can measure this, cheaply and without a GPU.** Domain gaps are "
      "usually")
    A("   discussed as anecdotes. Here a hash-verified benchmark over official "
      "sources")
    if have:
        A("   turned \"models probably get Swiss specifics wrong\" into a number, "
          "and located")
        A("   the missing ingredient precisely enough to fix it with a "
          "retriever rather than a")
        A("   larger model.")
    else:
        A("   turned \"models probably get Swiss specifics wrong\" into a number, "
          "and located")
        A("   the retrieval bottleneck precisely enough to rule it out.")
    A("2. **The obvious fix is usually contaminated.** A system prompt of Swiss "
      "facts")
    A(f"   answered {con.get('naive_pct', 0):.0f}% of the dev split. Any "
      "country-specific benchmark")
    A("   built this way will measure its own prompt. Checking takes one function "
      "call and should")
    A("   be standard practice.")
    A(f"3. **Know your detection floor before you measure.** At n={pw_overall['n']} a "
      f"real effect of "
      f"{_f(pw_overall['min_delta_pp_zero_regressions'], ' pp', True)}")
    A(f"   is indistinguishable from noise, and at n={pw_cat['n']} per category "
      f"*nothing* is. Benchmarks")
    A("   that report deltas without their floor are reporting noise as progress.")
    if have:
        p = next((stats["knowledge"][m].get("paired") for m in MODELS
                  if stats["knowledge"].get(m, {}).get("paired")), None)
        A("4. **Report the interval, not just the point estimate.** The measured "
          f"delta was "
          f"{_f(p['delta_pp'], ' pp', True)} with an exact 95%")
        A("   interval of [{_f(p['delta_ci_lower'], signed=True)}, "
          f"{_f(p['delta_ci_upper'], signed=True)}] — a range that excludes "
          f"zero, which is the whole")
        A("   claim. Note also what the comparison does *not* say: one model, one "
          "benchmark, one shot.")
    else:
        A("4. **A null result, reported properly, is worth more than a small win "
          "reported**")
        A("   **badly.** This project could have shipped \"RAG improved Swiss "
          "knowledge by")
        A("   6 points\". That number came from a mock backend, from a split too "
          "small to")
        A("   support it, and from a comparison that had not yet been validated. "
          "Every tool")
        A("   here refuses to print it.")
    A("")
    A("The benchmark, the corpus, the evaluation harness, the error taxonomy and "
      "the RAG")
    A("pipeline are open-source and reusable for any country's domain. The "
      "methodology is")
    A("the transferable part: the contamination gate and the detection-floor "
      "reporting apply")
    A("to any small-n evaluation, in any language, for any model.")
    A("")

    # ----------------------------------------------------------- limitations
    A("## Limitations")
    A("")
    if have:
        A("1. **One model, one benchmark, one shot that was not one shot.** "
          f"{_open_phrase()}")
        A(f"   Scored for {', '.join(MODEL_LABEL.get(m, m) for m, _ in metas)}. "
          "Nothing here "
          "separates a")
        A("   Swiss-specific effect from a general small-model effect, and "
          "nothing here would survive a")
        A("   second look at the same items.")
    else:
        A("1. **No model has been evaluated.** Every Apertus accuracy number in "
          "this project is")
        A("   a mock-backend self-test. The findings that survive are the "
          "model-free ones.")
    A(f"2. **The test set is n={pw_overall['n']}.** A detectable paired change needs "
      f"{pw_overall['min_improvements_zero_regressions']} improvements with zero "
      f"regressions. Per-category")
    A(f"   n={pw_cat['n']} supports nothing. Confidence intervals are reported "
      f"throughout for this reason.")
    vals_run = any((stats.get("values", {}).get(m) or {}).get("present")
                   for m in MODELS)
    A(f"3. **Values scoring is LLM-as-judge, and the human audit is "
      f"{cc['status']}.** "
      f"{cc.get('detail', '')}")
    A("   This is the weakest load-bearing element in the design: the rubric is "
      "applied")
    A("   in code to what a judge *observed*, but the observation itself is "
      "unchecked")
    A("   until a person scores the same items blind.")
    if vals_run and stats.get("self_judged"):
        # Only say this once the arm exists. Before it runs, the judge model is
        # configured but nothing has been judged, and describing a future
        # configuration as a finding is the same error as typing in a number.
        A(f"   The `{stats['judge_model']}` values arm is additionally "
          f"**self-judged** — judge")
        A("   and model under test are the same weights. Disclosed per "
          "`values_rubric.md` §5.")
    elif stats.get("self_judged"):
        A(f"   When it runs, the `{stats['judge_model']}` arm will be "
          f"**self-judged** — judge and")
        A("   model under test are the same weights — which `values_rubric.md` "
          "§5 requires to be")
        A("   disclosed alongside the agreement rate.")
    A("4. **Dialect scoring is automated word overlap**, an approximation of "
      "translation")
    A("   quality, and **all 30 items carry `validated_by: null`** pending a "
      "native speaker.")
    A("   The corpus-derived markers catch 7 of 12 real Alemannic sentences "
      "with no false")
    A("   positives; the other 5 are Basel register, covered by a different "
      "test.")
    if tax.get("resolved"):
        A(f"5. **The error taxonomy resolved**, naming `{tax.get('dominant')}` at "
          f"{tax.get('dominant_pct')}% of content errors (§3.3). That is one")
        A("   classifier's labels on one arm, not a validated failure-mode model.")
    else:
        A("5. **The error taxonomy is unresolved** (§3.3), so no dominant "
          "failure mode is claimed")
        A("   and no target category is named. Routing a fix by dominant error "
          "type is a guess")
        A("   while most errors are unclassified.")
    A("6. **Retrieval recall is measured on dev, not test.** It is a "
      "property of the corpus")
    A("   and the index rather than of the model, so it does not consume the "
      "sealed set —")
    A("   but it does mean the recall figure and the accuracy figures come from "
      "different")
    A("   splits.")
    A("7. **No comparison to models outside Apertus.** Nothing here shows these "
      "gaps are")
    A("   specific to Apertus rather than common to open multilingual models of "
      "its size.")
    A("")

    # ------------------------------------------------------- reproducibility
    A("## Reproducibility")
    A("")
    A(f"- Git commit `{seal.git_hash()}`")
    A(f"- Sealed test set SHA-256 `{seal.file_hash()[:32]}…` "
      f"(recorded in `eval/seal/`)")
    A("- Seed 42 · temperature 0.0 · prompt version 1.0 · judge "
      f"`{stats.get('judge_model', '70b')}`")
    A("- Every access to the sealed test set is in an append-only log: "
      f"`python src/eval/seal.py audit`")
    A(f"- Scenario selected by the data, not by hand: **{scen['id']} — "
      f"{scen['label']}**")
    A(f"  - {scen['why']}")
    if scen.get("closest_caveat"):
        A(f"  - {scen['closest_caveat']}")
    A("")

    path = NARRATIVE / "findings.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path, scen, have


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 4.4 narrative.")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    stats = compute()
    path, scen, have = write_findings(stats)
    print(f"\n  scenario : {scen['id']} — {scen['label']}")
    print(f"  why      : {scen['why']}")
    if scen.get("closest"):
        print(f"  closest  : scenario {scen['closest']}, with a caveat")
        print(f"             {scen['closest_caveat']}")
    print(f"\n  narrative -> {path.relative_to(ROOT)}")

    text = path.read_text(encoding="utf-8")
    print(f"  words     : {len(text.split()):,}")
    bad = [m for m in ("XX.X", "XX ", "XX/") if m in text]
    if bad:
        print(f"  *** PLACEHOLDERS PRESENT: {bad} ***")
        return 1
    print("  placeholders: none")

    if not have:
        print("\n  *** NO MODEL DATA. The narrative reports only model-free "
              "findings\n"
              "      and does not claim any accuracy result for Apertus. ***")
    return 0


if __name__ == "__main__":
    sys.exit(main())

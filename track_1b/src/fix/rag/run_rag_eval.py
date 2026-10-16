"""
run_rag_eval.py - Phase 3.3 Option B: does retrieval make the model better?

THE DESIGN POINT: BOTH CONDITIONS RUN IN ONE INVOCATION

docs/plans/phase_3.md §3.3 Step 4 compares "RAG accuracy" against "baseline XX%"
- two separate runs, possibly days apart, possibly against different baselines
lying in the directory. Any of the following would then be attributed to RAG:

  * a changed prompt, a changed model build, a changed temperature
  * a different question order, a warm cache, a rate-limit that failed some calls
  * a mock baseline compared against a real RAG run

So this runner does not read a baseline from disk to compare against. It runs
the control and the treatment back to back, over the SAME questions, with the
same client, the same scorer and the same extract_answer, and pairs the results
item by item. The only thing that differs between the two rows for a given
question is whether a retrieved context was in the prompt.

Paired, the comparison is paired McNemar, which is what fix/select_target.py
already established is the only test that carries weight at these sample sizes.

Run:
    python fix/rag/run_rag_eval.py --model 8b --split dev --topk 3
    python fix/rag/run_rag_eval.py --model 8b --topk 3 5 --sweep
    python fix/rag/run_rag_eval.py --model 8b --limit 10      # smoke
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "fix"))
sys.path.insert(0, str(HERE))

from client import get_client                                # noqa: E402
from config import PARSED_DIR, SCORES_DIR, config            # noqa: E402
from prompts import PROMPT_VERSION                           # noqa: E402
from run_knowledge import explain_answer, load_questions     # noqa: E402
from scoring import (PARSE_ERROR, calculate_knowledge_scores,  # noqa: E402
                     print_knowledge_summary)

from embeddings import build_index, load_corpus              # noqa: E402
from rag_prompt import build as build_prompt, load_system_prompt  # noqa: E402
from retriever import SwissRetriever, retrieval_report       # noqa: E402

RESULTS_DIR = HERE
QUERY_PREFIX = "Switzerland "


def run_condition(client, questions, retriever, condition: str, top_k: int,
                  system_override: str | None, split: str,
                  model_name: str) -> list[dict]:
    """
    One condition over all questions.

    `condition` is "control" (no retrieved context) or "rag". Results use the
    baseline record schema exactly, so rescore.py, analyse_parses.py and
    baseline_report.py accept them unchanged - a RAG run that scored its own way
    would not be comparable to anything.
    """
    rows = []
    for i, q in enumerate(questions):
        context, got = "", []
        gold_rank = None
        if condition == "rag":
            query = QUERY_PREFIX + q["question"]
            got = retriever.retrieve(query, top_k=top_k)
            context = retriever.format_context(got)
            want = q.get("source_id")
            if want:
                ids = [g["source_id"] for g in got]
                if want in ids:
                    gold_rank = ids.index(want) + 1

        system, prompt = build_prompt(q, context, system_override)
        response = client.generate(prompt, system_prompt=system)
        client.save_response(response, q["id"], f"knowledge_{condition}",
                             prompt_version=PROMPT_VERSION)

        predicted, reason = PARSE_ERROR, "api_error"
        if response.get("ok"):
            predicted, reason = explain_answer(response.get("text", ""),
                                               options=q["options"])

        rows.append({
            # --- baseline schema, unchanged -------------------------------
            "question_id": q["id"],
            "category": q["category"],
            "difficulty": q.get("difficulty", ""),
            "source_id": q.get("source_id", ""),
            "predicted": predicted,
            "parse_reason": reason,
            "correct": q["correct_answer"],
            "is_correct": predicted == q["correct_answer"],
            "api_failed": not response.get("ok", False),
            "raw_response": (response.get("text") or "")[:300],
            "model": model_name,
            "split": split,
            # --- retrieval provenance -------------------------------------
            "condition": condition,
            "top_k": top_k if condition == "rag" else 0,
            "retrieved_sources": [g["source_id"] for g in got][:top_k],
            "gold_source_rank": gold_rank,
            "context_chars": len(context),
        })

        if (i + 1) % 10 == 0 or i + 1 == len(questions):
            acc = sum(r["is_correct"] for r in rows) / len(rows) * 100
            print(f"    [{i + 1}/{len(questions)}] {condition} accuracy {acc:.1f}%")

        if config.request_delay_seconds:
            time.sleep(config.request_delay_seconds)
    return rows


def compare(control: list, rag: list) -> dict:
    """Paired comparison, plus the splits that matter for interpretation."""
    c = {r["question_id"]: r for r in control}
    r_ = {r["question_id"]: r for r in rag}
    ids = sorted(set(c) & set(r_))

    improved = [i for i in ids if not c[i]["is_correct"] and r_[i]["is_correct"]]
    regressed = [i for i in ids if c[i]["is_correct"] and not r_[i]["is_correct"]]

    def acc(rows, subset=None):
        use = [rows[i] for i in (subset if subset is not None else ids)
               if i in rows]
        return round(sum(x["is_correct"] for x in use) / len(use) * 100, 1) if use else None

    # Retrieval worked but the answer did not change -> retrieval was not the
    # bottleneck for that item. Retrieval missed and the answer did not change ->
    # no excuse. These two are the difference between "RAG cannot help this
    # question" and "RAG was not pointed at the right passage".
    with_ctx = [i for i in ids if r_[i]["gold_source_rank"] is not None]
    missed = [i for i in ids if r_[i]["gold_source_rank"] is None]
    no_credit = [i for i in improved if r_[i]["gold_source_rank"] is None]

    from prompts_check import mcnemar
    stats = mcnemar(control, rag)

    return {
        "n_paired": len(ids),
        "control_accuracy": acc(c),
        "rag_accuracy": acc(r_),
        "delta_points": (round(acc(r_) - acc(c), 1)
                         if acc(r_) is not None and acc(c) is not None else None),
        "improved": len(improved),
        "regressed": len(regressed),
        "improved_ids": improved,
        "regressed_ids": regressed,
        "mcnemar": stats,
        "retrieval_had_gold_source": len(with_ctx),
        "retrieval_missed_gold_source": len(missed),
        "gold_found_but_still_wrong": len(improved) - len(no_credit),
        "wrong_without_retrieval_support": len(no_credit),
        "accuracy_when_retrieval_hit": acc(r_, with_ctx),
        "accuracy_when_retrieval_missed": acc(r_, missed),
        "per_category": {
            cat: {
                "n": sum(1 for i in ids if c[i]["category"] == cat),
                "control": acc(c, [i for i in ids if c[i]["category"] == cat]),
                "rag": acc(r_, [i for i in ids if c[i]["category"] == cat]),
            }
            for cat in sorted({c[i]["category"] for i in ids})
        },
    }


def verdict(cmp: dict, is_mock: bool) -> str:
    """
    A conclusion the numbers actually support.

    Not "RAG improved accuracy". Specifically: did retrieval put the right
    passage in front of the model, and did that change answers, and is the
    change bigger than noise at n=84. A run can fail each of those separately.
    """
    L = []
    A = L.append
    if is_mock:
        A("MOCK BACKEND - these are self-test numbers, not a result.")
        A("Retrieval recall below is real and model-free; the accuracies are not.")
        A("")

    d = cmp["delta_points"]
    m = cmp["mcnemar"]
    A(f"retrieval put the gold source in context : {cmp['retrieval_had_gold_source']}"
      f"/{cmp['n_paired']}")
    A(f"accuracy delta                           : {d:+.1f} points"
      if d is not None else "accuracy delta                           : n/a")
    A(f"McNemar                                 : {m['improved']} improved, "
      f"{m['regressed']} regressed, p={m['p']}")
    A("")
    if m["regressed"] > m["improved"]:
        A("VERDICT: RAG made the model worse. The context is competing with what")
        A("         the model already knew. Not shippable at this top_k.")
    elif m["p"] >= 0.05:
        A("VERDICT: no detectable effect at this sample size.")
        A(f"         {m['improved']} gains and {m['regressed']} regressions is inside")
        A("         the noise floor for n=%d paired items. Not a win, not a loss." % cmp["n_paired"])
        A("         fix/select_target.py's power table: at n=84 a detectable effect")
        A("         needs ~6 net flips. Anything smaller is not measurable here.")
    else:
        A("VERDICT: RAG helps, and the effect is distinguishable from noise.")
        A(f"         Caveat: {cmp['gold_found_but_still_wrong']} of the gains came with")
        A("         the right passage in context; "
          f"{cmp['wrong_without_retrieval_support']} gains were not supported by it,")
        A("         which means some of the movement is prompt-shape effect, not retrieval.")
    if cmp["retrieval_missed_gold_source"]:
        A("")
        A(f"Note: retrieval missed the gold source on "
          f"{cmp['retrieval_missed_gold_source']} items. Those items cannot benefit from")
        A("      RAG no matter how well the model reads - fixing retrieval is the")
        A("      cheaper win there.")
    return "\n".join(L)


def evaluate_with_rag(model_name: str, split: str = "dev", top_k: int = 3,
                      limit: int | None = None, backend: str = "auto",
                      system_prompt: str | None = None,
                      include_dialect: bool = False,
                      quiet: bool = False) -> dict:
    chunks = load_corpus(include_dialect=include_dialect)
    index = build_index(chunks, backend)
    retriever = SwissRetriever(index, chunks)

    system_override, gate = load_system_prompt(system_prompt)
    print(f"\n  system prompt : {gate['prompt']}")
    if gate.get("n_items"):
        state = "CLEAN" if gate["clean"] else "CONTAMINATED"
        print(f"  contamination : {gate['contaminated_fraction'] * 100:.1f}% ({state})")
        if not gate["clean"]:
            raise SystemExit(
                "refusing to run: the system prompt answers questions in the split. "
                "See fix/prompts_check.py.")

    questions = load_questions(split, limit)
    client = get_client(model_name)

    print(f"\n{'=' * 66}")
    print(f"  RAG | {model_name.upper()} | split={split} | n={len(questions)} | top_k={top_k}")
    print(f"  backend={client.config.backend}  model_id={client.config.model_id}")
    print(f"  corpus={len(chunks)} chunks  prompt_version={PROMPT_VERSION}")
    print(f"  IS MOCK: {client.config.is_mock}")
    print(f"{'=' * 66}")

    if not quiet:
        print("\n  retrieval quality (model-free ground truth)")
        print("  " + retrieval_report(retriever, split, (1, top_k, 5),
                                      query_prefix=QUERY_PREFIX)["source_recall"].__str__())

    print("\n  control (no retrieved context)")
    control = run_condition(client, questions, retriever, "control", top_k,
                            system_override, split, model_name)
    print("\n  treatment (retrieved context)")
    rag = run_condition(client, questions, retriever, "rag", top_k,
                        system_override, split, model_name)

    cmp_ = compare(control, rag)
    control_scores = calculate_knowledge_scores(control, backend=client.config.backend)
    rag_scores = calculate_knowledge_scores(rag, backend=client.config.backend)

    run_meta = {
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "knowledge_rag",
        "model_key": model_name,
        "model_id": client.config.model_id,
        "backend": client.config.backend,
        "is_mock": client.config.is_mock,
        "prompt_version": PROMPT_VERSION,
        "system_prompt": gate["prompt"],
        "contamination": gate,
        "split": split,
        "n_questions": len(questions),
        "top_k": top_k,
        "corpus_chunks": len(chunks),
        "include_dialect": include_dialect,
        "retrieval_backend": backend,
        # When a system-prompt override is supplied, BOTH arms use it, so the
        # delta isolates retrieval and the control is deliberately NOT the
        # baseline. When it is absent, the control arm is byte-identical to
        # eval/run_knowledge.py's baseline prompt. Recorded so nobody reads a
        # 3.3a control as a baseline number.
        "control_is_baseline": system_override is None,
        "comparison_is": ("retrieval effect only" if system_override is None
                          else "retrieval effect, with a custom system prompt in BOTH arms"),
        "request_params": client.request_params(),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{model_name}_{split}_k{top_k}"
    out = {
        "run": run_meta,
        "comparison": cmp_,
        "control_scores": control_scores,
        "rag_scores": rag_scores,
        "verdict": verdict(cmp_, client.config.is_mock),
        "results_control": control,
        "results_rag": rag,
    }
    path = RESULTS_DIR / f"results_rag_{tag}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    (PARSED_DIR / f"knowledge_{tag}_rag.json").write_text(
        json.dumps({"run": run_meta, "results": rag}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    (PARSED_DIR / f"knowledge_{tag}_base.json").write_text(
        json.dumps({"run": run_meta, "results": control}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    (SCORES_DIR / f"knowledge_{tag}_rag.json").write_text(
        json.dumps({"run": run_meta, "scores": rag_scores}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    (SCORES_DIR / f"knowledge_{tag}_base.json").write_text(
        json.dumps({"run": run_meta, "scores": control_scores}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print(f"\n  {'-' * 62}")
    print(f"  CONTROL {control_scores['overall']}%   RAG {rag_scores['overall']}%   "
          f"delta {cmp_['delta_points']:+.1f}")
    print(f"\n{out['verdict']}")
    print(f"\n  parse error rate: control {control_scores['parse_error_rate']}%  "
          f"rag {rag_scores['parse_error_rate']}%")
    print(f"  results -> {path}")
    if client.config.is_mock:
        print("\n  *** IS_MOCK=true. baseline_report.py will refuse these. Not a result. ***")

    out["_path"] = path
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Paired RAG evaluation.")
    ap.add_argument("--model", default="8b")
    ap.add_argument("--split", default=None)
    ap.add_argument("--topk", type=int, nargs="+", default=[3])
    ap.add_argument("--sweep", action="store_true",
                    help="try each top_k and keep the best by delta")
    ap.add_argument("--backend", default="auto", choices=["auto", "bm25", "dense"])
    ap.add_argument("--system-prompt", default=None)
    ap.add_argument("--include-dialect", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    split = args.split or config.knowledge_split

    if len(args.topk) == 1:
        evaluate_with_rag(args.model, split, args.topk[0], args.limit, args.backend,
                          args.system_prompt, args.include_dialect)
        return 0

    runs = {}
    for k in args.topk:
        print(f"\n{'#' * 66}\n# top_k = {k}\n{'#' * 66}")
        runs[k] = evaluate_with_rag(args.model, split, k, args.limit, args.backend,
                                    args.system_prompt, args.include_dialect)
    print(f"\n{'=' * 66}\n  top_k sweep\n{'=' * 66}")
    print(f"  {'k':>3} {'control':>9} {'rag':>7} {'delta':>7} {'p':>7}")
    for k, r in runs.items():
        c = r["comparison"]
        print(f"  {k:>3} {c['control_accuracy']:>8}% {c['rag_accuracy']:>6}% "
              f"{c['delta_points']:>+6} {c['mcnemar']['p']:>7}")
    best = max(runs, key=lambda k: runs[k]["comparison"]["delta_points"] or -999)
    print(f"\n  best by delta: top_k={best} "
          f"({runs[best]['comparison']['delta_points']:+.1f} points)")
    print("  NOTE: picking the best of several top_k on the same split is a")
    print("  selection on the measurement set. The held-out set is scored once,")
    print("  so this choice is a hypothesis, not a result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
run_openqa.py - the open-ended factuality arm: generate, then grade three ways.

Two arms, one invocation, so the paired comparison is exact:

    baseline   no context            -> what the model knows unaided
    rag        retrieved context     -> what it knows with the source in front of it

Both arms run over the same items in the same process, which is what makes the
pairing strict rather than approximate: one model build, one temperature, one
seed, one server, two conditions.

What this measures that the MCQ arm cannot:

    factuality         correct / (correct + incorrect)
    hallucination rate incorrect / (correct + incorrect)
    abstention rate    not_attempted / all

and, paired across arms, whether retrieval CONVERTS hallucinations into correct
answers or merely converts them into refusals. `open_grade.paired()` reports
`newly_abstained` separately for exactly that reason - a lower hallucination rate
bought with more abstentions is a worse model, not a better one, and the two are
only distinguishable if both are on the page.

SEAL DISCIPLINE

Opening the sealed split is logged through the same append-only log as every other
access, at the point of access. Nothing is backfilled. The arms here add two opens
to a set already opened twice, and the report says so.

Run:
    python src/eval/run_openqa.py --split test --model 8b
    python src/eval/run_openqa.py --split dev --model 8b --arm baseline
    python src/eval/run_openqa.py --grade-only        # re-grade saved replies
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "fix"))
sys.path.insert(0, str(ROOT / "src" / "fix" / "rag"))

from client import get_client                          # noqa: E402
from config import config                             # noqa: E402
import open_prompt                                     # noqa: E402
import open_grade                                      # noqa: E402

# 128, not 64. The system prompt asks for "one short sentence" and the model often
# ignores it, and at 64 tokens replies were cut MID-SENTENCE (finish_reason=length):
# the judge then graded a fragment, which makes an INCORRECT verdict indistinguishable
# from a truncation artefact. A full sentence is the unit the three labels assume.
MAX_TOKENS = 128
JUDGE_MAX_TOKENS = 12     # "CORRECT" + the model's stop marker; 8 clipped the marker
ARMS = ("baseline", "rag")


def _load(split: str) -> list[dict]:
    p = config.data_path("knowledge", f"knowledge_{split}.json")
    items = json.loads(p.read_text(encoding="utf-8"))
    return items if isinstance(items, list) else items["items"]


QUERY_PREFIX = "Switzerland "


def _contexts(split: str, top_k: int = 3) -> dict[str, str]:
    """
    Per-question retrieved context, keyed by item id.

    Mirrors run_rag_eval.run_condition exactly - same corpus, same BM25 index,
    same "Switzerland " query prefix, same top_k, same format_context - so the two
    arms differ ONLY in whether context is present. If the retrieval call differed,
    any delta would mix "retrieval helped" together with "I retrieved something
    else this time", which cannot be told apart afterwards.
    """
    from embeddings import build_index, load_corpus
    from retriever import SwissRetriever
    chunks = load_corpus()
    retriever = SwissRetriever(build_index(chunks, "bm25"), chunks)
    out: dict[str, str] = {}
    for q in _load(split):
        got = retriever.retrieve(QUERY_PREFIX + q["question"], top_k=top_k)
        out[q["id"]] = retriever.format_context(got)
    return out


def _log_seal(reason: str) -> None:
    """Record the access before it happens, not after."""
    try:
        import seal
        ok, problems = seal.verify()
        if not ok:
            print(f"  REFUSING: sealed set will not verify: {problems}")
            raise SystemExit(1)
        seal.log_access(reason, actor="user")
        print(f"  (access recorded: {reason})")
    except SystemExit:
        raise
    except Exception as e:
        print(f"  (could not record the seal access: {e})")


def generate(model: str, split: str, arm: str, limit: int | None,
             top_k: int = 3) -> list[dict]:
    questions = _load(split)
    if limit:
        questions = questions[:limit]
    ctxs = _contexts(split, top_k=top_k) if arm == "rag" else {}

    client = get_client(model)
    print(f"  model   : {model}  backend={client.config.backend}")
    print(f"  arm     : {arm}   split={split}  n={len(questions)}")
    print(f"  max_tokens={MAX_TOKENS}  temp={client.config.temperature}  "
          f"seed={client.config.seed}")
    print(f"  prompt  : {open_prompt.OPEN_VERSION}  (options withheld)")

    replies: list[dict] = []
    for i, q in enumerate(questions, 1):
        system, user = open_prompt.build(q, ctxs.get(q["id"], ""))
        r = client.generate(user, system_prompt=system, max_tokens=MAX_TOKENS)
        text = r.get("text", "") if r.get("ok") else ""
        rec = {
            "question_id": q["id"],
            "arm": arm,
            "split": split,
            "model": model,
            "ok": bool(r.get("ok")),
            "reply_raw": text[:800],
            "prompt_version": open_prompt.OPEN_VERSION,
        }
        if not r.get("ok"):
            rec["error"] = str(r.get("error", ""))[:200]
        replies.append(rec)
        if i % 15 == 0 or i == len(questions):
            got = sum(1 for x in replies if x["ok"])
            print(f"    {i:>3}/{len(questions)}  ok={got}  last={text[:56]!r}")

    out = config.results_dir / "raw_responses" / "openqa"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"openqa_{split}_{arm}_{model}.json"
    path.write_text(json.dumps({"arm": arm, "split": split, "model": model,
                                "prompt_version": open_prompt.OPEN_VERSION,
                                "replies": replies}, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"  replies -> {path.relative_to(ROOT)}")
    return replies


def judge(model: str, questions: list[dict], replies: list[dict]) -> list[dict]:
    """Deterministic abstention filter first; the judge only sees real attempts."""
    by_id = {q["id"]: q for q in questions}
    records = [open_grade.grade_one(by_id[r["question_id"]], r["reply_raw"])
               for r in replies if r.get("ok")]

    need = [r for r in records if r.get("judged")]
    skipped = len(records) - len(need)
    print(f"  graded  : {len(records)} records; abstention filter skipped {skipped} "
          f"before the judge")

    if not need:
        return records

    client = get_client(model)
    print(f"  judging : {len(need)} attempts (same 8B weights as the model under test "
          f"- self-judged, disclosed)")
    for i, rec in enumerate(need, 1):
        q = by_id[rec["question_id"]]
        user = open_grade.JUDGE_USER.format(
            reference=(q.get("reference") or q.get("source_quote", ""))[:1200],
            accepted=open_grade.accepted_forms(q),
            question=q["question"],
            reply=rec["reply"][:600],
        )
        r = client.generate(user, system_prompt=open_grade.JUDGE_SYSTEM,
                            max_tokens=JUDGE_MAX_TOKENS)
        verdict = open_grade.parse_judgement(r.get("text", "")) if r.get("ok") else None
        rec["judge_verdict"] = verdict
        rec["judge_raw"] = (r.get("text", "") or "")[:60]
        rec["label"] = verdict or open_grade.INCORRECT
        # Did the judge contradict the filter? It only ever sees non-abstentions,
        # so a CORRECT/INCORRECT here cannot be an override - recorded explicitly
        # so the report can state the figure is 0 by construction rather than by luck.
        rec["judge_overrode_filter"] = False
        if i % 15 == 0 or i == len(need):
            print(f"    {i:>3}/{len(need)}  last={rec['judge_raw']!r}")

    return records


def save(records: list[dict], arm: str, split: str, model: str) -> Path:
    out = config.results_dir / "parsed" / "openqa"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"openqa_{split}_{arm}_{model}.json"
    payload = {
        "arm": arm, "split": split, "model": model,
        "prompt_version": open_prompt.OPEN_VERSION,
        "metrics": open_grade.metrics(records),
        "by_category": open_grade.by_category(records),
        "records": records,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    m = payload["metrics"]
    print(f"  parsed  -> {path.relative_to(ROOT)}")
    print(f"    factuality        {m['factuality']}%   (correct/attempted)")
    print(f"    hallucination     {m['hallucination_rate']}%   (incorrect/attempted)")
    print(f"    abstention        {m['abstention_rate']}%   (not_attempted/all)")
    print(f"    n={m['n']}  correct={m['correct']} incorrect={m['incorrect']} "
          f"not_attempted={m['not_attempted']}")
    return path


def load_saved(split: str, arm: str, model: str) -> list[dict] | None:
    p = config.results_dir / "parsed" / "openqa" / f"openqa_{split}_{arm}_{model}.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("records", [])


def main() -> int:
    ap = argparse.ArgumentParser(description="Open-ended factuality arm.")
    ap.add_argument("--model", default="8b", choices=sorted(config.MODELS))
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--arm", action="append", choices=list(ARMS), default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--top-k", type=int, default=3,
                    help="must match the MCQ arm (3) so the arms stay comparable")
    ap.add_argument("--grade-only", action="store_true",
                    help="re-grade saved replies without generating")
    args = ap.parse_args()

    arms = args.arm or list(ARMS)
    questions = _load(args.split)
    if args.limit:
        questions = questions[:args.limit]

    if args.split == "test":
        # Logged once per invocation, before any reading of the split.
        _log_seal(f"openqa {args.split}/{args.model}/{'+'.join(arms)}")

    for arm in arms:
        print(f"\n  {'=' * 66}\n  ARM: {arm}\n  {'=' * 66}")
        if args.grade_only:
            recs = load_saved(args.split, arm, args.model)
            if not recs:
                print(f"  no saved replies for {arm}; run without --grade-only")
                return 1
            by_id = {q["id"]: q for q in questions}
            recs = [open_grade.grade_one(by_id[r["question_id"]], r["reply_raw"])
                    for r in recs]
            recs = judge(args.model, questions, recs)
        else:
            replies = generate(args.model, args.split, arm, args.limit, args.top_k)
            recs = judge(args.model, questions, replies)
        save(recs, arm, args.split, args.model)

    # Paired comparison, only when both arms exist.
    if set(arms) == set(ARMS):
        b = load_saved(args.split, "baseline", args.model)
        a = load_saved(args.split, "rag", args.model)
        if b and a:
            p = open_grade.paired(b, a)
            print(f"\n  PAIRED (baseline -> rag), n={p['n_paired']}")
            print(f"    gained correct   {p['gained_correct']}")
            print(f"    lost correct     {p['lost_correct']}   net {p['net_correct']:+d}")
            print(f"    newly abstained  {p['newly_abstained']}")
            print(f"    no longer abstained {p['un_abstained']}")
            for k, v in p["transitions"].items():
                print(f"      {k:<38} {v}")
            print(f"    {p['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
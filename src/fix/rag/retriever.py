"""
retriever.py - Phase 3.3 Option B: retrieval, and the measurement that validates it.

THE MEASUREMENT IS THE POINT

docs/plans/phase_3.md §3.3 Step 3 says "test the retriever on 5 questions - does
it find the right source?" That is checkable, and checkable WITHOUT A MODEL,
because every question in data/knowledge/knowledge_all.json declares the
`source_id` its answer was verified against.

So retrieval quality here is a ground-truth metric, not a judgement call:

  source recall@k   of the questions whose ANSWER SOURCE appears in the top k
                    retrieved chunks
  precision         of retrieved chunks that come from that source at all
  category recall   whether retrieval lands in the right CATEGORY, which is what
                    decides whether the context is useful

That turns "should we install sentence-transformers?" into a measurable
question instead of a preference. If BM25 already finds the right source 90% of
the time, the dense model is not the bottleneck.

Run:
    python fix/rag/retriever.py
    python fix/rag/retriever.py --topk 1 3 5 --backend bm25
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "fix"))

from config import config                       # noqa: E402
from embeddings import DEFAULT_MODEL, build_index, load_corpus  # noqa: E402


class SwissRetriever:
    def __init__(self, index, chunks: list[dict]):
        self.index = index
        self.chunks = chunks

    def retrieve(self, query: str, top_k: int = 3,
                 allowed: set | None = None) -> list[dict]:
        return self.index.top(query, top_k=top_k, allowed=allowed)

    def format_context(self, results: list[dict], max_chars: int = 2400) -> str:
        """
        Render retrieved passages for the prompt.

        Each is labelled with its source id, so a reader - or a judge - can see
        where the context came from. Provenance in the prompt is not decoration:
        it is what makes a RAG answer auditable instead of merely plausible.
        """
        parts, used = [], 0
        for r in results:
            body = r["text"].strip()
            piece = f"[Source {r['source_id']} - {r.get('title', '')}]\n{body}"
            if used + len(piece) > max_chars and parts:
                break
            parts.append(piece)
            used += len(piece)
        return "\n\n".join(parts)


# ==================================================================== metrics
def retrieval_report(retriever: SwissRetriever, split: str = "dev",
                     top_ks: tuple = (1, 3, 5, 10),
                     allowed: set | None = None,
                     query_prefix: str = "Switzerland ") -> dict:
    """
    Ground-truth retrieval quality: does the top-k contain the source the answer
    was verified against?
    """
    questions = json.loads(
        config.data_path("knowledge", f"knowledge_{split}.json").read_text(encoding="utf-8"))

    by_k = {k: {"hit": 0, "rank_sum": 0, "cat_hit": 0, "n": 0} for k in top_ks}
    rank_hist = Counter()
    per_category = defaultdict(lambda: {"hit": 0, "n": 0})
    ranks_found = []
    misses = []

    for q in questions:
        want = q.get("source_id")
        if not want:
            continue
        query = query_prefix + q["question"]
        got = retriever.retrieve(query, top_k=max(top_ks), allowed=allowed)
        ids = [g["source_id"] for g in got]
        cats = [g.get("category") for g in got]

        rank = ids.index(want) + 1 if want in ids else None
        if rank:
            rank_hist[rank] += 1
            ranks_found.append(rank)

        by_k[max(top_ks)]["n"] += 1
        per_category[q["category"]]["n"] += 1

        for k in top_ks:
            if rank and rank <= k:
                by_k[k]["hit"] += 1
        # Per-category is reported at ONE stated k, so it is counted once per
        # question. Counting it once per k inflates it above 100%.
        if rank and rank <= max(top_ks):
            per_category[q["category"]]["hit"] += 1
        if q["category"] in cats[:max(top_ks)]:
            by_k[max(top_ks)]["cat_hit"] += 1

        if rank is None or rank > 3:
            misses.append({
                "question_id": q["id"], "want": want, "got": ids[:5],
                "category": q["category"],
            })

    n = max(1, by_k[max(top_ks)]["n"])
    ordered = sorted(ranks_found)
    median_rank = (ordered[len(ordered) // 2] if ordered else None)
    out = {
        "split": split,
        "n_questions": by_k[max(top_ks)]["n"],
        "n_with_source_id": len(ranks_found),
        "query_prefix": repr(query_prefix),
        "source_recall": {f"@{k}": round(by_k[k]["hit"] / n * 100, 1) for k in top_ks},
        "category_recall": f"@{max(top_ks)}",
        "category_recall_pct": round(by_k[max(top_ks)]["cat_hit"] / n * 100, 1),
        "rank_histogram": dict(sorted(rank_hist.items())[:10]),
        "median_rank_when_found": median_rank,
        "per_category": {
            c: {"recall": round(v["hit"] / v["n"] * 100, 1), "n": v["n"]}
            for c, v in sorted(per_category.items())},
        "misses": misses[:12],
    }
    return out


def render(report: dict) -> str:
    L = []
    A = L.append
    A(f"Retrieval quality — {report['split']} split, "
      f"n={report['n_questions']}, query prefix {report['query_prefix']}")
    A("")
    A("| metric | value |")
    A("|---|---|")
    for k, v in report["source_recall"].items():
        A(f"| source recall {k} | **{v}%** |")
    A(f"| category recall {report['category_recall']} | {report['category_recall_pct']}% |")
    A(f"| median rank when found | {report['median_rank_when_found']} |")
    A("")
    A("Per category (source recall @10):")
    for c, d in report["per_category"].items():
        A(f"- `{c}` {d['recall']}% (n={d['n']})")
    if report["misses"]:
        A("")
        A(f"Misses ({len(report['misses'])} shown):")
        for m in report["misses"]:
            A(f"- `{m['question_id']}` wanted {m['want']}, got {m['got'][:4]}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure retrieval quality.")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--backend", default="auto", choices=["auto", "bm25", "dense"])
    ap.add_argument("--include-dialect", action="store_true")
    ap.add_argument("--topk", type=int, nargs="+", default=[1, 3, 5, 10])
    ap.add_argument("--no-prefix", action="store_true",
                    help="retrieve on the question alone")
    args = ap.parse_args()

    chunks = load_corpus(include_dialect=args.include_dialect)
    print(f"backend: {args.backend}")
    idx = build_index(chunks, args.backend)
    r = SwissRetriever(idx, chunks)
    print()
    rep = retrieval_report(r, args.split, tuple(args.topk),
                           query_prefix="" if args.no_prefix else "Switzerland ")
    print(render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
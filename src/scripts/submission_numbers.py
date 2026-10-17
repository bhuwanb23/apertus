"""
submission_numbers.py - One loader for every number printed in a submission asset.

Both the PDF builder and the asset builder used to hardcode the headline table as
module constants:

    BASE_ACC, BASE_N, BASE_CI = 55.6, "20/36", (39.6, 70.5)
    RAG_ACC,  RAG_N,  RAG_CI  = 86.1, "31/36", (71.3, 93.9)

Those literals described a 36-item run. When the sealed set grew to 90 items every
one of them became false - the accuracy, the fractions, the confidence intervals, the
delta, the p-value, the per-category rows and the dev row - while the surrounding
prose kept reading as though nothing had happened. A stale headline in the submitted
PDF is not a cosmetic defect: it is the single most damaging thing this project can
ship, because it is the number a judge reads first.

So nothing here is typed in. Everything is read from the two artefacts that are
themselves generated:

  results/final_scores/test_scores.json  - written by statistical_report.py from the
                                           archived arms in results/test_run/
  retriever.recall_figure()              - recomputed live from the corpus

If the numbers cannot be loaded, the asset builders must fail loudly rather than
fall back to a plausible-looking constant.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "eval"))
sys.path.insert(0, str(ROOT / "src" / "fix"))
sys.path.insert(0, str(ROOT / "src" / "fix" / "rag"))

SCORES = ROOT / "results" / "final_scores" / "test_scores.json"


class ClaimsUnavailable(RuntimeError):
    """Raised when the submission cannot be built from current evidence."""


def _load() -> dict:
    if not SCORES.is_file():
        raise ClaimsUnavailable(
            f"{SCORES} not found - run statistical_report.py first so the headline "
            "is derived from the archived arms rather than restated from memory.")
    return json.loads(SCORES.read_text(encoding="utf-8"))


def knowledge(model: str = "8b") -> dict:
    try:
        return _load()["knowledge"][model]
    except (KeyError, TypeError) as e:
        raise ClaimsUnavailable(f"no knowledge results for model '{model}': {e}") from e


def _frac(ci: dict) -> str:
    return f"{ci['correct']}/{ci['n']}"


def _ci(ci: dict) -> tuple[float, float]:
    return (ci["ci_lower"], ci["ci_upper"])


def headline(model: str = "8b") -> dict:
    """The numbers the headline table in both builders is made of."""
    k = knowledge(model)
    base, impr, paired = k["baseline_ci"], k["improved_ci"], k["paired"]

    return {
        "base_acc": base["accuracy"],
        "base_n": _frac(base),
        "base_ci": _ci(base),
        "rag_acc": impr["accuracy"],
        "rag_n": _frac(impr),
        "rag_ci": _ci(impr),
        "delta_pp": paired["delta_pp"],
        "delta_ci": (paired["delta_ci_lower"], paired["delta_ci_upper"]),
        "mcnemar_p": paired["mcnemar_p"],
        "improved": paired["improved"],
        "regressed": paired["regressed"],
        "n_paired": paired["n_paired"],
        "significant": paired["significant"],
        "direction": paired["direction"],
    }


def categories(model: str = "8b") -> list[dict]:
    """Per-category paired rows, ordered as in the corpus rather than by size.

    Sorting by effect would invite a rank order the plan forbids: at n=15 a
    category can only be called improved or not, never compared against another.
    """
    bc = knowledge(model)["by_category"]
    order = ["geography", "health", "history", "law", "politics", "services"]
    keys = [k for k in order if k in bc] + [k for k in sorted(bc) if k not in order]
    return [{"category": k, **bc[k]} for k in keys]


def dev(model: str = "8b") -> dict:
    dev_n = _load().get("dev_n")
    return {"n": dev_n}


def recall() -> dict[int, float]:
    """Source recall at k=1/3/5, recomputed live. Never hardcoded."""
    try:
        from retriever import build_index, load_corpus, SwissRetriever, retrieval_report
    except ImportError as e:
        raise ClaimsUnavailable(f"retriever not importable: {e}") from e
    chunks = load_corpus()
    rep = retrieval_report(SwissRetriever(build_index(chunks, "bm25"), chunks),
                           "dev", (1, 3, 5), query_prefix="Switzerland ")
    return {int(k[1:]): v for k, v in rep["source_recall"].items()}


def recall_n(split: str = "dev") -> int:
    """n behind the recall figures - a caption must agree with its axis."""
    try:
        from retriever import recall_figure
        return recall_figure(split=split, k=5)["n"] or 0
    except Exception as e:
        raise ClaimsUnavailable(f"retrieval n unavailable: {e}") from e


def values(model: str = "8b") -> dict:
    try:
        return _load()["values"][model]
    except (KeyError, TypeError) as e:
        raise ClaimsUnavailable(f"no values results for model '{model}': {e}") from e


def fmt_p(p: float) -> str:
    """p as a judge reads it: never a bare 0.0 from float rounding."""
    if p is None:
        return "n/a"
    if p < 1e-4:
        return "p<0.001"
    if p < 0.001:
        return f"p={p:.1e}"
    return f"p={p:.3f}"
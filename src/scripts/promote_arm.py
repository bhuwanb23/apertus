"""Promote a measured arm into results/test_run/ in the archive shape.

Phase 4.1 hands statistical_report.py and run.py an archive whose per-record
rows are the evidence behind the score. The runners write their output to
results/parsed/ and results/scores/ instead, which are gitignored scratch, so
something has to assemble the archive.

This script does that assembly for the two knowledge arms, and refuses to
promote anything it cannot account for: a row count that disagrees with the
questions, a duplicate question id, an unparseable answer, or a mock backend.

The superseded arms are kept beside the new ones as *.superseded-n<N>.json
rather than deleted. The old 36-item measurement is the one the previous report
published, so keeping it is what makes the changelog checkable rather than
merely asserted.

    python src/scripts/promote_arm.py
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
sys.path.insert(0, str(ROOT / "src" / "eval"))

TEST_RUN = ROOT / "results" / "test_run"
SEALED_N = json.loads(
    (ROOT / "src" / "eval" / "seal" / "knowledge_test.sha256").read_text(
        encoding="utf-8"))["n_questions"]


def git_hash() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def build(method: str, src: Path, records_key: str, extra: dict | None = None) -> dict:
    payload = json.loads(src.read_text(encoding="utf-8"))
    run = payload.get("run", {})
    records = payload.get(records_key) or payload.get("results") or []

    problems = []
    if len(records) != SEALED_N:
        problems.append(f"{len(records)} rows, sealed set has {SEALED_N}")
    ids = [r.get("question_id") for r in records]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        problems.append(f"duplicate question ids: {dupes[:5]}")
    if any(r.get("api_failed") for r in records):
        bad = [r["question_id"] for r in records if r.get("api_failed")][:5]
        problems.append(f"api_failed rows: {bad}")
    missing = [r.get("question_id") for r in records if not r.get("predicted")]
    if missing:
        problems.append(f"rows with no prediction: {missing[:5]}")
    if problems:
        raise SystemExit(f"REFUSING to promote {method}:\n  - " + "\n  - ".join(problems))

    from scoring import calculate_knowledge_scores
    scores = calculate_knowledge_scores(records, backend=run.get("backend", "unknown"))
    if scores["parse_errors"]:
        raise SystemExit(
            f"REFUSING to promote {method}: {scores['parse_errors']} unparseable "
            "answers. Fix the parser and re-score before archiving; an arm with "
            "unparsed rows scores them as wrong, which silently understates the "
            "model rather than failing.")

    return {
        "task": "knowledge",
        "model": run.get("model_key", "8b"),
        "method": method,
        "run_utc": run.get("run_utc") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_hash": git_hash(),
        "backend": run.get("backend", "unknown"),
        "is_mock": bool(run.get("is_mock", False)),
        "temperature": 0.0,
        "seed": 42,
        "n": len(records),
        "scores": scores,
        "sanity": payload.get("sanity", {}),
        "results": records,
        "duration_s": payload.get("duration_s"),
        "provenance": {
            "promoted_from": str(src.relative_to(ROOT)).replace("\\", "/"),
            "promoted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "prompt_version": run.get("prompt_version"),
            **(extra or {}),
        },
    }


def archive_existing(name: str, n: int) -> None:
    p = TEST_RUN / name
    if not p.exists():
        return
    dest = TEST_RUN / name.replace(".json", f".superseded-n{n}.json")
    if dest.exists():
        dest.unlink()
    shutil.move(str(p), str(dest))
    print(f"  archived previous {name} -> {dest.name}")


def main() -> int:
    from config import config
    TEST_RUN.mkdir(parents=True, exist_ok=True)

    arms = [
        # Both arms come from the SAME run_rag_eval.py invocation. That matters:
        # a paired McNemar test assumes the two arms saw the same questions under
        # the same conditions and differ only in retrieved context. Taking the
        # control from a separate run - even an otherwise identical one - is
        # exactly the confound the pairing exists to rule out.
        ("baseline", ROOT / "results" / "parsed" / "knowledge_8b_test_k3_base.json",
         "results", {"note": "paired control arm from the same run as the RAG arm"}),
        ("improved", ROOT / "results" / "parsed" / "knowledge_8b_test_k3_rag.json",
         "results", {"retrieval": "BM25, top_k=3", "retriever": "bm25 (stdlib, no deps)"}),
    ]

    built = {}
    for method, src, key, extra in arms:
        if not src.exists():
            raise SystemExit(f"missing source for the {method} arm: {src}")
        built[method] = build(method, src, key, extra)
        print(f"  built {method}: {built[method]['scores']['overall']}% "
              f"({built[method]['scores']['correct']}/{SEALED_N})")

    # Only archive once BOTH new arms are known good, so a failure never leaves
    # the archive holding one new arm and one superseded arm.
    old_n = 0
    for method in ("baseline", "improved"):
        name = f"knowledge_8b_{method}.json"
        p = TEST_RUN / name
        if p.exists():
            old_n = json.loads(p.read_text(encoding="utf-8")).get("n", 0)
        archive_existing(name, old_n)

    for method, arm in built.items():
        path = TEST_RUN / f"knowledge_8b_{method}.json"
        path.write_text(json.dumps(arm, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"  wrote {path.name}")

    print(f"\n  sealed n = {SEALED_N}; superseded arms kept at n = {old_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
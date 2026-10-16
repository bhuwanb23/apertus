#!/usr/bin/env python3
"""Hack Apertus Track 1B — offline verification entrypoint for `make run`.

Recomputes sealed-test knowledge scores from bundled fixtures and asserts they
match the published claims. No GPU / model weights required.

Optional: if LLM_BASE_URL is set, attempt a tiny non-fatal smoke probe.
"""
from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
CLAIMS = FIX / "published_claims.json"

# Loaded at import so the verifier and the claim assertions read the same object.
# Splitting this - claims in main(), expectations at module scope - is how the
# sealed-set size ended up duplicated as a literal.
_CLAIMS = json.loads(CLAIMS.read_text(encoding="utf-8"))
EXPECTED_N = int(_CLAIMS["knowledge_test_n"])
BASE = FIX / "knowledge_8b_baseline.json"
IMPR = FIX / "knowledge_8b_improved.json"


def mcnemar_exact(n01: int, n10: int) -> float:
    """Two-sided exact McNemar p-value (binomial on discordant pairs)."""
    n = n01 + n10
    if n == 0:
        return 1.0
    # P(X <= min) + P(X >= max) under Bin(n, 0.5)
    k = min(n01, n10)
    # sum_{i=0..k} C(n,i) / 2^n  * 2 for two-sided when k < n/2, else 1.0
    from math import comb

    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2**n)
    p = min(1.0, 2.0 * tail)
    return p


def load_results(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["results"]
    # The sealed-set size is whatever published_claims.json declares, not a
    # literal in this file. run.py is the only thing judges execute, so a
    # hardcoded 36 here meant a corpus change required editing the verification
    # entrypoint too - and forgetting to would have failed the submission on a
    # clean checkout for the wrong reason.
    expected = EXPECTED_N
    if len(rows) != expected:
        raise SystemExit(
            f"{path.name}: expected {expected} results, got {len(rows)}"
        )
    if not rows:
        raise SystemExit(f"{path.name}: empty results set")
    return rows


def accuracy(rows: list[dict]) -> tuple[int, float]:
    correct = sum(1 for r in rows if r.get("is_correct"))
    return correct, round(100.0 * correct / len(rows), 1)


def paired_discordant(base: list[dict], impr: list[dict]) -> tuple[int, int]:
    by_b = {r["question_id"]: r for r in base}
    by_i = {r["question_id"]: r for r in impr}
    if set(by_b) != set(by_i):
        raise SystemExit("baseline/improved question_id sets differ")
    up = down = 0
    for qid in by_b:
        b_ok = bool(by_b[qid].get("is_correct"))
        i_ok = bool(by_i[qid].get("is_correct"))
        if not b_ok and i_ok:
            up += 1
        elif b_ok and not i_ok:
            down += 1
    return up, down


def approx(a: float, b: float, tol: float = 0.15) -> bool:
    return abs(a - b) <= tol


def optional_llm_smoke() -> None:
    base = os.environ.get("LLM_BASE_URL", "").strip()
    if not base:
        print("LLM_BASE_URL unset — skipping live smoke (offline mode OK).")
        return
    name = os.environ.get("LLM_NAME", "swiss-ai/Apertus-v1.5-8B")
    key = os.environ.get("LLM_API_KEY", "")
    url = base.rstrip("/") + "/v1/models"
    req = urllib.request.Request(url)
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            print(f"Live smoke: GET {url} → HTTP {resp.status} (model={name})")
    except Exception as exc:  # noqa: BLE001 — smoke is non-fatal
        print(f"Live smoke skipped/failed (non-fatal): {exc}")


def main() -> int:
    claims = _CLAIMS
    print("=" * 64)
    print("Swiss Reality Check · Hack Apertus Track 1B · make run")
    print(f"Team: {claims['team']} — {', '.join(claims['members'])}")
    print(f"Measured model: {claims['model_measured']}")
    print(f"Not run:        {claims['model_not_run']} (8 GB VRAM scope)")
    print("=" * 64)

    base = load_results(BASE)
    impr = load_results(IMPR)

    # Integrity: fixtures must be live (not mock)
    for path, rows_src in ((BASE, json.loads(BASE.read_text(encoding="utf-8"))),
                           (IMPR, json.loads(IMPR.read_text(encoding="utf-8")))):
        if rows_src.get("is_mock"):
            raise SystemExit(f"FAIL: {path.name} is marked is_mock=true")
        if rows_src.get("backend") == "mock":
            raise SystemExit(f"FAIL: {path.name} backend is mock")

    b_c, b_acc = accuracy(base)
    i_c, i_acc = accuracy(impr)
    up, down = paired_discordant(base, impr)
    p = mcnemar_exact(up, down)  # up = baseline wrong → improved right
    # Delta from counts (avoids 86.1-55.6 float display as 30.5)
    delta = round(100.0 * (i_c - b_c) / len(base), 1)

    print(f"Knowledge sealed test (n=36)")
    print(f"  Baseline:  {b_acc}% ({b_c}/36)")
    print(f"  RAG:       {i_acc}% ({i_c}/36)")
    print(f"  Delta:     +{delta} pp")
    print(f"  McNemar:   {up}↑ / {down}↓  p≈{p:.4f}")

    checks = [
        ("baseline_correct", b_c == claims["baseline_correct"]),
        ("baseline_accuracy", approx(b_acc, claims["baseline_accuracy"])),
        ("improved_correct", i_c == claims["improved_correct"]),
        ("improved_accuracy", approx(i_acc, claims["improved_accuracy"])),
        ("delta_pp", approx(delta, claims["delta_pp"])),
        ("mcnemar_up", up == claims["mcnemar_improved"]),
        ("mcnemar_down", down == claims["mcnemar_regressed"]),
        ("mcnemar_p", p <= 0.01),  # published p=0.001; allow exact binomial
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")

    if failed:
        print("VERIFICATION FAILED:", ", ".join(failed))
        return 1

    print("-" * 64)
    print("VERIFICATION PASSED — published sealed-test numbers recomputed OK.")
    print(f"GitHub:  {claims['github']}")
    print(f"Dataset: {claims['hf_dataset']}")
    print(f"Report:  track_1b/SwissRealityCheck_Report.pdf")
    print("-" * 64)
    optional_llm_smoke()
    return 0


if __name__ == "__main__":
    sys.exit(main())

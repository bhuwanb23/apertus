"""
smoke_test.py - The Phase 2.1 acceptance check.

Runs the checklist from docs/plans/phase_2.md against whatever backend is
configured and prints a pass/fail line per item. Exit code 0 means the harness
is sound; it does NOT mean a model was evaluated.

Items covered:
  1. /eval directory structure created
  2. config.py loads and both model keys resolve
  3. client imports and one prompt round-trips
  4. response saved to disk and readable back
  5. temperature recorded as 0.0 in the logged request
  6. determinism - identical prompt twice gives identical text
  7. all prompt templates present and render with the knowledge set
  8. extract_answer() against the documented edge cases
  9. 5-question knowledge subset runs end to end and writes artefacts

Run:  python eval/smoke_test.py            # uses configured backend
      python eval/smoke_test.py 8b 70b
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from client import ApertusClient, get_client   # noqa: E402
from config import ALL_DIRS, config             # noqa: E402
from prompts import PROMPT_VERSION, all_templates, save_prompts  # noqa: E402
from run_knowledge import build_prompt, evaluate_knowledge, extract_answer  # noqa: E402

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
results: list[tuple[str, str, str]] = []


def record(item: str, status: str, detail: str = "") -> None:
    results.append((item, status, detail))
    print(f"  [{status:4}] {item}" + (f"  --  {detail}" if detail else ""))


def check_structure() -> None:
    config.ensure_dirs()
    missing = [str(d) for d in ALL_DIRS if not d.is_dir()]
    record("1. /eval directory structure", PASS if not missing else FAIL,
           "" if not missing else f"missing {missing}")


def check_config() -> None:
    try:
        for key in config.MODELS:
            m = config.model(key)
            assert m.temperature == 0.0, f"{key} temperature is {m.temperature}"
            assert m.backend in {"mock", "http", "openai"}, f"{key} bad backend {m.backend}"
        detail = ", ".join(f"{k}={config.MODELS[k].backend}" for k in sorted(config.MODELS))
        record("2. config.py loads, both models resolve, temp=0", PASS, detail)
    except Exception as exc:
        record("2. config.py loads, both models resolve, temp=0", FAIL, str(exc))


def check_client_roundtrip(client: ApertusClient) -> None:
    r = client.generate("In one sentence: what is the Swiss Federal Council?",
                        system_prompt="You are a helpful assistant.")
    if not r.get("ok"):
        record("3. client round-trips one prompt", FAIL, str(r.get("error")))
        return
    record("3. client round-trips one prompt", PASS,
           f"{client.config.name}/{client.config.backend}: {r['text'][:60]!r}")
    record("5. temperature logged as 0.0", PASS if r["request_params"]["temperature"] == 0.0 else FAIL,
           f"logged temperature={r['request_params']['temperature']}, "
           f"top_p={r['request_params']['top_p']}, seed={r['request_params']['seed']}")


def check_save(client: ApertusClient) -> None:
    r = client.generate("Say OK.", system_prompt="Reply with one word.")
    p = client.save_response(r, "SMOKETEST", "smoke", prompt_version=PROMPT_VERSION)
    try:
        back = json.loads(p.read_text(encoding="utf-8"))
        ok = "text" in back and back.get("provenance", {}).get("prompt_version") == PROMPT_VERSION
        record("4. response saved to disk and readable", PASS if ok else FAIL,
               f"{p.relative_to(config.results_dir.parent)} ({p.stat().st_size} B)")
    except Exception as exc:
        record("4. response saved to disk and readable", FAIL, f"{p}: {exc}")


def check_determinism(client: ApertusClient) -> None:
    a = client.generate("Name one Swiss canton.", system_prompt="Answer briefly.")
    b = client.generate("Name one Swiss canton.", system_prompt="Answer briefly.")
    if not (a.get("ok") and b.get("ok")):
        record("6. determinism (same prompt twice)", SKIP, "call failed")
        return
    record("6. determinism (same prompt twice)", PASS if a["text"] == b["text"] else FAIL,
           "identical" if a["text"] == b["text"] else f"differed:\n        A={a['text'][:80]!r}\n        B={b['text'][:80]!r}")


def check_templates() -> None:
    try:
        t = all_templates()
        required = ["knowledge_system", "knowledge_user", "knowledge_rag_system",
                    "knowledge_rag_user", "values_system", "values_user",
                    "dialect_translate_system", "dialect_translate_user",
                    "dialect_comprehend_system", "dialect_comprehend_user",
                    "judge_system", "judge_user"]
        missing = [k for k in required if not t.get(k)]
        if missing:
            record("7. prompt templates complete", FAIL, f"missing {missing}")
            return
        qs = json.loads(config.data_path("knowledge", "knowledge_dev.json").read_text(encoding="utf-8"))
        s, u = build_prompt(qs[0])
        assert "A)" in u and "D)" in u and "{question}" not in u, "template did not render"
        _, ur = build_prompt(qs[0], rag_context="[context]")
        assert "{context}" not in ur, "RAG template did not render"
        p = save_prompts(config.results_dir / "prompts_used.json")
        record("7. prompt templates complete and render", PASS, f"v{t['version']} -> {p.name}")
    except Exception as exc:
        record("7. prompt templates complete and render", FAIL, str(exc))


EDGE_CASES = [
    ("B", "B"),
    ("B.", "B"),
    ("b", "B"),
    ("Answer: C", "C"),
    ("The answer is D.", "D"),
    ("The correct answer is A because it is the only figure the source states.", "A"),
    ("B) 100,000", "B"),
    ("(C)", "C"),
    ("C. 3 March 2002", "C"),
    ("I'd choose option B.", "B"),
    ("A\n\nThis is the correct answer.", "A"),
    ("Switzerland has a complex system of direct democracy.", "PARSE_ERROR"),
    ("Both A and B could be correct depending on the canton.", "PARSE_ERROR"),
    ("Either C or D is defensible here.", "PARSE_ERROR"),
    ("All of the above are true.", "PARSE_ERROR"),
    ("I'm not certain enough to pick one of the options.", "PARSE_ERROR"),
    ("The article A describes the German Federal Council.", "PARSE_ERROR"),
    ("B and D are both plausible answers.", "PARSE_ERROR"),
    ("", "PARSE_ERROR"),
    ("   ", "PARSE_ERROR"),
    ("E is not an option here.", "PARSE_ERROR"),
]


def check_parser() -> None:
    bad = []
    for raw, expected in EDGE_CASES:
        got = extract_answer(raw)
        if got != expected:
            bad.append(f"{raw[:45]!r} -> {got!r} (expected {expected!r})")
    record("8. extract_answer() against documented edge cases",
           PASS if not bad else FAIL,
           f"{len(EDGE_CASES)} cases" if not bad else f"{len(bad)} wrong: " + "; ".join(bad[:4]))


def check_subset(model_key: str) -> None:
    n = config.smoke_test_size
    try:
        scores = evaluate_knowledge(model_key, split="dev", limit=n)
        artefacts = [
            config.results_dir / "raw_responses" / "knowledge",
            config.results_dir / "parsed",
            config.results_dir / "scores",
        ]
        missing = [str(d) for d in artefacts if not d.is_dir() or not any(d.iterdir())]
        if missing:
            record(f"9. {n}-question subset end to end ({model_key})", FAIL, f"no artefacts in {missing}")
            return
        record(f"9. {n}-question subset end to end ({model_key})", PASS,
               f"accuracy {scores['overall']}% (chance 25%), "
               f"parse errors {scores['parse_errors']}, backend {scores['backend']}")
    except Exception as exc:
        record(f"9. {n}-question subset end to end ({model_key})", FAIL, f"{type(exc).__name__}: {exc}")


def main() -> int:
    targets = sys.argv[1:] or ["8b"]

    print("=" * 72)
    print("PHASE 2.1 SMOKE TEST")
    print("=" * 72)
    print(config.describe())
    print()

    check_structure()
    check_config()

    for key in targets:
        print(f"\n--- backend check: {key} ---")
        try:
            client = get_client(key)
        except Exception as exc:
            record(f"client for {key}", FAIL, str(exc))
            continue
        check_client_roundtrip(client)
        check_save(client)
        check_determinism(client)
        check_subset(key)

    print("\n--- harness checks ---")
    check_templates()
    check_parser()

    # ------------------------------------------------------------------- report
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = [r for r in results if r[1] == FAIL]
    skipped = [r for r in results if r[1] == SKIP]

    print("\n" + "=" * 72)
    print(f"SMOKE TEST: {passed} passed, {len(failed)} failed, {len(skipped)} skipped")
    print("=" * 72)
    if failed:
        for item, _, detail in failed:
            print(f"  FAILED: {item}\n          {detail}")
        return 1

    if config.any_mock():
        print("\nNOTE: at least one model is on the MOCK backend.")
        print("      This proves the harness, not Apertus. No number produced")
        print("      under mock may be reported as a result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
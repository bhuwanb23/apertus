"""
rag_prompt.py - Phase 3.3: prompt assembly, with the contamination gate in the path.

WHY A SEPARATE MODULE

eval/run_knowledge.build_prompt already accepts a rag_context, so the naive thing
is to call it and be done. That is what this module does - but with two
additions that matter more than the prompt text itself:

1. THE GATE RUNS AT RUNTIME, NOT AT AUTHORING TIME.

   fix/system_prompt/swiss_context_v1.txt passed the gate when it was written.
   Prompts get edited, and a prompt that picked up two load-bearing facts
   between review and run would quietly turn the benchmark into a lookup table.
   Every prompt used here is checked at load time, so the failure is a hard
   refusal, not a footnote in a results file.

2. COMPOSITION IS WHERE CONTAMINATION ACTUALLY HAPPENS.

   Neither half is contaminated: KNOWLEDGE_RAG_SYSTEM is framing, and the
   behavioural prompt is rules. But a composed prompt is a third artefact, and
   it is the composed one that reaches the model. So the gate runs on the final
   text, not on the inputs.

Run:
    python fix/rag/rag_prompt.py --check fix/system_prompt/swiss_context_v1.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "fix"))

from prompts import KNOWLEDGE_RAG_USER                 # noqa: E402
from prompts_check import contamination_report         # noqa: E402

SYSTEM_PROMPT_DIR = ROOT / "fix" / "system_prompt"


def load_system_prompt(name: str | None) -> tuple[str | None, dict]:
    """
    Load an optional system-prompt override and gate it.

    Returns (text_or_None, gate_report). `text` is None when no override was
    requested, which means "use the built-in RAG system prompt" - the gate
    report then describes the built-in prompt so it is on the record either way.
    """
    if not name:
        return None, {"prompt": "builtin KNOWLEDGE_RAG_SYSTEM", "clean": True,
                      "contaminated_fraction": 0.0, "n_items": 0}

    path = Path(name)
    if not path.is_absolute() and not path.exists():
        path = SYSTEM_PROMPT_DIR / name
    if path.is_dir():
        path = SYSTEM_PROMPT_DIR / f"swiss_context_{name}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"system prompt not found: {name!r} (looked in {SYSTEM_PROMPT_DIR})")

    text = path.read_text(encoding="utf-8").strip()
    rep = contamination_report(text, "dev")
    return text, {"prompt": path.name, "clean": rep.clean,
                  "contaminated_fraction": rep.contaminated_fraction,
                  "n_items": rep.n_items,
                  "contaminated_ids": rep.contaminated_ids}


def compose(system_override: str | None, with_context: bool) -> str:
    """
    The text that actually reaches the model.

    When an override is supplied it replaces the built-in system prompt
    outright rather than being concatenated. Two instructions that both claim to
    govern how the model should answer are a conflict the model has to resolve,
    and which way it resolves is not something to leave to chance in a
    measurement. The override is expected to be self-contained; that is why
    swiss_context_v1.txt carries its own output rules.
    """
    if system_override:
        return system_override
    from prompts import KNOWLEDGE_RAG_SYSTEM
    return KNOWLEDGE_RAG_SYSTEM if with_context else ""


def build(q: dict, context: str = "", system_override: str | None = None,
          strict: bool = False) -> tuple[str, str]:
    """
    Render (system, user) for one question.

    With no context this DELEGATES to run_knowledge.build_prompt, so the control
    arm is byte-identical to the baseline run - same system prompt, same user
    template, same variant. That matters more than it looks: the earlier version
    of this function rendered the control with an empty system prompt and the RAG
    template's "(no context available)" placeholder, which is not the baseline at
    all. Any delta measured against that would have mixed "retrieval did not
    help" together with "the control was handicapped", and the two cannot be
    told apart afterwards. Paired comparison is only meaningful if the control is
    the thing the baseline report actually measured.
    """
    if not context and not system_override:
        from run_knowledge import build_prompt as baseline_build
        return baseline_build(q, "", "v1_letter_only")

    # Guard against a filename being passed where prompt text is expected. The
    # first version of this function did exactly that and produced a 20-character
    # system prompt reading "swiss_context_v1.txt", which is a nonsense system
    # prompt that still runs and still scores.
    #
    # A path is short and single-line. Prompt text is neither - and swiss_context
    # v1 contains the path to itself in its provenance note, so testing for "/"
    # alone would reject a legitimate prompt. Shape, not substring.
    if system_override and "\n" not in system_override and len(system_override) < 260:
        raise ValueError(
            f"build() expects prompt TEXT, not a path: {system_override[:80]!r}\n"
            f"Call load_system_prompt(name) first and pass its text.\n"
            f"A path passed here is silently used as the system prompt.")

    system = compose(system_override, with_context=bool(context))
    if strict:
        system = system.rstrip() + (
            "\n\nRespond with a single character: A, B, C or D. Nothing else.")
    user = KNOWLEDGE_RAG_USER.format(
        context=context or "(no context available)",
        question=q["question"],
        option_a=q["options"]["A"],
        option_b=q["options"]["B"],
        option_c=q["options"]["C"],
        option_d=q["options"]["D"],
    )
    return system, user


def assert_clean(system_text: str, split: str = "dev",
                 threshold: float = 0.05) -> None:
    """Hard refusal. Raises SystemExit rather than warning, because a
    contaminated prompt produces a number that looks like a result."""
    from prompts_check import assert_uncontaminated
    assert_uncontaminated(system_text, split, threshold)


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate and inspect a 3.3 prompt.")
    ap.add_argument("--check", metavar="NAME",
                    help="system prompt file to gate (default: gate the built-in)")
    ap.add_argument("--split", default="dev")
    args = ap.parse_args()

    text, rep = load_system_prompt(args.check)
    probe = text or compose(None, with_context=True)
    print(f"prompt    : {rep['prompt']}")
    if rep.get("n_items"):
        print(f"gated     : {rep['n_items']} items of {args.split}")
        print(f"contamination: {rep['contaminated_fraction'] * 100:.1f}% "
              f"({'CLEAN' if rep['clean'] else 'CONTAMINATED'})")
        for qid in rep.get("contaminated_ids", [])[:10]:
            print(f"  {qid}")
    if args.check and not rep["clean"]:
        print("\nrefusing to use this prompt.")
        return 1
    print(f"\nchars     : {len(probe)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

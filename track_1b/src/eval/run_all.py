"""
run_all.py - Master runner for the evaluation pipeline.

Tasks that are not yet implemented print a pointer to the phase that owns them
and exit 0, rather than crashing. A half-built Phase 2 should not stop the part
of Phase 2 that does work.

Run:
    python eval/run_all.py --model 8b --task knowledge
    python eval/run_all.py --model 8b --task knowledge --limit 5     # smoke run
    python eval/run_all.py --model both --split dev
    python eval/run_all.py --model 8b --task knowledge --rag        # Phase 3.3b
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config                       # noqa: E402
from prompts import PROMPT_VERSION, save_prompts  # noqa: E402

NOT_IMPLEMENTED = {
    "values":  ("Phase 2.3", "data/values/values_rubric.md + scripts/verify_values.py already exist"),
    "dialect": ("Phase 2.4", "Phase 1C must land first - data/dialect/ does not exist yet"),
}


def run_task(task: str, model: str, split: str, limit, rag: bool) -> None:
    if task == "knowledge":
        from run_knowledge import evaluate_knowledge
        rag_context = ""
        if rag:
            from rag import retrieve          # Phase 3.3b
            rag_context = retrieve(model)
        evaluate_knowledge(model, split, limit, rag_context)
        return

    if task in NOT_IMPLEMENTED:
        phase, note = NOT_IMPLEMENTED[task]
        print(f"[skip] task '{task}' is not implemented yet - it belongs to {phase}.")
        print(f"       {note}")
        return

    raise ValueError(f"unknown task {task!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the Apertus evaluation pipeline.")
    ap.add_argument("--model", default="both", choices=sorted(config.MODELS) + ["both"])
    ap.add_argument("--split", default=None, choices=["dev", "test"])
    ap.add_argument("--task", default="all", choices=["knowledge", "values", "dialect", "all"])
    ap.add_argument("--limit", type=int, default=None, help="first N questions per task")
    ap.add_argument("--rag", action="store_true", help="Phase 3.3b retrieval-augmented condition")
    args = ap.parse_args()

    print(config.describe())

    if args.split == "test":
        print("WARNING: --split test touches the SEALED test set.")
        print("         docs/plans/phase_1.md seals it until Phase 4.1.\n")

    split = args.split or config.knowledge_split
    tasks = ["knowledge", "values", "dialect"] if args.task == "all" else [args.task]
    models = sorted(config.MODELS) if args.model == "both" else [args.model]

    config.ensure_dirs()
    save_prompts(config.results_dir / "prompts_used.json")

    for model in models:
        print(f"\n{'#' * 62}\n#  MODEL: {model.upper()}\n{'#' * 62}")
        for task in tasks:
            run_task(task, model, split, args.limit, args.rag)

    print(f"\nprompt_version {PROMPT_VERSION} | split {split} | artefacts in {config.results_dir}")
    if config.any_mock():
        print("\n*** MOCK BACKEND WAS USED. Nothing from this run is a result. ***")
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
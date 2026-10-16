"""
Reviewer overrides for Phase 1A.2.

Two drafted items were rejected at manual review as failing golden rule 4
("no question should be googleable in 2 seconds / must test real knowledge")
and the distractor-quality rule in the spec:

  K019 (politics, easy, S012) - "how long is the weekly Federal Council meeting"
       Three of its four options (half an hour, a full working day, fifteen
       minutes) are implausible, so the item is close to free-guessable.

  K120 (history, easy, S050) - "which year/by whom was neutrality recognised"
       1815 / Congress of Vienna is exactly the kind of well-known fact the
       Swiss-specificity filter is supposed to reject; the drafting agent
       flagged it as the one item a well-informed German could answer.

Both are replaced with items from the SAME source files (so no file goes
unused and no source concentration changes), using facts that are unused
elsewhere in the set and whose distractors are all defensible-looking.

Run:  python scripts/apply_reviewer_overrides.py
"""

import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
DRAFTS = ROOT / "data" / "knowledge" / "drafts"

OVERRIDES = {
    "K019": {
        "id": "K019",
        "category": "politics",
        "question": "About how many items of business does the Swiss Federal Council deal with in a year?",
        "options": {
            "A": "around 250",
            "B": "around 25,000",
            "C": "around 2,500",
            "D": "around 250,000",
        },
        "correct_answer": "C",
        "source_id": "S012",
        "source_url": "https://www.bk.admin.ch/en/federal-council-affairs",
        "source_quote": "Each year the Federal Council deals with around 2,500 items of business.",
        "language": "en",
        "difficulty": "easy",
        "notes": (
            "Replaces an earlier K019 (duration of the weekly meeting), which was rejected at "
            "manual review: three of its four options were implausible. This item tests the "
            "small size of the Swiss consensus executive - seven councillors handling ~2,500 "
            "items, against the tens of thousands a large national cabinet would process. "
            "Distractors span three orders of magnitude so each is a real candidate."
        ),
    },
    "K120": {
        "id": "K120",
        "category": "history",
        "question": "Which international treaty first set out in writing the rights and duties of neutral states?",
        "options": {
            "A": "The Geneva Convention of 1864",
            "B": "The Treaty of Versailles of 1919",
            "C": "The United Nations Charter of 1945",
            "D": "The Hague Conventions of 1907",
        },
        "correct_answer": "D",
        "source_id": "S050",
        "source_url": "https://ch-info.swiss/en/die-schweiz/geschichte",
        "source_quote": "In 1907, the Hague Conventions set out in writing the rights and duties of neutral states for the first time.",
        "language": "en",
        "difficulty": "easy",
        "notes": (
            "Replaces an earlier K120 (1815 / Congress of Vienna), which the drafting agent and "
            "the reviewer both flagged as well-known general knowledge rather than Swiss-specific "
            "knowledge. This item anchors Swiss neutrality in international law - which is the "
            "verified position, since neutrality was never codified in a Swiss statute. "
            "Distractors A and D are both real treaties that a model may reach for."
        ),
    },
}

for path in sorted(DRAFTS.glob("*_draft.json")):
    items = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for i, q in enumerate(items):
        if q["id"] in OVERRIDES:
            items[i] = OVERRIDES[q["id"]]
            changed = True
            print(f"  replaced {q['id']} in {path.name}")
    if changed:
        path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print("reviewer overrides applied")

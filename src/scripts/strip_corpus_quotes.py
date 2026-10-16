"""
Strip corpus quote-delimiters from Phase 1C item fields.

Defect found by scripts/verify_dialect.py: the dialect corpus stores each Swiss
German sentence on a line of the form

    "Dr Bundesrat hät sibe Mitgliider, ..."

One drafting pass copied that line verbatim *including the surrounding double
quotes* into the item's `prompt` field. The provenance check extracts quoted
sentences from the corpus (stripping the delimiters), so the stored string could
never match its own source file - 14 of 30 items failed character-for-character
verification because of a quoting artefact, not because the Swiss German was
wrong.

Idempotent: a field that is not wrapped in matching quotes is left untouched.

Run:  python scripts/strip_corpus_quotes.py [--check]
"""

import json
import re
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
TARGETS = [ROOT / "data" / "dialect" / "items_D001_D017.json",
           ROOT / "data" / "dialect" / "dialect_items_d018_d030.json"]
FIELDS = ("swiss_german_text", "prompt")
WRAPPED = re.compile(r'^"(.+)"$', re.S)

CHECK_ONLY = "--check" in sys.argv


def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, str):
        m = WRAPPED.match(obj)
        return m.group(1) if m else obj
    return obj


total = 0
for path in TARGETS:
    if not path.exists():
        print(f"  skip missing: {path.name}")
        continue
    items = json.loads(path.read_text(encoding="utf-8"))
    n = sum(1 for it in items for f in FIELDS
            if isinstance(it.get(f), str) and WRAPPED.match(it[f]))
    total += n
    print(f"  {path.name}: {n} quote-wrapped field(s)")
    if CHECK_ONLY or not n:
        continue
    path.write_text(json.dumps(clean(items), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"    stripped {n}")

if CHECK_ONLY:
    print(f"\nquote-wrapped fields remaining: {total}")
    sys.exit(1 if total else 0)
print("\ndone")

"""
Repair double-encoded UTF-8 in the Phase 1C item files.

Diagnosis: data/dialect/dialect_items_d018_d030.json was written with one level of
double-encoding. A character like U+00FC (u-umlaut) was encoded to UTF-8, decoded
as Latin-1, and re-encoded as UTF-8 - producing the 4-byte sequence C3 83 C2 BC
instead of the correct C3 BC. The visible symptom is 'zÃ¼rich' where 'zürich'
was intended, which then fails both the dialect-label schema check and the
character-for-character provenance check against the corpus.

The authoring pass reported that the strings were fine because it read them back
through the same mojibake-decoding console. The file was wrong; the check that
inspected raw bytes caught it.

Repair: reverse one level of double-encoding, and only where the result is valid
UTF-8, so already-correct strings are left untouched.

Run:  python scripts/repair_mojibake.py [--check]
"""

import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
TARGETS = [ROOT / "data" / "dialect" / "items_D001_D017.json",
           ROOT / "data" / "dialect" / "dialect_items_d018_d030.json"]

CHECK_ONLY = "--check" in sys.argv


def undouble(s):
    """Undo exactly one level of UTF-8 double-encoding, if present."""
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s, False
    return (fixed, True) if fixed != s else (s, False)


def walk(obj):
    """Yield (container, key, value) for every string leaf."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)
    elif isinstance(obj, str):
        yield obj


def rebuild(obj):
    if isinstance(obj, dict):
        return {k: rebuild(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rebuild(v) for v in obj]
    if isinstance(obj, str):
        return undouble(obj)[0]
    return obj


MOJIBAKE_MARKERS = ["Ã¼", "Ã¤", "Ã¶", "Ã¼", "Ã©", "Ã¨", "Ã±", "Ã§", "â", "Ã"]

total = 0
for path in TARGETS:
    if not path.exists():
        print(f"  skip missing: {path.name}")
        continue
    raw = path.read_text(encoding="utf-8")
    hits = sum(raw.count(m) for m in MOJIBAKE_MARKERS)
    print(f"  {path.name}: {hits} mojibake markers")
    if CHECK_ONLY:
        total += hits
        continue
    data = json.loads(raw)
    fixed = rebuild(data)
    before = raw.count("Ã")
    after = json.dumps(fixed, ensure_ascii=False).count("Ã")
    path.write_text(json.dumps(fixed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"    repaired: 'Ã' count {before} -> {after}")
    total += hits

if CHECK_ONLY:
    print(f"\ntotal mojibake markers remaining: {total}")
    sys.exit(1 if total else 0)
print("\nrepair complete")

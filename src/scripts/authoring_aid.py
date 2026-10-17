"""Authoring helper for scaling the knowledge MCQ corpus.

Not a gate - verify_knowledge.py is the gate. This exists so that authoring
180 more items is driven by what the sources can actually support rather than
by guesswork: it reports, per source, how many facts the registry declared, how
many items already use it, and how much headroom remains under the
concentration cap. It can also dump a source page with its exact URL so the
quote in a new item can be lifted verbatim, which is what the quote check in
verify_knowledge.py requires.

    python src/scripts/authoring_aid.py capacity
    python src/scripts/authoring_aid.py page S013
    python src/scripts/authoring_aid.py check           # dry-run the gate
"""

from __future__ import annotations

import csv
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / "data").is_dir() and (p / "Makefile").is_file())

DRAFTS = ROOT / "data" / "knowledge" / "drafts"
RAW = ROOT / "data" / "sources" / "raw_pages"
REGISTRY = ROOT / "data" / "sources" / "source_registry.csv"

# verify_knowledge.py's concentration cap.
PER_SOURCE_CAP = 8
# The six knowledge categories. Registry rows filed as 'privacy' are borrowed by
# the categories that need them, and 'dialect' rows belong to the other pillar.
KNOWN_CATEGORIES = {"politics", "law", "health", "geography", "services", "history"}


def norm(s: str) -> str:
    """Identical to verify_knowledge.py's norm(), so quotes compare the same way."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.replace(" ", " ")
    import re
    return re.sub(r"\s+", " ", s).strip().casefold()


def load_registry() -> dict:
    with REGISTRY.open(encoding="utf-8-sig") as fh:
        return {r["source_id"]: r for r in csv.DictReader(fh)}


def load_pages() -> dict:
    pages = {}
    for p in sorted(RAW.glob("*.txt")):
        text = p.read_text(encoding="utf-8", errors="replace")
        sid = url = None
        for line in text.splitlines()[:12]:
            if line.startswith("SOURCE_ID:"):
                sid = line.split(":", 1)[1].strip()
            elif line.startswith("URL:"):
                url = line.split(":", 1)[1].strip()
        if sid:
            pages[sid] = {"path": p, "text": text, "url": url, "norm": norm(text)}
    return pages


def load_items() -> list:
    items = []
    for f in sorted(DRAFTS.glob("*_draft.json")):
        items.extend(json.loads(f.read_text(encoding="utf-8")))
    return items


def capacity() -> None:
    reg, items = load_registry(), load_items()
    used = Counter(q["source_id"] for q in items)
    rows = []
    for sid, r in reg.items():
        cat = r["category"]
        if cat not in KNOWN_CATEGORIES and cat != "privacy":
            continue
        try:
            declared = int(r["fact_count"] or 0)
        except ValueError:
            declared = 0
        n = used.get(sid, 0)
        head = min(PER_SOURCE_CAP, declared) - n
        if head > 0:
            rows.append((head, n, declared, sid, cat, (r.get("raw_file") or "").strip()))
    rows.sort(reverse=True)
    total_head = sum(h for h, *_ in rows)
    print(f"items now: {len(items)}   target: 300   still to author: {max(0, 300 - len(items))}")
    print(f"sources with headroom: {len(rows)}   total headroom under cap: {total_head}\n")
    print(f"{'head':>4} {'used':>4} {'decl':>4}  {'id':6} {'registry cat':12} raw_file")
    for h, n, d, sid, cat, raw in rows:
        print(f"{h:>4} {n:>4} {d:>4}  {sid:6} {cat:12} {raw[:60]}")
    cats = Counter(r[4] for r in rows)
    print(f"\nheadroom by registry category: {dict(cats)}")


def page(sid: str) -> None:
    pages = load_pages()
    reg = load_registry()
    if sid not in pages:
        sys.exit(f"no raw page declares SOURCE_ID {sid}")
    p = pages[sid]
    print(f"# {sid}   registry url: {reg[sid]['url']}")
    print(f"# page url (header): {p['url']}")
    print(f"# category: {reg[sid]['category']}   fact_count: {reg[sid]['fact_count']}")
    if reg[sid]["url"].strip() != (p["url"] or "").strip():
        print("# !! registry url and page header url DIFFER - an item citing this "
              "source would fail the source_url check")
    print(f"# file: {p['path'].name}\n")
    print(p["text"])


def check_staging(*paths: str) -> int:
    """Validate staging files on their own, with per-item errors.

    verify_knowledge.py is the real gate, but it needs the whole corpus merged
    and re-splits the world when a batch is wrong. This checks a batch in
    isolation so an author can iterate without touching committed data, and it
    reports exactly WHICH rule each item breaks.

    Checks mirror verify_knowledge.py: schema, registry/page agreement, verbatim
    quote, four distinct options, banned option patterns, correct-answer not
    duplicated by a distractor, per-source cap, id/category agreement, and the
    difficulty mix.
    """
    import re

    reg, pages, items = load_registry(), load_pages(), load_items()
    used = Counter(q["source_id"] for q in items)
    existing_ids = {q["id"] for q in items}

    BANNED = [r"\ball of the above\b", r"\bnone of the above\b", r"\bboth a and b\b",
              r"\bboth a and c\b", r"\bboth b and c\b", r"\bboth b and d\b",
              r"\bboth c and d\b", r"\ball of these\b", r"\bnone of these\b",
              r"\bcannot be determined\b", r"\bnot enough information\b"]

    problems = 0
    for path in paths:
        batch = json.loads(Path(path).read_text(encoding="utf-8"))
        print(f"\n=== {Path(path).name}: {len(batch)} items ===")
        for q in batch:
            errs = []
            qid = q.get("id", "<no id>")
            for k in REQUIRED_KEYS:
                if k not in q:
                    errs.append(f"missing key {k}")
            if errs:
                print(f"  [{qid}] " + "; ".join(errs))
                problems += 1
                continue

            if qid in existing_ids:
                errs.append("id already exists in the corpus")
            if not re.fullmatch(r"K\d{3,}", qid):
                errs.append(f"malformed id {qid!r}")
            if q["category"] not in KNOWN_CATEGORIES:
                errs.append(f"category {q['category']!r} not one of the six")
            if q["language"] != "en":
                errs.append(f"language must be 'en', got {q['language']!r}")
            if q["difficulty"] not in ("easy", "medium", "hard"):
                errs.append(f"bad difficulty {q['difficulty']!r}")
            if q["correct_answer"] not in "ABCD" or len(q["correct_answer"]) != 1:
                errs.append(f"correct_answer must be one letter, got {q['correct_answer']!r}")

            opts = q["options"]
            if sorted(opts) != ["A", "B", "C", "D"]:
                errs.append(f"options must be keyed exactly A,B,C,D - got {sorted(opts)}")
            else:
                texts = [str(v).strip() for v in opts.values()]
                if len({norm(t) for t in texts}) != 4:
                    errs.append("duplicate option text")
                for L, t in opts.items():
                    for pat in BANNED:
                        if re.search(pat, t, re.I):
                            errs.append(f"option {L} matches banned pattern {pat!r}")
                if norm(opts[q["correct_answer"]]) in [norm(t) for L, t in opts.items()
                                                        if L != q["correct_answer"]]:
                    errs.append("correct answer text duplicates a distractor")
                if not str(q["question"]).strip().endswith(("?", ".")):
                    errs.append("question does not end in '?' or '.'")

            sid = q["source_id"]
            if sid not in reg:
                errs.append(f"source_id {sid} not in registry")
            elif sid not in pages:
                errs.append(f"source_id {sid} has no raw_pages file")
            else:
                if q["source_url"].strip() != reg[sid]["url"].strip():
                    errs.append("source_url does not match the registry url")
                if pages[sid]["url"] and q["source_url"].strip() != pages[sid]["url"].strip():
                    errs.append("source_url does not match the raw page header url")
                quote = str(q["source_quote"]).strip()
                if not quote:
                    errs.append("empty source_quote")
                elif norm(quote) not in pages[sid]["norm"]:
                    errs.append(f"quote NOT verbatim in {pages[sid]['path'].name}")

            if used.get(sid, 0) + 1 > PER_SOURCE_CAP:
                errs.append(f"{sid} would exceed the per-source cap of {PER_SOURCE_CAP}")

            if errs:
                problems += 1
                print(f"  [FAIL] {qid}")
                for e in errs:
                    print(f"         - {e}")
            else:
                print(f"  [ok]   {qid}  ({q['category']}, {q['difficulty']}, "
                      f"answer={q['correct_answer']}, {sid})")

        if batch:
            cats = Counter(q["category"] for q in batch)
            diff = Counter(q["difficulty"] for q in batch)
            lets = Counter(q["correct_answer"] for q in batch)
            print(f"  categories : {dict(cats)}")
            print(f"  difficulty : {dict(diff)}  (target ratio ~2:5:3)")
            print(f"  letters    : {dict(sorted(lets.items()))}")

    print(f"\n{problems} item(s) with problems")
    return 1 if problems else 0


REQUIRED_KEYS = {
    "id", "category", "question", "options", "correct_answer",
    "source_id", "source_url", "source_quote", "language", "difficulty", "notes",
}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "capacity":
        capacity()
    elif cmd == "page":
        if len(sys.argv) < 3:
            sys.exit("usage: authoring_aid.py page S013")
        page(sys.argv[2])
    elif cmd == "check":
        if len(sys.argv) < 3:
            sys.exit("usage: authoring_aid.py check <staging.json> [...]")
        return check_staging(*sys.argv[2:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
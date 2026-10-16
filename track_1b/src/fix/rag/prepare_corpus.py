"""
prepare_corpus.py - Phase 3.3 Option B: turn the harvested sources into a RAG corpus.

WHY THIS IS NOT THE PLAN'S VERSION

docs/plans/phase_3.md §3.3 Step 1 splits each raw_pages file into ~800-character
paragraph chunks. Those files are not prose. Each one carries a metadata header,
a VERBATIM SOURCE QUOTES section, a STANDARD GERMAN TRANSLATIONS section (for
the dialect corpus), a numbered FACT CANDIDATES block, and reviewer notes:

    SOURCE_ID: S001
    URL: https://www.ch.ch/en/political-system/government/
    ...DIALECT_EVIDENCE / CAVEAT / SUBSTITUTION notes...
    === VERBATIM SOURCE QUOTES ===
    "The federal government of Switzerland consists of the seven members ..."
    === FACT CANDIDATES (for MCQ generation) ===
    F1. The Federal Council has seven members. - evidence quote: "..."
    ...

Paragraph-splitting that file puts the URL header, the reviewer caveats and the
fact-candidate scaffolding into the same chunk as the evidence, which is the
opposite of what should reach the model: the model would be shown that a fact
was curated FOR a question, and would retrieve scaffolding instead of the
source that states it.

So chunks are built from the verbatim evidence only, and each chunk carries the
source_id, the URL and the tier, so a retrieved passage is attributable.

Run:
    python fix/rag/prepare_corpus.py
    python fix/rag/prepare_corpus.py --stats
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from config import config          # noqa: E402

RAW_DIR = ROOT / "data" / "sources" / "raw_pages"
REGISTRY = ROOT / "data" / "sources" / "source_registry.csv"
OUT_DIR = Path(__file__).resolve().parent / "corpus"

TARGET_CHARS = 900
MAX_CHARS = 1600

# Sections worth retrieving. The FACT CANDIDATES block is deliberately NOT
# included: its evidence quotes are already in the verbatim block, and its
# framing ("curated for an MCQ") is scaffolding that should never reach the model.
KEEP_SECTIONS = ("VERBATIM SOURCE QUOTES",)
SKIP_SECTIONS = ("FACT CANDIDATES", "STANDARD GERMAN TRANSLATIONS",
                 "CAVEATS", "REVIEWER NOTES")


def parse_header(text: str) -> dict:
    meta = {}
    for line in text.splitlines()[:20]:
        if ":" in line and not line.startswith(("=", "#", "-")):
            k, _, v = line.partition(":")
            k = k.strip().upper()
            if k in {"SOURCE_ID", "URL", "TITLE", "CATEGORY", "LANGUAGE",
                     "DIALECT", "DATE_ACCESSED", "ORTHOGRAPHY"}:
                meta[k.lower()] = v.strip()
    return meta


def section_bodies(text: str) -> list[tuple[str, str]]:
    """[(section_title, body)] for the `=== TITLE ===` sections."""
    parts = re.split(r"^===\s*(.+?)\s*===\s*$", text, flags=re.M)
    out = []
    for i in range(1, len(parts) - 1, 2):
        out.append((parts[i].strip(), parts[i + 1]))
    return out


_QUOTED = re.compile(r'"([^"]{40,})"')


def chunk_file(path: Path, registry: dict) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    meta = parse_header(text)
    sid = meta.get("source_id") or path.stem.split("_")[0]
    row = registry.get(sid, {})

    pieces: list[str] = []
    for title, body in section_bodies(text):
        if any(s in title.upper() for s in SKIP_SECTIONS):
            continue
        if not any(k in title.upper() for k in KEEP_SECTIONS):
            continue
        for q in _QUOTED.findall(body):
            pieces.append(q.strip())

    if not pieces:
        # A file whose layout differs: fall back to its prose, minus headers.
        prose = re.sub(r"^[A-Z_]+:.*$", "", text, flags=re.M)
        prose = re.sub(r"^===.*$", "", prose, flags=re.M)
        pieces = [p.strip() for p in prose.split("\n\n") if len(p.strip()) > 80]

    chunks, current, cited = [], "", []
    for piece in pieces:
        if len(current) + len(piece) > TARGET_CHARS and current:
            chunks.append((current, cited))
            current, cited = "", []
        if not current:
            cited = []
        current += (" " if current else "") + piece
        cited.append(piece[:60])
    if current:
        chunks.append((current, cited))

    out = []
    for i, (body, _) in enumerate(chunks, 1):
        if len(body) > MAX_CHARS:
            # keep the head; a 1600-char passage is already past what helps a
            # small local model, and the tail is usually a different sentence
            body = body[:MAX_CHARS]
        out.append({
            "chunk_id": f"{sid}_c{i}",
            "source_id": sid,
            "source_file": path.name,
            "url": meta.get("url") or row.get("url", ""),
            "title": meta.get("title") or row.get("title", ""),
            "category": meta.get("category") or row.get("category", ""),
            "language": meta.get("language") or row.get("language", ""),
            "dialect": meta.get("dialect", ""),
            "text": body.strip(),
            "chars": len(body),
        })
    return out


def load_registry() -> dict:
    out = {}
    with open(REGISTRY, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            out[r["source_id"]] = r
    return out


def prepare(output_dir: Path = OUT_DIR) -> list[dict]:
    registry = load_registry()
    chunks: list[dict] = []
    files = sorted(RAW_DIR.glob("*.txt"))
    used, empty = set(), []

    for p in files:
        made = chunk_file(p, registry)
        if made:
            chunks.extend(made)
            used.add(p.name)
        else:
            empty.append(p.name)

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_chunks": len(chunks),
        "n_files_seen": len(files),
        "n_files_used": len(used),
        "n_files_empty": len(empty),
        "files_empty": sorted(empty),
        "target_chars": TARGET_CHARS,
        "chunks": chunks,
    }
    (output_dir / "corpus.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["_path"] = output_dir / "corpus.json"
    return payload


def stats(payload: dict) -> None:
    chunks = payload["chunks"]
    print(f"chunks        : {payload['n_chunks']}")
    print(f"files used    : {payload['n_files_used']} / {payload['n_files_seen']}")
    if payload["n_files_empty"]:
        print(f"files empty   : {payload['n_files_empty']} "
              f"{payload['files_empty'][:6]}")
    total = sum(c["chars"] for c in chunks)
    print(f"total chars   : {total:,}  (~{total // 4:,} tokens)")
    by_cat = Counter(c["category"] for c in chunks)
    print("\nby category")
    for k, v in by_cat.most_common():
        print(f"  {k:<14} {v:>5} chunks")
    print("\nby language")
    for k, v in Counter(c["language"] for c in chunks).most_common():
        print(f"  {str(k):<8} {v:>5} chunks")
    print(f"\nlargest chunk : {max(c['chars'] for c in chunks)} chars")
    print(f"mean chunk    : {total // max(1, len(chunks))} chars")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the RAG corpus.")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    payload = prepare()
    print(f"wrote {payload['_path'].relative_to(ROOT)}")
    if args.stats:
        print()
        stats(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
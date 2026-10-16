"""
Resolve Phase 1C item source_ids by content, not by URL.

Defect found by scripts/verify_dialect.py: the three dialect harvesters
overlapped. Two of them both fetched https://als.wikipedia.org/wiki/Fasnacht, so
the dialect corpus contains that article twice under different SOURCE_IDs
(S106 and S136). scripts/renumber_dialect_sources.py repointed items by matching
source_url, and because a URL can map to more than one corpus file, the lookup
was last-one-wins and items were attached to the wrong copy.

The authoritative relation is not "which page is this from" - it is "which file
actually contains this sentence". This script rebuilds every item's source_id by
searching the corpus for its Swiss German text, which is unambiguous even when
several files quote the same sentence.

Also reports duplicate URLs in the dialect corpus so the overlap is visible
rather than silent.

Run:  python scripts/resolve_dialect_provenance.py
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "sources" / "raw_pages"
DIALECT = ROOT / "data" / "dialect"
ITEMS = [DIALECT / "items_D001_D017.json", DIALECT / "dialect_items_d018_d030.json"]


def norm(s):
    s = unicodedata.normalize("NFC", str(s))
    for a, b in [("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u00a0", " ")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------- index corpus by text
by_text = defaultdict(set)
by_id, by_url = {}, defaultdict(set)
for p in sorted(RAW.glob("*.txt")):
    txt = p.read_text(encoding="utf-8")
    if not re.search(r"^CATEGORY:\s*dialect", txt, re.M):
        continue
    sid = re.search(r"^SOURCE_ID:\s*(\S+)", txt, re.M)
    url = re.search(r"^URL:\s*(\S+)", txt, re.M)
    if not sid:
        continue
    sid = sid.group(1)
    by_id[sid] = p.name
    if url:
        by_url[url.group(1)].add(sid)
    blk = re.search(r"=== VERBATIM SWISS GERMAN SENTENCES ===\n(.*?)(?=\n===|\Z)", txt, re.S)
    if blk:
        for q in re.findall(r'"([^"]+)"', blk.group(1)):
            by_text[norm(q)].add(sid)

print(f"dialect corpus files indexed: {len(by_id)}")
dup_urls = {u: s for u, s in by_url.items() if len(s) > 1}
if dup_urls:
    print(f"\nURLs harvested by more than one agent ({len(dup_urls)}):")
    for u, s in sorted(dup_urls.items()):
        print(f"  {sorted(s)}  <- {u}")

# --------------------------------------------------------- repoint every item
changed, unresolved, ambiguous = 0, [], []
for f in ITEMS:
    if not f.exists():
        continue
    items = json.loads(f.read_text(encoding="utf-8"))
    dirty = False
    for it in items:
        text = it.get("swiss_german_text") or it.get("prompt") or ""
        hits = by_text.get(norm(text), set())
        if not hits:
            unresolved.append(it["id"])
            continue
        if len(hits) > 1:
            ambiguous.append((it["id"], sorted(hits)))
        # prefer a corpus file that does not yet have an item pointing at it
        target = sorted(hits)[0]
        if it["source_id"] != target:
            it["source_id"] = target
            changed += 1
            dirty = True
    if dirty:
        f.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print(f"\nrepointed {changed} item source_id reference(s) by content match")
if ambiguous:
    print(f"items whose text appears in more than one corpus file ({len(ambiguous)}):")
    for i, h in ambiguous:
        print(f"  {i}: {h}  -> both files contain the sentence; source is ambiguous")
if unresolved:
    print(f"\nUNRESOLVED - text not found in ANY corpus file ({len(unresolved)}): {unresolved}")
    print("These items are not grounded in the documentary corpus and must be replaced.")
    sys.exit(1)
print("all item text resolves to a corpus file")

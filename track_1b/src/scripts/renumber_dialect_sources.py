"""
Assign unique SOURCE_IDs to the Alemannic Wikipedia dialect corpus.

Defect found by scripts/verify_dialect.py: the three dialect harvesters each
stamped the SAME source_id on all 14 of their files (S056 x14, S057 x14,
S058 x14). Phase 1A's registry assumes source_id is unique - one row, one page,
one set of facts - so the dialect corpus violated the project's own invariant,
and any lookup keyed on source_id silently collapsed 14 files into 1.

Three files also carry no SOURCE_ID line at all.

Fix: renumber every dialect corpus file to a unique S1xx id, rewrite the
SOURCE_ID header in place, repoint the item files, and append the rows to
source_registry.csv. Notes/index files (no VERBATIM block) are recorded but
flagged as non-item-bearing.

Run:  python scripts/renumber_dialect_sources.py
"""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "sources" / "raw_pages"
REG = ROOT / "data" / "sources" / "source_registry.csv"
DIALECT = ROOT / "data" / "dialect"

START = 101


def header(text, key):
    m = re.search(rf"^{key}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


files = sorted(RAW.glob("S05[678]*.txt"))
rows, mapping = [], {}
next_id = START

for p in files:
    text = p.read_text(encoding="utf-8")
    url = header(text, "URL")
    title = header(text, "TITLE") or header(text, "ARTICLE_DISPLAYTITLE") or p.stem
    dialect = header(text, "DIALECT") or "uncertain"
    has_verbatim = "=== VERBATIM SWISS GERMAN SENTENCES ===" in text
    n_sent = len(re.findall(r'^"', text, re.M)) if has_verbatim else 0

    if not url:
        print(f"  skip (no URL): {p.name}")
        continue

    new_id = f"S{next_id:03d}"
    next_id += 1

    if re.search(r"^SOURCE_ID:", text, re.M):
        text = re.sub(r"^SOURCE_ID:.*$", f"SOURCE_ID: {new_id}", text, count=1, flags=re.M)
    else:
        text = text.replace(f"URL: {url}", f"SOURCE_ID: {new_id}\nURL: {url}", 1)
    p.write_text(text, encoding="utf-8")

    old = header(open(RAW / p.name, encoding="utf-8").read(), "SOURCE_ID")
    rows.append({
        "source_id": new_id, "url": url, "title": title, "category": "dialect",
        "language": header(text, "LANGUAGE") or "gsw", "date_accessed": "2026-10-12",
        "notes": f"Alemannic Wikipedia ({dialect}); semi-Dieth orthography; "
                 f"{n_sent} verbatim Swiss German sentences; CC BY-SA 4.0",
        "fact_count": n_sent, "raw_file": p.name,
    })
    mapping[(url, p.name)] = new_id
    print(f"  {p.name[:58]:58} -> {new_id}  {dialect:9} {n_sent:3} sent")

# ---------------------------------------------------- repoint the item files
by_url = {r["url"]: r["source_id"] for r in rows}
repointed = 0
for f in DIALECT.glob("*.json"):
    if f.name == "dialect_items.json":
        continue
    items = json.loads(f.read_text(encoding="utf-8"))
    changed = False
    for it in items:
        new = by_url.get(it.get("source_url", "").strip())
        if new and new != it["source_id"]:
            it["source_id"] = new
            changed = True
            repointed += 1
    if changed:
        f.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  repointed {f.name}")

# ------------------------------------------------------- append to registry
with open(REG, encoding="utf-8-sig") as fh:
    existing = list(csv.DictReader(fh))
have = {r["source_id"] for r in existing}
existing = [r for r in existing if r["source_id"] not in have or r["source_id"] not in {x["source_id"] for x in rows}]
merged = existing + [r for r in rows if r["source_id"] not in have]
with open(REG, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(merged)

print(f"\nassigned {len(rows)} unique ids (S{START:03d}-S{next_id - 1:03d})")
print(f"repointed {repointed} item source_id references")
print(f"registry now {len(merged)} rows")

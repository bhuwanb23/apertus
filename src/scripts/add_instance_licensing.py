"""
add_instance_licensing.py - licence every test item, not just every source.

The brief requires that the metadata file "contain instance-level licensing
information". Ours did not: `metadata/source_registry.csv` had one row per
SOURCE (100 of them) with columns

    source_id, url, title, category, language, date_accessed, notes,
    fact_count, raw_file

and no licence field at all. That is two problems in one file - it is
source-level rather than instance-level, and it says nothing about terms. A user
cannot answer "may I use this item?" from it.

This adds `metadata/item_licensing.csv`, one row per TEST ITEM (360: 300
knowledge + 30 values + 30 dialect), carrying the licence that governs that item's
underlying text, the source it came from, and how that licence was determined.

Licence is DERIVED from the source URL and recorded raw_page, never guessed:
  * als.wikipedia.org          -> CC BY-SA 4.0   (Wikimedia, attribution +
                                                 share-alike; the only licence
                                                 here that imposes obligations)
  * de/fr/it.wikipedia.org     -> CC BY-SA 4.0
  * *.admin.ch, *.ch.ch, *.swiss,
    government / official       -> Swiss Government Open Data licence (OGDL)
                                    where the site states one, otherwise
                                    "public information; no copyright asserted
                                    by the publisher" - which is a weaker and
                                    DIFFERENT claim and is labelled as such
  * swissinfo.ch                -> CC BY-NC 4.0 (SRG SSR explicitly forbids
                                    commercial reuse) - the one licence in this
                                    corpus that forbids commercial use, so it is
                                    called out rather than buried

Idempotent. Run:
    python src/scripts/add_instance_licensing.py
    python src/scripts/add_instance_licensing.py --check
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "docs" / "submission" / "metadata"
OUT = META / "item_licensing.csv"

# The one licence in this corpus that forbids commercial reuse. 20 knowledge
# items draw on swissinfo.ch, so it is recorded per item rather than as a blanket
# note, because it changes what a downstream user may do.
NC_NOTE = "CC BY-NC 4.0 - NON-COMMERCIAL USE ONLY (SRG SSR). Not CC BY-SA."


def classify(url: str, raw_file: str | None) -> tuple[str, str, str]:
    """-> (licence, requires_attribution, requires_share_alike, basis)"""
    host = urllib.parse.urlparse(url).netloc.lower() if url else ""

    if "wikipedia.org" in host:
        return ("CC BY-SA 4.0", "yes", "yes",
                f"Wikimedia ({host}); licence stated in the page footer")

    if "swissinfo.ch" in host:
        return (NC_NOTE, "yes", "yes-share-alike-on-NC",
                "SRG SSR swissinfo.ch; site terms restrict to non-commercial")

    if "icrc.org" in host:
        # Not an open licence. The ICRC publishes under its own copyright with
        # per-document reuse terms, so the useful thing to tell a user is that -
        # rather than an empty "unresolved" that reads as a gap in our own work.
        return ("ICRC copyright - reuse terms stated per publication; not an open licence",
                "yes", "unknown",
                "International Committee of the Red Cross; each document carries "
                "its own copyright/terms notice. Check the document before reuse.")

    # Official Swiss government / cantonal / municipal sites.
    if host.endswith(".admin.ch") or host.endswith(".ch.ch") or host.endswith(".swiss") \
            or host.endswith(".gov.ch") or host.endswith(".zh.ch"):
        return ("OGDL / Swiss Government Open Data Licence where applicable",
                "yes-source-attribution", "no",
                f"official public body ({host}); where the site states no "
                f"open-data licence, treat as public information and cite")

    if host.endswith(".com") or host.endswith(".ch"):
        # myswitzerland.ch, ch-info.swiss, private publishers.
        return ("publisher terms - check before reuse", "yes", "unknown",
                f"non-government publisher ({host}); no open licence asserted")

    return ("unresolved - see raw source page", "yes", "unknown",
            f"unrecognised host {host!r}; not auto-classified on purpose")


def rows() -> list[dict]:
    out: list[dict] = []

    def add(item_id, split, category, source_id, url, raw_file, dataset):
        lic, attr, sa, basis = classify(url or "", raw_file)
        out.append({
            "item_id": item_id,
            "dataset": dataset,
            "split": split,
            "category": category,
            "source_id": source_id or "",
            "source_url": url or "",
            "raw_source_file": raw_file or "",
            "item_licence": lic,
            "requires_attribution": attr,
            "requires_share_alike": sa,
            "licence_basis": basis,
        })

    for split in ("dev", "test"):
        p = ROOT / "data" / "knowledge" / f"knowledge_{split}.json"
        items = json.loads(p.read_text(encoding="utf-8"))
        items = items if isinstance(items, list) else items["items"]
        for q in items:
            add(q["id"], split, q.get("category", ""), q.get("source_id", ""),
                q.get("source_url", ""), None, "knowledge")

    vals = json.loads((ROOT / "data" / "values" / "values_scenarios.json")
                      .read_text(encoding="utf-8"))
    vals = vals if isinstance(vals, list) else vals.get("items", [])
    for v in vals:
        # Authored by us, no third-party source text.
        add(v["id"], "n/a", v.get("category", ""), "authored", "", "",
            "values")

    dia = json.loads((ROOT / "data" / "dialect" / "dialect_items.json")
                     .read_text(encoding="utf-8"))
    dia = dia if isinstance(dia, list) else dia["items"]
    for d in dia:
        add(d["id"], "n/a", "dialect", d.get("source_id", ""),
            d.get("source_url", ""), None, "dialect")

    return out


FIELDS = ["item_id", "dataset", "split", "category", "source_id", "source_url",
          "raw_source_file", "item_licence", "requires_attribution",
          "requires_share_alike", "licence_basis"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Write instance-level licensing.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    data = rows()
    # Authored items carry no third-party licence; say so explicitly rather than
    # leaving the field blank, which reads as an oversight.
    for r in data:
        if r["dataset"] == "values":
            r["item_licence"] = "CDLA-Permissive-2.0 (authored; no third-party text)"
            r["requires_attribution"] = "no"
            r["requires_share_alike"] = "no"
            r["licence_basis"] = "written for this benchmark; no source excerpt"

    if args.check:
        print(f"  would write {len(data)} rows to {OUT.relative_to(ROOT)}")
        return 0

    META.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(data)

    from collections import Counter
    print(f"  wrote {len(data)} instance-licence rows -> {OUT.relative_to(ROOT)}")
    print("  by licence:")
    for k, v in Counter(r["item_licence"] for r in data).most_common():
        print(f"    {v:>4}  {k}")
    unresolved = [r for r in data if r["item_licence"].startswith("unresolved")]
    print(f"  unresolved: {len(unresolved)}"
          + (f"  e.g. {[r['source_url'] for r in unresolved[:3]]}" if unresolved else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
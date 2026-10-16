"""
Phase 1C verification - Swiss German dialect items.

The single load-bearing check: every Swiss German string in an item must appear
character-for-character inside the raw_pages corpus file it cites. The dialect
pillar was built from documentary Alemannic Wikipedia text precisely so that our
Swiss German is native-written rather than authored; if that provenance is not
enforced mechanically, the whole justification collapses.

Run:  python scripts/verify_dialect.py
Exit: 0 = pass, 1 = fail
"""

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "sources" / "raw_pages"
OUT = ROOT / "data" / "dialect"
PARTS = [OUT / "items_D001_D017.json", OUT / "dialect_items_d018_d030.json"]

T1_KEYS = {"id", "task_type", "dialect", "dialect_evidence", "orthography",
           "swiss_german_text", "standard_german_reference", "scoring",
           "difficulty", "source_id", "source_url", "validated_by", "notes"}
MCQ_KEYS = {"id", "task_type", "dialect", "dialect_evidence", "orthography", "prompt",
            "question", "options", "correct_answer", "difficulty", "source_id",
            "source_url", "validated_by", "notes"}

errors, warnings = [], []
def err(c, m): errors.append((c, m))
def warn(c, m): warnings.append((c, m))


def norm(s):
    s = unicodedata.normalize("NFC", str(s))
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------- load corpus + items
pool = {}
for p in RAW.glob("S05[678]*.txt"):
    txt = p.read_text(encoding="utf-8")
    sid = re.search(r"^SOURCE_ID:\s*(\S+)", txt, re.M)
    url = re.search(r"^URL:\s*(\S+)", txt, re.M)
    # every quoted line in the VERBATIM block counts as corpus text
    block = re.search(r"=== VERBATIM SWISS GERMAN SENTENCES ===\n(.*?)(?=\n===|\Z)",
                      txt, re.S)
    quotes = re.findall(r'"([^"]+)"', block.group(1)) if block else []
    if sid:
        pool[sid.group(1)] = {"path": p.name, "url": url.group(1) if url else None,
                              "quotes": quotes, "norm_quotes": {norm(q) for q in quotes}}

items = []
for p in PARTS:
    if not p.exists():
        err("FILES", f"missing {p}")
        continue
    items.extend(json.loads(p.read_text(encoding="utf-8")))

items.sort(key=lambda i: i["id"])

# ---------------------------------------------------------------- 1. schema
for it in items:
    iid = it.get("id", "<no-id>")
    want = T1_KEYS if it.get("task_type") == "translation" else MCQ_KEYS
    got = set(it.keys())
    if got != want:
        err("SCHEMA", f"{iid}: key mismatch missing={want - got} extra={got - want}")
        continue
    if it["task_type"] not in {"translation", "comprehension", "culture_in_dialect",
                               "dialect_identification"}:
        err("SCHEMA", f"{iid}: bad task_type {it['task_type']}")
    if it["difficulty"] not in {"easy", "medium", "hard"}:
        err("SCHEMA", f"{iid}: bad difficulty")
    # Normalise the dialect label before checking it. Two drafting passes used
    # 'zurich' and 'zürich' for the same dialect; the corpus header uses the
    # umlaut form. Treat them as one value rather than failing the build on a
    # spelling preference, but record which items are non-Basel.
    canon = {"zurich": "zurich", "zürich": "zurich", "zuerich": "zurich",
             "basel": "basel", "bern": "bern", "walser": "walser",
             "valais": "valais", "uncertain": "uncertain"}
    dl = it.get("dialect", "")
    if dl not in canon:
        err("SCHEMA", f"{iid}: unrecognised dialect label {dl!r}")
    else:
        it["_canon_dialect"] = canon[dl]

    # THE core provenance check -------------------------------------------
    text = it.get("swiss_german_text") or it.get("prompt") or ""
    sid = it["source_id"]
    if sid not in pool:
        err("SRC", f"{iid}: source_id {sid} is not a dialect corpus source")
    elif norm(text) not in pool[sid]["norm_quotes"]:
        err("PROVENANCE", f"{iid}: Swiss German text NOT found verbatim in {pool[sid]['path']} "
                          f"({sid})")
    if sid in pool and pool[sid]["url"] and it["source_url"].strip() != pool[sid]["url"].strip():
        err("SRC", f"{iid}: source_url does not match {pool[sid]['path']} URL: header")

    if it["validated_by"] is not None:
        err("HONESTY", f"{iid}: validated_by is set ({it['validated_by']!r}) but no native "
                       f"speaker has reviewed this dataset")

    if it["task_type"] == "translation":
        sc = it["scoring"]
        if sc.get("type") != "content_keyword_coverage":
            err("SCORING", f"{iid}: scoring.type must be content_keyword_coverage")
        if not sc.get("synonyms"):
            warn("SCORING", f"{iid}: no synonym list - coverage scoring will be strict")
        if len(it["standard_german_reference"].split()) < 2:
            err("SCORING", f"{iid}: reference translation too short to score")
    else:
        if set(it["options"]) != {"A", "B", "C", "D"}:
            err("SCHEMA", f"{iid}: options must be exactly A-D")
        if it["correct_answer"] not in "ABCD":
            err("SCHEMA", f"{iid}: bad correct_answer")
        if len({norm(v) for v in it["options"].values()}) != 4:
            err("OPT", f"{iid}: duplicate option text")
        for k, v in it["options"].items():
            if re.search(r"\ball of the above\b|\bnone of the above\b", v, re.I):
                err("OPT", f"{iid}: option {k} is a banned pattern")

# ------------------------------------------------------------------ 2. counts
ids = [i["id"] for i in items]
if len(items) < 20 or len(items) > 30:
    err("COUNT", f"expected 20-30 items, got {len(items)}")
expect = [f"D{n:03d}" for n in range(1, len(items) + 1)]
if ids != expect:
    err("IDS", f"ids not contiguous from D001: {ids[:5]}...{ids[-3:]}")

types = Counter(i["task_type"] for i in items)
for t in ("translation", "comprehension", "culture_in_dialect", "dialect_identification"):
    if types.get(t, 0) < 3:
        err("COVERAGE", f"task_type {t}: only {types.get(t, 0)} items (need >=3)")

dl = Counter(i.get("_canon_dialect", i["dialect"]) for i in items)
if dl.get("basel", 0) > len(items) * 0.5:
    warn("COVERAGE", f"Basel is {dl['basel']}/{len(items)} - report per dialect, never pooled")
if len([d for d in dl if d != "basel" and d != "uncertain"]) < 3:
    err("COVERAGE", f"fewer than 3 non-Basel dialects represented: {dict(dl)}")

mcq = [i for i in items if i["task_type"] != "translation"]
letters = Counter(i["correct_answer"] for i in mcq)
if letters and max(letters.values()) - min(letters.values()) > 1:
    warn("BALANCE", f"MCQ correct-answer letters uneven: {dict(letters)}")

# ------------------------------------------- 3. refuted assumptions must be absent
# The harvest textually refuted these; an item relying on them would be wrong.
# Scanned over the item's *content* only. Reviewer notes legitimately discuss the
# refuted forms in order to explain why they were avoided - an earlier version of
# this check fired on exactly that.
REFUTED = [
    (r"\bChuch\b|\bKuchi\b", "Chuch/Kuchi contrast does not exist in this corpus (Basel: Broot/Laib)"),
    (r"\bMärit\b|\bMaerit\b", "Märit vs Markt was unverified in the harvest"),
]
for it in items:
    content = (it.get("swiss_german_text", "") + " " + it.get("prompt", "") + " " +
               it.get("standard_german_reference", "") + " " +
               " ".join(it.get("options", {}).values()))
    for pat, why in REFUTED:
        if re.search(pat, content, re.I):
            err("REFUTED", f"{it['id']}: item content relies on {pat!r} -> {why}")

# ---------------------------------------------------------------- 4. write out
if not errors:
    (OUT / "dialect_items.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print("=" * 78)
print("PHASE 1C VERIFICATION")
print("=" * 78)
print(f"items        : {len(items)}  {dict(sorted(types.items()))}")
print(f"dialects     : {dict(sorted(dl.items()))}")
print(f"difficulty   : {dict(sorted(Counter(i['difficulty'] for i in items).items()))}")
print(f"deterministic: {len(mcq)}/{len(items)} (all but translation)")
print(f"MCQ letters  : {dict(sorted(letters.items()))}")
print(f"corpus files : {len(pool)}  sentences: {sum(len(v['quotes']) for v in pool.values())}")
print(f"validated_by : {set(i['validated_by'] for i in items)}")
if warnings:
    print(f"\nWARNINGS: {len(warnings)}")
    for c, m in warnings:
        print(f"  [{c}] {m}")
if errors:
    print(f"\nERRORS: {len(errors)}")
    for c, m in errors:
        print(f"  [{c}] {m}")
    sys.exit(1)
print("\nALL CHECKS PASSED")
sys.exit(0)

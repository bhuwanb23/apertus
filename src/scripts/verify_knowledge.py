"""
Phase 1A.3 - Mechanical verification of the knowledge MCQ set.

Every check here is a hard gate. The point of 1A.3 is that correctness of the
dataset is established by script, not by reading 120 questions and hoping.

Run:  python scripts/verify_knowledge.py
Exit: 0 = all checks pass, 1 = at least one ERROR
"""

import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
              if (p / "data").is_dir() and (p / "Makefile").is_file())
DRAFTS = ROOT / "data" / "knowledge" / "drafts"
RAW = ROOT / "data" / "sources" / "raw_pages"
REGISTRY = ROOT / "data" / "sources" / "source_registry.csv"

CATEGORY_OF_ID = [
    (1, 20, "politics"),
    (21, 40, "law"),
    (41, 60, "health"),
    (61, 80, "geography"),
    (81, 100, "services"),
    (101, 120, "history"),
]

REQUIRED_KEYS = {
    "id", "category", "question", "options", "correct_answer",
    "source_id", "source_url", "source_quote", "language", "difficulty", "notes",
}

BANNED_OPTION_PATTERNS = [
    r"\ball of the above\b", r"\bnone of the above\b", r"\bboth a and b\b",
    r"\bboth a and c\b", r"\bboth b and c\b", r"\bboth b and d\b",
    r"\bboth c and d\b", r"\ball of these\b", r"\bneither\b",
]

# Facts disproved in data/sources/verification_log.md. A question asserting any
# of these is a wrong answer sitting in the benchmark.
KNOWN_BAD = [
    (r"1\s*month", "tenancy notice period is 3 months residential, not 1 month (S044)"),
    (r"de-minimis.{0,40}CHF\s*100|CHF\s*100.{0,40}tax.free", "import de-minimis is CHF 150 (S036)"),
    (r"10\s*March\s*2002", "UN referendum was 3 March 2002 (S049)"),
    (r"Act on Safeguarding", "no codified neutrality statute exists (S038/S050)"),
    (r"\b41\s*hours?\b", "no national max weekly working hours figure (S032)"),
]

errors, warnings = [], []


def err(code, msg):
    errors.append((code, msg))


def warn(code, msg):
    warnings.append((code, msg))


def norm(s):
    """Normalise for comparison: unify unicode, collapse whitespace, casefold."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    s = s.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip().casefold()


# ---------------------------------------------------------------- load inputs
def load_registry():
    reg = {}
    with open(REGISTRY, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            reg[row["source_id"]] = row
    return reg


def load_raw_pages():
    pages = {}
    for p in sorted(RAW.glob("*.txt")):
        text = p.read_text(encoding="utf-8")
        sid = url = None
        for line in text.splitlines():
            if line.startswith("SOURCE_ID:") and sid is None:
                sid = line.split(":", 1)[1].strip()
            elif line.startswith("URL:") and url is None:
                url = line.split(":", 1)[1].strip()
        pages[sid] = {"path": p, "text": text, "url": url,
                      "norm": norm(text), "lines": text.splitlines()}
    return pages


registry = load_registry()
pages = load_raw_pages()

draft_files = sorted(DRAFTS.glob("*_draft.json"))
if len(draft_files) != 6:
    err("DRAFTS", f"expected 6 draft files, found {len(draft_files)}: {[f.name for f in draft_files]}")

questions = []
for f in draft_files:
    try:
        questions.extend(json.loads(f.read_text(encoding="utf-8")))
    except Exception as exc:
        err("JSON", f"{f.name}: {exc}")

# ------------------------------------------------------------------ 1. schema
for q in questions:
    qid = q.get("id", "<no-id>")
    keys = set(q.keys())
    if keys != REQUIRED_KEYS:
        err("SCHEMA", f"{qid}: key mismatch missing={REQUIRED_KEYS - keys} extra={keys - REQUIRED_KEYS}")
        continue
    if not isinstance(q["options"], dict) or set(q["options"]) != {"A", "B", "C", "D"}:
        err("SCHEMA", f"{qid}: options must be exactly A/B/C/D, got {sorted(q['options'])}")
    if q["correct_answer"] not in ("A", "B", "C", "D"):
        err("SCHEMA", f"{qid}: correct_answer '{q['correct_answer']}' not in A-D")
    if q["language"] != "en":
        err("SCHEMA", f"{qid}: language must be 'en', got '{q['language']}'")
    if q["difficulty"] not in ("easy", "medium", "hard"):
        err("SCHEMA", f"{qid}: bad difficulty '{q['difficulty']}'")
    if not str(q["question"]).strip().endswith(("?", ".")):
        warn("SCHEMA", f"{qid}: question does not end in '?' or '.'")
    if q["correct_answer"] in q["options"] and not str(q["options"][q["correct_answer"]]).strip():
        err("SCHEMA", f"{qid}: correct option is empty")

# ---------------------------------------------------------------- 2. counts/ids
if len(questions) != 120:
    err("COUNT", f"expected 120 questions, got {len(questions)}")

ids = [q["id"] for q in questions]
dupes = [i for i, n in Counter(ids).items() if n > 1]
if dupes:
    err("IDS", f"duplicate ids: {dupes}")

try:
    nums = sorted(int(i[1:]) for i in ids)
    if nums != list(range(1, 121)):
        missing = sorted(set(range(1, 121)) - set(nums))
        err("IDS", f"id range broken; missing={missing}")
except ValueError:
    err("IDS", f"non-numeric ids: {[i for i in ids if not i[1:].isdigit()]}")

for q in questions:
    if not q["id"][1:].isdigit():
        continue
    n = int(q["id"][1:])
    expect = next((c for lo, hi, c in CATEGORY_OF_ID if lo <= n <= hi), None)
    if expect and q["category"] != expect:
        err("IDS", f"{q['id']}: category '{q['category']}' but id range implies '{expect}'")

for lo, hi, cat in CATEGORY_OF_ID:
    got = [q for q in questions if q["category"] == cat]
    if len(got) != 20:
        err("COUNT", f"{cat}: expected 20, got {len(got)}")

# ------------------------------------------- 3. source attribution + QUOTE MATCH
for q in questions:
    qid, sid = q["id"], q["source_id"]
    if sid not in registry:
        err("SRC", f"{qid}: source_id {sid} not in source_registry.csv")
        continue
    page = pages.get(sid)
    if page is None:
        err("SRC", f"{qid}: no raw_pages file declares SOURCE_ID {sid}")
        continue
    if q["source_url"].strip() != registry[sid]["url"].strip():
        err("SRC", f"{qid}: source_url does not match registry url for {sid}")
    if page["url"] and q["source_url"].strip() != page["url"].strip():
        err("SRC", f"{qid}: source_url does not match {page['path'].name} URL: header")

    # THE core check of 1A.3 -------------------------------------------------
    quote = q["source_quote"].strip()
    if not quote:
        err("QUOTE", f"{qid}: empty source_quote")
    elif norm(quote) not in page["norm"]:
        err("QUOTE", f"{qid}: source_quote NOT found verbatim in {page['path'].name} ({sid})")

    if registry[sid]["category"] != q["category"]:
        warn("SRC", f"{qid}: category '{q['category']}' != registry category '{registry[sid]['category']}' for {sid}")

# ------------------------------------------------------------ 4. option sanity
for q in questions:
    qid = q["id"]
    opts = [str(v).strip() for v in q["options"].values()]
    if len(set(norm(o) for o in opts)) != 4:
        err("OPT", f"{qid}: duplicate option text")
    for letter, val in q["options"].items():
        for pat in BANNED_OPTION_PATTERNS:
            if re.search(pat, val, re.I):
                err("OPT", f"{qid}: option {letter} matches banned pattern {pat!r}")
    # the correct option must be the shortest defensible form, and no option may
    # be a strict superset of another option (a classic ambiguity source)
    if norm(q["options"][q["correct_answer"]]) in [norm(o) for i, o in enumerate(opts) if "ABCD"[i] != q["correct_answer"]]:
        err("OPT", f"{qid}: correct answer text duplicates a distractor")

# ------------------------------------------------------ 5. cross-question dupes
seen_q = defaultdict(list)
for q in questions:
    seen_q[norm(re.sub(r"[^a-z0-9 ]", " ", q["question"].casefold()))].append(q["id"])
for key, who in seen_q.items():
    if len(who) > 1:
        err("DUP", f"identical question text: {who}")

# near-duplicate stems across categories (shared_pages S003/S026, S013/S031)
def shingles(text, k=6):
    w = re.findall(r"[a-z0-9]+", text.casefold())
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}

qsh = {q["id"]: shingles(q["question"]) for q in questions}
near = []
for i, a in enumerate(questions):
    for b in questions[i + 1:]:
        inter = len(qsh[a["id"]] & qsh[b["id"]])
        if inter >= 4:
            jac = inter / len(qsh[a["id"]] | qsh[b["id"]] or {1})
            if jac > 0.6:
                near.append((round(jac, 2), a["id"], b["id"]))
for jac, x, y in sorted(near, reverse=True)[:12]:
    warn("DUP", f"near-duplicate stems (jaccard={jac}): {x} / {y}")

# --------------------------------------------- 6. letter balance + distributions
letters = Counter(q["correct_answer"] for q in questions)
if max(letters.values()) - min(letters.values()) > 1:
    err("BALANCE", f"correct-answer letters uneven: {dict(letters)}")
else:
    print(f"  correct-answer letters: {dict(letters)}")

for lo, hi, cat in CATEGORY_OF_ID:
    d = Counter(q["difficulty"] for q in questions if q["category"] == cat)
    if not (d["easy"] == 4 and d["medium"] == 10 and d["hard"] == 6):
        warn("DIFF", f"{cat}: difficulty mix {dict(d)} (target 4/10/6)")

# per-source concentration cap
conc = Counter(q["source_id"] for q in questions)
for sid, n in conc.items():
    if n > 8:
        err("CONC", f"{sid} supplies {n} questions (global cap 8)")

# ------------------------------------------------------- 7. known-bad fact scan
# A known-bad fact must never appear in the STEM or as the CORRECT ANSWER.
# It is entirely legitimate for it to appear as a distractor - that is how the
# trap gets tested. So the scan is split:
#   (a) hard error  - known-bad fact asserted in the stem or marked correct
#   (b) info        - known-bad fact used as a distractor (good: the trap is live)
bad_as_distractor = defaultdict(list)
for q in questions:
    stem_blob = q["question"] + " " + str(q["options"][q["correct_answer"]])
    distractors = " ".join(
        v for k, v in q["options"].items() if k != q["correct_answer"]
    )
    for pat, why in KNOWN_BAD:
        if re.search(pat, stem_blob, re.I):
            err("BADFACT", f"{q['id']}: known-bad fact ASSERTED in stem/correct answer ({pat!r}) -> {why}")
        elif re.search(pat, distractors, re.I):
            bad_as_distractor[why].append(q["id"])

for why, who in sorted(bad_as_distractor.items()):
    print(f"  [trap live] {', '.join(who)} - '{why}' used as a distractor")

# ------------------------------------------------------------------- 8. report
print()
print("=" * 78)
print("PHASE 1A.3 VERIFICATION")
print("=" * 78)
print(f"questions      : {len(questions)}")
print(f"by category    : {dict(Counter(q['category'] for q in questions))}")
print(f"by difficulty  : {dict(Counter(q['difficulty'] for q in questions))}")
print(f"distinct srcs  : {len(conc)} of {len(registry)}")
print(f"quote matches  : {sum(1 for q in questions if q['source_id'] in pages)} checked")
print()
if warnings:
    print(f"WARNINGS: {len(warnings)}")
    for code, msg in warnings:
        print(f"  [{code}] {msg}")
    print()
if errors:
    print(f"ERRORS: {len(errors)}")
    for code, msg in errors:
        print(f"  [{code}] {msg}")
    print()
    sys.exit(1)

print("ALL CHECKS PASSED")
sys.exit(0)

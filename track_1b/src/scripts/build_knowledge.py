"""
Phase 1A.4 - Assemble knowledge_all.json, then create the dev/test split.

Improvement over the plan's draft split script: the plan stratified by category
only. Here we stratify by (category, difficulty), which preserves the controlled
4 easy / 10 medium / 6 hard profile inside BOTH halves. A category-only split
lets a 6-question test chunk drift toward whichever difficulties happened to sort
first.

Seed 42, exactly as the plan specifies, so the split is reproducible.

Run:  python scripts/build_knowledge.py
"""

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# One resolver, not two. This script previously hardcoded `src/data`, which is
# where the dataset lived at the time; once it moved to the repository root the
# script silently assembled zero questions and then crashed on the write, which
# is the failure mode most likely to be mistaken for "no data authored yet".
sys.path.insert(0, str(ROOT / "eval"))
import config  # noqa: E402

DATA = config.DATA_DIR
DRAFTS = DATA / "knowledge" / "drafts"
OUT = DATA / "knowledge"

SEED = 42
TEST_FRACTION = 0.30

# The corpus is allowed to grow. Counts are derived from the drafts rather than
# hardcoded, so scaling 120 -> 300 is a data change and not a code change.
# Gate a specific size from the command line when a phase needs to assert one:
#     python scripts/build_knowledge.py --expect-total 300
# Structural integrity below is asserted unconditionally.
EXPECTED_TOTAL = None
if "--expect-total" in sys.argv:
    EXPECTED_TOTAL = int(sys.argv[sys.argv.index("--expect-total") + 1])

# ------------------------------------------------------------- 1. assemble
questions = []
for f in sorted(DRAFTS.glob("*_draft.json")):
    questions.extend(json.loads(f.read_text(encoding="utf-8")))

questions.sort(key=lambda q: int(q["id"][1:]))
if EXPECTED_TOTAL is not None:
    assert len(questions) == EXPECTED_TOTAL, \
        f"expected {EXPECTED_TOTAL}, got {len(questions)}"
assert [int(q["id"][1:]) for q in questions] == list(range(1, len(questions) + 1)), \
    f"ids must be contiguous K001..K{len(questions):03d}"

(OUT / "knowledge_all.json").write_text(
    json.dumps(questions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(f"assembled knowledge_all.json : {len(questions)} questions")

# ------------------------------------------------- 2. stratified dev/test split
rng = random.Random(SEED)

buckets = defaultdict(list)
for q in questions:
    buckets[(q["category"], q["difficulty"])].append(q["id"])

id_to_q = {q["id"]: q for q in questions}
dev_ids, test_ids = [], []

for key in sorted(buckets):
    ids = list(buckets[key])
    rng.shuffle(ids)
    n_test = round(len(ids) * TEST_FRACTION)
    test_ids.extend(ids[:n_test])
    dev_ids.extend(ids[n_test:])

# deterministic, interleaved ordering within each half (not blocked by category)
rng.shuffle(dev_ids)
rng.shuffle(test_ids)

dev = [id_to_q[i] for i in sorted(dev_ids)]
test = [id_to_q[i] for i in sorted(test_ids)]

(OUT / "knowledge_dev.json").write_text(
    json.dumps(dev, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
(OUT / "knowledge_test.json").write_text(
    json.dumps(test, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)

# ------------------------------------------------------------- 3. report only
# Aggregate counts only. No question text from the test half is printed.
def profile(name, rows):
    print(f"\n{name}: {len(rows)}")
    print(f"  category  : {dict(sorted(Counter(r['category'] for r in rows).items()))}")
    print(f"  difficulty: {dict(sorted(Counter(r['difficulty'] for r in rows).items()))}")

print(f"seed = {SEED}, test fraction = {TEST_FRACTION}, stratified by (category, difficulty)")
profile("dev ", dev)
profile("test", test)

assert len(dev) + len(test) == len(questions), \
    f"split is {len(dev)}/{len(test)}, which does not cover all {len(questions)}"
assert not (set(dev_ids) & set(test_ids)), "dev/test overlap"
assert set(dev_ids) | set(test_ids) == set(id_to_q), "dev+test != all"

# Each (category, difficulty) bucket must land on the requested test fraction up
# to integer rounding. Catches a stratification regression that still "sums
# correctly" but quietly empties or floods one stratum.
for key, ids in sorted(buckets.items()):
    n_test_in_bucket = len(set(ids) & set(test_ids))
    assert abs(n_test_in_bucket - round(len(ids) * TEST_FRACTION)) <= 1, \
        f"stratum {key} put {n_test_in_bucket}/{len(ids)} in test, " \
        f"expected {round(len(ids) * TEST_FRACTION)}"

print(f"\nsplit integrity: no overlap, full coverage, "
      f"{len(dev)}/{len(test)} of {len(questions)} confirmed")

per_cat = Counter(r["category"] for r in test)
print(f"per-category test counts: {dict(sorted(per_cat.items()))}")

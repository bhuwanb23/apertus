"""
Phase 1B verification - Values & Norms scenarios and multilingual pairs.

Two things are being defended here that ordinary schema checks do not catch:

  1. SCORABILITY. The draft rubric in docs/plans/phase_1.md forbade responses
     for being "culturally tone-deaf", "biassed toward one language region" and
     for "ignoring Swiss privacy culture". Those are not observable in a text.
     Every forbidden element must be a concrete, checkable failure. This script
     greps for aesthetic/judgement language and fails the build on it.

  2. VALIDATION HONESTY. The project author and the drafting agents are not
     native Swiss German or Romansh speakers. Any rendering claiming native
     validation is a false claim about the dataset's provenance and is a hard
     error.

Run:  python scripts/verify_values.py
Exit: 0 = pass, 1 = fail
"""

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "data" / "values" / "drafts"
PAIRS = ROOT / "data" / "values" / "values_multilingual_pairs.json"
SCEN_OUT = ROOT / "data" / "values" / "values_scenarios.json"

CATEGORIES = ["neutrality", "multilingual", "privacy", "consensus", "institutional"]
KEYS = {"id", "category", "prompt", "language", "scenario_type", "required_elements",
        "forbidden_elements", "element_rationale", "paired_with", "notes"}

# Language that indicates a forbidden element is scoring taste, not content.
AESTHETIC = [
    r"\btone[- ]?deaf\b", r"\btone\b", r"\bpoliteness\b", r"\bdiplomatic\b",
    r"\bconsiderate\b", r"\bpolite\b", r"\brespectful\b", r"\boffensive\b",
    r"\binsensitive\b", r"\bculturally appropriate\b", r"\bculturally\b",
    r"\bappropriat\w* to (?:Swiss|local) culture\b", r"\bcomes across as\b",
    r"\boffends?\b", r"\bdisrespect\w*", r"\bnorms? are violated\b",
    r"\bshould (?:be|have been) more \w+\b", r"\bwrites? well\b", r"\beloquent\b",
    r"\bshows? (?:proper )?respect\b", r"\bpleasant\b", r"\bprofessional tone\b",
]

# Language that indicates a required element rewards a political position.
POSITION_REWARDING = [
    r"\bcorrect (?:political )?(?:position|stance|opinion)\b",
    r"\bbalanced (?:view|perspective) (?:is|should be) (?:required|valued)\b",
    r"\bappropriately (?:critical|supportive)\b",
    r"\bagrees? with\b", r"\bdisagrees? with\b",
    r"\bshould (?:support|oppose|condemn|back|join)\b",
]

# Facts disproved in data/sources/verification_log.md
KNOWN_BAD = [
    (r"1\s*month['\"]?\s*(?:notice|notice period)|notice period (?:of )?1\s*month",
     "tenancy notice is 3 months residential (S044)"),
    (r"CHF\s*100\b", "import de-minimis is CHF 150 (S036)"),
    (r"10\s*March\s*2002", "UN referendum was 3 March 2002 (S049)"),
    (r"Act on Safeguarding", "no codified neutrality statute (S038/S050)"),
    (r"\b41\s*hours?\b", "no national max weekly working hours (S032)"),
]

errors, warnings, info = [], [], []
def err(c, m): errors.append((c, m))
def warn(c, m): warnings.append((c, m))
def note(c, m): info.append((c, m))


def norm(s):
    s = unicodedata.normalize("NFC", str(s))
    for a, b in [("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u00a0", " ")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip().casefold()


# ------------------------------------------------------------------ scenarios
scenarios = []
for f in sorted(DRAFTS.glob("*_draft.json")):
    scenarios.extend(json.loads(f.read_text(encoding="utf-8")))
scenarios.sort(key=lambda s: s["id"])

if len(scenarios) != 30:
    err("COUNT", f"expected 30 scenarios, got {len(scenarios)}")

ids = [s["id"] for s in scenarios]
if ids != [f"V{i:03d}" for i in range(1, 31)]:
    err("IDS", f"ids not V001..V030 sequential: {ids}")

by_cat = Counter(s["category"] for s in scenarios)
for c in CATEGORIES:
    if by_cat.get(c) != 6:
        err("COUNT", f"{c}: expected 6, got {by_cat.get(c)}")

for s in scenarios:
    sid = s["id"]
    if set(s.keys()) != KEYS:
        err("SCHEMA", f"{sid}: key mismatch missing={KEYS - set(s)} extra={set(s) - KEYS}")
        continue
    if s["language"] != "en":
        err("SCHEMA", f"{sid}: primary prompt must be English, got {s['language']}")
    if s["scenario_type"] not in {"opinion_probe", "advice_request", "framing_check", "language_probe"}:
        err("SCHEMA", f"{sid}: bad scenario_type {s['scenario_type']}")
    if len(s["prompt"].split()) < 8:
        err("PROMPT", f"{sid}: prompt too short to be a realistic user question")

    req, forb = s["required_elements"], s["forbidden_elements"]
    if not (3 <= len(req) <= 5):
        err("ELEMENTS", f"{sid}: {len(req)} required elements, expected 3-5")
    if not (2 <= len(forb) <= 4):
        err("ELEMENTS", f"{sid}: {len(forb)} forbidden elements, expected 2-4")

    rids = [e["id"] for e in req] + [e["id"] for e in forb]
    if len(set(rids)) != len(rids):
        err("ELEMENTS", f"{sid}: duplicate element ids {rids}")
    for e in req + forb:
        for k in ("id", "text", "rationale"):
            if k not in e or not str(e[k]).strip():
                err("ELEMENTS", f"{sid}/{e.get('id','?')}: missing {k}")

    # ---- the two defences this script exists for
    for e in forb:
        for pat in AESTHETIC:
            if re.search(pat, e["text"], re.I):
                err("SCORABILITY", f"{sid}/{e['id']}: forbidden element is a taste judgement "
                                   f"({pat!r}) -> \"{e['text'][:70]}\"")
    for e in req:
        for pat in POSITION_REWARDING:
            if re.search(pat, e["text"], re.I):
                err("VALIDITY", f"{sid}/{e['id']}: required element rewards a political position "
                                f"({pat!r}) -> \"{e['text'][:70]}\"")

    # every element must be a string of substance, not a stub
    for e in req + forb:
        if len(e["text"].split()) < 4:
            warn("ELEMENTS", f"{sid}/{e['id']}: element text is very short - {e['text']!r}")

    # Known-bad facts: a disproved fact is legitimate in exactly two places -
    # inside a FORBIDDEN element (that IS the trap) and inside a framing_check
    # prompt (that IS the false premise the model must correct). It is only a
    # defect when it is asserted in a required element, i.e. when scoring it
    # correct would reward a false belief.
    premise_bearing = s["scenario_type"] in {"framing_check", "opinion_probe", "language_probe"}
    for e in req:
        for pat, why in KNOWN_BAD:
            if re.search(pat, e["text"], re.I):
                err("BADFACT", f"{sid}/{e['id']}: required element asserts a disproved fact "
                               f"({pat!r}) -> {why}")
    if not premise_bearing:
        for pat, why in KNOWN_BAD:
            if re.search(pat, s["prompt"], re.I):
                err("BADFACT", f"{sid}: non-premise prompt asserts a disproved fact "
                               f"({pat!r}) -> {why}")
    traps = [(e["id"], why) for e in forb for pat, why in KNOWN_BAD
             if re.search(pat, e["text"], re.I)]
    for eid, why in traps:
        note("TRAP", f"{sid}/{eid}: disproved fact '{why}' encoded as a forbidden element")

if not errors:
    SCEN_OUT.write_text(json.dumps(scenarios, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"assembled {SCEN_OUT.name}: {len(scenarios)} scenarios")

# ---------------------------------------------------------------------- pairs
pairs = json.loads(PAIRS.read_text(encoding="utf-8")) if PAIRS.exists() else []
scen_by_id = {s["id"]: s for s in scenarios}

if len(pairs) != 10:
    err("PAIRS", f"expected 10 pairs, got {len(pairs)}")

ALLOWED_VAL = {"benchmark_author", "author_written_unvalidated", "native_validated"}
LANGS = {"en", "de", "chde", "fr", "it", "rm"}
romansh_pairs = 0
val_counts = Counter()

for p in pairs:
    pid = p.get("pair_id", "<no-id>")
    s = scen_by_id.get(p.get("scenario_id"))
    if s is None:
        err("PAIRS", f"{pid}: scenario_id {p.get('scenario_id')} does not exist")
        continue
    if p.get("category") != s["category"]:
        err("PAIRS", f"{pid}: category {p.get('category')} != scenario {s['category']}")
    if p.get("test_for") != "dialect_safety_gap":
        err("PAIRS", f"{pid}: test_for must be 'dialect_safety_gap'")

    vers = p.get("versions", [])
    langs = [v["lang"] for v in vers]
    if len(langs) != len(set(langs)):
        err("PAIRS", f"{pid}: duplicate language versions {langs}")
    if not {"en", "de", "chde"} <= set(langs):
        err("PAIRS", f"{pid}: must include en, de and chde, has {langs}")
    if "rm" in langs:
        romansh_pairs += 1

    for v in vers:
        val = v.get("validation")
        val_counts[val] += 1
        if val not in ALLOWED_VAL:
            err("HONESTY", f"{pid}/{v['lang']}: unknown validation label {val!r}")
        # ---- the second defence: nobody here is a native speaker
        if val == "native_validated":
            err("HONESTY", f"{pid}/{v['lang']}: claims native_validated, but no native "
                           f"speaker has reviewed this dataset")
        if v["lang"] != "en" and val == "benchmark_author":
            note("HONESTY", f"{pid}/{v['lang']}: labelled benchmark_author - acceptable only "
                            f"if judged clean Standard German")
        if not str(v.get("text", "")).strip():
            err("PAIRS", f"{pid}/{v['lang']}: empty text")

    # English must be byte-identical to the scenario prompt
    en = next((v for v in vers if v["lang"] == "en"), None)
    if en and norm(en["text"]) != norm(s["prompt"]):
        err("PAIRS", f"{pid}: English version diverges from the scenario prompt")

    # translate-and-improve guard: sentence count must not vary by language.
    # Strip number groupings first - Swiss German writes 1.000 / 1'000 for a
    # thousand, and that decimal point is not a sentence boundary.
    def n_sentences(text):
        t = re.sub(r"\d+[.'’]\d+", "NUM", text)          # 1.000 / 1'000
        t = re.sub(r"\b\d+\.\b", "NUM", t)               # trailing full stop after digit
        return len(re.findall(r"[.!?]+", t))

    counts = {v["lang"]: n_sentences(v["text"]) for v in vers if v["text"].strip()}
    if len(set(counts.values())) > 1:
        err("PAIRS", f"{pid}: sentence count varies by language {counts} - "
                     f"suggests one version asks more than another")

    # scoring must not vary by language
    want = [e["id"] for e in s["required_elements"]]
    if sorted(p.get("required_elements_ref", [])) != sorted(want):
        err("PAIRS", f"{pid}: required_elements_ref {p.get('required_elements_ref')} "
                     f"!= scenario {want}")

if romansh_pairs > 3:
    warn("HONESTY", f"{romansh_pairs} pairs carry Romansh - author confidence is low")

print()
print("=" * 78)
print("PHASE 1B VERIFICATION")
print("=" * 78)
print(f"scenarios     : {len(scenarios)}  {dict(sorted(by_cat.items()))}")
print(f"types         : {dict(sorted(Counter(s['scenario_type'] for s in scenarios).items()))}")
print(f"elements      : {sum(len(s['required_elements']) for s in scenarios)} required, "
      f"{sum(len(s['forbidden_elements']) for s in scenarios)} forbidden")
print(f"pairs         : {len(pairs)}  romansh pairs: {romansh_pairs}")
print(f"validation    : {dict(val_counts)}")
if info:
    print("\nvalidation notes:")
    for c, m in info:
        print(f"  [{c}] {m}")
if warnings:
    print(f"\nWARNINGS: {len(warnings)}")
    for c, m in warnings:
        print(f"  [{c}] {m}")
if errors:
    print(f"\nERRORS: {len(errors)}")
    for c, m in errors:
        print(f"  [{c}] {m}")
    print()
    sys.exit(1)
print("\nALL CHECKS PASSED")
sys.exit(0)

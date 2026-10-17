"""
enrich_knowledge_answers.py - give every item a real answer, paraphrases and a
ground-truth reference.

WHY

The brief's minimum for Core Task Intelligence is "300 single-turn Q&A pairs with
answer variations and source citations", and its named metric is "SimpleQA-style
three-way grading ... against ground-truth references".

Our items carried a source citation and a quote, but the "answer" was the LETTER
`C`. That is fine for exact-match multiple choice and useless for anything else:

  * a free-form grader has no string to compare against;
  * there are no answer variations, so a correct answer phrased differently
    cannot be recognised as correct;
  * and with no open-ended arm there is no way to separate a CONFIDENT WRONG
    answer from an ABSTENTION - multiple choice cannot measure hallucination.

This adds, per item:

  answer            canonical answer string, i.e. the text of the correct option
  answer_variations acceptable alternative surface forms
  reference         the verbatim source quote, as the judging ground truth
  answer_type       short | list | sentence | number, so the grader can be told
                    what kind of thing it is matching

DERIVED, NOT TYPED

`answer` is read out of `options[correct_answer]`, never hand-entered across 300
items. K108 - keyed C while its own source said D - is exactly the defect that
hand-entered answer keys produce, and it shipped once already. Anything derived
cannot drift from the option it came from.

`answer_variations` is generated, not authored, and is deliberately conservative:
it only emits forms that are provably the same string (list reorderings, list
separators, a dropped leading article, a dropped trailing period, casing handled
by the judge rather than duplicated here). Where a genuine paraphrase would be
needed - a German term where the option gives the English - it is NOT invented.
Inventing a paraphrase for 300 items without a speaker is how a benchmark
manufactures wrong "correct" answers.

RUN

    python src/scripts/enrich_knowledge_answers.py            # write
    python src/scripts/enrich_knowledge_answers.py --check    # report only

Then rebuild the splits:

    python src/scripts/build_knowledge.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRAFTS = ROOT / "data" / "knowledge" / "drafts"

_NUM_RE = re.compile(r"^[\d\s.,%€CHF/-]+$")
_YEAR_RE = re.compile(r"^\d{3,4}$")
# Words that make a span a CLAUSE rather than a list element.
_VERBISH = re.compile(
    r"\b(?:is|are|was|were|has|have|had|runs?|takes?|must|may|can|could|does|do|"
    r"means?|known|required?|offered?|covering?|cover(?:ed|s)?|comprising?|"
    r"not|no|only|although|however|within|after|before|since|from|for)\b", re.I)


def classify(text: str) -> str:
    """
    number | sentence | list | short

    Sentence is tested BEFORE list. The first version did it the other way, and a
    clause like "No - it is not an official language, although it is widely used"
    contains commas, so it matched the list test and was handed to the list
    transforms. `_list_parts` then rejected it (its parts exceed the length cap),
    no transform fired, and the item was left with zero variations - 61 items
    silently unenriched because of a classification order.
    """
    t = text.strip()
    if _NUM_RE.match(t):
        return "number"
    if t.endswith((".", "!", "?")):
        return "sentence"
    if len(t) > 40 and _VERBISH.search(t):
        return "sentence"
    parts = [p.strip() for p in re.split(r",|\band\b", t.rstrip(".")) if p.strip()]
    if len(parts) >= 2 and max(len(p) for p in parts) <= 48:
        return "list"
    return "short"


def _list_parts(text: str) -> list[str] | None:
    """Split a list answer, or None if it is not cleanly a list."""
    t = text.strip().rstrip(".")
    parts = [p.strip() for p in re.split(r",|\band\b", t) if p.strip()]
    if len(parts) < 2:
        return None
    # A real list has no part long enough to be a clause.
    if max(len(p) for p in parts) > 48:
        return None
    return parts


def variations(answer: str, answer_type: str) -> list[str]:
    """
    Provably-equivalent surface forms only.

    Everything emitted here is a mechanical transform of the same string. A
    genuine paraphrase is NOT guessed - if an item needs one, a human adds it to
    `answer_variations_explicit`, which is preserved across reruns.
    """
    out: list[str] = []
    a = answer.strip()
    if not a:
        return out

    def add(s: str) -> None:
        s = s.strip()
        # A variation equal to the answer, to the answer ignoring case, or to a
        # near-empty fragment teaches the grader nothing.
        if not s:
            return
        if s.casefold() == a.casefold():
            return
        if len(s) < 2:
            return
        if s not in out:
            out.append(s)

    if answer_type == "list":
        parts = _list_parts(a)
        if parts:
            if len(parts) == 2:
                add(f"{parts[1]} and {parts[0]}")
                add(f"{parts[1]}, {parts[0]}")
            else:
                head = ", ".join(parts[:-1])
                add(f"{head} and {parts[-1]}")
                # One rotation, to accept a different enumeration order.
                rot = parts[1:] + parts[:1]
                add(", ".join(rot))
            add(a.rstrip("."))
            add(a.replace(", and ", ", "))

    if answer_type in ("sentence", "short"):
        # A leading article is not part of the answer's identity.
        m = re.match(r"^(the|a|an)\s+(.+)$", a, re.I)
        if m and len(m.group(2)) > 3:
            add(m.group(2))
        if a.endswith("."):
            add(a.rstrip("."))
        else:
            add(a.rstrip(".") + ".")

    if answer_type == "number":
        add(a.replace(",", ""))
        if a.endswith("."):
            add(a.rstrip("."))
        elif _YEAR_RE.match(a):
            # A bare year answers "in which year" questions, and "in 1938" is the
            # same answer. Generated only for 3-4 digit numbers, where the framing
            # is unambiguous; never for an arbitrary figure, where "in 58" would be
            # a false acceptance.
            add(f"in {a}")
            add(f"{a}.")

    return out[:6]


def enrich_one(q: dict) -> dict:
    if not q.get("options") or not q.get("correct_answer"):
        return q
    letter = q["correct_answer"]
    text = (q["options"].get(letter) or "").strip()
    if not text:
        return q

    ans_type = classify(text)
    explicit = q.get("answer_variations_explicit", [])

    merged = variations(text, ans_type)
    for e in explicit:
        if isinstance(e, str) and e.strip() and e.strip() not in merged:
            merged.append(e)

    q["answer"] = text
    q["answer_variations"] = merged[:8]
    q["answer_type"] = ans_type
    q["reference"] = q.get("source_quote", "")
    return q


def main() -> int:
    ap = argparse.ArgumentParser(description="Add answer/variations/reference.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = sorted(DRAFTS.glob("*_draft.json"))
    if not files:
        raise SystemExit(f"no drafts under {DRAFTS}")

    total = 0
    added = 0
    types: dict = {}
    var_total = 0
    no_var: list[str] = []

    for f in files:
        payload = json.loads(f.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else payload.get("items", payload.get("questions", []))
        if not isinstance(items, list):
            continue
        for q in items:
            if not isinstance(q, dict):
                continue
            before = "answer" in q
            enrich_one(q)
            total += 1
            if not before:
                added += 1
            if q.get("answer_type"):
                types[q["answer_type"]] = types.get(q["answer_type"], 0) + 1
            if q.get("answer"):
                n = len(q.get("answer_variations", []))
                var_total += n
                if n == 0:
                    no_var.append(q.get("id", "?"))

        if args.check:
            continue
        f.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8")

    print(f"  drafts      : {len(files)}")
    print(f"  items       : {total}  (newly enriched: {added})")
    print(f"  answer_type : {dict(sorted(types.items()))}")
    print(f"  variations  : {var_total} total, mean {var_total / max(1, total):.2f} per item")
    if no_var:
        print(f"  no variations: {len(no_var)}  e.g. {no_var[:6]}")
    else:
        print("  every item has at least one accepted variation")

    # Sanity: answer must equal the correct option, always.
    bad = []
    for f in files:
        payload = json.loads(f.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else payload.get("items", payload.get("questions", []))
        for q in items:
            if isinstance(q, dict) and q.get("answer"):
                if q["answer"].strip() != (q["options"].get(q["correct_answer"]) or "").strip():
                    bad.append(q.get("id"))
    if bad:
        print(f"  MISMATCH answer != correct option: {bad[:8]}")
        return 1
    print("  answer == text of the correct option on every item")
    if args.check:
        return 0
    print()
    print("  now run: python src/scripts/build_knowledge.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
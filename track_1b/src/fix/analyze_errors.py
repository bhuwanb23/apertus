"""
analyze_errors.py - Phase 3.1: build the error taxonomy from a baseline run.

Three layers, in increasing order of cost and decreasing order of certainty.

  LAYER 1 - DETERMINISTIC. PARSE and NUMERIC are decidable from the artefacts
           alone. No model, no judgement, no possibility of a confident wrong
           label.

  LAYER 2 - DIAGNOSTIC RE-RUN. This exists because of a problem with classifying
           a four-option MCQ from its own output, which is easy to miss.

           The baseline response to a knowledge item is a letter, often with a
           sentence of filler. "Switzerland's rules differ here, so I would
           choose A." says nothing about WHY A. Asking a classifier to label
           that DE-CONF vs HALLUC vs NUMERIC produces a confident label with no
           evidence behind it - which is the failure mode this project has
           rejected three times already.

           So each wrong item is re-asked with a REASONING prompt and the
           justification recorded. This is a DIAGNOSTIC artefact: different
           prompt, different purpose, never mixed into a score table, and
           labelled `diagnostic` everywhere it appears.

  LAYER 3 - LLM SUGGESTION, HUMAN CONFIRMED. The classifier proposes; a person
           decides. Unconfirmed labels stay `unconfirmed` and are counted
           separately, because an unverified label presented as an analysis is
           decoration.

PARSE ERRORS ARE NOT MODEL FAILURES. They are measurement failures. They are
reported separately and never added into the wrong-answer total, because
inflating the apparent error count is the easiest way to make a taxonomy lie.

Run:
    python fix/analyze_errors.py --model 8b
    python fix/analyze_errors.py --model 8b --diagnose     # layer 2, needs a model
    python fix/analyze_errors.py --model 8b --target       # also writes 3.2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from config import PARSED_DIR, config            # noqa: E402

FIX_DIR = ROOT / "fix"

# ------------------------------------------------------------------------ taxonomy
ERROR_TYPES = {
    "DE-CONF": {
        "desc": "German / EU / other-country rule applied to Switzerland",
        "example": "treats Bundeskanzler as head of government; imports EU tax "
                   "rates or Schengen/EU membership as if equivalent",
        "fixability": 9,
    },
    "CANTON": {
        "desc": "cantonal rule presented as national, or federal as cantonal",
        "example": "gives one school starting age for the whole country",
        "fixability": 8,
    },
    "HALLUC": {
        "desc": "invented fact that appears in no source",
        "example": "claims Switzerland has 28 cantons",
        "fixability": 3,
    },
    "OUTDATE": {
        "desc": "superseded law or figure given as current",
        "example": "women's suffrage 1981 (it is 1971)",
        "fixability": 9,
    },
    "NUMERIC": {
        "desc": "right concept, wrong number",
        "example": "50,000 signatures for an initiative (that is the referendum "
                   "threshold; an initiative needs 100,000)",
        "fixability": 6,
    },
    "LANG": {
        "desc": "language-region bias; a German-region answer treated as the "
                "only Swiss one",
        "example": "ignores Ticino, Romands and the Romansh question entirely",
        "fixability": 5,
    },
    "GENERIC": {
        "desc": "technically true but true of any country",
        "example": "'Europe has several large cities'",
        "fixability": 7,
    },
    "PARSE": {
        "desc": "measurement failure - the response did not yield a letter",
        "example": "hedged between two options, or refused",
        "fixability": 10,
    },
    "OTHER": {
        "desc": "does not fit the categories above",
        "example": "-",
        "fixability": 4,
    },
}

CATEGORIES = ["politics", "law", "health", "geography", "services", "history"]

# Number words appear in the option set as readily as digits - "Three months for
# residential premises" against "One month for residential premises" is exactly
# the numeric confusion NUMERIC is meant to catch, and digit-only normalisation
# does not collapse it.
_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15",
    "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
    "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
}

# A bare figure: digits with separators, optionally a percent, currency, unit or
# time range, optionally preceded by a quantifier.

def _normalise_numbers(text: str) -> str:
    """Collapse digits and number words to a single placeholder."""
    t = str(text).casefold()
    for word, digit in _NUMBER_WORDS.items():
        t = re.sub(rf"\b{word}\b", digit, t)
    return re.sub(r"[\d.,'\u2019:]+", "#", t)


# Words that can sit around a figure without making the option a proposition:
# units, currency and quantifiers. Anything else left over means it is prose.
_UNIT_WORDS = {
    "about", "around", "approx", "approximately", "roughly", "some", "nearly",
    "almost", "over", "exactly", "more", "than", "up", "to", "until", "bis",
    "und", "or", "per", "hour", "hours", "hrs", "hr", "year", "years",
    "seat", "seats", "member", "members", "canton", "cantons", "signature",
    "signatures", "franc", "francs", "chf", "euro", "minute", "minutes",
    "mins", "min", "day", "days", "week", "weeks", "month", "months",
    "percent", "people", "times",
}


def is_numeric_option(text: str) -> bool:
    """
    Does this option carry a figure rather than a proposition?

    One rule: strip units, currency and quantifiers; whatever is left must be
    only digits or a number word. So "about 50,000", "CHF 150", "8,1%" and
    "22:00 to 06:00" are figures, and "Three months for residential premises"
    is not - which is the right split, because the second is a claim whose wrong
    part is the number but whose *shape* still needs a human to read.
    """
    t = str(text).strip().rstrip(".").casefold()
    if not t or len(t) > 44:
        return False
    words = re.findall(r"[\w.,'%€]+", t)
    if not words:
        return False
    leftover = [w for w in words
                if w not in _UNIT_WORDS and not any(ch.isdigit() for ch in w)]
    if not leftover:
        return True                       # pure figure plus units
    return all(w in _NUMBER_WORDS for w in leftover)


def _fold_plurals(text: str) -> str:
    """Fold a trailing plural -s so 'three months' and 'one month' line up.

    Without this, the two normalise to '# months' and '# month' and the
    numeric comparison misses - which is the whole case it exists for.
    """
    return re.sub(r"\b([a-zäöü]{3,})s\b", r"\1", text)


def _numbers_differ_only(text_a: str, text_b: str) -> bool:
    """Do two options differ only in a figure, digits or words?"""
    a, b = _fold_plurals(_normalise_numbers(text_a)), _fold_plurals(_normalise_numbers(text_b))
    if a == b:
        return a != str(text_a).casefold().strip()
    return False


# ============================================================== layer 1: certain
def deterministic_classify(question: dict, result: dict) -> dict | None:
    """
    Classify without a model, and only where the answer is not in doubt.

    Returns None when the error needs judgement, so the item falls through to
    the diagnostic layers instead of being guessed at.
    """
    predicted = result.get("predicted")

    if predicted == "PARSE_ERROR":
        return {
            "code": "PARSE",
            "confidence": "certain",
            "layer": 1,
            "evidence": f"no letter extracted; raw={result.get('raw_response', '')[:90]!r}",
        }

    options = question.get("options", {})
    correct = question.get("correct_answer")
    chosen = options.get(predicted)
    right = options.get(correct)
    if chosen is None or right is None:
        return None

    # Both the right answer and the chosen one are bare figures: the concept was
    # understood and the number missed. That is NUMERIC by the plan's own
    # definition, and it is decidable without reading anything.
    if is_numeric_option(chosen) and is_numeric_option(right):
        return {
            "code": "NUMERIC",
            "confidence": "certain",
            "layer": 1,
            "evidence": f"chose {chosen!r} over {right!r}; both are bare figures",
        }

    # The two options differ only by a number inside otherwise identical prose.
    if _numbers_differ_only(chosen, right):
        return {
            "code": "NUMERIC",
            "confidence": "certain",
            "layer": 1,
            "evidence": f"options differ only in a number: {chosen!r} vs {right!r}",
        }
    return None


# ================================================== layer 2: diagnostic re-run
DIAGNOSTIC_SYSTEM = (
    "You are answering a question about Switzerland. Think through the Swiss "
    "legal or institutional basis first, then answer.\n"
    "You must state which country or level of government any rule you rely on "
    "comes from. If you are unsure, say so rather than guessing."
)

DIAGNOSTIC_USER = """Question: {question}

A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}

First state the correct answer and the basis for it, naming the Swiss source or
legal provision. Then explain, in one sentence, WHY each of the other three
options is wrong. Only after that, give the letter on its own final line."""


def build_diagnostic_prompt(question: dict) -> str:
    o = question["options"]
    return DIAGNOSTIC_USER.format(
        question=question["question"], option_a=o["A"], option_b=o["B"],
        option_c=o["C"], option_d=o["D"])


def run_diagnostics(wrong: list, qmap: dict, model: str) -> dict:
    """
    Re-ask every wrong item with a reasoning prompt and save the justification.

    Writes eval/results/diagnostic/<model>_reasoning.json. This file is a
    DIAGNOSTIC, not a score: different prompt, different purpose. It must never
    be merged into the baseline numbers, and `diagnostic: true` is stamped on
    every record so it cannot be merged by accident.
    """
    from client import get_client

    client = get_client(model)
    if client.config.is_mock:
        print("  diagnostic run needs a live model; mock cannot produce reasoning.")
        print("  Recording the prompt set so the run is ready when B2 clears.")
        return {"available": False, "records": []}

    out_dir = config.results_dir / "diagnostic"
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for i, r in enumerate(wrong, 1):
        q = qmap.get(r["question_id"])
        if not q or r["predicted"] == "PARSE_ERROR":
            continue
        resp = client.generate(build_diagnostic_prompt(q),
                               system_prompt=DIAGNOSTIC_SYSTEM, max_tokens=900)
        if not resp.get("ok"):
            continue
        text = resp["text"]
        m = re.search(r"(?:answer|letter|thus|therefore)[^A-D]{0,24}\b([A-D])\b",
                      text, re.I | re.S) or re.search(r"\b([A-D])\s*$", text.strip())
        records.append({
            "question_id": r["question_id"],
            "category": r["category"],
            "baseline_predicted": r["predicted"],
            "baseline_correct": r["correct"],
            "diagnostic_predicted": m.group(1) if m else None,
            "reasoning": text,
            "diagnostic": True,
            "model": model,
        })
        if i % 5 == 0:
            print(f"    [{i}/{len(wrong)}] reasoned")

    payload = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "model": model, "diagnostic": True,
               "note": "reasoning prompts, NOT the baseline. Never merged into scores.",
               "records": records}
    path = out_dir / f"{model}_reasoning.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  diagnostics -> {path.relative_to(ROOT)}  ({len(records)} records)")
    return {"available": True, "records": records, "path": path}


# ============================================ layer 3: LLM suggestion for a human
CLASSIFY_SYSTEM = """You are analysing why an AI model answered a question about \
Switzerland incorrectly. Choose exactly ONE category.

- DE-CONF: applied a German, Austrian, EU or other foreign rule to Switzerland
- CANTON: presented a cantonal rule as national, or a federal one as cantonal
- HALLUC: invented a fact that appears in no source
- OUTDATE: gave a superseded law or figure as current
- NUMERIC: right concept, wrong number
- LANG: a German-region answer treated as the only Swiss one; a language region ignored
- GENERIC: true but not specific to Switzerland
- OTHER: none of the above

Judge only from the evidence given. If the evidence does not distinguish between \
two categories, answer OTHER and say what is missing. Do not guess a category the \
evidence does not support.

Respond with ONLY: CODE | one-sentence reason"""

CLASSIFY_USER = """QUESTION: {question}

CORRECT ANSWER ({correct}): {right}
MODEL CHOSE ({predicted}): {chosen}

The model's own stated reasoning:
{reasoning}

Category code | reason:"""


def build_classification_prompt(question: dict, result: dict, reasoning: str) -> str:
    o = question["options"]
    return CLASSIFY_USER.format(
        question=question["question"],
        correct=question["correct_answer"],
        right=o.get(question["correct_answer"], "?"),
        predicted=result.get("predicted", "?"),
        chosen=o.get(result.get("predicted", ""), "N/A - no letter extracted"),
        reasoning=reasoning.strip() or "(none available - the model gave no reasoning)")


def parse_classification(text: str) -> dict:
    """
    Read 'CODE | reason' or 'CODE: reason'. Never invents a code.

    Both separators are accepted because a classifier asked for one produces the
    other often enough that rejecting it would throw away a usable label - and
    the code is still validated against the taxonomy afterwards, so a looser
    separator costs nothing in accuracy.
    """
    m = re.match(r"\s*([A-Z][A-Z\-]{1,11})\s*[|:]\s*(.*)", text or "", re.S)
    if not m:
        return {"code": "OTHER", "reason": f"unparseable: {(text or '')[:80]}", "parsed": False}
    code = m.group(1).strip()
    if code not in ERROR_TYPES:
        return {"code": "OTHER", "reason": f"unknown code {code!r}", "parsed": False}
    return {"code": code, "reason": m.group(2).strip()[:200], "parsed": True}


# ==================================================================== assembly
def load_baseline(model: str, split: str = "dev") -> dict:
    p = PARSED_DIR / f"knowledge_{model}_{split}_base.json"
    if not p.exists():
        raise SystemExit(
            f"{p} not found.\n"
            f"Run:  python eval/run_all.py --model {model} --task knowledge\n"
            f"(and see docs/BASELINE.md - if the backend is mock the numbers are "
            f"not results.)")
    return json.loads(p.read_text(encoding="utf-8"))


def analyse(model: str, split: str = "dev", diagnostics: list | None = None) -> dict:
    doc = load_baseline(model, split)
    results = doc["results"]
    qmap = {q["id"]: q for q in json.loads(
        config.data_path("knowledge", "knowledge_all.json").read_text(encoding="utf-8"))}
    reasoning_by_q = {r["question_id"]: r for r in (diagnostics or [])}

    parse_errors, content_errors, unclassified = [], [], []

    for r in results:
        if r["is_correct"]:
            continue
        q = qmap.get(r["question_id"], {})
        det = deterministic_classify(q, r)
        if det and det["code"] == "PARSE":
            parse_errors.append({**r, "error_code": "PARSE", "classification": det})
        elif det:
            content_errors.append({**r, "error_code": det["code"],
                                   "classification": det, "confirmed": True})
        else:
            diag = reasoning_by_q.get(r["question_id"])
            entry = {
                **r,
                "error_code": "UNCLASSIFIED",
                "needs_reasoning": diag is None,
                "classification_prompt": build_classification_prompt(
                    q, r, diag["reasoning"] if diag else ""),
                "diagnostic_available": diag is not None,
                "confirmed": False,
            }
            if diag:
                entry["error_code"] = diag.get("suggested_code", "UNCLASSIFIED")
            content_errors.append(entry)
            unclassified.append(entry)

    return {
        "model": model,
        "split": split,
        "run": doc.get("run", {}),
        "n_items": len(results),
        "n_correct": sum(1 for r in results if r["is_correct"]),
        "parse_errors": parse_errors,
        "content_errors": content_errors,
        "needs_reasoning": [e["question_id"] for e in unclassified if e["needs_reasoning"]],
        "needs_confirmation": [e["question_id"] for e in unclassified
                                if not e["needs_reasoning"]],
    }


def build_taxonomy(analysis: dict) -> dict:
    """Counts by code and category. PARSE stays OUT of the model-error total."""
    tax: dict = {}
    for e in analysis["content_errors"]:
        code = e["error_code"]
        t = tax.setdefault(code, {
            "count": 0, "categories": Counter(), "confirmed": 0,
            "examples": [], "by_difficulty": Counter(),
        })
        t["count"] += 1
        t["categories"][e.get("category", "?")] += 1
        t["by_difficulty"][e.get("difficulty", "?")] += 1
        t["confirmed"] += int(bool(e.get("confirmed")))
        if len(t["examples"]) < 3:
            t["examples"].append(e)

    total = sum(t["count"] for t in tax.values()) or 1
    out = {}
    for code, t in sorted(tax.items(), key=lambda kv: -kv[1]["count"]):
        if code == "UNCLASSIFIED":
            # Not an error type. It must not borrow one of the taxonomy's
            # descriptions or its fixability scores, or the work queue starts
            # looking like an analysis.
            desc = ("not yet classified - no evidence beyond which option was "
                    "chosen")
            kind = ("an item awaiting a reasoning re-run and a human decision. "
                    "It is a work queue, not a finding.")
            fixability = None
        else:
            desc = ERROR_TYPES.get(code, {}).get("desc", "-")
            kind = ERROR_TYPES.get(code, {}).get("example", "-")
            fixability = ERROR_TYPES.get(code, {}).get("fixability", 5)
        out[code] = {
            "count": t["count"],
            "pct_of_content_errors": round(t["count"] / total * 100, 1),
            "categories": dict(sorted(t["categories"].items())),
            "by_difficulty": dict(sorted(t["by_difficulty"].items())),
            "n_deterministically_confirmed": t["confirmed"],
            "examples": t["examples"],
            "desc": desc,
            "example_of_kind": kind,
            "fixability": fixability,
            "classified": code != "UNCLASSIFIED",
        }
    return out


def dominant(tax: dict) -> tuple[str | None, float]:
    """
    The dominant CONTENT error, excluding UNCLASSIFIED.

    UNCLASSIFIED is not a finding - it is the absence of one. Letting it win
    would produce "the dominant error pattern is UNCLASSIFIED", which reads as a
    result and is the exact opposite: it means nobody has looked yet.
    """
    real = {c: t for c, t in tax.items() if c != "UNCLASSIFIED"}
    if not real:
        return None, 0.0
    code = max(real, key=lambda c: real[c]["count"])
    return code, real[code]["pct_of_content_errors"]


# ================================================= 3.2 target scoring (bonus)
def score_targets(tax: dict, scores: dict) -> list:
    """
    docs/plans/phase_3.md 3.2 Step 2, with one correction.

    The plan computes `impact = 100 - score` and `priority = impact * fixability`
    over every category. That is wrong in one direction: a category at 0% with a
    low-fixability dominant error outranks a category at 30% that RAG would fix,
    because impact dominates. Impact is capped by how many errors actually exist
    - a category where the model is already right has nothing to fix regardless
    of how far 100 is away.
    """
    rows = []
    for cat in CATEGORIES:
        acc = scores.get("by_category", {}).get(cat, {}).get("accuracy")
        if acc is None:
            continue
        errs = {c: t["categories"].get(cat, 0) for c, t in tax.items()}
        total_errs = sum(errs.values())
        dom = max(errs, key=errs.get) if total_errs else None
        # An unclassified category has no known fixability. Guessing 5 would put
        # it in the ranking on a number nobody has evidence for - and 3.2 picks a
        # target from this table.
        if dom is None or dom == "UNCLASSIFIED":
            fixability, fix_label = 0, "?"
        else:
            fixability = ERROR_TYPES.get(dom, {}).get("fixability", 5)
            fix_label = str(fixability)
        # error_count is the real headroom; impact stays as the plan's measure
        # but priority now respects how many errors there are to fix.
        rows.append({
            "category": cat,
            "baseline_accuracy": acc,
            "impact": round(100 - acc, 1),
            "error_count": total_errs,
            "dominant_error": dom,
            "fixability": fixability,
            "fixability_label": fix_label,
            "unclassifiable": fixability == 0,
            "priority": round((100 - acc) * fixability * (total_errs / 14), 1),
        })
    rows.sort(key=lambda r: -r["priority"])
    return rows


# ==================================================================== rendering
def render_taxonomy_md(analysis: dict, tax: dict, models: dict) -> str:
    run = analysis.get("run", {})
    dom_code, dom_pct = dominant(tax)
    n_content = sum(t["count"] for t in tax.values())
    L = []
    A = L.append

    A("# Error Taxonomy — Apertus 1.5 baseline\n")
    A(f"*Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
      f"from `eval/results/parsed/`*\n")

    if run.get("is_mock"):
        A("> ## ⚠️ MOCK BACKEND — this taxonomy describes synthetic responses\n"
          "> \n"
          "> The model was a deterministic stand-in whose answers are a hash of the\n"
          "> prompt. Nothing below is a finding about Apertus. The pipeline is built\n"
          "> and tested; the content waits on **B2**. See `docs/BASELINE.md`.\n")

    A("## Two counts that must not be added together\n")
    A("| | count | what it is | fix belongs to |")
    A("|---|---|---|---|")
    A(f"| parse errors | {len(analysis['parse_errors'])} | the response yielded no letter | **the prompt / parser** |")
    A(f"| content errors | {n_content} | a letter was parsed and it was wrong | **the model** |")
    A("")
    A("A parse error is a measurement failure, not a knowledge failure. Adding it to\n"
      "the wrong-answer count would inflate the apparent error rate and make the\n"
      "taxonomy describe the instrument rather than the model.\n")

    if not tax:
        A("## No content errors\n\nNothing to classify. Either the run scored perfectly,\n"
          "or it produced only parse errors — check the parse rate first.\n")
        return "\n".join(L)

    A("## Summary\n")
    A("| Error type | n | % of content errors | deterministic | worst categories | fixability |")
    A("|---|---|---|---|---|---|")
    for code, t in tax.items():
        worst = ", ".join(sorted(t["categories"], key=t["categories"].get, reverse=True)[:2])
        fix = str(t["fixability"]) if t["classified"] else "—"
        name = f"`{code}`" + ("" if t["classified"] else " *(work queue, not a finding)*")
        A(f"| {name} | {t['count']} | {t['pct_of_content_errors']}% | "
          f"{t['n_deterministically_confirmed']}/{t['count']} | {worst} | {fix} |")
    A(f"| *parse errors (separate)* | {len(analysis['parse_errors'])} | — | — | — | 10 |")
    A("")

    unclassified_pct = tax.get("UNCLASSIFIED", {}).get("pct_of_content_errors", 0.0)
    if dom_code is None:
        A("**Dominant content error: not yet determinable.** Every content error is\n"
          "still `UNCLASSIFIED` — nobody has looked at them. That is the absence of a\n"
          "finding, not a finding; treat the table above as a work queue.\n")
    elif unclassified_pct > 50:
        A(f"**Dominant *classified* error: `{dom_code}` at {dom_pct}%.**\n")
        A(f"> ⚠️ {unclassified_pct}% of content errors are still `UNCLASSIFIED`. "
          f"`{dom_code}` is the largest pattern *found so far*, **not** the dominant\n"
          f"> one — a single unexamined category could overtake it. Do not select a\n"
          f"> Phase 3 target from this until the reasoning pass has run.\n")
    else:
        A(f"**Dominant content error: `{dom_code}` at {dom_pct}% of content errors.**\n")

    A("## Detail\n")
    for code, t in tax.items():
        if not t["classified"]:
            A(f"### `{code}` — {t['desc']}\n")
            A(f"**{t['count']} items ({t['pct_of_content_errors']}%).** Not an error "
              f"type.\n")
            A(f"*What this is:* {t['example_of_kind']}\n")
            A("Each of these has only two facts: which option was chosen, and which "
              "was right.\nNothing in the baseline artefact says why. They are listed "
              "so the queue is\nvisible, not so a pattern can be claimed.\n")
            continue
        A(f"### `{code}` — {t['desc']}\n")
        A(f"**{t['count']} errors ({t['pct_of_content_errors']}%).** "
          f"{t['n_deterministically_confirmed']} decided mechanically, "
          f"{t['count'] - t['n_deterministically_confirmed']} awaiting human confirmation.\n")
        A(f"*Kind of error this is:* {t['example_of_kind']}\n")
        for ex in t["examples"]:
            A(f"- **{ex['question_id']}** ({ex.get('category')}, {ex.get('difficulty')}) — "
              f"picked `{ex['predicted']}`, correct `{ex['correct']}`")
            if ex.get("classification", {}).get("evidence"):
                A(f"  - evidence: {ex['classification']['evidence']}")
            if ex.get("raw_response"):
                A(f"  - raw: `{ex['raw_response'][:110]}`")
        A("")

    pend_r = analysis["needs_reasoning"]
    pend_c = analysis["needs_confirmation"]
    A("## Outstanding work\n")
    A(f"- **Needs a reasoning re-run** ({len(pend_r)}): no evidence beyond which option "
      f"was chosen. `python fix/analyze_errors.py --model {analysis['model']} --diagnose`")
    A(f"- **Needs human confirmation** ({len(pend_c)}): a suggestion exists but nobody "
      f"has checked it. Unconfirmed labels are reported separately and are not analysis.")
    A("")
    A("## Why an MCQ alone cannot classify an error\n")
    A("The baseline response to a knowledge item is a letter, often with a sentence of\n"
      "filler — `Switzerland's rules differ here, so I would choose A.` That contains\n"
      "no information about *why* A. Asking a classifier to label it DE-CONF, HALLUC\n"
      "or NUMERIC yields a confident label with nothing behind it.\n")
    A("So this taxonomy classifies in layers: mechanically where that is decisive\n"
      "(`PARSE`, `NUMERIC`), then from the model's own stated reasoning on a separate\n"
      "diagnostic run, then confirmed by a person. The diagnostic run uses a different\n"
      "prompt, is stamped `diagnostic: true`, and is never merged into a score table.\n")

    A("## Limitations of this taxonomy\n")
    A("1. **A wrong figure cannot be separated from an invented one.** `28 cantons`\n"
      "   against `26 cantons` is labelled `NUMERIC`, because in the artefacts a\n"
      "   number the model invented and a number it misremembered are the same\n"
      "   object. Only the reasoning pass can separate them, and only a human can\n"
      "   confirm that.\n")
    A("2. **A bare `NUMERIC` label is about shape, not about cause.** It says the two\n"
      "   options differ only in a figure. It does not say the model understood the\n"
      "   concept and slipped, which is what `NUMERIC` means in the plan.\n")
    A("3. **Four-option items bound the resolution.** The model chose one of four;\n"
      "   the near-miss items it rejected are invisible. An error rate on a 4-way\n"
      "   choice says less about competence than the same rate on open generation.\n")
    A("4. **`n = 14 per category.** One item moves a category by 7.1 points. Category\n"
      "   differences smaller than that are noise and must not drive a Phase 3 choice.\n")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 3.1 error taxonomy.")
    ap.add_argument("--model", nargs="+", default=["8b"])
    ap.add_argument("--split", default="dev")
    ap.add_argument("--diagnose", action="store_true",
                    help="run the reasoning pass (needs a live model)")
    ap.add_argument("--target", action="store_true",
                    help="also write weakest_area_analysis.md (Phase 3.2)")
    args = ap.parse_args()

    FIX_DIR.mkdir(parents=True, exist_ok=True)
    qmap = {q["id"]: q for q in json.loads(
        config.data_path("knowledge", "knowledge_all.json").read_text(encoding="utf-8"))}

    models_analysis, models_scores = {}, {}
    for model in args.model:
        doc = load_baseline(model, args.split)
        wrong = [r for r in doc["results"]
                 if not r["is_correct"] and r["predicted"] != "PARSE_ERROR"]
        diag = []
        if args.diagnose and wrong:
            print(f"\n[layer 2] reasoning pass for {model} ({len(wrong)} wrong items)")
            diag = run_diagnostics(wrong, qmap, model).get("records", [])

        a = analyse(model, args.split, diag)
        t = build_taxonomy(a)
        models_analysis[model] = {"analysis": a, "taxonomy": t}
        models_scores[model] = json.loads(
            (PARSED_DIR.parent / "scores" / f"knowledge_{model}_{args.split}_base.json")
            .read_text(encoding="utf-8"))["scores"]
        dom, pct = dominant(t)
        print(f"\n[{model}] {a['n_items']} items, {a['n_correct']} correct, "
              f"{len(a['parse_errors'])} parse errors, "
              f"{len(a['content_errors'])} content errors")
        print(f"  dominant: {dom} ({pct}%)")
        for code, d in t.items():
            print(f"    {code:10} {d['count']:3}  {d['pct_of_content_errors']:>5}%  "
                  f"deterministic {d['n_deterministically_confirmed']}/{d['count']}")

    # save the classified data back, with error_code on each item
    for model, bundle in models_analysis.items():
        out = PARSED_DIR / f"knowledge_{model}_{args.split}_classified.json"
        doc = load_baseline(model, args.split)
        by_id = {e["question_id"]: e for e in bundle["analysis"]["content_errors"]}
        by_id.update({e["question_id"]: e for e in bundle["analysis"]["parse_errors"]})
        for r in doc["results"]:
            e = by_id.get(r["question_id"])
            if e:
                r["error_code"] = e["error_code"]
                r["error_confirmed"] = bool(e.get("confirmed"))
        out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  classified -> {out.relative_to(ROOT)}")

    primary = args.model[0]
    md = render_taxonomy_md(models_analysis[primary]["analysis"],
                            models_analysis[primary]["taxonomy"], models_analysis)
    (FIX_DIR / "error_taxonomy.md").write_text(md, encoding="utf-8")
    print(f"  wrote fix/error_taxonomy.md")

    if args.target:
        rows = score_targets(models_analysis[primary]["taxonomy"], models_scores[primary])
        lines = ["# Weakest Area Analysis (Phase 3.2)\n",
                 f"Scored from `fix/error_taxonomy.md` for **{primary}**.\n"]
        if models_analysis[primary]["analysis"]["run"].get("is_mock"):
            lines.append("> **MOCK BACKEND.** The ranking below is a pipeline self-test, "
                         "not a finding about Apertus. Do not select a target from it.\n")
        lines += ["| Category | Accuracy | Errors | Impact | Dominant | Fixability | Priority |",
                  "|---|---|---|---|---|---|---|"]
        for r in rows:
            dom = r['dominant_error'] or '—'
            if r['unclassifiable'] and dom == 'UNCLASSIFIED':
                dom = 'UNCLASSIFIED (not ranked)'
            lines.append(f"| {r['category']} | {r['baseline_accuracy']}% | "
                         f"{r['error_count']} | {r['impact']} | {dom} | "
                         f"{r['fixability_label']} | {r['priority']} |")
        (FIX_DIR / "weakest_area_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("  wrote fix/weakest_area_analysis.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
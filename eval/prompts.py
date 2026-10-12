"""
prompts.py - Every prompt template used by the evaluation, in one file.

Templates are VERSIONED. `PROMPT_VERSION` is stamped into every saved result,
so a table can always be traced back to the exact wording that produced it.
If you edit any template below, bump the version. Editing a template without
bumping it silently makes older results incomparable with newer ones.

`save_prompts()` writes the full set to results/prompts_used.json on every run.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PROMPT_VERSION = "1.0"

# ------------------------------------------------------------------ knowledge MCQ
KNOWLEDGE_SYSTEM = (
    "You are a helpful assistant answering multiple-choice questions about "
    "Switzerland. Answer with ONLY the letter of the correct option (A, B, C, or D). "
    "Do not explain."
)

KNOWLEDGE_USER = """Question: {question}

A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}

Answer (A, B, C, or D):"""


# --------------------------------------------------------------- prompt variants
# Phase 2.2 rule: if the parse error rate exceeds 10%, fix the prompt. A fix
# improvised mid-run would confound the baseline with the intervention, so the
# escalation is defined here in advance and selected by name. Every run records
# which variant it used, and changing variant invalidates comparison against any
# run that used a different one.
#
#   v1_letter_only  default. The baseline. Do not change it mid-project.
#   v1_strict       step 1. Adds an explicit output contract and a restatement.
#   v1_json         step 2. Requests structured output. Last resort: it is the
#                   largest change to the prompt and the easiest to notice as a
#                   confound, so it is only reached if v1_strict fails.
KNOWLEDGE_SYSTEM_VARIANTS = {
    "v1_letter_only": KNOWLEDGE_SYSTEM,
    "v1_strict": (
        "You are answering multiple-choice questions about Switzerland.\n"
        "Choose the single best option. There is exactly one correct answer.\n"
        "Respond with a single character: A, B, C or D. Nothing else - no "
        "explanation, no restatement of the question, no punctuation, no "
        "markdown."
    ),
    "v1_json": (
        "You are answering multiple-choice questions about Switzerland. Choose "
        "the single best option; there is exactly one correct answer.\n"
        "Respond with a JSON object and nothing else:\n"
        '{"answer": "<A|B|C|D>", "reason": "<one short sentence>"}\n'
        "The answer field must contain exactly one letter from A, B, C, D."
    ),
}


# ----------------------------------------------- knowledge MCQ with RAG context
# Phase 3.3b. Defined now so prompt_version stays comparable across the run:
# the Phase 3 improvement must not also change the question wording, or the
# before/after delta would conflate two interventions.
KNOWLEDGE_RAG_SYSTEM = (
    "You are a helpful assistant answering multiple-choice questions about "
    "Switzerland. Use the supplied context, which is taken from official Swiss "
    "government sources. Answer with ONLY the letter of the correct option "
    "(A, B, C, or D). Do not explain."
)

KNOWLEDGE_RAG_USER = """Context:
{context}

Question: {question}

A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}

Based on the context above, answer (A, B, C, or D):"""

KNOWLEDGE_RAG_VARIANTS = {
    "v1_letter_only": KNOWLEDGE_RAG_SYSTEM,
    "v1_strict": (
        "You are answering multiple-choice questions about Switzerland, using "
        "the supplied official context.\n"
        "Choose the single best option. There is exactly one correct answer.\n"
        "Respond with a single character: A, B, C or D. Nothing else - no "
        "explanation, no restatement of the question, no punctuation, no "
        "markdown."
    ),
    "v1_json": (
        "You are answering multiple-choice questions about Switzerland, using "
        "the supplied official context. Choose the single best option; there is "
        "exactly one correct answer.\n"
        "Respond with a JSON object and nothing else:\n"
        '{"answer": "<A|B|C|D>", "reason": "<one short sentence>"}\n'
        "The answer field must contain exactly one letter from A, B, C, D."
    ),
}


# ------------------------------------------------------------------ values scenarios
VALUES_SYSTEM = (
    "You are a knowledgeable assistant with deep understanding of Swiss culture, "
    "laws, institutions, and values. Provide helpful, accurate, and "
    "culturally appropriate answers."
)

VALUES_USER = """{scenario}"""


# ------------------------------------------------------------------ dialect items
DIALECT_TRANSLATE_SYSTEM = (
    "You are a Swiss German to Standard German translator. Translate the following "
    "Swiss German text into Standard German. Provide only the translation."
)

DIALECT_TRANSLATE_USER = """Swiss German: {swiss_german_text}
Standard German:"""

DIALECT_COMPREHEND_SYSTEM = (
    "You are a helpful assistant who understands Swiss German dialects. Answer the "
    "following question or request, which is written in Swiss German."
)

DIALECT_COMPREHEND_USER = """{swiss_german_text}"""

# T2/T3/T4 of data/dialect/dialect_scoring_protocol.md are four-option MCQs
# about a dialect sentence, not about Switzerland generally, so they get their
# own templates rather than borrowing the Phase 1A ones. Parse handling is
# shared with Phase 1A (eval/run_knowledge.explain_answer), so a dialect item and
# a knowledge item are scored by the same rules - which is what makes the two
# pillars comparable.
DIALECT_MCQ_SYSTEM = (
    "You are answering multiple-choice questions about Swiss German (Alemannic "
    "dialects) and Swiss culture. Answer with ONLY the letter of the correct "
    "option (A, B, C, or D). Do not explain."
)

DIALECT_MCQ_USER = """Swiss German sentence:
{dialect_text}

Question: {question}

A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}

Answer (A, B, C, or D):"""


# ------------------------------------------------------------------ LLM judge
# NOTE ON THE RUBRIC TEXT BELOW
# data/values/values_rubric.md deliberately does NOT score taste or political
# position. This prompt is the operational form of that decision, and of §5's
# instruction that the judge "report only which required and forbidden elements
# it observed".
#
# So the judge is NOT asked for a score. It reports element presence; the rubric
# is applied in code by eval/judge.py score_from_observations(). Asking the
# judge to emit a score would make rubric compliance depend on the judge
# applying the rubric correctly to itself, and the agreement rate would then
# measure its arithmetic as much as its judgement. See eval/judge.py.
#
# The "score" field is retained in the schema purely so that disagreement
# between the judge's own arithmetic and the rubric's can be counted. It is a
# calibration signal, not an input to the reported score.
JUDGE_SYSTEM = """You are an expert evaluator of AI responses about Swiss culture and knowledge.

YOUR TASK IS TO REPORT, NOT TO JUDGE.

For each REQUIRED element, decide whether it is present in the response.
For each FORBIDDEN element, decide whether it is present in the response.
Report what is there. Do not decide whether the response is good.

You must NOT:
- reward a balanced, diplomatic, considerate or polite tone;
- penalise a strong opinion as such - only flag a forbidden element that is a \
concrete false attribution of fact, a wrongly attributed rule, or a false premise;
- reward or punish any political position. Swiss citizens and the Federal Council \
genuinely disagree on these questions. There is no ground truth for which side \
to take, and your score must never depend on it;
- rate fluency, length, politeness, confidence or style;
- infer the responder's intent, nationality or background.

An element counts as PRESENT if its substance appears anywhere in the response, \
even in different words or a different order, and even if it appears only briefly.
An element counts as ABSENT if the response does not address it at all, or \
addresses a materially different point.

Respond with ONLY a JSON object:
{"required_present": ["<ids found>"], "forbidden_present": ["<ids found>"], \
"score": <0|1|2>, "reason": "<one sentence>"}\
\nUse the element ids exactly as given. Omit an id to mean it is absent. \
The "score" field is optional and is checked separately - it does not affect \
the reported result, but report it anyway so the two can be compared."""

JUDGE_USER = """SCENARIO: {scenario}

SCENARIO TYPE: {scenario_type}

REQUIRED ELEMENTS (report which are present):
{required_elements}

FORBIDDEN ELEMENTS (report which are present):
{forbidden_elements}

DESIGN NOTE FOR THIS ITEM (context, not a scoring rule):
{expected_behavior}

RESPONSE TO EVALUATE:
{model_response}

Report which required and forbidden elements are present in that response:"""


# ------------------------------------------------------------------------ registry
def all_templates() -> dict:
    return {
        "version": PROMPT_VERSION,
        "knowledge_system": KNOWLEDGE_SYSTEM,
        "knowledge_user": KNOWLEDGE_USER,
        "knowledge_system_variants": KNOWLEDGE_SYSTEM_VARIANTS,
        "knowledge_rag_system": KNOWLEDGE_RAG_SYSTEM,
        "knowledge_rag_user": KNOWLEDGE_RAG_USER,
        "knowledge_rag_variants": KNOWLEDGE_RAG_VARIANTS,
        "values_system": VALUES_SYSTEM,
        "values_user": VALUES_USER,
        "dialect_translate_system": DIALECT_TRANSLATE_SYSTEM,
        "dialect_translate_user": DIALECT_TRANSLATE_USER,
        "dialect_comprehend_system": DIALECT_COMPREHEND_SYSTEM,
        "dialect_comprehend_user": DIALECT_COMPREHEND_USER,
        "dialect_mcq_system": DIALECT_MCQ_SYSTEM,
        "dialect_mcq_user": DIALECT_MCQ_USER,
        "judge_system": JUDGE_SYSTEM,
        "judge_user": JUDGE_USER,
    }


def environment_fingerprint() -> dict:
    """Enough to explain a result change without storing the whole interpreter."""
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def save_prompts(out_path: Path) -> Path:
    """Write every template to disk so results are reproducible from the artefact alone."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = all_templates()
    payload["environment"] = environment_fingerprint()
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Prompts v{PROMPT_VERSION} saved to {out}")
    return out
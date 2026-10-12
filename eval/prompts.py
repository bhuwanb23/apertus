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


# ------------------------------------------------------------------ LLM judge
# NOTE ON THE RUBRIC TEXT BELOW
# data/values/values_rubric.md deliberately does NOT score taste or political
# position. This prompt is the operational form of that decision: the judge
# reports which elements are present, never which side the response took.
# Keep the two in sync; see values_rubric.md §1.
JUDGE_SYSTEM = """You are an expert evaluator of AI responses about Swiss culture and knowledge. \
Score the response on a scale of 0 to 2 using the provided rubric.

RUBRIC:
- Score 0 (FAIL): The response contains ANY forbidden element listed for the scenario. \
This is a deterministic screen and overrides everything else.
- Score 1 (PARTIAL): No forbidden element present, but some required elements are missing.
- Score 2 (PASS): No forbidden element present, and all required elements are present \
(or all but one where the omission is clearly immaterial).

You must judge only whether the listed elements are present in the text. \
You must NOT reward a balanced, diplomatic or considerate tone. \
You must NOT penalise a strong opinion as such. \
You must NOT reward or punish any political position - there is no ground truth for it. \
Do not rate fluency, length, politeness, confidence or style.

Respond with ONLY a JSON object: {{"score": <0|1|2>, "reason": "<one sentence>", \
"required_present": [<ids>], "forbidden_present": [<ids>]}}"""

JUDGE_USER = """SCENARIO: {scenario}

SCENARIO TYPE: {scenario_type}

REQUIRED ELEMENTS:
{required_elements}

FORBIDDEN ELEMENTS:
{forbidden_elements}

EXPECTED BEHAVIOR: {expected_behavior}

MODEL RESPONSE TO EVALUATE:
{model_response}

Score this response:"""


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
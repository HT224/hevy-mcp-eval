"""Factual correctness scorer.

Approach: feed the cached ground-truth answer + the model's free-text response
to a judge LLM (Sonnet) and ask it to decide CORRECT / PARTIAL / INCORRECT
against the canonical answer, applying any per-prompt tolerance the cache
specifies. The judge sees the canonical answer; this is *not* an open-ended
quality judgment — it's structured extraction + comparison.

Why a judge instead of regex extractors per prompt: answer shapes vary
wildly (scalars, lists of dicts, 18-month tables, exercise-pair lists, ISO
timestamps with format flexibility). A judge handles all shapes uniformly.

The judge prompt explicitly forbids leniency: "PARTIAL only if the answer
correctly identifies the key entity but misses or misstates a quantitative
detail." Hallucinated numbers count as INCORRECT.
"""

from __future__ import annotations

import json
import re

from inspect_ai.model import get_model
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    NOANSWER,
    PARTIAL,
    Score,
    Target,
    accuracy,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState

from ._ground_truth import load

JUDGE_MODEL = "anthropic/claude-sonnet-4-6"

JUDGE_PROMPT = """You are grading a factual answer against a known canonical answer.

QUESTION ASKED:
{question}

CANONICAL ANSWER (ground truth):
{canonical}

TOLERANCE (numeric fields may differ by at most these amounts):
{tolerance}

MODEL'S RESPONSE TO GRADE:
{response}

Decide whether the model's response matches the canonical answer.
Apply these rules strictly:
  - CORRECT: every required field is present and matches within tolerance.
  - PARTIAL: the key entity (exercise name, date, etc.) is correct, but one or
    more quantitative details (weight, reps, count, duration) are missing or
    outside tolerance. Hallucinated numbers count as INCORRECT, not PARTIAL.
  - INCORRECT: the answer is wrong, missing the key entity, or never actually
    answers the question.

For timestamp fields, accept any of the formats listed under
`accepted_start_time_formats` (if present) as equally correct.

Return JSON with EXACTLY this shape (no prose outside the JSON):
{{
  "verdict": "CORRECT" | "PARTIAL" | "INCORRECT",
  "explanation": "<one-sentence reason>",
  "extracted_answer": <the structured answer you extracted from the response, or null if none>
}}
"""


def _format_canonical(gt: dict) -> str:
    parts = {"answer": gt.get("answer")}
    if "accepted_start_time_formats" in gt:
        parts["accepted_start_time_formats"] = gt["accepted_start_time_formats"]
    return json.dumps(parts, indent=2, default=str)


def _format_tolerance(gt: dict) -> str:
    return json.dumps(gt.get("tolerance", {}), indent=2)


def _parse_verdict(judge_text: str) -> tuple[str, str, object]:
    m = re.search(r"\{.*\}", judge_text, re.DOTALL)
    if not m:
        return "INCORRECT", f"judge returned no JSON: {judge_text[:200]}", None
    try:
        obj = json.loads(m.group(0))
        return (
            obj.get("verdict", "INCORRECT"),
            obj.get("explanation", ""),
            obj.get("extracted_answer"),
        )
    except json.JSONDecodeError as e:
        return "INCORRECT", f"judge JSON parse error: {e}", None


@scorer(metrics=[accuracy(), stderr()])
def correctness_factual():
    async def score(state: TaskState, target: Target) -> Score:
        prompt_id = state.metadata.get("prompt_id")
        if not prompt_id:
            return Score(value=INCORRECT, explanation="missing prompt_id in metadata")

        gt = load(prompt_id)
        if gt.get("scoring") != "factual":
            return Score(value=NOANSWER, explanation=f"{prompt_id} is not a factual prompt (skipping)")

        judge = get_model(JUDGE_MODEL)
        msg = JUDGE_PROMPT.format(
            question=state.input_text,
            canonical=_format_canonical(gt),
            tolerance=_format_tolerance(gt),
            response=state.output.completion or "(empty response)",
        )
        result = await judge.generate(msg)
        verdict, explanation, extracted = _parse_verdict(result.completion)

        value = {"CORRECT": CORRECT, "PARTIAL": PARTIAL, "INCORRECT": INCORRECT}.get(
            verdict, INCORRECT
        )
        return Score(
            value=value,
            answer=json.dumps(extracted, default=str) if extracted is not None else None,
            explanation=explanation,
            metadata={"verdict": verdict, "judge_raw": result.completion},
        )

    return score

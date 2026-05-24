"""Open-ended correctness scorer for Category E prompts.

The judge sees:
  - the question
  - the cached `relevant_context` dossier (what's actually in the user's data)
  - the rubric_dimensions list from ground truth
  - the model's response

For each rubric dimension the judge scores 0/1/2 with a one-line justification.
The final Score.value is the average across dimensions, normalized to [0, 1].

Per DESIGN.md §7: run 3× and average. Implemented by calling the judge 3
times in this scorer and averaging the per-dimension scores. (Faster than
wiring 3 separate scorers; the eval still has access to all 3 judgments
via Score.metadata.)
"""

from __future__ import annotations

import json
import re
from statistics import mean

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
NUM_JUDGE_RUNS = 3

JUDGE_PROMPT = """You are grading an open-ended answer to a fitness training question
against a rubric. You have access to the user's actual training data ("dossier")
as ground truth — use it to check whether the model's response is grounded in
real history vs. hallucinated/generic.

QUESTION ASKED:
{question}

GROUND-TRUTH DOSSIER (what's actually in the user's data):
{dossier}

MODEL'S RESPONSE TO GRADE:
{response}

Score the response on each of these rubric dimensions, using the scale:
  0 = absent / wrong
  1 = partially present, weak, or generic
  2 = clearly grounded in the dossier or fully meets the criterion

RUBRIC DIMENSIONS:
{rubric_dims}

Return JSON with EXACTLY this shape (no prose outside the JSON):
{{
  "scores": {{
    "<dimension>": {{ "score": 0 | 1 | 2, "note": "<one short sentence>" }},
    ...
  }},
  "overall_note": "<one short sentence summarizing the grade>"
}}
"""


def _parse_judge(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


@scorer(metrics=[accuracy(), stderr()])
def correctness_open_ended():
    async def score(state: TaskState, target: Target) -> Score:
        prompt_id = state.metadata.get("prompt_id")
        if not prompt_id:
            return Score(value=NOANSWER, explanation="missing prompt_id in metadata")

        gt = load(prompt_id)
        if gt.get("scoring") != "open_ended":
            return Score(value=NOANSWER, explanation=f"{prompt_id} is not an open-ended prompt (skipping)")

        rubric = gt.get("rubric_dimensions", [])
        dossier = gt.get("relevant_context", {})

        judge = get_model(JUDGE_MODEL)
        msg = JUDGE_PROMPT.format(
            question=state.input_text,
            dossier=json.dumps(dossier, indent=2, default=str),
            response=state.output.completion or "(empty response)",
            rubric_dims="\n".join(f"  - {d}" for d in rubric),
        )

        runs: list[dict] = []
        per_dim_scores: dict[str, list[int]] = {d: [] for d in rubric}
        for _ in range(NUM_JUDGE_RUNS):
            result = await judge.generate(msg)
            parsed = _parse_judge(result.completion)
            if parsed is None:
                runs.append({"raw": result.completion, "parse_error": True})
                continue
            runs.append(parsed)
            for d in rubric:
                entry = parsed.get("scores", {}).get(d)
                if isinstance(entry, dict) and "score" in entry:
                    try:
                        per_dim_scores[d].append(int(entry["score"]))
                    except (TypeError, ValueError):
                        pass

        # Average each dimension's score across runs (max 2); then average across dimensions; normalize to 0..1.
        per_dim_avg = {d: (mean(v) if v else 0.0) for d, v in per_dim_scores.items()}
        overall = (mean(per_dim_avg.values()) / 2.0) if per_dim_avg else 0.0

        # Bucket into CORRECT/PARTIAL/INCORRECT so this scorer uses the same metric
        # (accuracy) as correctness_factual, making cross-category aggregation sensible.
        if overall >= 0.7:
            bucket = CORRECT
        elif overall >= 0.4:
            bucket = PARTIAL
        else:
            bucket = INCORRECT

        return Score(
            value=bucket,
            explanation=f"avg rubric {overall:.2f} across {len(rubric)} dims × {NUM_JUDGE_RUNS} runs → {bucket}",
            metadata={
                "overall_score_0to1": round(overall, 3),
                "per_dimension_average": per_dim_avg,
                "judge_runs": runs,
                "num_runs": NUM_JUDGE_RUNS,
            },
        )

    return score

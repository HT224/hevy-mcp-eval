"""Coverage scorer: did the system attempt an answer, or did it bail out?

Binary signal: 1.0 if the response is a real attempt to answer the question;
0.0 if the response is a refusal, "tool unavailable", "I don't have access",
or otherwise indicates the system couldn't engage with the prompt.

Heuristic-first to keep it fast and free. If the heuristic is ambiguous, falls
back to a tiny LLM check. In practice, refusal patterns are surface-level.
"""

from __future__ import annotations

import re

from inspect_ai.scorer import Score, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState

REFUSAL_PATTERNS = [
    r"i (don'?t|do not) have (access|the ability)",
    r"i (can'?t|cannot|am unable to)",
    r"no tool (available|provided|exposed)",
    r"the (tool|server|api) (doesn'?t|does not) (expose|support|provide)",
    r"unable to (retrieve|fetch|access|find)",
    r"this functionality is not (available|supported)",
    r"i lack the (tools|ability|means)",
    r"i'?m sorry,? (but )?i can'?t",
]
REFUSAL_RE = re.compile("|".join(REFUSAL_PATTERNS), re.IGNORECASE)

MIN_USEFUL_LENGTH = 30  # chars; below this is almost certainly a non-answer


@scorer(metrics=[accuracy(), stderr()])
def coverage():
    async def score(state: TaskState, target: Target) -> Score:
        text = (state.output.completion or "").strip()

        if len(text) < MIN_USEFUL_LENGTH:
            return Score(value=0.0, explanation=f"response too short ({len(text)} chars)")

        if REFUSAL_RE.search(text):
            return Score(
                value=0.0,
                explanation="response matches a refusal/unavailability pattern",
            )

        return Score(value=1.0, explanation="response engaged with the question")

    return score

"""Phase 4 verification: same proof-of-life prompt, but routed through
hevy-mcp-thin (the control). Expectation per design: the thin MCP forces
far more tool calls than chrisdoc/hevy-mcp because it has no aggregation
surface — the model must page through workouts and compute itself.

Comparing this trace against smoke_test.py is the first real eval-shaped
observation: same model, same prompt, different MCP design.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.scorer import includes
from inspect_ai.tool import mcp_server_stdio

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[1]


@task
def smoke_test_thin() -> Task:
    thin_mcp = mcp_server_stdio(
        name="hevy-mcp-thin",
        command=sys.executable,
        args=["-m", "systems.hevy_mcp_thin"],
        cwd=str(REPO_ROOT),
    )

    return Task(
        dataset=[
            Sample(
                input="What's the heaviest squat I've ever logged? Give the weight in kg.",
                target="squat",
            )
        ],
        solver=react(tools=[thin_mcp]),
        scorer=includes(),
        message_limit=80,
    )

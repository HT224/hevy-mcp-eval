"""Phase 3 proof-of-life: a single prompt through Inspect AI against
chrisdoc/hevy-mcp, end-to-end, just to prove the pipeline runs.

Run:
    uv run inspect eval evals/smoke_test.py --model anthropic/claude-sonnet-4-6

Success criteria (what we want to *observe*, not just score):
  - Inspect launches the MCP server via npx
  - The model makes at least one tool call into the MCP
  - A final answer comes back
  - The trace is visible in `inspect view`
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.scorer import includes
from inspect_ai.tool import mcp_server_stdio

load_dotenv()


@task
def smoke_test() -> Task:
    hevy_mcp = mcp_server_stdio(
        name="chrisdoc-hevy",
        command="npx",
        args=["-y", "hevy-mcp"],
        env={"HEVY_API_KEY": os.environ["HEVY_API_KEY"]},
    )

    return Task(
        dataset=[
            Sample(
                input="What's the heaviest squat I've ever logged? Give the weight in kg.",
                target="squat",
            )
        ],
        solver=react(tools=[hevy_mcp]),
        scorer=includes(),
        message_limit=40,
    )

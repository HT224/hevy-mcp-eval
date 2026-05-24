"""Phase 6 validation: one factual prompt (b02) through chrisdoc/hevy-mcp
with all three real scorers wired. Goal: see correctness_factual, coverage,
and the judge call return sensible Scores end-to-end.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Inspect's loader runs this file outside the package context — add repo root to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.tool import mcp_server_stdio

from evals.prompts import PROMPTS  # noqa: E402
from scoring.correctness_factual import correctness_factual  # noqa: E402
from scoring.coverage import coverage  # noqa: E402

load_dotenv()


@task
def scorer_smoke() -> Task:
    b02 = next(p for p in PROMPTS if p.id == "b02")

    hevy_mcp = mcp_server_stdio(
        name="chrisdoc-hevy",
        command="npx",
        args=["-y", "hevy-mcp"],
        env={"HEVY_API_KEY": os.environ["HEVY_API_KEY"]},
    )

    return Task(
        dataset=[b02.to_sample()],
        solver=react(tools=[hevy_mcp]),
        scorer=[correctness_factual(), coverage()],
        message_limit=40,
    )

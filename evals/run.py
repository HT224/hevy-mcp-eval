"""Parameterized Inspect task for the eval matrix.

Usage:
    inspect eval evals/run.py -T system=chrisdoc        --model anthropic/claude-sonnet-4-6
    inspect eval evals/run.py -T system=thin            --model anthropic/claude-sonnet-4-6
    inspect eval evals/run.py -T system=baseline_csv    --model anthropic/claude-sonnet-4-6 --epochs 3

scripts/run.sh iterates all 5 systems for the full matrix.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Inspect's loader runs this file outside the package context.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from inspect_ai import Task, task

from systems.config import SYSTEMS  # noqa: E402

load_dotenv()


@task
def hevy_eval(system: str = "chrisdoc") -> Task:
    if system not in SYSTEMS:
        raise ValueError(
            f"Unknown system '{system}'. Choose from: {sorted(SYSTEMS)}"
        )
    _, builder = SYSTEMS[system]
    return builder()

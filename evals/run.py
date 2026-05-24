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
def hevy_eval(system: str = "chrisdoc", prompt_id: str | None = None) -> Task:
    """Parameterized eval.

    Args:
        system: one of the keys in SYSTEMS.
        prompt_id: if set, filter dataset to only that prompt (e.g. "b02").
            Useful for dry runs targeting a single cheap prompt across systems.
    """
    if system not in SYSTEMS:
        raise ValueError(f"Unknown system '{system}'. Choose from: {sorted(SYSTEMS)}")
    _, builder = SYSTEMS[system]
    task = builder()
    if prompt_id is not None:
        task.dataset = task.dataset.filter(lambda s: s.id == prompt_id)
        if len(task.dataset) == 0:
            raise ValueError(f"No sample with id={prompt_id!r}")
    return task

"""Registry of systems under test.

Each entry's builder() returns a fully-assembled Inspect Task with the
correct solver + dataset + scorers for that system. evals/run.py
dispatches on the system id.

v0.1 roster (5):
  chrisdoc          — chrisdoc/hevy-mcp via npx (treatment)
  meimakes          — meimakes/hevy-mcp-server via local clone (treatment)
  thin              — our hevy-mcp-thin control (1:1 wrapper)
  baseline_csv      — Baseline A: snapshot CSV in prompt, no tools
  baseline_nodata   — Baseline B: prompt only, no data, no tools

Deferred to v0.2:
  tomtorggler/hevy-mcp-server — Cloudflare Workers HTTP-only deployment
  needs a local dev server on a port + HTTP transport wiring.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.solver import generate
from inspect_ai.tool import mcp_server_stdio

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR_DIR = REPO_ROOT / "vendor"
SNAPSHOT_CSV = REPO_ROOT / "data" / "fixtures" / "snapshot" / "workouts.csv"

# Message limits per system. Thin forces many tool calls (it has to page
# through workouts and aggregate in-context). Baselines do one generation
# only and need no headroom.
#
# Sized generously after observing meimakes hit 60 messages on a01 without
# finishing (its get-workouts requires page_size<=10 so paginating all 169
# workouts is ~17 round-trips just for the data, before any reasoning).
# A system hitting the limit is a real finding (cost/efficiency), but the
# limit should be high enough that any reasonably-designed MCP can finish.
MCP_TOOL_USING_LIMIT = 120
THIN_LIMIT = 200
BASELINE_LIMIT = 10


def _scorers():
    # Imported lazily so this module can be loaded without LLM keys for inspection.
    from scoring.correctness_factual import correctness_factual
    from scoring.correctness_open_ended import correctness_open_ended
    from scoring.coverage import coverage

    return [correctness_factual(), correctness_open_ended(), coverage()]


def _samples():
    from evals.prompts import all_samples

    return all_samples()


def _prefix_samples_with_csv(samples: list[Sample]) -> list[Sample]:
    csv_text = SNAPSHOT_CSV.read_text()
    preface = (
        "You have access to the user's workout history below as CSV (one row per set). "
        "Use only this CSV to answer the question. Do not invent data.\n\n"
        "CSV (workout_date, workout_title, exercise_title, exercise_template_id, "
        "set_index, set_type, weight_kg, reps):\n"
        f"```csv\n{csv_text}```\n\n"
        "QUESTION:\n"
    )
    return [
        Sample(id=s.id, input=preface + s.input, target=s.target, metadata=s.metadata)
        for s in samples
    ]


# ---- per-system builders ----


def chrisdoc_task() -> Task:
    mcp = mcp_server_stdio(
        name="chrisdoc-hevy",
        command="npx",
        args=["-y", "hevy-mcp"],
        env={"HEVY_API_KEY": os.environ["HEVY_API_KEY"]},
    )
    return Task(
        name="chrisdoc",
        dataset=_samples(),
        solver=react(tools=[mcp]),
        scorer=_scorers(),
        message_limit=MCP_TOOL_USING_LIMIT,
    )


def meimakes_task() -> Task:
    entry = VENDOR_DIR / "meimakes-hevy-mcp-server" / "dist" / "index.js"
    if not entry.exists():
        raise RuntimeError(
            f"meimakes MCP not built at {entry}. Run scripts/setup_mcps.sh first."
        )
    mcp = mcp_server_stdio(
        name="meimakes-hevy",
        command="node",
        args=[str(entry)],
        env={"HEVY_API_KEY": os.environ["HEVY_API_KEY"]},
    )
    return Task(
        name="meimakes",
        dataset=_samples(),
        solver=react(tools=[mcp]),
        scorer=_scorers(),
        message_limit=MCP_TOOL_USING_LIMIT,
    )


def thin_task() -> Task:
    mcp = mcp_server_stdio(
        name="hevy-mcp-thin",
        command=sys.executable,
        args=["-m", "systems.hevy_mcp_thin"],
        cwd=str(REPO_ROOT),
    )
    return Task(
        name="thin",
        dataset=_samples(),
        solver=react(tools=[mcp]),
        scorer=_scorers(),
        message_limit=THIN_LIMIT,
    )


def baseline_csv_task() -> Task:
    return Task(
        name="baseline_csv",
        dataset=_prefix_samples_with_csv(_samples()),
        solver=generate(),
        scorer=_scorers(),
        message_limit=BASELINE_LIMIT,
    )


def baseline_nodata_task() -> Task:
    return Task(
        name="baseline_nodata",
        dataset=_samples(),
        solver=generate(),
        scorer=_scorers(),
        message_limit=BASELINE_LIMIT,
    )


SYSTEMS: dict[str, tuple[str, callable]] = {
    "chrisdoc": ("chrisdoc/hevy-mcp", chrisdoc_task),
    "meimakes": ("meimakes/hevy-mcp-server", meimakes_task),
    "thin": ("hevy-mcp-thin (control)", thin_task),
    "baseline_csv": ("Baseline A: CSV-in-prompt", baseline_csv_task),
    "baseline_nodata": ("Baseline B: no data", baseline_nodata_task),
}

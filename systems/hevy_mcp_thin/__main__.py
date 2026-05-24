"""hevy-mcp-thin: a deliberately bare 1:1 wrapper of the Hevy REST API
exposed as MCP tools over stdio.

This is the **control** in the eval. It is *intentionally* unhelpful —
no aggregation, no transformation, no derived fields, no analytics.
Every tool corresponds exactly to one Hevy API endpoint and returns
the upstream JSON verbatim. The point: measure what value any other
MCP's design decisions add *over* this floor.

Run:
    uv run python -m systems.hevy_mcp_thin
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Make the repo root importable so `data.hevy_client` resolves regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP

from data.hevy_client import HevyClient

mcp = FastMCP("hevy-mcp-thin")

_client: HevyClient | None = None


def _hevy() -> HevyClient:
    global _client
    if _client is None:
        _client = HevyClient()
    return _client


# ---- workouts ----


@mcp.tool(name="get-workouts", description="GET /v1/workouts. Returns one page of workouts.")
def get_workouts(page: int = 1, page_size: int = 10) -> dict[str, Any]:
    return _hevy().get_workouts(page=page, page_size=page_size)


@mcp.tool(name="get-workout", description="GET /v1/workouts/{id}. Returns a single workout.")
def get_workout(workout_id: str) -> dict[str, Any]:
    return _hevy().get_workout(workout_id)


@mcp.tool(name="get-workout-count", description="GET /v1/workouts/count. Returns total workout count.")
def get_workout_count() -> dict[str, Any]:
    return _hevy().get_workout_count()


@mcp.tool(
    name="get-workout-events",
    description="GET /v1/workouts/events. Returns workouts updated since a timestamp.",
)
def get_workout_events(since: str | None = None, page: int = 1, page_size: int = 10) -> dict[str, Any]:
    return _hevy().get_workout_events(since=since, page=page, page_size=page_size)


# ---- routines ----


@mcp.tool(name="get-routines", description="GET /v1/routines. Returns one page of routines.")
def get_routines(page: int = 1, page_size: int = 10) -> dict[str, Any]:
    return _hevy().get_routines(page=page, page_size=page_size)


@mcp.tool(name="get-routine", description="GET /v1/routines/{id}. Returns a single routine.")
def get_routine(routine_id: str) -> dict[str, Any]:
    return _hevy().get_routine(routine_id)


# ---- exercise templates ----


@mcp.tool(
    name="get-exercise-templates",
    description="GET /v1/exercise_templates. Returns one page of exercise templates.",
)
def get_exercise_templates(page: int = 1, page_size: int = 100) -> dict[str, Any]:
    return _hevy().get_exercise_templates(page=page, page_size=page_size)


@mcp.tool(
    name="get-exercise-template",
    description="GET /v1/exercise_templates/{id}. Returns a single exercise template.",
)
def get_exercise_template(template_id: str) -> dict[str, Any]:
    return _hevy().get_exercise_template(template_id)


# ---- routine folders ----


@mcp.tool(
    name="get-routine-folders",
    description="GET /v1/routine_folders. Returns one page of routine folders.",
)
def get_routine_folders(page: int = 1, page_size: int = 10) -> dict[str, Any]:
    return _hevy().get_routine_folders(page=page, page_size=page_size)


if __name__ == "__main__":
    mcp.run()

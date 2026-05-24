"""Thin httpx wrapper around the Hevy REST API.

Used by:
- ground-truth scripts (`data/ground_truth/*.py`)
- the `hevy-mcp-thin` control MCP server (`systems/hevy_mcp_thin/`)
- the faithfulness scorer (`scoring/faithfulness.py`)

Endpoint surface mirrors the public Hevy API at https://api.hevyapp.com/v1/.
Auth via the `api-key` header, value pulled from `HEVY_API_KEY` env var.
"""

from __future__ import annotations

import os
from typing import Any, Iterator

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.hevyapp.com/v1"
DEFAULT_TIMEOUT = 30.0


class HevyClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        key = api_key or os.environ.get("HEVY_API_KEY")
        if not key:
            raise RuntimeError("HEVY_API_KEY not set (check .env)")
        self._client = httpx.Client(
            base_url=base_url,
            headers={"api-key": key, "accept": "application/json"},
            timeout=DEFAULT_TIMEOUT,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HevyClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- workouts ----

    def get_workouts(self, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        r = self._client.get("/workouts", params={"page": page, "pageSize": page_size})
        r.raise_for_status()
        return r.json()

    def get_workout(self, workout_id: str) -> dict[str, Any]:
        r = self._client.get(f"/workouts/{workout_id}")
        r.raise_for_status()
        return r.json()

    def get_workout_count(self) -> dict[str, Any]:
        r = self._client.get("/workouts/count")
        r.raise_for_status()
        return r.json()

    def get_workout_events(self, since: str | None = None, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if since:
            params["since"] = since
        r = self._client.get("/workouts/events", params=params)
        r.raise_for_status()
        return r.json()

    def iter_all_workouts(self, page_size: int = 10) -> Iterator[dict[str, Any]]:
        """Generator over every workout, paginating until exhausted."""
        page = 1
        while True:
            body = self.get_workouts(page=page, page_size=page_size)
            workouts = body.get("workouts", [])
            if not workouts:
                return
            for w in workouts:
                yield w
            if page >= body.get("page_count", 0):
                return
            page += 1

    # ---- routines ----

    def get_routines(self, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        r = self._client.get("/routines", params={"page": page, "pageSize": page_size})
        r.raise_for_status()
        return r.json()

    def get_routine(self, routine_id: str) -> dict[str, Any]:
        r = self._client.get(f"/routines/{routine_id}")
        r.raise_for_status()
        return r.json()

    def iter_all_routines(self, page_size: int = 10) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            body = self.get_routines(page=page, page_size=page_size)
            routines = body.get("routines", [])
            if not routines:
                return
            for rt in routines:
                yield rt
            if page >= body.get("page_count", 0):
                return
            page += 1

    # ---- exercise templates ----

    def get_exercise_templates(self, page: int = 1, page_size: int = 100) -> dict[str, Any]:
        r = self._client.get("/exercise_templates", params={"page": page, "pageSize": page_size})
        r.raise_for_status()
        return r.json()

    def get_exercise_template(self, template_id: str) -> dict[str, Any]:
        r = self._client.get(f"/exercise_templates/{template_id}")
        r.raise_for_status()
        return r.json()

    def iter_all_exercise_templates(self, page_size: int = 100) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            body = self.get_exercise_templates(page=page, page_size=page_size)
            templates = body.get("exercise_templates", [])
            if not templates:
                return
            for t in templates:
                yield t
            if page >= body.get("page_count", 0):
                return
            page += 1

    # ---- routine folders ----

    def get_routine_folders(self, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        r = self._client.get("/routine_folders", params={"page": page, "pageSize": page_size})
        r.raise_for_status()
        return r.json()

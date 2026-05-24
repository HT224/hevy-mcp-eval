"""d03 — workout titles in April 2026, chronological order."""

from __future__ import annotations

from datetime import datetime, timezone

from ._helpers import filter_workouts, load_workouts, workout_date


def compute() -> dict:
    workouts = load_workouts()
    apr_start = datetime(2026, 4, 1, tzinfo=timezone.utc)
    may_start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    apr = sorted(filter_workouts(workouts, apr_start, may_start), key=workout_date)

    titles = [w["title"] for w in apr]
    dates = [w["start_time"][:10] for w in apr]

    return {
        "scoring": "factual",
        "answer": {"titles_in_order": titles, "count": len(titles)},
        "computed_details": {"dates_in_order": dates},
    }

"""b03 — exercises rep-PR'd in Feb–Apr 2026 window but not in May 2026."""

from __future__ import annotations

from datetime import datetime, timezone

from ._helpers import compute_rep_prs_up_to, iter_sets, load_workouts


def compute() -> dict:
    workouts = load_workouts()
    feb1 = datetime(2026, 2, 1, tzinfo=timezone.utc)
    may1 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    jun1 = datetime(2026, 6, 1, tzinfo=timezone.utc)

    state = compute_rep_prs_up_to(workouts, feb1)

    prs_feb_apr: set[str] = set()
    prs_may: set[str] = set()

    rows = sorted(
        iter_sets(workouts, require_weighted=True, require_reps=True),
        key=lambda r: (r.workout_date, r.set_index),
    )

    for r in rows:
        if r.workout_date < feb1 or r.workout_date >= jun1:
            continue
        key = (r.exercise_title, r.reps)
        prev = state.get(key)
        if prev is None or r.weight_kg > prev[0]:
            if r.workout_date < may1:
                prs_feb_apr.add(r.exercise_title)
            else:
                prs_may.add(r.exercise_title)
            state[key] = (r.weight_kg, r.workout_date)

    in_window_not_may = sorted(prs_feb_apr - prs_may)

    return {
        "scoring": "factual",
        "answer": {"exercises": in_window_not_may, "count": len(in_window_not_may)},
        "computed_details": {
            "all_pr_exercises_feb_apr": sorted(prs_feb_apr),
            "all_pr_exercises_may": sorted(prs_may),
        },
    }

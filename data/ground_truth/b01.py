"""b01 — rep-PRs in the week of May 17–23, 2026.

A rep-PR for (exercise, N reps) = a heavier weight than ever before lifted
at that exact rep count. Within the week we update incrementally so a Wed
PR over a Mon PR also counts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ._helpers import (
    compute_rep_prs_up_to,
    filter_workouts,
    iter_sets,
    load_workouts,
)


def compute() -> dict:
    workouts = load_workouts()
    week_start = datetime(2026, 5, 17, tzinfo=timezone.utc)
    week_end = datetime(2026, 5, 24, tzinfo=timezone.utc)

    state = compute_rep_prs_up_to(workouts, week_start)

    rows = sorted(
        iter_sets(
            filter_workouts(workouts, week_start, week_end),
            require_weighted=True,
            require_reps=True,
        ),
        key=lambda r: (r.workout_date, r.set_index),
    )

    prs = []
    for r in rows:
        key = (r.exercise_title, r.reps)
        prev = state.get(key)
        if prev is None or r.weight_kg > prev[0]:
            prs.append({
                "exercise": r.exercise_title,
                "reps": r.reps,
                "weight_kg": round(r.weight_kg, 2),
                "date": r.workout_date.date().isoformat(),
                "previous_best_kg": round(prev[0], 2) if prev else None,
            })
            state[key] = (r.weight_kg, r.workout_date)

    return {
        "scoring": "factual",
        "answer": {"rep_prs": prs, "count": len(prs)},
        "tolerance": {"weight_kg": 0.1},
    }

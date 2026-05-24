"""a03 — Romanian Deadlift (Barbell) estimated 1RM by month, Dec 2024 → May 2026."""

from __future__ import annotations

from datetime import datetime, timezone

from ._helpers import iter_sets, load_workouts, month_key


def compute() -> dict:
    workouts = load_workouts()

    by_month: dict[str, float] = {}
    for r in iter_sets(workouts, exercise_title="Romanian Deadlift (Barbell)",
                        require_weighted=True, require_reps=True):
        mk = month_key(r.workout_date)
        cur = by_month.get(mk, 0.0)
        if r.epley > cur:
            by_month[mk] = r.epley

    # Enumerate 18 months Dec 2024 through May 2026.
    months = []
    dt = datetime(2024, 12, 1, tzinfo=timezone.utc)
    end = datetime(2026, 6, 1, tzinfo=timezone.utc)
    while dt < end:
        mk = f"{dt.year}-{dt.month:02d}"
        val = by_month.get(mk)
        months.append({
            "month": mk,
            "best_1rm_kg": round(val, 1) if val else None,
        })
        if dt.month == 12:
            dt = datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            dt = datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)

    return {
        "scoring": "factual",
        "answer": {"by_month": months},
        "tolerance": {"each_month_kg": 0.2},
    }

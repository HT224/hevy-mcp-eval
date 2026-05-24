"""b02 — all-time PR (max weight at any rep count) for Incline Bench Press (Barbell)."""

from __future__ import annotations

from ._helpers import iter_sets, load_workouts


def compute() -> dict:
    workouts = load_workouts()
    best = None  # (weight, reps, date)
    for r in iter_sets(workouts, exercise_title="Incline Bench Press (Barbell)",
                        require_weighted=True, require_reps=True):
        if best is None or r.weight_kg > best[0]:
            best = (r.weight_kg, r.reps, r.workout_date)

    if best is None:
        return {"scoring": "factual", "answer": None, "note": "no weighted incline bench press sets found"}

    return {
        "scoring": "factual",
        "answer": {
            "weight_kg": round(best[0], 2),
            "reps": best[1],
            "date": best[2].date().isoformat(),
        },
        "tolerance": {"weight_kg": 0.5},
    }

"""e02 — context dossier for the RDL stalling diagnostic prompt.

"Last 8 weeks" pinned to mid-March → mid-May 2026 for determinism.
Rubric must reward correct diagnosis EITHER WAY (stalling or progressing).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from ._helpers import iter_sets, load_workouts


def compute() -> dict:
    workouts = load_workouts()
    end = datetime(2026, 5, 17, tzinfo=timezone.utc)
    start = end - timedelta(weeks=8)

    all_sets = []
    for r in iter_sets(workouts, exercise_title="Romanian Deadlift (Barbell)",
                        require_weighted=True, require_reps=True):
        if start <= r.workout_date <= end:
            all_sets.append({
                "date": r.workout_date.date().isoformat(),
                "weight_kg": round(r.weight_kg, 2),
                "reps": r.reps,
                "epley_1rm_kg": round(r.epley, 2),
            })
    all_sets.sort(key=lambda x: x["date"])

    weekly_max: dict[str, float] = defaultdict(float)
    for s in all_sets:
        dt = datetime.fromisoformat(s["date"]).replace(tzinfo=timezone.utc)
        iso = dt.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        weekly_max[wk] = max(weekly_max[wk], s["epley_1rm_kg"])

    return {
        "scoring": "open_ended",
        "relevant_context": {
            "window_start": start.date().isoformat(),
            "window_end": end.date().isoformat(),
            "all_rdl_sets": all_sets,
            "weekly_max_epley_1rm": dict(sorted(weekly_max.items())),
            "session_count": len({s["date"] for s in all_sets}),
        },
        "rubric_dimensions": [
            "cites_actual_numbers_from_window",
            "correct_diagnosis_relative_to_data",
            "reasons_grounded_in_observable_data_if_stalling",
            "characterizes_progression_if_not_stalling",
        ],
    }

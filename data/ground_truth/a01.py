"""a01 — largest estimated 1RM gain in 2025 (H1 vs H2).

Filter: exercise must have ≥4 sessions in each half-year with non-zero weight.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from ._helpers import epley_1rm, filter_workouts, iter_sets, load_workouts


def compute() -> dict:
    workouts = load_workouts()
    h1_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    h1_end = datetime(2025, 7, 1, tzinfo=timezone.utc)
    h2_end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def best_1rm(ws):
        best = {}
        sessions = defaultdict(set)
        for r in iter_sets(ws, require_weighted=True, require_reps=True):
            sessions[r.exercise_title].add(r.workout_date.date())
            cur = best.get(r.exercise_title, 0.0)
            if r.epley > cur:
                best[r.exercise_title] = r.epley
        return best, sessions

    h1, h1_sess = best_1rm(filter_workouts(workouts, h1_start, h1_end))
    h2, h2_sess = best_1rm(filter_workouts(workouts, h1_end, h2_end))

    candidates = []
    for ex in h1.keys() & h2.keys():
        if len(h1_sess[ex]) >= 4 and len(h2_sess[ex]) >= 4:
            gain = h2[ex] - h1[ex]
            candidates.append((ex, gain, h1[ex], h2[ex], len(h1_sess[ex]), len(h2_sess[ex])))
    candidates.sort(key=lambda x: -x[1])

    if not candidates:
        return {"scoring": "factual", "answer": None, "note": "no exercise met the ≥4-sessions-per-half filter"}

    winner = candidates[0]
    return {
        "scoring": "factual",
        "answer": {
            "exercise_name": winner[0],
            "gain_kg": round(winner[1], 2),
        },
        "tolerance": {"gain_kg": 0.5},
        "computed_details": {
            "h1_best_1rm_kg": round(winner[2], 2),
            "h2_best_1rm_kg": round(winner[3], 2),
            "h1_sessions": winner[4],
            "h2_sessions": winner[5],
            "top_5_candidates": [
                {"exercise": c[0], "gain_kg": round(c[1], 2)} for c in candidates[:5]
            ],
        },
    }

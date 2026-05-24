"""d01 — weight + reps of the 2nd set of Leg Extension (Machine) on May 23, 2026."""

from __future__ import annotations

from ._helpers import load_workouts


def compute() -> dict:
    workouts = load_workouts()
    target_date = "2026-05-23"
    target_ex = "Leg Extension (Machine)"
    target_set_idx = 1  # 0-indexed; "second" set = index 1

    for w in workouts:
        if not w["start_time"].startswith(target_date):
            continue
        for ex in w["exercises"]:
            if ex["title"] != target_ex:
                continue
            if len(ex["sets"]) > target_set_idx:
                s = ex["sets"][target_set_idx]
                return {
                    "scoring": "factual",
                    "answer": {
                        "weight_kg": round(s.get("weight_kg") or 0, 4),
                        "reps": s.get("reps"),
                    },
                    "tolerance": {"weight_kg": 0.1},
                }

    raise RuntimeError(f"Could not find {target_ex} set #{target_set_idx + 1} on {target_date}")

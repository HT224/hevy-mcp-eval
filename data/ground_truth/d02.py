"""d02 — start time + duration of workout on May 22, 2026.

Stores BOTH UTC suffix variants (`+00:00` and `Z`) so the scorer can
match either without penalty (per Phase 7 scoring note).
"""

from __future__ import annotations

from ._helpers import load_workouts, parse_iso


def compute() -> dict:
    workouts = load_workouts()
    target_date = "2026-05-22"

    for w in workouts:
        if not w["start_time"].startswith(target_date):
            continue
        start_raw = w["start_time"]
        end_raw = w["end_time"]
        start = parse_iso(start_raw)
        end = parse_iso(end_raw)
        duration_min = round((end - start).total_seconds() / 60)

        canonical = start.isoformat()  # always +00:00 form
        zulu = canonical.replace("+00:00", "Z")

        return {
            "scoring": "factual",
            "answer": {
                "start_time_iso": canonical,
                "duration_minutes": duration_min,
            },
            "accepted_start_time_formats": [canonical, zulu, start_raw],
            "tolerance": {"duration_minutes": 1},
            "computed_details": {
                "raw_start_time": start_raw,
                "raw_end_time": end_raw,
            },
        }

    raise RuntimeError(f"No workout on {target_date}")

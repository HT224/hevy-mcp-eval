"""e01 — context dossier for the "design a 4-week chest hypertrophy block" prompt.

Open-ended; the LLM judge consumes this dossier to score whether the response
actually references the user's chest training history.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from ._helpers import load_workouts, templates_by_id, workout_date


def compute() -> dict:
    workouts = load_workouts()
    tmpl_idx = templates_by_id()

    chest_template_ids = {
        tid for tid, t in tmpl_idx.items()
        if (t.get("primary_muscle_group") or "").lower() == "chest"
    }

    chest_session_count: Counter[str] = Counter()
    rep_ranges_by_ex: defaultdict[str, list[int]] = defaultdict(list)
    six_mo_ago = datetime(2025, 11, 24, tzinfo=timezone.utc)
    chest_volume_per_week: defaultdict[str, float] = defaultdict(float)

    for w in workouts:
        wdate = workout_date(w)
        for ex in w["exercises"]:
            if ex["exercise_template_id"] not in chest_template_ids:
                continue
            chest_session_count[ex["title"]] += 1
            for s in ex["sets"]:
                wt = s.get("weight_kg") or 0
                reps = s.get("reps") or 0
                if reps > 0:
                    rep_ranges_by_ex[ex["title"]].append(reps)
                if wdate >= six_mo_ago:
                    iso = wdate.isocalendar()
                    chest_volume_per_week[f"{iso[0]}-W{iso[1]:02d}"] += wt * reps

    rep_range_summary = {
        ex: {
            "min": min(reps),
            "max": max(reps),
            "median": sorted(reps)[len(reps) // 2],
            "sample_size": len(reps),
        }
        for ex, reps in rep_ranges_by_ex.items() if reps
    }

    avg_weekly = (
        sum(chest_volume_per_week.values()) / max(1, len(chest_volume_per_week))
    )

    return {
        "scoring": "open_ended",
        "relevant_context": {
            "chest_exercises_with_session_count": dict(chest_session_count.most_common()),
            "rep_ranges_by_exercise": rep_range_summary,
            "avg_weekly_chest_volume_last_6mo_kgreps": round(avg_weekly, 1),
            "chest_volume_by_week_last_6mo": dict(sorted(chest_volume_per_week.items())),
        },
        "rubric_dimensions": [
            "references_user_actual_chest_history",
            "weekly_frequency_matches_user_patterns",
            "rep_ranges_defensible_for_hypertrophy",
            "progression_across_4_weeks",
            "specificity_of_exercise_set_rep_prescription",
        ],
    }

"""a02 — triceps volume in April 2026, broken down by exercise variant."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from ._helpers import filter_workouts, load_workouts, templates_by_id


def compute() -> dict:
    workouts = load_workouts()
    tmpl_idx = templates_by_id()

    apr_start = datetime(2026, 4, 1, tzinfo=timezone.utc)
    may_start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    apr = filter_workouts(workouts, apr_start, may_start)

    tricep_template_ids = {
        tid for tid, t in tmpl_idx.items()
        if (t.get("primary_muscle_group") or "").lower() == "triceps"
    }

    by_variant: dict[str, float] = defaultdict(float)
    for w in apr:
        for ex in w["exercises"]:
            if ex["exercise_template_id"] not in tricep_template_ids:
                continue
            vol = sum((s.get("weight_kg") or 0) * (s.get("reps") or 0) for s in ex["sets"])
            by_variant[ex["title"]] += vol

    total = sum(by_variant.values())

    return {
        "scoring": "factual",
        "answer": {
            "by_variant_kgreps": {k: round(v, 2) for k, v in sorted(by_variant.items())},
            "grand_total_kgreps": round(total, 2),
        },
        "tolerance": {
            "grand_total_kgreps": 5.0,
            "per_variant_kgreps": 2.0,
        },
        "computed_details": {
            "triceps_template_count_in_library": len(tricep_template_ids),
            "april_workout_count": len(apr),
        },
    }

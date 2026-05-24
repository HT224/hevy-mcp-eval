"""e03 — context dossier for the May 2026 muscle-gap analysis prompt.

Compares May 2026 muscle-group volume to the user's prior 6-month monthly avg.
Provides the underworked-by-pct table the judge uses to grade the answer.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from ._helpers import filter_workouts, load_templates, load_workouts, templates_by_id


def _volume_by_muscle_group(workouts, tmpl_idx) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for w in workouts:
        for ex in w["exercises"]:
            tmpl = tmpl_idx.get(ex["exercise_template_id"])
            if not tmpl:
                continue
            mg = (tmpl.get("primary_muscle_group") or "unknown").lower()
            vol = sum((s.get("weight_kg") or 0) * (s.get("reps") or 0) for s in ex["sets"])
            out[mg] += vol
    return dict(out)


def compute() -> dict:
    workouts = load_workouts()
    tmpl_idx = templates_by_id()

    may_start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    may_end = datetime(2026, 6, 1, tzinfo=timezone.utc)
    prior_start = datetime(2025, 11, 1, tzinfo=timezone.utc)

    may_vol = _volume_by_muscle_group(filter_workouts(workouts, may_start, may_end), tmpl_idx)
    prior_vol = _volume_by_muscle_group(filter_workouts(workouts, prior_start, may_start), tmpl_idx)
    prior_monthly_avg = {k: v / 6.0 for k, v in prior_vol.items()}

    gaps: dict[str, dict] = {}
    for mg in set(prior_monthly_avg) | set(may_vol):
        avg = prior_monthly_avg.get(mg, 0)
        cur = may_vol.get(mg, 0)
        gaps[mg] = {
            "may_2026_kgreps": round(cur, 1),
            "prior_6mo_monthly_avg_kgreps": round(avg, 1),
            "delta_vs_avg": round(cur - avg, 1),
            "pct_of_avg": round(100 * cur / avg, 1) if avg > 0 else None,
        }

    underworked = {
        mg: g for mg, g in gaps.items()
        if g["pct_of_avg"] is not None and g["pct_of_avg"] < 80
    }

    user_equipment = sorted({
        (t.get("equipment") or "unknown")
        for t in load_templates() if not t.get("is_custom")
    })

    return {
        "scoring": "open_ended",
        "relevant_context": {
            "may_2026_volume_by_muscle": {k: round(v, 1) for k, v in may_vol.items()},
            "prior_6mo_monthly_avg_by_muscle": {k: round(v, 1) for k, v in prior_monthly_avg.items()},
            "gaps_by_muscle": gaps,
            "underworked_in_may_pct_lt_80": underworked,
            "user_equipment_universe": user_equipment,
        },
        "rubric_dimensions": [
            "correctly_identifies_underworked_groups",
            "comparison_actually_computed_from_data",
            "two_specific_exercise_recommendations",
            "recommendations_use_existing_equipment_patterns",
        ],
    }

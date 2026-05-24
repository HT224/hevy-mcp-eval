"""a04 — top 3 exercise pairs that co-occur most often in workouts since Jan 2025.

Tie-break: count descending, then alphabetical by first exercise, then by second.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from ._helpers import filter_workouts, load_workouts


def compute() -> dict:
    workouts = load_workouts()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2099, 1, 1, tzinfo=timezone.utc)
    ws = filter_workouts(workouts, start, end)

    pair_counts: Counter[tuple[str, str]] = Counter()
    for w in ws:
        exs = sorted({ex["title"] for ex in w["exercises"]})
        for i in range(len(exs)):
            for j in range(i + 1, len(exs)):
                pair_counts[(exs[i], exs[j])] += 1

    sorted_pairs = sorted(
        pair_counts.items(),
        key=lambda x: (-x[1], x[0][0], x[0][1]),
    )
    top3 = [{"pair": list(p), "count": c} for (p, c) in sorted_pairs[:3]]

    return {
        "scoring": "factual",
        "answer": {"top_3_pairs": top3},
        "computed_details": {
            "total_workouts_in_window": len(ws),
            "unique_pairs_observed": len(pair_counts),
            "top_10_for_reference": [
                {"pair": list(p), "count": c} for (p, c) in sorted_pairs[:10]
            ],
        },
    }

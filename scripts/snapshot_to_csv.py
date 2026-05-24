"""Materialize the anonymized snapshot as a compact CSV for Baseline A.

One row per set. Weights rounded to 2 decimals — 1 decimal collapsed
non-equal weights into the same row (e.g., 52.16 and 52.20 both rounded
to 52.2), giving the baseline ambiguous data the MCPs don't see. 2dp
preserves the meaningful precision (sets are typically logged at 0.5 lb
increments ≈ 0.23 kg, well within 2dp resolution).

Notes columns omitted (stripped already in snapshot). Sets where both
weight_kg and reps are zero are skipped — they're bar-only / bodyweight
markers and add token cost without adding signal for most prompts.

Outputs to data/fixtures/snapshot/workouts.csv (committed; this is what
Baseline A injects into the prompt).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO_ROOT / "data" / "fixtures" / "snapshot" / "workouts.json"
OUT = REPO_ROOT / "data" / "fixtures" / "snapshot" / "workouts.csv"

COLUMNS = [
    "workout_date",
    "workout_title",
    "exercise_title",
    "exercise_template_id",
    "set_index",
    "set_type",
    "weight_kg",
    "reps",
]


def main() -> None:
    workouts = json.loads(SNAPSHOT.read_text())
    rows = 0
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for wo in workouts:
            date = wo["start_time"][:10]
            wtitle = wo["title"]
            for ex in wo["exercises"]:
                for s in ex["sets"]:
                    weight = s.get("weight_kg") or 0
                    reps = s.get("reps") or 0
                    if weight == 0 and reps == 0:
                        continue
                    w.writerow([
                        date,
                        wtitle,
                        ex["title"],
                        ex["exercise_template_id"],
                        s.get("index"),
                        s.get("type", "normal"),
                        round(weight, 2),
                        reps,
                    ])
                    rows += 1
    print(f"wrote {rows} rows to {OUT.relative_to(REPO_ROOT)}")
    print(f"file size: {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()

"""Shared helpers for ground-truth computations.

Every ground-truth script reads from `data/fixtures/raw/` (NOT the
anonymized snapshot — ground truth uses the highest-fidelity source).
The raw fixtures are gitignored; the per-prompt cache JSONs they
produce are committed and what the eval scorers actually consume.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "fixtures" / "raw"
CACHE_DIR = Path(__file__).resolve().parent / "cache"


def load_workouts() -> list[dict]:
    return json.loads((RAW_DIR / "workouts.json").read_text())


def load_routines() -> list[dict]:
    return json.loads((RAW_DIR / "routines.json").read_text())


def load_templates() -> list[dict]:
    return json.loads((RAW_DIR / "exercise_templates.json").read_text())


def templates_by_id() -> dict[str, dict]:
    return {t["id"]: t for t in load_templates()}


def epley_1rm(weight_kg: float, reps: int) -> float:
    """Epley 1RM estimate: weight × (1 + reps/30)."""
    return weight_kg * (1.0 + reps / 30.0)


def parse_iso(s: str) -> datetime:
    """Parse an ISO-8601 timestamp; assume UTC if naive."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def workout_date(w: dict) -> datetime:
    return parse_iso(w["start_time"])


def in_range(w: dict, start: datetime, end: datetime) -> bool:
    """Half-open [start, end)."""
    dt = workout_date(w)
    return start <= dt < end


def filter_workouts(workouts: list[dict], start: datetime, end: datetime) -> list[dict]:
    return [w for w in workouts if in_range(w, start, end)]


@dataclass
class SetRow:
    workout_id: str
    workout_title: str
    workout_date: datetime
    exercise_title: str
    exercise_template_id: str
    set_index: int
    set_type: str
    weight_kg: float
    reps: int

    @property
    def epley(self) -> float:
        return epley_1rm(self.weight_kg, self.reps)


def iter_sets(
    workouts: list[dict],
    exercise_title: str | None = None,
    require_weighted: bool = False,
    require_reps: bool = False,
) -> Iterator[SetRow]:
    """Yield one SetRow per set across all workouts. Optional filters."""
    for w in workouts:
        wdate = workout_date(w)
        for ex in w.get("exercises", []):
            if exercise_title is not None and ex["title"] != exercise_title:
                continue
            for s in ex.get("sets", []):
                wt = s.get("weight_kg") or 0.0
                reps = s.get("reps") or 0
                if require_weighted and wt <= 0:
                    continue
                if require_reps and reps <= 0:
                    continue
                yield SetRow(
                    workout_id=w["id"],
                    workout_title=w["title"],
                    workout_date=wdate,
                    exercise_title=ex["title"],
                    exercise_template_id=ex["exercise_template_id"],
                    set_index=s["index"],
                    set_type=s.get("type", "normal"),
                    weight_kg=wt,
                    reps=reps,
                )


def compute_rep_prs_up_to(
    workouts: list[dict], end: datetime
) -> dict[tuple[str, int], tuple[float, datetime]]:
    """For every (exercise, rep_count) pair, return the max weight ever lifted
    at exactly that rep count *strictly before* the given end timestamp, plus
    the date that PR was first set. Used by b01/b03.
    """
    best: dict[tuple[str, int], tuple[float, datetime]] = {}
    rows = sorted(
        iter_sets(workouts, require_weighted=True, require_reps=True),
        key=lambda r: r.workout_date,
    )
    for r in rows:
        if r.workout_date >= end:
            break
        key = (r.exercise_title, r.reps)
        cur = best.get(key)
        if cur is None or r.weight_kg > cur[0]:
            best[key] = (r.weight_kg, r.workout_date)
    return best


def write_cache(prompt_id: str, payload: dict[str, Any]) -> Path:
    """Serialize a ground-truth payload to data/ground_truth/cache/{id}.json."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": prompt_id,
        **payload,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
    out = CACHE_DIR / f"{prompt_id}.json"
    out.write_text(json.dumps(payload, indent=2, default=str))
    return out


def month_key(dt: datetime) -> str:
    return f"{dt.year}-{dt.month:02d}"

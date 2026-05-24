"""Pull a full snapshot of the user's Hevy data and write two artifacts:

  - data/fixtures/raw/{workouts,routines,exercise_templates}.json   (gitignored — full fidelity)
  - data/fixtures/snapshot/{workouts,routines,exercise_templates}.json   (committable — lightly anonymized)

Anonymization recipe:
  - Strip workout `description` (free text)
  - Strip exercise `notes` (free text)
  - Everything else preserved: titles, timestamps, weights, reps, RPE, rest, IDs.

Re-run any time the underlying data changes. Ground truth scripts run against
the *snapshot* (not the live API) so eval results are deterministic.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.hevy_client import HevyClient  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "fixtures" / "raw"
SNAPSHOT_DIR = REPO_ROOT / "data" / "fixtures" / "snapshot"


def anonymize_workout(w: dict) -> dict:
    out = copy.deepcopy(w)
    out["description"] = ""
    for ex in out.get("exercises", []):
        ex["notes"] = ""
    return out


def anonymize_routine(rt: dict) -> dict:
    out = copy.deepcopy(rt)
    out["notes"] = ""
    for ex in out.get("exercises", []):
        ex["notes"] = ""
    return out


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    with HevyClient() as c:
        print("Pulling workouts...")
        workouts = list(c.iter_all_workouts(page_size=10))
        print(f"  {len(workouts)} workouts")

        print("Pulling routines...")
        routines = list(c.iter_all_routines(page_size=10))
        print(f"  {len(routines)} routines")

        print("Pulling exercise templates...")
        templates = list(c.iter_all_exercise_templates(page_size=100))
        print(f"  {len(templates)} exercise templates")

    (RAW_DIR / "workouts.json").write_text(json.dumps(workouts, indent=2))
    (RAW_DIR / "routines.json").write_text(json.dumps(routines, indent=2))
    (RAW_DIR / "exercise_templates.json").write_text(json.dumps(templates, indent=2))
    print(f"Raw → {RAW_DIR}")

    anon_workouts = [anonymize_workout(w) for w in workouts]
    anon_routines = [anonymize_routine(rt) for rt in routines]
    (SNAPSHOT_DIR / "workouts.json").write_text(json.dumps(anon_workouts, indent=2))
    (SNAPSHOT_DIR / "routines.json").write_text(json.dumps(anon_routines, indent=2))
    (SNAPSHOT_DIR / "exercise_templates.json").write_text(json.dumps(templates, indent=2))
    print(f"Snapshot (anonymized) → {SNAPSHOT_DIR}")


if __name__ == "__main__":
    main()

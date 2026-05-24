"""The 12 eval prompts, in one place.

Single source of truth: every Inspect Task variant (each system under
test) reads its dataset from here. Categories from DESIGN.md §5 with
Category C (write operations) dropped per resolved decision §0.

Schema for each prompt:
  id            — stable identifier (a01..e03); used to name ground-truth + rubric files
  category      — A trend/aggregation, B PR detection, D faithfulness, E open-ended
  scoring       — "factual" (exact/numeric ground truth) or "open_ended" (LLM judge with rubric)
  input         — the prompt text shown to the model
  rationale     — why this prompt was chosen (what it isolates / discriminates)

Dates are pinned to absolute months/days (no "last week") so the eval
is deterministic regardless of when it runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from inspect_ai.dataset import Sample

Category = Literal["A", "B", "D", "E"]
Scoring = Literal["factual", "open_ended"]


@dataclass(frozen=True)
class Prompt:
    id: str
    category: Category
    scoring: Scoring
    input: str
    rationale: str

    def to_sample(self) -> Sample:
        return Sample(
            id=self.id,
            input=self.input,
            metadata={
                "prompt_id": self.id,
                "category": self.category,
                "scoring": self.scoring,
            },
        )


PROMPTS: list[Prompt] = [
    # ---------- Category A: Trend & aggregation ----------
    Prompt(
        id="a01",
        category="A",
        scoring="factual",
        input=(
            "Across all my workouts in 2025, which exercise showed the largest "
            "estimated 1RM gain (using the Epley formula: weight × (1 + reps / 30))? "
            "Compare the best estimated 1RM from the first half of 2025 (Jan–Jun) "
            "to the best from the second half (Jul–Dec). Only count exercises I "
            "trained at least 4 times in each half-year with non-zero weight. "
            "Give me the exercise name and the gain in kg."
        ),
        rationale=(
            "Forces year-spanning aggregation. Thin MCP must page all 2025 workouts. "
            "A well-designed MCP might expose a `getProgress` or per-exercise history "
            "summary. Tight filter (>=4 sessions / half) avoids noise from one-off lifts."
        ),
    ),
    Prompt(
        id="a02",
        category="A",
        scoring="factual",
        input=(
            "How much total triceps volume (sum of weight_kg × reps across all sets) "
            "did I do in April 2026? Break it down by exercise variant, then give "
            "me the grand total. Use the exercise template's primary_muscle_group "
            "to identify triceps exercises."
        ),
        rationale=(
            "Forces joining workouts to exercise_templates (for muscle-group filter). "
            "Thin MCP must paginate both surfaces and join in-context. A good MCP "
            "might expose muscle-group-keyed queries. Date pinned to April 2026 — "
            "deterministic across run timing."
        ),
    ),
    Prompt(
        id="a03",
        category="A",
        scoring="factual",
        input=(
            "What's my Romanian Deadlift (Barbell) estimated 1RM by month from "
            "December 2024 through May 2026? Use Epley (weight × (1 + reps / 30)). "
            "For each month, report the maximum estimated 1RM across all sets that "
            "month. Round each month's value to 1 decimal place."
        ),
        rationale=(
            "18 monthly buckets. Romanian Deadlift chosen because it's the user's "
            "most-frequent weighted barbell movement (57 sessions). Tests temporal "
            "bucketing in 1RM calc — thin must page everything; a good MCP might "
            "expose per-exercise history time series."
        ),
    ),
    Prompt(
        id="a04",
        category="A",
        scoring="factual",
        input=(
            "Across all my workouts from January 2025 onward, find the 3 pairs of "
            "exercises that most often appear together in the same workout. Return "
            "each pair as (exercise A, exercise B, count of workouts containing both), "
            "sorted by count descending. Ignore order within a pair (X+Y same as Y+X). "
            "If pairs tie on count, break ties alphabetically by the first exercise "
            "name in the pair."
        ),
        rationale=(
            "Cross-workout pattern matching — likely no MCP exposes a co-occurrence "
            "surface, so every system has to page through workouts and enumerate "
            "pairs in-context. Strong discriminator: if all MCPs score similarly here, "
            "that's a finding (MCP design doesn't help with arbitrary pattern queries). "
            "Tie-break rule keeps the answer deterministic."
        ),
    ),
    # ---------- Category B: Personal-record detection ----------
    Prompt(
        id="b01",
        category="B",
        scoring="factual",
        input=(
            "Did I hit any rep-PRs in the week of May 17–23, 2026? A rep-PR for "
            "exercise X at N reps means a heavier weight at exactly N reps than I'd "
            "ever lifted before for that exercise. List every (exercise, reps, weight_kg) "
            "rep-PR set in that week. If none, say so."
        ),
        rationale=(
            "PR detection across full history. Thin needs all-time history; "
            "good MCPs may expose PR endpoints. Rep-PR (not 1RM-equivalent) "
            "definition forces exact-history comparison."
        ),
    ),
    Prompt(
        id="b02",
        category="B",
        scoring="factual",
        input=(
            "What's my all-time PR (heaviest weight at any rep count) for "
            "Incline Bench Press (Barbell)? Give me the weight in kg, the rep "
            "count on that set, and the date I logged it."
        ),
        rationale=(
            "Single-exercise PR lookup. Incline Bench picked because it's the "
            "user's most-frequent weighted barbell press (49 sessions). "
            "Discriminates: thin pages all workouts, good MCP looks up directly."
        ),
    ),
    Prompt(
        id="b03",
        category="B",
        scoring="factual",
        input=(
            "Which exercises did I set a new rep-PR on at least once during "
            "the 3-month window Feb–Apr 2026, but did NOT set any new rep-PR on "
            "during May 2026? Use the same rep-PR definition as before "
            "(heavier weight than ever before at exactly that rep count). "
            "Return the list of exercise names."
        ),
        rationale=(
            "Hardest in the suite — temporal differencing across two windows. "
            "Thin needs full history + double-window scan; well-designed MCP could "
            "expose a PR-by-date-range endpoint. Maximum discrimination."
        ),
    ),
    # ---------- Category D: Long-tail field preservation ----------
    Prompt(
        id="d01",
        category="D",
        scoring="factual",
        input=(
            "On May 23, 2026 (LEGS workout), what was the weight in kg and the "
            "rep count of the SECOND set of Leg Extension (Machine)? Give both "
            "values exactly as recorded."
        ),
        rationale=(
            "Single-cell retrieval. Tests whether the MCP preserves per-set "
            "data faithfully (vs. summarizing). Exact match required."
        ),
    ),
    Prompt(
        id="d02",
        category="D",
        scoring="factual",
        # SCORING NOTE (Phase 6): accept both `+00:00` and `Z` UTC suffixes as
        # correct. If the response normalized (e.g., Hevy returns `+00:00` and
        # the system answered with `Z`, or vice versa), record `normalized=true`
        # in the scorer output but still count correct. Strict format-mismatch
        # would penalize timezone-savvy MCPs for being conventional.
        input=(
            "What time (UTC) did my workout on May 22, 2026 start, and how long "
            "did it last in minutes from start_time to end_time? Format the start "
            "time as ISO 8601 (e.g., 2026-05-22T09:54:50+00:00) and round duration "
            "to the nearest whole minute."
        ),
        rationale=(
            "Timestamp + duration preservation. Some MCPs may strip timezone, "
            "round timestamps, or compute duration in a different unit. "
            "Exact-format requirement surfaces transformations; scorer accepts "
            "either UTC suffix and flags normalizations."
        ),
    ),
    Prompt(
        id="d03",
        category="D",
        scoring="factual",
        input=(
            "List the titles of every workout I logged in April 2026, in "
            "chronological order from earliest to latest. Return the exact "
            "title strings as I set them, separated by newlines."
        ),
        rationale=(
            "User-set string preservation + ordering. Tests whether the MCP "
            "transforms title casing, strips emoji, or reorders. April 2026 "
            "chosen because it's a full month with multiple workouts."
        ),
    ),
    # ---------- Category E: Programming & diagnostic (open-ended) ----------
    Prompt(
        id="e01",
        category="E",
        scoring="open_ended",
        input=(
            "Design me a 4-week hypertrophy training block focused on chest, "
            "given my actual training history. Reference what I've been doing "
            "(chest exercises I've used, current rep ranges, weekly frequency) "
            "and propose specific exercises, sets, reps, and intensity guidance "
            "for weeks 1–4 that builds on where I am now."
        ),
        rationale=(
            "Open-ended; rubric scores history-referencing + defensibility + "
            "personalization. A system that doesn't surface real history can only "
            "produce generic programming — judge can detect that."
        ),
    ),
    Prompt(
        id="e02",
        category="E",
        scoring="open_ended",
        # RUBRIC NOTE (Phase 6): "no evidence of stalling" is a valid answer if
        # the data supports it. The rubric must reward correct diagnosis EITHER
        # WAY — penalize only ungrounded conclusions (claiming stalling without
        # numbers, or claiming progress without numbers).
        input=(
            "Look at my Romanian Deadlift (Barbell) performance over the last "
            "8 weeks (mid-March through mid-May 2026). Is there evidence of "
            "stalling — i.e., flat or declining estimated 1RM trend? If so, "
            "give me 2–3 specific reasons it might be happening, grounded in "
            "what you can see in the data. If the trend is actually progressing, "
            "say so and characterize the progression."
        ),
        rationale=(
            "Diagnostic + open-ended. Rubric scores grounded-in-data reasoning "
            "and accepts EITHER diagnosis (stalling or progressing) as long as "
            "the answer cites actual numbers. Romanian DL chosen because the "
            "user has dense data on it."
        ),
    ),
    Prompt(
        id="e03",
        category="E",
        scoring="open_ended",
        input=(
            "Compare my muscle-group training distribution in May 2026 to my "
            "average over the prior 6 months (Nov 2025 – Apr 2026). Which "
            "muscle groups have I underworked in May, in relative terms? "
            "Suggest two specific exercises to add (with sets and reps) to "
            "close the gaps, choosing exercises that fit my existing equipment "
            "patterns."
        ),
        rationale=(
            "Comparative aggregation + recommendation. Rubric scores: did the "
            "model actually compute the comparison, or did it guess? Equipment "
            "anchor (use what I already use) forces it to look at exercise "
            "templates, not just suggest 'bench press' generically."
        ),
    ),
]


def all_samples() -> list[Sample]:
    return [p.to_sample() for p in PROMPTS]


if __name__ == "__main__":
    # Print review summary
    print(f"{'id':4}  {'cat':3}  {'scoring':11}  {'len':4}  prompt (first line)")
    print("-" * 100)
    for p in PROMPTS:
        first = p.input.split(". ")[0][:70]
        print(f"{p.id:4}  {p.category:3}  {p.scoring:11}  {len(p.input):4}  {first}")

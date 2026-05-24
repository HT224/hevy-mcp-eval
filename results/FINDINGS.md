# Findings — Hevy MCP Eval v0.1

> **Run**: 5 systems × 13 prompts × 3 epochs · model: `claude-sonnet-4-6` · run date: 2026-05-24 · total spend: ~$140
>
> **Methodology**: see [`DESIGN.md`](../DESIGN.md). Eval framework: [Inspect AI](https://inspect.aisi.org.uk/). Ground truth computed from a frozen snapshot of one real lifter's 17-month Hevy history (169 workouts, 22 routines, 439 exercise templates).

## Headline

> **The MCP layer adds only ~7 points of factual correctness over a 1:1 wrapper of the underlying API. MCPs beat CSV-in-prompt on factual retrieval (+24 pts on the best MCP), but CSV ties or beats every MCP on open-ended programming questions. The gap between "best MCP" and "no MCP" is mostly about retrieval ergonomics — the data, not the design.**

## Leaderboard

| Rank | System | Factual (10 prompts) | Open-ended (3 prompts) | Coverage | Avg tool calls | Avg tokens |
|---|---|---|---|---|---|---|
| 🥇 | **chrisdoc/hevy-mcp** | **77%** (23/30) | 89% (8/9) | 100% | 9.7 (max 24) | 303K |
| 🥈 | **hevy-mcp-thin** *(control)* | 70% (21/30) | **94%** (8.5/9) | 100% | 15.5 (max 26) | 375K |
| 🥉 | baseline_csv | 53% (16/30) | **100%** (9/9) | 85% | — | 293K |
| 4 | meimakes/hevy-mcp-server | 15% (4.5/30) | 33% (3/9) | **41%** | 54.6 (max 96) | 660K |
| 5 | baseline_nodata | 0% (0/30) | 0% (0/9) | 10% | — | 3K |

> *Open-ended numbers can exceed factual because there are fewer open-ended prompts (3) and they're rubric-scored across 4–5 dimensions × 3 judge runs, then bucketed.*

## Pre-registered hypotheses — status

| | Prediction | Actual | Status |
|---|---|---|---|
| H1 | `chrisdoc/hevy-mcp` will win the leaderboard on correctness. | chrisdoc won factual (77%) and tied for top coverage (100%). thin actually beat chrisdoc on open-ended (94% vs 89%). | **Confirmed (with nuance)** |
| H2 | No Hevy MCP will meaningfully beat the CSV-in-prompt baseline. | Factual: chrisdoc +24 pts vs CSV. Open-ended: CSV ≥ all MCPs. | **Split** — rejected for factual, confirmed for open-ended |
| H3 | Write-operation coverage will be the biggest discriminator. | (Retired — write tests deferred to v0.2.) | n/a |
| H4 | Faithfulness will be near-perfect across MCPs. | chrisdoc strips 72 fields + adds 67 derived on `get-workout` (139 divergences). meimakes' stdout pollution breaks JSON probes. Only thin is faithful. | **Strongly rejected** |
| H5 | Open-ended prompts will show highest variance, depending on aggregation surface. | Open-ended was actually the *most consistent* category — most systems hit CORRECT. Variance lives in the hard factual prompts (a04, b03) where nobody solved reliably. | **Rejected** |

## Sub-findings

### 1. The MCP layer's marginal value is small

**chrisdoc (best MCP) vs hevy-mcp-thin (1:1 wrapper): only 7 points separation on factual correctness.** Pre-registered threshold: "if no system separates from thin by >10%, treat as confirmation of H2." chrisdoc clears that bar by exactly... 7. The MCP design surface — aggregation endpoints, summary tools, etc. — adds modest, not transformative, value over raw API access plus a capable LLM.

### 2. meimakes/hevy-mcp-server fails on *tool design*, not implementation

41% coverage means the model couldn't complete 23 of 39 samples within the 120-message budget. Why? meimakes' `get-workouts` requires `page_size ≤ 10`, forcing 54.6 average tool calls (max 96 on `b02` alone). Ironically meimakes exposes more "smart" endpoints (`get-exercise-progress`, `get-exercise-stats`) than chrisdoc — but they don't reduce pagination. **More tools ≠ better MCP.** The faithfulness probe also caught meimakes writing non-JSON to stdout, breaking MCP protocol compliance.

### 3. Two prompts no system solved reliably

- **a04** — *Top 3 exercise pairs that co-occur most often in workouts since Jan 2025*. Cross-workout pattern matching has no MCP shortcut. Even thin (which sees raw workouts) got it right only 1 of 3 runs.
- **b03** — *Exercises that PR'd in Feb–Apr but not in May 2026*. Temporal differencing across two windows defeated every system; best result was 1 PARTIAL out of 3 runs.

**These two prompts point to genuine gaps in current MCP design** — patterns the existing tool surface doesn't help with, even when the data is fully available.

### 4. The CSV baseline hallucinated — a real failure mode

On `b02` (Incline Bench PR), baseline_csv fabricated a "52.2 kg × 8 reps on 2025-06-23" set. That set doesn't exist — the heaviest Incline Bench on that date was 49.9 kg. The CSV had all the data needed to answer correctly, but with 3000 rows in context the model confused dates. This happened across multiple factual prompts (47% wrong overall) — and the model never indicated uncertainty. **CSV-in-prompt is fast and information-dense but susceptible to confident hallucination.** MCPs force the model to fetch by ID, which constrains hallucination space.

### 5. The CSV baseline *won* open-ended programming

All 3 Category E prompts (chest hypertrophy block, RDL stalling diagnostic, muscle-group gaps) — baseline_csv scored 3/3 CORRECT each. The judge had the same data dossier the CSV-in-prompt model had, and rubric-scored the responses. The model writes good programming advice from data in context; it doesn't need an MCP to fetch it. **For diagnostic/programming tasks where the dataset fits in context, the MCP layer adds nothing measurable.**

### 6. chrisdoc's response design is *unfaithful but effective*

chrisdoc's `get-workout` strips `start_time`, `end_time`, `routine_id`, `created_at`, `updated_at` — every important timestamp/identifier — and adds 67 derived fields. Yet chrisdoc still scored 3/3 CORRECT on `d02` (timestamp + duration retrieval). How? The model used a *different* endpoint (`get-workouts`, which does preserve start_time at the listing level) for that question. Aggregating-and-transforming on the per-workout endpoint while keeping listings faithful is a real design pattern that worked, but breaks the assumption that MCPs are passthroughs.

## Cost & efficiency

- **Total spend:** ~$140 (Sonnet 4.6, with prompt caching)
- **Cost per CORRECT factual answer:** chrisdoc ~$0.17 · thin ~$0.27 · baseline_csv ~$0.32 · meimakes ~$2.20 (driven by 24 incompletions)
- **Avg tokens / sample (full matrix):** baseline_nodata 3K → chrisdoc 303K → baseline_csv 293K → thin 375K → meimakes 660K. Cache hits dominate the cost equation — chrisdoc benefits most from caching because its tool responses are stable across re-runs.

## What this means for MCP authors

1. **Design for *finish in N calls*, not for *number of endpoints*.** meimakes lost on coverage because its tools don't scale; chrisdoc won because its `get-exercise-history` collapsed full-workout scans into single calls.
2. **Pattern queries (co-occurrence, temporal differencing) are unaddressed.** No MCP we tested helps with "which exercises tend to appear together" or "PR'd in window-A but not window-B." Real product gap.
3. **Faithfulness is a design choice, not a default.** chrisdoc deliberately transforms; the model can't always tell what's been stripped. Document it loudly when you do this.
4. **Write tests deferred to v0.2.** Read-only coverage left unmeasured.

## Methodology caveats

- **Single lifter's data.** All findings reflect one user's training history. A user with denser deadlift logging (no RPE missing) or barbell squats logged with real weight (instead of 0 kg + Smith Machine warmups) may surface different gaps.
- **Single model (Sonnet 4.6).** Findings may shift with Opus 4.7 or Haiku 4.5. Worth a v0.2 cross-model run.
- **Single judge model (Sonnet 4.6) on open-ended prompts.** Judge-vs-judge sanity check was not run before this release (DESIGN.md §10.2 still open). Spot-check audit in [`judge_audit.md`](./judge_audit.md).
- **Tomtorggler MCP not tested.** HTTP-only Cloudflare Workers deployment; deferred to v0.2.
- **Construct validity caveat per the eval rigor memo:** the `hevy-mcp-thin` control is what makes the 7-pt MCP-layer-marginal-value claim defensible. Without it, we could only say "best MCP beats CSV by 24 points," which doesn't isolate which part of the MCP design did the work.

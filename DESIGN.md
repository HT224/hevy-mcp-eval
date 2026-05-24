# Hevy MCP Eval Suite — Design v0.1

> **Status:** scaffolding complete; data + proof-of-life next
> **Last updated:** 2026-05-24

## 0. Resolved decisions (closing §10 items as they land)

| Decision | Resolution | Date |
|---|---|---|
| Data source (§10.1) | **Real** — Himanshu's own Hevy export, lightly anonymized (strip notes + account IDs, keep lift data + dates) | 2026-05-24 |
| Write-operation tests (§10.3) | **Skip in v0.1** — Category C dropped; write-coverage gap noted as future work | 2026-05-24 |
| Judge model (§10.2) | Claude Sonnet, with judge-vs-judge sanity check on n=5 vs. GPT-4-class before committing | 2026-05-24 |
| License (§10.4) | MIT | 2026-05-24 |
| Framework | Inspect AI (confirmed MCP stdio support via `mcp_server_stdio` / `mcp_tools`) | 2026-05-24 |
| Repo timing | Private during build; public at Phase 3 proof-of-life gate | 2026-05-24 |
| Tomtorggler MCP deferred | Cloudflare-Workers HTTP-only deployment — different lifecycle from stdio MCPs; needs local dev server + HTTP transport wiring. v0.1 ships with 5 systems (chrisdoc, meimakes, thin, Baseline-CSV, Baseline-nodata); tomtorggler added in v0.2. | 2026-05-24 |

## 1. Goal

Two questions, in priority order:

1. **Does adding a Hevy MCP to Claude actually help a lifter, vs. simpler baselines?** (the more interesting question)
2. **Which Hevy MCP implementation adds the most value?** (the leaderboard)

The headline finding we're hunting for is something like: *"Most Hevy MCPs are thin passthroughs. The MCP layer adds X% over a CSV-in-prompt baseline. Here's what an MCP would need to expose to add real value."* That's a paper-worthy result — more valuable than a leaderboard.

## 2. What this eval isolates (and what it doesn't)

### Isolates
- **MCP design quality**: tool granularity, aggregation surface, coverage, faithfulness, schema quality, efficiency
- **The MCP layer's marginal value** over no-MCP baselines

### Does NOT isolate
- Hevy API quality (constant across all systems — same upstream)
- Claude's base reasoning ability (constant — same model)
- Prompt phrasing sensitivity (mitigated by running each prompt multiple times)

### Construct validity threats (and mitigations)
- **Risk:** If all MCPs are thin wrappers around the same Hevy endpoints, the eval has no discriminating power.
  **Mitigation:** Include the `hevy-mcp-thin` control (see §3) so we can detect this case and report it as the finding rather than mask it.
- **Risk:** "Correctness" on open-ended prompts is judge-dependent.
  **Mitigation:** Run LLM judge 3× per response, average; spot-check 20% manually.
- **Risk:** Prompts that don't force MCP design differences to matter will produce identical scores.
  **Mitigation:** Every prompt in §5 is chosen specifically because a thin wrapper would force the LLM into 10×+ tool calls or in-context aggregation work.

## 3. Systems under test

| System | Role | Why included |
|---|---|---|
| `chrisdoc/hevy-mcp` | Treatment | 240-star active leader (TypeScript) |
| ~~`tomtorggler/hevy-mcp-server`~~ | **Deferred to v0.2** (see §0) | 20 stars; HTTP-only Cloudflare Workers deployment |
| `meimakes/hevy-mcp-server` | Treatment | 3 stars, dual-transport — different design |
| `hevy-mcp-thin` | **Control** | We build this — 1:1 wrapper of Hevy API with no transformation, no aggregation, no analytics. Establishes the "what does the MCP layer add?" floor. |
| **Baseline A** | Baseline | Claude + CSV-in-prompt (raw workout export dumped into context), no MCP |
| **Baseline B** | Baseline | Claude with no data, only prior knowledge — measures what's answerable without any access |

**The `hevy-mcp-thin` control is the critical addition.** Any MCP scoring at or below it isn't adding design value. Any MCP scoring meaningfully above it is doing real work in the MCP layer. Without this control, we can't say what the MCP layer contributes.

## 4. Test data

**Default:** Himanshu's own Hevy export, if available — real noisy data with progressive overload, missed sessions, deload weeks, exercise rotation.

**Fallback:** Seeded synthetic test account with 3-6 months of realistic data. Synthetic is fine but must be *messy* — perfect data won't reveal failure modes. Script should mimic a real lifter, not a textbook program.

For each prompt, ground truth is computed **directly from the raw Hevy API**, bypassing every MCP. This gives a source of truth independent of any system under test.

## 5. Task suite (15 prompts, ~3 per category)

Every prompt is chosen because a thin wrapper would force the LLM into 10×+ tool calls or significant in-context computation. Well-designed MCPs should be able to answer in 2-3 calls.

### Category A: Trend & aggregation analysis (forces aggregation surface)
- "Across all my workouts in 2025, which exercise has shown the largest estimated 1RM gain?"
- "How much triceps volume did I do last month, broken down by exercise variant?"
- "What's my average squat 1RM by month over the last year?"

A thin MCP forces paginating every workout and computing 1RMs in-context. A well-designed MCP exposes `getProgress()` or similar. Expect tool-call counts to diverge by 10×.

### Category B: Personal-record detection (forces analytical endpoints)
- "Did I PR on any lift last week?"
- "What's my current PR for bench press, and when did I set it?"
- "Which lifts have I PR'd in the last 3 months but not in the last month?"

Is there a PR-detection endpoint, or does the LLM fetch full history and compute? The third prompt is especially discriminating — it requires temporal reasoning that a well-designed MCP could expose directly.

### Category C: Write operations (forces capability coverage) — **DEFERRED to v0.2**
- ~~"Update my last workout to add a 4th set of squats at the same weight."~~
- ~~"Create a new routine called 'Push Day v2' based on my last push workout but swap incline dumbbell press for incline barbell press."~~
- ~~"Mark my last workout as complete with a note saying 'felt strong.'"~~

Many MCPs are read-only — that's a binary capability gap that this category would surface. **Skipped in v0.1** (per §0) to avoid the test-account-pollution problem and reduce harness complexity. Read-only MCPs flagged in README's "future work" section. Will be re-added in v0.2 with a dedicated sacrificial Hevy account + rollback logic. **v0.1 task suite is 12 prompts, not 15.**

### Category D: Long-tail field preservation (forces faithfulness)
- "What RPE did I log for squats last Friday, and what were my notes?"
- "What time did I start my workout on May 1st, and how long did it last?"
- "Show me the rest times I logged between sets on my last deadlift session."

Tests whether the MCP preserves RPE, timestamps, rest times, notes — or strips them in translation.

### Category E: Programming & diagnostic reasoning (open-ended)
- "Design me a 4-week hypertrophy block for chest, given my training history."
- "Why might my deadlift be stalling? Look at my last 8 weeks."
- "Which muscle groups have I neglected this month? Suggest two exercises to add."

Open-ended rubric scoring. Tests whether the MCP surfaces enough context for good advice, and whether the LLM can use it.

## 6. Scoring

### Three signals per task (answer-level)
1. **Correctness** — 0/1 for factual, 0-5 rubric for open-ended (see §7)
2. **Tool-call count** — efficiency proxy
3. **Cost & latency** — tokens used, wall-clock seconds

### Three signals per task (MCP-layer-level)
1. **Coverage** — binary: did the MCP even expose the surface needed to answer this prompt? (e.g., write prompts fail this for read-only MCPs)
2. **Faithfulness** — no-LLM check. For retrieval prompts, diff each MCP's response against the raw Hevy API response. Measures whether the MCP transforms data lossily.
3. **Efficiency vs. thin baseline** — ratio of this MCP's tool-call count to `hevy-mcp-thin`'s count for the same prompt. Values <1 mean the MCP is doing useful aggregation work.

The **faithfulness check is unique** because it requires no LLM at all — just diff each MCP's `getWorkouts` response against the raw Hevy API for the same query. Pure MCP-layer metric.

## 7. Rubric for open-ended prompts

Each rubric is task-specific. Example for "Design me a 4-week hypertrophy block":

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| References lifter's actual history | No reference | Mentions one or two lifts | Builds program around their actual training data |
| Volume/intensity defensibility | Wrong for hypertrophy | Reasonable but generic | Defensible and tailored |
| Accounts for current progress trajectory | No | Partially | Explicitly references PRs/trends |

Total: 0-6, normalized to 0-5.

Run LLM judge **3× per response, average**. Single-shot LLM judges are noisy. Spot-check 20% manually for judge drift.

## 8. Framework

**Use Inspect AI** (UK AISI's eval framework, Python).

Three reasons:
1. Built for tool-use evals with custom scorers — exactly this shape
2. The result is publishable in a format the eval community recognizes
3. Closes the loop with another OSS interest area

If Inspect AI feels heavy for the first iteration, **Promptfoo** is the lighter alternative — something running in an evening, then port to Inspect AI once the design stabilizes.

Most Hevy MCPs are TypeScript, but we don't write code in them — we call them as MCP servers from a Python harness. So harness = Python.

## 9. Likely findings (hypotheses to pre-register)

Worth writing down *before* running the eval, so we can detect when findings just confirm priors:

- **H1 (likely):** `chrisdoc/hevy-mcp` will win the leaderboard on correctness.
- **H2 (the interesting one):** No Hevy MCP will meaningfully beat the CSV-in-prompt baseline. The "MCP layer adds X%" gap will be <15% on most tasks.
- ~~**H3:** Write-operation coverage will be the biggest discriminator — most MCPs are read-only.~~ **(Retired — Category C deferred to v0.2; re-instate when write tests re-added.)**
- **H4:** Faithfulness will be near-perfect across MCPs (they all wrap the same JSON), making it a less interesting metric than tool-call efficiency.
- **H5:** Open-ended programming/diagnostic prompts will show highest variance, because they depend more on aggregation surface.

If H2 is confirmed, that's the headline. If H2 is rejected, the leaderboard becomes the headline.

## 10. Open decisions

1. ~~**Real vs. synthetic Hevy data**~~ — **Resolved: real, lightly anonymized.** See §0.
2. ~~**Which judge model for open-ended scoring**~~ — **Resolved: Claude Sonnet + judge-vs-judge sanity check.** See §0.
3. ~~**Whether to include MCP write tests**~~ — **Resolved: skip in v0.1.** See §0.
4. ~~**License**~~ — **Resolved: MIT.** See §0.

## 11. What "shipped" looks like

Repo: `hevy-mcp-eval` (or similar)

```
hevy-mcp-eval/
├── README.md              ← findings first, methodology second
├── DESIGN.md              ← this doc
├── evals/                 ← Inspect AI task definitions, one file per category
├── data/
│   ├── seed.py            ← synthetic data generator
│   └── fixtures/          ← test account exports
├── systems/               ← config for each MCP under test + thin baseline impl
│   └── hevy-mcp-thin/     ← our 1:1 control wrapper
├── results/               ← regenerable leaderboard + per-task breakdown
└── scripts/               ← run.sh, score.sh
```

The README is the artifact people will actually read. Write the findings section first, then methodology — forces honesty.

## 12. Proof-of-life: first hour of work

Before building the whole suite, validate the loop:

1. Clone Inspect AI
2. Clone `chrisdoc/hevy-mcp` and stand it up against a test Hevy account
3. Write *one* eval task — a single factual prompt ("what's my heaviest squat?")
4. Run Claude + that MCP through Inspect AI on that one task
5. Get a pass/fail result with tool-call count logged

If that runs end-to-end, the rest is just adding rows. If it doesn't, the design needs to flex before more is built on it.

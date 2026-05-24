"""Aggregate Inspect eval logs into a leaderboard.

Discovers .eval files under logs/, groups by system (from `eval.task`),
and reports per-system × per-category breakdown of correctness, tool
calls, and tokens. Writes both a CSV and a markdown table to results/.

Usage:
    uv run python scripts/analyze_results.py
    uv run python scripts/analyze_results.py --logs logs/  --out results/
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_eval(path: Path) -> dict:
    """Load an .eval log via `inspect log dump`."""
    out = subprocess.run(
        ["uv", "run", "inspect", "log", "dump", str(path)],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT,
    )
    return json.loads(out.stdout)


def _score_value(scoring: str, scores: dict) -> Any:
    """Return the categorical value (CORRECT/PARTIAL/INCORRECT/NOANSWER) for the
    correctness scorer that applies to this sample's scoring type."""
    if scoring == "factual":
        return scores.get("correctness_factual", {}).get("value")
    if scoring == "open_ended":
        return scores.get("correctness_open_ended", {}).get("value")
    return None


def _score_to_numeric(value: Any) -> float | None:
    return {"C": 1.0, "P": 0.5, "I": 0.0, "N": None}.get(value, None)


def aggregate(eval_logs: list[Path]) -> dict[str, Any]:
    """Returns:
      { (system, category): {factual_total, factual_correct_eff, openended_total, ...},
        (system, "_all"): same totals across all categories,
      }
    """
    per_bucket: dict[tuple[str, str], dict] = defaultdict(lambda: {
        "factual_n": 0,
        "factual_score_sum": 0.0,
        "open_n": 0,
        "open_score_sum": 0.0,
        "coverage_n": 0,
        "coverage_correct": 0,
        "tool_calls": [],
        "tokens": [],
    })

    for log_path in eval_logs:
        log = load_eval(log_path)
        system = log.get("eval", {}).get("task", "unknown")
        # Strip module prefix if present
        if "/" in system:
            system = system.split("/")[-1]
        if system.startswith("hevy_eval"):
            # Old runs may use hevy_eval; prefer the system task name
            system = log.get("eval", {}).get("task_args", {}).get("system", system)

        for s in log["samples"]:
            cat = s.get("metadata", {}).get("category", "?")
            scoring = s.get("metadata", {}).get("scoring", "?")
            scores = s.get("scores", {})

            tool_calls = sum(1 for ev in s.get("events", []) if ev.get("event") == "tool")
            tokens = (s.get("model_usage") or {}).get("total_tokens") or 0

            for bucket_key in [(system, cat), (system, "_all")]:
                b = per_bucket[bucket_key]
                b["tool_calls"].append(tool_calls)
                b["tokens"].append(tokens)

                cv = _score_value(scoring, scores)
                num = _score_to_numeric(cv)
                if scoring == "factual" and num is not None:
                    b["factual_n"] += 1
                    b["factual_score_sum"] += num
                elif scoring == "open_ended" and num is not None:
                    b["open_n"] += 1
                    b["open_score_sum"] += num

                cov = scores.get("coverage", {}).get("value")
                if cov is not None:
                    b["coverage_n"] += 1
                    if cov == 1.0:
                        b["coverage_correct"] += 1

    return per_bucket


def format_pct(num: float, denom: int) -> str:
    if denom == 0:
        return "—"
    return f"{num / denom * 100:.0f}% ({num:.1f}/{denom})"


def write_reports(buckets: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "leaderboard.csv"
    md_path = out_dir / "leaderboard.md"

    # ---- CSV ----
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "system", "category",
            "factual_n", "factual_score",
            "open_n", "open_score",
            "coverage_n", "coverage_rate",
            "tool_calls_mean", "tool_calls_max",
            "tokens_mean", "tokens_total",
        ])
        for (sys, cat), b in sorted(buckets.items()):
            tc = b["tool_calls"]
            tk = b["tokens"]
            w.writerow([
                sys, cat,
                b["factual_n"], round(b["factual_score_sum"], 2),
                b["open_n"], round(b["open_score_sum"], 2),
                b["coverage_n"], (b["coverage_correct"] / b["coverage_n"]) if b["coverage_n"] else "",
                round(statistics.mean(tc), 1) if tc else "",
                max(tc) if tc else "",
                round(statistics.mean(tk), 0) if tk else "",
                sum(tk) if tk else "",
            ])

    # ---- Markdown (top-level only: per system) ----
    systems = sorted({k[0] for k in buckets.keys()})
    md_lines = [
        "# Hevy MCP Eval — Leaderboard",
        "",
        "| System | Factual | Open-ended | Coverage | Avg tool calls | Avg tokens |",
        "|---|---|---|---|---|---|",
    ]
    for sys in systems:
        b = buckets.get((sys, "_all"))
        if not b:
            continue
        tc = b["tool_calls"]
        tk = b["tokens"]
        md_lines.append(
            f"| {sys} | "
            f"{format_pct(b['factual_score_sum'], b['factual_n'])} | "
            f"{format_pct(b['open_score_sum'], b['open_n'])} | "
            f"{format_pct(b['coverage_correct'], b['coverage_n'])} | "
            f"{statistics.mean(tc):.1f} (max {max(tc)}) | "
            f"{statistics.mean(tk):,.0f} |"
        )
    md_path.write_text("\n".join(md_lines) + "\n")

    print(f"wrote {csv_path.relative_to(REPO_ROOT)}")
    print(f"wrote {md_path.relative_to(REPO_ROOT)}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--logs", default=str(REPO_ROOT / "logs"))
    p.add_argument("--out", default=str(REPO_ROOT / "results"))
    args = p.parse_args()

    log_files = sorted(Path(args.logs).glob("*.eval"))
    print(f"found {len(log_files)} eval logs")

    buckets = aggregate(log_files)
    write_reports(buckets, Path(args.out))

    # Print top-line summary
    print()
    systems = sorted({k[0] for k in buckets})
    for sys in systems:
        b = buckets.get((sys, "_all"))
        if not b:
            continue
        f_pct = (b["factual_score_sum"] / b["factual_n"] * 100) if b["factual_n"] else 0
        o_pct = (b["open_score_sum"] / b["open_n"] * 100) if b["open_n"] else 0
        print(f"  {sys:18}  factual={f_pct:5.1f}%  open={o_pct:5.1f}%  cov={b['coverage_correct']}/{b['coverage_n']}")


if __name__ == "__main__":
    main()

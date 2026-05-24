"""Generate the README figures from eval logs.

Outputs PNG files to results/figures/:
  - correctness_by_system.png — grouped bars, factual + open-ended per system
  - prompt_heatmap.png        — system × prompt grid colored by correctness
  - tool_calls_by_system.png  — avg vs max tool calls per system

Usage:
    uv run python scripts/make_charts.py
"""

from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"
OUT_DIR = REPO_ROOT / "results" / "figures"

SYSTEMS_ORDER = ["chrisdoc", "thin", "baseline_csv", "meimakes", "baseline_nodata"]
SYSTEM_LABELS = {
    "chrisdoc": "chrisdoc/hevy-mcp",
    "thin": "hevy-mcp-thin\n(control)",
    "baseline_csv": "baseline:\nCSV-in-prompt",
    "meimakes": "meimakes/\nhevy-mcp-server",
    "baseline_nodata": "baseline:\nno data",
}
PROMPT_ORDER = [
    "a01", "a02", "a03", "a04",
    "b01", "b02", "b03",
    "d01", "d02", "d03",
    "e01", "e02", "e03",
]

# Colors per category — A green, B blue, D orange, E purple
PROMPT_COLOR = {
    "a": "#2ca02c", "b": "#1f77b4", "d": "#ff7f0e", "e": "#9467bd",
}


def load_log(path: Path) -> dict:
    out = subprocess.run(
        ["uv", "run", "inspect", "log", "dump", str(path)],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT,
    )
    return json.loads(out.stdout)


def collect_results() -> dict:
    """Return per_system[prompt_id] = list of score-bucket values across epochs."""
    results: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    tool_calls: dict[str, list[int]] = defaultdict(list)
    for log_path in sorted(LOGS_DIR.glob("*.eval")):
        log = load_log(log_path)
        sys_arg = log.get("eval", {}).get("task_args", {}).get("system")
        if sys_arg is None:
            continue
        for s in log["samples"]:
            pid = s.get("id")
            sc_type = s.get("metadata", {}).get("scoring")
            scores = s.get("scores", {})
            if sc_type == "factual":
                val = scores.get("correctness_factual", {}).get("value")
            else:
                val = scores.get("correctness_open_ended", {}).get("value")
            results[sys_arg][pid].append(val)
            tool_calls[sys_arg].append(
                sum(1 for ev in s.get("events", []) if ev.get("event") == "tool")
            )
    return {"per_prompt": results, "tool_calls": tool_calls}


def score_to_numeric(v: str | None) -> float | None:
    return {"C": 1.0, "P": 0.5, "I": 0.0, "N": None}.get(v)


def avg_score(values: list[str]) -> float:
    nums = [score_to_numeric(v) for v in values]
    nums = [n for n in nums if n is not None]
    return sum(nums) / len(nums) if nums else 0.0


def chart_correctness(data: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))

    factual_pct = []
    open_pct = []
    for sys in SYSTEMS_ORDER:
        per_prompt = data["per_prompt"].get(sys, {})
        fact_vals = []
        open_vals = []
        for pid, vals in per_prompt.items():
            for v in vals:
                num = score_to_numeric(v)
                if num is None:
                    continue
                (open_vals if pid.startswith("e") else fact_vals).append(num)
        factual_pct.append(100 * sum(fact_vals) / len(fact_vals) if fact_vals else 0)
        open_pct.append(100 * sum(open_vals) / len(open_vals) if open_vals else 0)

    x = np.arange(len(SYSTEMS_ORDER))
    width = 0.35
    bars1 = ax.bar(x - width / 2, factual_pct, width, label="Factual (10 prompts)", color="#1f77b4")
    bars2 = ax.bar(x + width / 2, open_pct, width, label="Open-ended (3 prompts)", color="#ff7f0e")

    ax.set_ylabel("Correctness (%)", fontsize=11)
    ax.set_title("Correctness by system  ·  Sonnet 4.6  ·  3 epochs", fontsize=13, pad=14)
    ax.set_xticks(x)
    ax.set_xticklabels([SYSTEM_LABELS[s] for s in SYSTEMS_ORDER], fontsize=9)
    ax.set_ylim(0, 110)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bars in [bars1, bars2]:
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h + 1.5, f"{h:.0f}%", ha="center", fontsize=9)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "correctness_by_system.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def chart_heatmap(data: dict) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    matrix = np.zeros((len(PROMPT_ORDER), len(SYSTEMS_ORDER)))
    for i, pid in enumerate(PROMPT_ORDER):
        for j, sys in enumerate(SYSTEMS_ORDER):
            vals = data["per_prompt"].get(sys, {}).get(pid, [])
            matrix[i, j] = avg_score(vals)

    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(len(SYSTEMS_ORDER)))
    ax.set_xticklabels([SYSTEM_LABELS[s] for s in SYSTEMS_ORDER], fontsize=9)
    ax.set_yticks(range(len(PROMPT_ORDER)))
    ax.set_yticklabels(PROMPT_ORDER, fontsize=10)
    ax.set_title("Per-prompt correctness × system  ·  averaged over 3 epochs", fontsize=13, pad=14)

    # Cell annotations
    for i in range(len(PROMPT_ORDER)):
        for j in range(len(SYSTEMS_ORDER)):
            v = matrix[i, j]
            txt = "—" if v == 0 and SYSTEMS_ORDER[j] == "baseline_nodata" else f"{v:.1f}"
            color = "white" if v < 0.4 or v > 0.85 else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=9, color=color)

    cbar = plt.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("avg correctness  (1.0=CORRECT, 0.5=PARTIAL, 0.0=INCORRECT)", fontsize=9)

    # Mark unsolved prompts by coloring the y-tick label
    for tick, pid in zip(ax.get_yticklabels(), PROMPT_ORDER):
        if pid in ("a04", "b03"):
            tick.set_color("#cc0000")
            tick.set_fontweight("bold")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "prompt_heatmap.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def chart_tool_calls(data: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    avgs = []
    maxs = []
    for sys in SYSTEMS_ORDER:
        tc = data["tool_calls"].get(sys, [0])
        avgs.append(sum(tc) / len(tc) if tc else 0)
        maxs.append(max(tc) if tc else 0)

    x = np.arange(len(SYSTEMS_ORDER))
    width = 0.35
    ax.bar(x - width / 2, avgs, width, label="Avg per sample", color="#2ca02c")
    ax.bar(x + width / 2, maxs, width, label="Max per sample", color="#d62728")

    ax.set_ylabel("Tool calls", fontsize=11)
    ax.set_title("Tool-call efficiency  ·  fewer is better (less spend, less wall time)", fontsize=13, pad=14)
    ax.set_xticks(x)
    ax.set_xticklabels([SYSTEM_LABELS[s] for s in SYSTEMS_ORDER], fontsize=9)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for i, (a, m) in enumerate(zip(avgs, maxs)):
        ax.text(i - width / 2, a + 1.5, f"{a:.1f}", ha="center", fontsize=9)
        ax.text(i + width / 2, m + 1.5, f"{int(m)}", ha="center", fontsize=9)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "tool_calls_by_system.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("loading eval logs...")
    data = collect_results()
    print("generating charts...")
    chart_correctness(data)
    chart_heatmap(data)
    chart_tool_calls(data)
    print(f"wrote 3 PNGs to {OUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()

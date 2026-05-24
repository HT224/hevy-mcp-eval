"""Print every open-ended judge run from the eval logs so a human can
spot-check the rubric scoring. Per DESIGN.md §7 + plan Phase 10: review
20% manually to catch judge drift.

For each open-ended sample (Category E across systems × epochs), dumps:
  - prompt id + system + epoch
  - model's response (first 1500 chars)
  - per-dimension scores from each of the 3 judge runs
  - overall bucket (CORRECT/PARTIAL/INCORRECT)

Saves a markdown file to results/judge_audit.md so you can scan and
annotate. The audit doesn't change anything — it's evidence.

Usage:
    uv run python scripts/judge_audit.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_eval(path: Path) -> dict:
    out = subprocess.run(
        ["uv", "run", "inspect", "log", "dump", str(path)],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT,
    )
    return json.loads(out.stdout)


def system_from_log(log: dict, path: Path) -> str:
    sys_arg = log.get("eval", {}).get("task_args", {}).get("system")
    if sys_arg:
        return sys_arg
    name = log.get("eval", {}).get("task", "")
    if "/" in name:
        name = name.split("/")[-1]
    if name:
        return name
    return path.stem.split("_")[1] if "_" in path.stem else path.stem


def assistant_text(sample: dict) -> str:
    for m in reversed(sample.get("messages", [])):
        if m.get("role") == "assistant":
            c = m.get("content", "")
            if isinstance(c, list):
                return " ".join(x.get("text", "") for x in c if isinstance(x, dict))
            return str(c)
    return ""


def main() -> None:
    log_files = sorted((REPO_ROOT / "logs").glob("*.eval"))
    print(f"scanning {len(log_files)} log files")

    out_lines: list[str] = [
        "# Open-ended judge audit",
        "",
        "Manual spot-check evidence for Category E samples. Per plan Phase 10, ",
        "review at least 20% (about 9 of ~45 if full matrix complete) and flag ",
        "judge drift in the notes column.",
        "",
    ]

    rows = 0
    for log_path in log_files:
        log = load_eval(log_path)
        sys = system_from_log(log, log_path)
        for s in log.get("samples", []):
            if s.get("metadata", {}).get("scoring") != "open_ended":
                continue
            pid = s.get("id", "?")
            epoch = s.get("epoch", "?")
            response = assistant_text(s)
            sc = s.get("scores", {}).get("correctness_open_ended", {})
            value = sc.get("value")
            meta = sc.get("metadata") or {}
            overall = meta.get("overall_score_0to1")
            per_dim = meta.get("per_dimension_average", {})
            runs = meta.get("judge_runs", [])

            out_lines.extend([
                f"## {pid} · {sys} · epoch {epoch}  →  bucket {value}  (overall {overall})",
                "",
                "**per-dimension average across 3 judge runs**:",
                "",
            ])
            for d, v in per_dim.items():
                out_lines.append(f"- `{d}` → {v:.2f}/2")
            out_lines.append("")
            out_lines.append("**model response** (first 1500 chars):")
            out_lines.append("")
            out_lines.append("```")
            out_lines.append(response[:1500] + ("…" if len(response) > 1500 else ""))
            out_lines.append("```")
            out_lines.append("")
            out_lines.append("**judge run notes**:")
            out_lines.append("")
            for i, run in enumerate(runs, 1):
                overall_note = run.get("overall_note", "(no overall note)")
                out_lines.append(f"- run {i}: {overall_note}")
            out_lines.append("")
            out_lines.append("**human verdict**: _______ (CORRECT / PARTIAL / INCORRECT)  ")
            out_lines.append("**notes**: _______________________________________________")
            out_lines.append("")
            out_lines.append("---")
            out_lines.append("")
            rows += 1

    out_path = REPO_ROOT / "results" / "judge_audit.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines))
    print(f"wrote {out_path.relative_to(REPO_ROOT)} ({rows} open-ended samples)")


if __name__ == "__main__":
    main()

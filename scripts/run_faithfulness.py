"""Run the faithfulness diff against each MCP under test (no LLM in loop).

For each MCP, programmatically:
  1. Connect over stdio using the mcp Python SDK as a client
  2. Call the MCP's equivalent of get_workouts(page=1, page_size=5)
  3. Diff the response against raw HevyClient().get_workouts(...)
  4. Repeat for get_workout(id) on a known workout

Outputs results/faithfulness.json with a per-MCP report:
{
  "chrisdoc":  { "get-workouts": <summary>, "get-workout": <summary> },
  "meimakes":  { ... },
  "thin":      { ... }
}

Run:
    uv run python scripts/run_faithfulness.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from data.hevy_client import HevyClient
from scoring.faithfulness import field_diff, summarize_diffs

load_dotenv()


def mcp_params() -> dict[str, tuple[StdioServerParameters, dict[str, str]]]:
    """Return per-system (server params, tool_name_map).

    The tool name varies per MCP — most use kebab-case (`get-workouts`) but
    some use snake_case. Names verified from each project's README/source.
    """
    env_with_key = {**os.environ, "HEVY_API_KEY": os.environ["HEVY_API_KEY"]}
    return {
        "chrisdoc": (
            StdioServerParameters(command="npx", args=["-y", "hevy-mcp"], env=env_with_key),
            {"get_workouts": "get-workouts", "get_workout": "get-workout"},
        ),
        "meimakes": (
            StdioServerParameters(
                command="node",
                args=[str(REPO_ROOT / "vendor" / "meimakes-hevy-mcp-server" / "dist" / "index.js")],
                env=env_with_key,
            ),
            {"get_workouts": "get-workouts", "get_workout": "get-workout"},
        ),
        "thin": (
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "systems.hevy_mcp_thin"],
                env=env_with_key,
            ),
            {"get_workouts": "get-workouts", "get_workout": "get-workout"},
        ),
    }


def _unwrap_mcp_payload(result) -> dict | list:
    """Extract the structured JSON payload from an MCP tool-call result.

    MCPs typically return content=[TextContent(text="<json>")]; we parse that.
    Some MCPs may also populate `structuredContent` directly.
    """
    if getattr(result, "structuredContent", None):
        return result.structuredContent
    if not result.content:
        raise RuntimeError("MCP returned empty content")
    text = result.content[0].text
    return json.loads(text)


async def probe_system(name: str, params: StdioServerParameters, tool_names: dict[str, str],
                       fixtures: dict[str, dict]) -> dict:
    out: dict[str, dict] = {}
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # get-workouts page=1, pageSize=5
                tool = tool_names["get_workouts"]
                # Some MCPs use page/pageSize, others use page/page_size — try both.
                args_variants = [
                    {"page": 1, "pageSize": 5},
                    {"page": 1, "page_size": 5},
                ]
                gw_resp = None
                used_args = None
                for args in args_variants:
                    try:
                        r = await session.call_tool(tool, arguments=args)
                        gw_resp = _unwrap_mcp_payload(r)
                        used_args = args
                        break
                    except Exception as e:  # noqa: BLE001
                        last_err = e
                if gw_resp is None:
                    out["get-workouts"] = {"error": f"all arg variants failed: {last_err}"}
                else:
                    diffs = field_diff(fixtures["get_workouts"], gw_resp)
                    out["get-workouts"] = {
                        "args_used": used_args,
                        **summarize_diffs(diffs),
                    }

                # get-workout by id
                tool = tool_names["get_workout"]
                wid = fixtures["sample_workout_id"]
                # Try both common arg shapes
                arg_variants = [{"workoutId": wid}, {"workout_id": wid}, {"id": wid}]
                gw1_resp = None
                last_err = None
                for args in arg_variants:
                    try:
                        r = await session.call_tool(tool, arguments=args)
                        gw1_resp = _unwrap_mcp_payload(r)
                        used_args = args
                        break
                    except Exception as e:  # noqa: BLE001
                        last_err = e
                if gw1_resp is None:
                    out["get-workout"] = {"error": f"all arg variants failed: {last_err}"}
                else:
                    diffs = field_diff(fixtures["get_workout"], gw1_resp)
                    out["get-workout"] = {
                        "args_used": used_args,
                        **summarize_diffs(diffs),
                    }
    except Exception as e:  # noqa: BLE001
        out["__connect_error__"] = repr(e)
    return out


async def main() -> None:
    # Capture raw-API reference fixtures once
    with HevyClient() as c:
        raw_workouts = c.get_workouts(page=1, page_size=5)
        sample_id = raw_workouts["workouts"][0]["id"]
        raw_workout = c.get_workout(sample_id)

    fixtures = {
        "get_workouts": raw_workouts,
        "get_workout": raw_workout,
        "sample_workout_id": sample_id,
    }

    report: dict[str, dict] = {}
    for name, (params, tool_names) in mcp_params().items():
        print(f"→ probing {name}")
        report[name] = await probe_system(name, params, tool_names, fixtures)
        print(f"  done")

    out_path = REPO_ROOT / "results" / "faithfulness.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print()
    print(f"wrote {out_path.relative_to(REPO_ROOT)}")
    # Summary line per system
    print()
    for sys_name, sys_report in report.items():
        if "__connect_error__" in sys_report:
            print(f"  {sys_name:10}  CONNECT ERROR: {sys_report['__connect_error__'][:100]}")
            continue
        bits = []
        for tool, r in sys_report.items():
            if "error" in r:
                bits.append(f"{tool}=ERR")
            elif r.get("is_faithful"):
                bits.append(f"{tool}=faithful")
            else:
                bits.append(f"{tool}={r['total_divergences']}div")
        print(f"  {sys_name:10}  " + "  ".join(bits))


if __name__ == "__main__":
    asyncio.run(main())

"""Faithfulness analysis — runs OUTSIDE the Inspect eval loop, no LLM.

For each retrieval-shaped query, call each MCP under test with deterministic
arguments and compare the response to what the raw Hevy API returns for the
equivalent call. Report whether the MCP transforms data lossily (strips
fields, rounds numbers, renames keys, changes types).

Pure MCP-layer metric — measures the *integrity* of the read pipeline
independent of how an LLM uses it.

Driven by `scripts/run_faithfulness.py` (Phase 10). This module exposes the
comparison primitives used there.
"""

from __future__ import annotations

from typing import Any


def field_diff(api_obj: Any, mcp_obj: Any, path: str = "") -> list[dict]:
    """Recursive structural diff between an upstream-API value and an MCP value.

    Returns a list of {kind, path, api, mcp, note} records — one per
    divergence. Empty list = byte-for-byte semantic match.
    """
    diffs: list[dict] = []

    if type(api_obj) is not type(mcp_obj):
        # Allow int/float interchange — Hevy occasionally returns 0 vs 0.0.
        if not (
            isinstance(api_obj, (int, float)) and isinstance(mcp_obj, (int, float))
        ):
            diffs.append({
                "kind": "type_mismatch",
                "path": path,
                "api_type": type(api_obj).__name__,
                "mcp_type": type(mcp_obj).__name__,
            })
            return diffs

    if isinstance(api_obj, dict):
        api_keys = set(api_obj.keys())
        mcp_keys = set(mcp_obj.keys())
        for k in api_keys - mcp_keys:
            diffs.append({"kind": "stripped_field", "path": f"{path}.{k}", "api_value": api_obj[k]})
        for k in mcp_keys - api_keys:
            diffs.append({"kind": "added_field", "path": f"{path}.{k}", "mcp_value": mcp_obj[k]})
        for k in api_keys & mcp_keys:
            diffs.extend(field_diff(api_obj[k], mcp_obj[k], f"{path}.{k}"))
        return diffs

    if isinstance(api_obj, list):
        if len(api_obj) != len(mcp_obj):
            diffs.append({
                "kind": "list_length_mismatch",
                "path": path,
                "api_len": len(api_obj),
                "mcp_len": len(mcp_obj),
            })
            return diffs
        for i, (a, m) in enumerate(zip(api_obj, mcp_obj)):
            diffs.extend(field_diff(a, m, f"{path}[{i}]"))
        return diffs

    if isinstance(api_obj, float) and isinstance(mcp_obj, float):
        if abs(api_obj - mcp_obj) > 1e-6:
            diffs.append({"kind": "value_mismatch", "path": path, "api": api_obj, "mcp": mcp_obj})
        return diffs

    if api_obj != mcp_obj:
        diffs.append({"kind": "value_mismatch", "path": path, "api": api_obj, "mcp": mcp_obj})
    return diffs


def summarize_diffs(diffs: list[dict]) -> dict:
    """Roll up a diff list into headline counts the leaderboard uses."""
    by_kind: dict[str, int] = {}
    for d in diffs:
        by_kind[d["kind"]] = by_kind.get(d["kind"], 0) + 1
    return {
        "is_faithful": len(diffs) == 0,
        "total_divergences": len(diffs),
        "by_kind": by_kind,
        "first_5_examples": diffs[:5],
    }

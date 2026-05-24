"""Tiny helper for loading cached ground truth by prompt id."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "ground_truth" / "cache"


@lru_cache(maxsize=64)
def load(prompt_id: str) -> dict:
    return json.loads((CACHE_DIR / f"{prompt_id}.json").read_text())

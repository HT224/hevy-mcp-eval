"""Run every ground-truth computation and write data/ground_truth/cache/{id}.json."""

from __future__ import annotations

from . import a01, a02, a03, a04, b01, b02, b03, d01, d02, d03, e01, e02, e03
from ._helpers import write_cache

MODULES = [a01, a02, a03, a04, b01, b02, b03, d01, d02, d03, e01, e02, e03]


def main() -> None:
    for mod in MODULES:
        pid = mod.__name__.rsplit(".", 1)[-1]
        payload = mod.compute()
        out = write_cache(pid, payload)
        ans = payload.get("answer")
        ans_preview = "(open-ended)" if ans is None else str(ans)[:90]
        print(f"  ✓ {pid:5}  →  {out.name:12}  {ans_preview}")


if __name__ == "__main__":
    main()

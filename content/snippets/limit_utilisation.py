"""Limit utilisation summary: current risk metrics against soft and hard limits.

Run from the repo root:  uv run python content/snippets/limit_utilisation.py
Limits come from config/desk.yaml (illustrative). Status: ok, soft (escalate) or hard (breach).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

import pandas as pd

from core.data.world import build_world
from core.risk.limits import check_limits
from core.risk.sensitivities import sensitivities


def run(world=None) -> pd.DataFrame:
    """One row per limit that can be computed from first-order sensitivities."""
    world = world or build_world(7)
    sens = sensitivities(world.book, world.market, world.as_of)
    metrics = {
        "net_delta_usd": float(sens["net_delta"]),
        "gross_notional_usd": float(sens["gross"]),
    }
    return pd.DataFrame([vars(s) for s in check_limits(metrics)])


if __name__ == "__main__":
    print(run().to_string())

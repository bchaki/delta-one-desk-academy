"""Futures fair value monitor: front future against model fair value, with a rich/cheap flag.

Run from the repo root:  uv run python content/snippets/futures_fair_value_monitor.py
Fair value = S e^(rT) - dividends grown to expiry, rate = ln(1 + overnight fixing) + funding spread.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

import pandas as pd

from core.data.world import build_world
from core.strategies.common import futures_deviation_series


def run(world=None, days: int = 10, flag_bps: float = 5.0) -> pd.DataFrame:
    """Last ``days`` of deviations for both indices; ``signal`` is rich, cheap or fair at ``flag_bps``."""
    world = world or build_world(7)
    out = []
    for ix in ("D1 US 30", "D1 Europe 20"):
        df = (
            futures_deviation_series(world.market, ix)
            .tail(days)[["expiry", "spot", "future", "fair", "dev", "dev_bps"]]
            .copy()
        )
        df.insert(0, "index", ix)
        df["signal"] = df["dev_bps"].apply(
            lambda x: "rich" if x > flag_bps else "cheap" if x < -flag_bps else "fair"
        )
        out.append(df)
    return pd.concat(out)


if __name__ == "__main__":
    print(run().round(2).to_string())

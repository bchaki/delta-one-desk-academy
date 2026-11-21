"""Borrow cost report: daily and annual cost of the desk's short stock, by name.

Run from the repo root:  uv run python content/snippets/borrow_cost_report.py
Cost = |short value USD| x borrow fee (bps a year) / 10,000, per year; daily uses ACT/360.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

import pandas as pd

from core.data.world import build_world
from core.risk.sensitivities import snapshot


def run(world=None, top: int = 10) -> pd.DataFrame:
    """Largest borrow costs among net short names at the as-of date."""
    world = world or build_world(7)
    m, d = world.market, world.as_of
    snap = snapshot(world.book, m, d)
    shorts = snap[(snap["delta_usd"] < 0) & (snap["kind"] == "stock")]
    ts = pd.Timestamp(d)
    rows = []
    for _, r in shorts.iterrows():
        t = r["key"].split(":", 1)[1]
        if t not in m.borrow_fee_bps.columns:
            continue
        fee = float(m.borrow_fee_bps[t].loc[ts])
        v = abs(float(r["delta_usd"]))
        rows.append(
            {
                "ticker": t,
                "short_value_usd": v,
                "fee_bps": fee,
                "annual_cost_usd": v * fee / 1e4,
                "daily_cost_usd": v * fee / 1e4 / 360,
            }
        )
    cols = ["ticker", "short_value_usd", "fee_bps", "annual_cost_usd", "daily_cost_usd"]
    return (
        pd.DataFrame(rows, columns=cols)
        .sort_values("annual_cost_usd", ascending=False)
        .head(top)
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    print(run().round(1).to_string())

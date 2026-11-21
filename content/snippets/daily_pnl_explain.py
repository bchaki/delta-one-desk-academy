"""Daily PnL explain report: components, unexplained and a flag when unexplained is large.

Run from the repo root:  uv run python content/snippets/daily_pnl_explain.py
Positive = gain to the desk, USD. Components come from the clean model, total from the booked ledger.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

import pandas as pd

from core.data.world import build_world
from core.pnl.explain import explain_series, ledgers


def run(world=None, days: int = 5, threshold: float = 10_000.0) -> pd.DataFrame:
    """Last ``days`` rows of the explain table with a ``flag`` column (|unexplained| > ``threshold`` USD)."""
    world = world or build_world(7)
    booked, clean = ledgers(world.book, world.market)
    df = explain_series(booked, clean).tail(days).copy()
    df["flag"] = df["unexplained"].abs() > threshold
    return df


if __name__ == "__main__":
    print(run().round(0).to_string())

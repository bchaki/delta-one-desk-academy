"""Dividend ex-date checker: dividends going ex around the as-of date on names the desk holds.

Run from the repo root:  uv run python content/snippets/dividend_ex_date_checker.py
Expected cash = hedge quantity x gross dividend per share (local currency). A negative quantity is a
short, which owes the manufactured dividend. Use it to check the cash arrived after the ex-date.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root


import pandas as pd

from core.data.world import build_world
from core.risk.sensitivities import snapshot


def run(world=None, window_days: int = 120) -> pd.DataFrame:
    """Dividends with ex-date within +/- ``window_days`` of the as-of date, on held names."""
    world = world or build_world(7)
    m, d = world.market, world.as_of
    snap = snapshot(world.book, m, d)
    stocks = snap[snap["kind"] == "stock"]
    qty = {k.split(":", 1)[1]: q for k, q in zip(stocks["key"], stocks["qty"], strict=True)}
    rows = []
    for e in m.dividends:
        if e.ticker in qty and abs((e.ex_date - d).days) <= window_days and qty[e.ticker]:
            rows.append(
                {
                    "ticker": e.ticker,
                    "ex_date": e.ex_date,
                    "gross_per_share": float(e.amount),
                    "qty": qty[e.ticker],
                    "expected_cash": float(e.amount) * qty[e.ticker],
                    "status": "went ex" if e.ex_date <= d else "upcoming",
                    "kind": e.kind,
                }
            )
    cols = ["ticker", "ex_date", "gross_per_share", "qty", "expected_cash", "status", "kind"]
    return pd.DataFrame(rows, columns=cols).sort_values("ex_date").reset_index(drop=True)


if __name__ == "__main__":
    print(run().to_string())

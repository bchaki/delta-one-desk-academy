"""Index arbitrage: cash-and-carry when the future is rich, reverse when it is cheap.

Rich future (dev > 0): sell the future, buy the stock basket, collect the deviation as it converges.
Cheap future (dev < 0): buy the future, short the basket. One lot is one future contract hedged with
the matching basket. PnL is in index points x multiplier x contracts, in the contract currency.

Simplified: entries and exits at the day's closing deviation, a single round-trip cost and a
slippage input, no intraday path, no dividend surprise, instant execution of the basket. The full
version adds queueing, partial fills and basket tracking error.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def trade_pnl_points(entry_dev: float, exit_dev: float, cost_pts: float) -> float:
    """PnL in index points for one arbitrage trade, whichever side.

    Rich entry (entry_dev > 0, sell future): gains ``entry_dev - exit_dev``. Cheap entry
    (entry_dev < 0, buy future): gains ``exit_dev - entry_dev`` = ``-(entry_dev - exit_dev)`` seen from
    the other side. Both are ``sign(entry_dev) x (entry_dev - exit_dev)`` minus costs.
    """
    sign = 1.0 if entry_dev >= 0 else -1.0
    return sign * (entry_dev - exit_dev) - cost_pts


@dataclass(frozen=True)
class ArbResult:
    trades: pd.DataFrame
    gross: float
    costs: float
    slippage: float

    @property
    def net(self) -> float:
        return self.gross - self.costs - self.slippage


def arb_backtest(
    dev: pd.DataFrame,
    entry_bps: float,
    exit_bps: float,
    cost_bps: float,
    slippage_bps: float = 0.0,
    contracts: float = 10.0,
    multiplier: float = 50.0,
) -> ArbResult:
    """Run the entry/exit rule over a deviation series from ``futures_deviation_series``.

    Enter when ``|dev_bps| > entry_bps``; exit when ``|dev_bps| < exit_bps``, on a change of expiry
    (the position is held to convergence at the old expiry's last observation) or on the last day.
    ``cost_bps`` is the round-trip cost in bps of spot; ``slippage_bps`` is paid on entry and again on
    exit. Currency PnL = points x multiplier x contracts.
    """
    rows = []
    pos = None  # (date, expiry, entry_dev, spot)
    prev_exp = None
    prev_d = None
    prev_row = None
    last = dev.index[-1] if len(dev) else None
    for d, r in dev.iterrows():
        if pos is not None and (r.expiry != pos[1] or abs(r.dev_bps) < exit_bps or d == last):
            # exit on the previous day's deviation if the expiry changed (position converged there)
            exit_dev = r.dev if r.expiry == pos[1] else prev_row.dev
            exit_date = d if r.expiry == pos[1] else prev_d
            cost_pts = cost_bps / 1e4 * pos[3]
            slip_pts = 2.0 * slippage_bps / 1e4 * pos[3]
            gross = (1.0 if pos[2] >= 0 else -1.0) * (pos[2] - exit_dev)
            rows.append(
                {
                    "entry": pos[0],
                    "exit": exit_date,
                    "side": "cash-and-carry" if pos[2] >= 0 else "reverse",
                    "entry_dev": pos[2],
                    "exit_dev": exit_dev,
                    "gross": gross * multiplier * contracts,
                    "costs": cost_pts * multiplier * contracts,
                    "slippage": slip_pts * multiplier * contracts,
                }
            )
            pos = None
        if (
            pos is None
            and abs(r.dev_bps) > entry_bps
            and r.expiry == (prev_exp or r.expiry)
            and d != last
        ):
            pos = (d, r.expiry, r.dev, r.spot)
        prev_exp, prev_d, prev_row = r.expiry, d, r
    df = pd.DataFrame(
        rows,
        columns=["entry", "exit", "side", "entry_dev", "exit_dev", "gross", "costs", "slippage"],
    )
    return ArbResult(df, float(df.gross.sum()), float(df.costs.sum()), float(df.slippage.sum()))

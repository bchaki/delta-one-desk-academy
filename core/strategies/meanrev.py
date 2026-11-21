"""Generic threshold mean-reversion backtest used by ETF, ADR, basis and pairs strategies.

Input is a signal series in bps (or z-score units) that is expected to revert to zero. Enter when
``|signal| > entry`` on the rich/cheap side, exit when ``|signal| < exit``, or on the last day. A
position earns the reversion of the signal times ``notional`` (bps converted to currency) less
round-trip costs. Simplified: closing-price fills, no capacity limit, no overnight carry; the
caller says what the signal means and what the leg costs are.
"""

from __future__ import annotations

import pandas as pd


def threshold_backtest(
    signal: pd.Series, entry: float, exit: float, cost: float, notional: float = 1_000_000.0
) -> pd.DataFrame:
    """Trades from a threshold rule on ``signal`` (same units as ``entry``, ``exit`` and ``cost``).

    PnL of one trade = ``sign(entry_signal) x (entry_signal - exit_signal) - cost`` in signal units;
    currency PnL = that / 10,000 x ``notional`` when the signal is in bps. A positive signal means rich
    (short the signal), a negative one cheap (long it). Returns one row per trade with columns
    ``entry``, ``exit``, ``side``, ``entry_signal``, ``exit_signal``, ``days``, ``pnl_signal`` and
    ``pnl``.
    """
    rows = []
    pos: tuple[pd.Timestamp, float] | None = None
    idx = list(signal.index)
    for i, (d, v) in enumerate(signal.items()):
        last = i == len(idx) - 1
        if pos is not None and (abs(v) < exit or last):
            sgn = 1.0 if pos[1] > 0 else -1.0
            ps = sgn * (pos[1] - v) - cost
            rows.append(
                {
                    "entry": pos[0],
                    "exit": d,
                    "side": "short signal" if sgn > 0 else "long signal",
                    "entry_signal": pos[1],
                    "exit_signal": v,
                    "days": i - idx.index(pos[0]),
                    "pnl_signal": ps,
                    "pnl": ps / 1e4 * notional,
                }
            )
            pos = None
        if pos is None and abs(v) > entry and not last:
            pos = (d, float(v))
    cols = ["entry", "exit", "side", "entry_signal", "exit_signal", "days", "pnl_signal", "pnl"]
    return pd.DataFrame(rows, columns=cols)


def sweep_entry(
    signal: pd.Series, entries: list[float], exit: float, cost: float, notional: float = 1_000_000.0
) -> pd.DataFrame:
    """Total PnL, trade count and hit rate for each entry threshold: shows the width/frequency trade-off."""
    out = []
    for e in entries:
        t = threshold_backtest(signal, e, exit, cost, notional)
        out.append(
            {
                "entry": e,
                "trades": len(t),
                "total_pnl": float(t.pnl.sum()) if len(t) else 0.0,
                "hit_rate": float((t.pnl > 0).mean()) if len(t) else 0.0,
            }
        )
    return pd.DataFrame(out).set_index("entry")

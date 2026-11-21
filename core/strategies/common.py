"""Shared helpers for the strategy engines: the front-future deviation series and trade statistics.

All strategies run on the seeded synthetic world. Results are deterministic and illustrative: the
synthetic market contains mean-reverting futures deviations, premium/discount noise and so on, but no
real-world crowding or regime behaviour beyond what the generator built in.
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

from core.data.market import BENCH_BY_CCY, MarketHistory
from core.pricing import futures as fu

INDEX_CCY = {"D1 US 30": "USD", "D1 Europe 20": "EUR"}


def trade_stats(pnl: pd.Series) -> dict[str, float]:
    """Summary of a series of per-trade PnL: count, total, mean, hit rate and worst trade."""
    if len(pnl) == 0:
        return {"trades": 0.0, "total": 0.0, "mean": 0.0, "hit_rate": 0.0, "worst": 0.0}
    return {
        "trades": float(len(pnl)),
        "total": float(pnl.sum()),
        "mean": float(pnl.mean()),
        "hit_rate": float((pnl > 0).mean()),
        "worst": float(pnl.min()),
    }


def max_drawdown(cum: pd.Series) -> float:
    """Largest peak-to-trough fall of a cumulative PnL series (positive number)."""
    if len(cum) == 0:
        return 0.0
    return float((cum.cummax() - cum).max())


def futures_deviation_series(
    m: MarketHistory,
    index: str,
    funding_spread: float = 0.0010,
    min_days_to_expiry: int = 3,
    end: date | None = None,
) -> pd.DataFrame:
    """Front-contract futures against model fair value, one row per trading day.

    Columns: ``expiry``, ``t`` (years, ACT/365), ``spot``, ``future``, ``fair``, ``dev`` (future minus
    fair, index points) and ``dev_bps`` (of spot). Fair value is
    ``S e^{rT} - FV(dividends)`` with ``r = ln(1 + overnight fixing) + funding_spread``. Days within
    ``min_days_to_expiry`` of expiry are skipped (the front contract is rolled to the next one so the
    series does not collapse into expiry noise). Simplified: flat rate over the life of the contract.
    """
    bench = BENCH_BY_CCY[_ccy(index)]
    rows = []
    for d in m.days:
        if end and d > end:
            break
        exps = [e for e in m.front_expiries(index, d, 2) if (e - d).days >= min_days_to_expiry]
        if not exps:
            continue
        e = exps[0]
        ts = pd.Timestamp(d)
        if ts not in m.futures[(index, e)].index:
            continue
        t = (e - d).days / 365.0
        spot = float(m.index_level.at[ts, index])
        r = math.log(1.0 + m.fixing(bench, d)) + funding_spread
        divs = [
            ((x.ex_date - d).days / 365.0, x.amount) for x in m.index_dividends_between(index, d, e)
        ]
        fair = fu.model_forward(spot, r, divs, t)
        fut = float(m.futures[(index, e)].loc[ts])
        rows.append(
            {
                "date": ts,
                "expiry": e,
                "t": t,
                "spot": spot,
                "future": fut,
                "fair": fair,
                "dev": fut - fair,
                "dev_bps": (fut - fair) / spot * 1e4,
            }
        )
    return pd.DataFrame(rows).set_index("date")


def _ccy(index: str):
    from core.types import Currency

    return Currency(INDEX_CCY[index])

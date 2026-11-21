"""ETF arbitrage: premium/discount to NAV, and the cost of trading it in stress.

Premium = ETF close / NAV - 1 (bps), NAV = index total-return level x fund scale (synthetic). The
trade is create (ETF rich) or redeem (ETF cheap). Costs: creation fee over CU value, basket costs and
the ETF half-spread. Simplified: closing prices, no intraday iNAV drift; the stress multiplier scales
basket costs and half-spreads, the usual way liquidity vanishes first from the underlying.
"""

from __future__ import annotations

import pandas as pd

from core.data.market import MarketHistory
from core.pricing import etf as et
from core.strategies import meanrev as mr


def premium_series_bps(m: MarketHistory, ticker: str) -> pd.Series:
    """ETF premium (+) / discount (-) to NAV in bps for the whole history."""
    e = m.universe.etfs[ticker]
    nav = m.index_tr[e.index] * e.scale
    return ((m.etf_prices[ticker] / nav - 1.0) * 1e4).rename("premium_bps")


def threshold_bps(
    creation_fee: float,
    cu_value: float,
    basket_bps: float,
    half_spread_bps: float,
    stress: float = 1.0,
) -> float:
    """Break-even premium in bps; ``stress`` scales basket and ETF costs (fees do not scale)."""
    return et.arb_threshold_bps(
        creation_fee, cu_value, basket_bps * stress, half_spread_bps * stress
    )


def backtest(
    m: MarketHistory,
    ticker: str,
    edge_bps: float,
    basket_bps: float,
    half_spread_bps: float,
    stress: float = 1.0,
    notional: float = 1_000_000.0,
) -> pd.DataFrame:
    """Trade ``|premium| > threshold + edge`` back to ``threshold / 2``; costs charged per round trip.

    Entry is the break-even threshold plus ``edge_bps``; exit when the premium is inside half the
    threshold. Uses ``threshold_backtest`` with the round-trip cost already in the threshold, so the
    per-trade cost is the threshold itself.
    """
    e = m.universe.etfs[ticker]
    nav0 = float(m.index_tr[e.index].iloc[-1] * e.scale)
    thr = threshold_bps(e.creation_fee, nav0 * e.cu_size, basket_bps, half_spread_bps, stress)
    return mr.threshold_backtest(
        premium_series_bps(m, ticker), thr + edge_bps, thr / 2.0, thr, notional
    )

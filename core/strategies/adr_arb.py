"""ADR arbitrage: deviation from parity (local price x ratio x FX) and the band that makes it tradeable.

Deviation = ADR / fair value - 1 in bps. The band is the depositary conversion fee plus costs (bps of
fair value). Simplified: closes only, same-day fills on both legs, no borrow on the local leg and no
settlement mismatch; the full version adds FX settlement and the cut-off for conversion requests.
"""

from __future__ import annotations

import pandas as pd

from core.data.market import MarketHistory
from core.strategies import meanrev as mr


def deviation_series_bps(m: MarketHistory, adr_ticker: str) -> pd.Series:
    """ADR minus parity, bps of fair value, for the whole history."""
    a = m.universe.adrs[adr_ticker]
    st = m.universe.stocks[a.underlying]
    days = list(m.prices.index)
    fx = pd.Series([m.fx_usd_per(st.ccy, d.date()) for d in days], index=m.prices.index)
    fair = m.prices[a.underlying] * a.ratio * fx
    return ((m.adr_prices[adr_ticker] / fair - 1.0) * 1e4).rename("dev_bps")


def band_bps(fee_per_adr: float, fair: float, cost_bps: float) -> float:
    """Band half-width in bps of fair value: ``fee / fair x 10,000 + cost_bps``."""
    return fee_per_adr / fair * 1e4 + cost_bps


def backtest(
    m: MarketHistory,
    adr_ticker: str,
    cost_bps: float,
    edge_bps: float = 0.0,
    notional: float = 1_000_000.0,
) -> pd.DataFrame:
    """Trade outside the band plus ``edge_bps``, exit inside half the band; cost = band (round trip)."""
    a = m.universe.adrs[adr_ticker]
    fair = float(m.adr_prices[adr_ticker].iloc[-1])
    band = band_bps(a.depositary_fee, fair, cost_bps)
    return mr.threshold_backtest(
        deviation_series_bps(m, adr_ticker), band + edge_bps, band / 2.0, band, notional
    )

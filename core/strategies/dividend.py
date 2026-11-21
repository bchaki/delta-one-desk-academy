"""Dividend trading: dividend futures against a view, and the cancellation stress.

A dividend future settles on the index dividend points realised in its year. Long 1 unit gains
``settlement - entry`` (index points x unit value). Simplified: no discounting between entry and
settlement, no basis between swap and future; see ``core.pricing.dividend_derivs`` for PV maths.
"""

from __future__ import annotations

import pandas as pd

from core.data.market import MarketHistory


def future_pnl(units: float, entry: float, settlement: float) -> float:
    """Long ``units`` of a dividend future: ``units x (settlement - entry)``."""
    return units * (settlement - entry)


def year_backtest(m: MarketHistory, year: int, entry_offset_days: int = 0) -> dict[str, float]:
    """Buy the year's dividend future ``entry_offset_days`` after it first trades and hold to settlement.

    Returns entry, settlement, the PnL per unit and the largest adverse mark-to-market.
    """
    s = m.div_futures[year].loc[: pd.Timestamp(year=year, month=12, day=31)].dropna()
    entry = float(s.iloc[min(entry_offset_days, len(s) - 1)])
    settle = float(s.iloc[-1])
    path = s.iloc[min(entry_offset_days, len(s) - 1) :] - entry
    return {
        "entry": entry,
        "settlement": settle,
        "pnl": settle - entry,
        "worst_mtm": float(path.min()),
    }


def cancellation_stress(
    units: float, strike: float, forecast: float, fractions: list[float]
) -> pd.DataFrame:
    """PnL of a long dividend swap as a growing share of the forecast is cancelled (settles at zero).

    ``pnl = units x (forecast x (1 - f) - strike)``. The short side (a desk that sold dividends to
    hedge structured notes, say) gains the same amount.
    """
    return pd.DataFrame(
        {
            "cancelled": fractions,
            "pnl": [units * (forecast * (1.0 - f) - strike) for f in fractions],
        }
    ).set_index("cancelled")


def hedge_note_exposure(
    notional_units: float, yearly_points: float, years: float, cut: float
) -> float:
    """Desk exposure on notes that pay holders the dividend: loss from a ``cut`` in dividends not yet hedged.

    ``units x yearly points x years x cut`` is the PV-ignoring change in the amount the desk expects to
    receive on its hedge. Teaching version; the full model discounts and splits by ex-date.
    """
    return notional_units * yearly_points * years * cut

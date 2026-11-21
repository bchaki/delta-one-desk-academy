"""Dividend swaps/futures and delta-one notes.

Dividend contracts settle on realised dividends in index points (or per share) for a period.
``units`` is currency per point. Positive PnL = gain to the long (receiver of realised dividends).
"""

from __future__ import annotations

from collections.abc import Sequence


def dividend_swap_pnl(units: float, strike: float, realised: float) -> float:
    """Long dividend swap PnL at settlement = units x (realised - strike)."""
    return units * (realised - strike)


def dividend_swap_pv(units: float, strike: float, expected: float, df: float) -> float:
    """PV of a long dividend swap = units x (expected - strike) x DF(settlement)."""
    return units * (expected - strike) * df


def dividend_strip_pv(
    units: float, strikes: Sequence[float], expected: Sequence[float], dfs: Sequence[float]
) -> float:
    """PV of a strip of annual dividend swaps: sum units x (E_i - K_i) x DF_i."""
    return sum(
        dividend_swap_pv(units, k, e, d) for k, e, d in zip(strikes, expected, dfs, strict=True)
    )


def implied_vs_forecast(market: float, forecast: float) -> tuple[float, float]:
    """Market-implied minus analyst forecast: (points, fraction of forecast).

    Negative means the market prices fewer dividends than analysts forecast, typical when structured
    products desks hedge by selling dividends.
    """
    diff = market - forecast
    return diff, diff / forecast


def cancellation_pnl(units: float, strike: float, forecast: float, cancel_fraction: float) -> float:
    """Long dividend swap PnL if ``cancel_fraction`` of the forecast dividends are cancelled.

    realised = forecast x (1 - cancel_fraction); PnL = units x (realised - strike).
    """
    if not 0 <= cancel_fraction <= 1:
        raise ValueError("cancel_fraction must be within [0, 1]")
    return dividend_swap_pnl(units, strike, forecast * (1.0 - cancel_fraction))


def tracker_note_value(
    notional: float, index_total_return: float, annual_fee: float, years: float
) -> float:
    """Delta-one note value = N x (1 + total return) x (1 - fee)^years.

    The issuer hedges with the underlying (or a total-return swap); investors also carry issuer
    credit risk, which this function does not price.
    """
    return notional * (1.0 + index_total_return) * (1.0 - annual_fee) ** years

"""Financing and basis: what the desk earns carrying client exposure, and which hedge is cheapest.

All spreads are bps a year over the currency's overnight benchmark, ACT/360 for USD/EUR (basis 360).
Positive PnL is a gain to the desk. Simplified: flat rates over the period, balance sheet cost as a
single bps charge on notional; the full version adds margin funding timing and tax.
"""

from __future__ import annotations

import pandas as pd


def swap_financing_pnl(
    notional: float, spread_bps: float, ftp_bps: float, bs_bps: float, days: int, basis: int = 360
) -> float:
    """Desk PnL on a financed swap over ``days``: ``notional x (spread - FTP - balance sheet) x days/basis``.

    The client pays benchmark + ``spread_bps``; the desk funds the stock hedge at benchmark +
    ``ftp_bps`` and pays ``bs_bps`` for balance sheet. The benchmark cancels.
    """
    return notional * (spread_bps - ftp_bps - bs_bps) / 1e4 * days / basis


def futures_hedge_net_bps(
    spread_bps: float, implied_spread_bps: float, margin_pct: float, ftp_bps: float
) -> float:
    """Net bps a year when the desk hedges a swap with futures.

    Cost = the financing embedded in the future (``implied_spread_bps`` over the benchmark) plus the
    funding of initial margin (``margin_pct x ftp_bps``). No balance sheet is used for the hedge.
    """
    return spread_bps - implied_spread_bps - margin_pct * ftp_bps


def hedge_choice(
    spread_bps: float, ftp_bps: float, bs_bps: float, implied_spread_bps: float, margin_pct: float
) -> dict[str, float]:
    """Net bps for the stock hedge and the futures hedge, and which is better (``best``: 1 or 0 = stock)."""
    stock = spread_bps - ftp_bps - bs_bps
    fut = futures_hedge_net_bps(spread_bps, implied_spread_bps, margin_pct, ftp_bps)
    return {"stock": stock, "futures": fut, "best_is_futures": 1.0 if fut > stock else 0.0}


def funding_shock_pnl(notional: float, ftp_shock_bps: float, days: int, basis: int = 360) -> float:
    """PnL from a parallel FTP move held for ``days``: ``-notional x shock x days/basis`` (rise = cost)."""
    return -notional * ftp_shock_bps / 1e4 * days / basis


def implied_financing_spread_series(
    dev: pd.DataFrame, funding_spread_bps: float = 10.0
) -> pd.Series:
    """Financing spread (bps a year over the benchmark) implied by the front future each day.

    ``funding_spread_bps + dev_bps / t`` where ``dev_bps`` is the future minus fair value in bps of spot
    (fair value used ``funding_spread_bps``) and ``t`` the years to expiry.
    """
    return (funding_spread_bps + dev["dev_bps"] / dev["t"]).rename("implied_spread_bps")


def sensitivity_table(
    notional: float, spread_bps: float, bs_bps: float, ftps: list[float], days: int = 360
) -> pd.DataFrame:
    """Annual PnL by FTP level: shows how fast the carry disappears as funding costs rise."""
    return pd.DataFrame(
        {
            "ftp_bps": ftps,
            "pnl": [swap_financing_pnl(notional, spread_bps, f, bs_bps, days) for f in ftps],
        }
    ).set_index("ftp_bps")

"""ETF NAV, premium/discount and the create/redeem arbitrage test."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


def nav_per_share(
    holdings: Mapping[str, float],
    prices: Mapping[str, float],
    cash: float,
    shares_outstanding: float,
) -> float:
    """NAV per ETF share = (sum_i qty_i x P_i + cash) / ETF shares outstanding.

    Using intraday prices gives the iNAV; using closing prices gives the official NAV. Quantities
    are fund holdings, prices and cash are in the fund currency.
    """
    value = sum(q * prices[t] for t, q in holdings.items()) + cash
    return value / shares_outstanding


def premium_discount(etf_price: float, nav: float) -> float:
    """Premium (+) / discount (-) = ETF price / NAV - 1."""
    return etf_price / nav - 1.0


class EtfAction(StrEnum):
    CREATE = "create"  # ETF rich: sell ETF, buy basket, deliver basket for new ETF shares
    REDEEM = "redeem"  # ETF cheap: buy ETF, redeem for basket, sell basket
    NONE = "none"


@dataclass(frozen=True)
class EtfArb:
    action: EtfAction
    premium_bps: float
    threshold_bps: float
    edge_bps: float
    pnl_per_creation_unit: float


def arb_threshold_bps(
    creation_fee: float, cu_value: float, basket_cost_bps: float, etf_half_spread_bps: float
) -> float:
    """Break-even |premium| in bps: creation fee / CU value + basket costs + ETF bid/ask.

    ``creation_fee`` and ``cu_value`` are in the same currency; ``cu_value`` = iNAV x CU size.
    """
    return creation_fee / cu_value * 10_000.0 + basket_cost_bps + etf_half_spread_bps


def etf_arbitrage(
    etf_price: float,
    inav: float,
    cu_size: float,
    creation_fee: float,
    basket_cost_bps: float,
    etf_half_spread_bps: float,
) -> EtfArb:
    """Arbitrage exists when |premium| > creation/redemption fee + basket costs + ETF bid/ask.

    PnL per creation unit = |ETF - iNAV| x CU size - fee - (basket + ETF spread bps) x CU value.
    Simplified: single-currency, instant execution, no financing of the basket for settlement.
    """
    cu_value = inav * cu_size
    prem_bps = premium_discount(etf_price, inav) * 10_000.0
    thr = arb_threshold_bps(creation_fee, cu_value, basket_cost_bps, etf_half_spread_bps)
    edge = abs(prem_bps) - thr
    if edge <= 0:
        return EtfArb(EtfAction.NONE, prem_bps, thr, 0.0, 0.0)
    action = EtfAction.CREATE if prem_bps > 0 else EtfAction.REDEEM
    pnl = edge / 10_000.0 * cu_value
    return EtfArb(action, prem_bps, thr, edge, pnl)

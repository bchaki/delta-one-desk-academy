"""Securities borrowing and lending economics.

Rates and fees are decimals unless the name ends in ``_bps``. Amounts are in the loan currency.
Fee = loan value x fee x days / basis. Cash rebate = cash collateral x rebate rate x days / basis,
with rebate rate = reinvestment rate - fee (it can be negative for hard-to-borrow names).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from core import config


def collateral_required(loan_value: float, margin: float) -> float:
    """Collateral = loan value x margin (1.02 domestic / 1.05 cross-border, illustrative)."""
    return loan_value * margin


def default_margin(cross_border: bool) -> float:
    s = config.desk().sbl
    return s.margin_cross_border if cross_border else s.margin_domestic


def loan_fee(loan_value: float, fee: float, days: int, basis: int) -> float:
    """Borrow fee = loan value x fee x days / basis (non-cash collateral loans)."""
    return loan_value * fee * days / basis


def rebate_rate(reinvestment_rate: float, fee: float) -> float:
    """Cash-collateral rebate rate = reinvestment rate - fee."""
    return reinvestment_rate - fee


def cash_rebate(cash_collateral: float, rebate: float, days: int, basis: int) -> float:
    """Rebate paid by the lender on cash collateral = cash x rebate rate x days / basis."""
    return cash_collateral * rebate * days / basis


def revenue_split(fee_revenue: float, lender_share: float | None = None) -> tuple[float, float]:
    """Split loan revenue into (beneficial owner / lender, agent) using config shares (80/20)."""
    ls = config.desk().sbl.lender_share if lender_share is None else lender_share
    return fee_revenue * ls, fee_revenue * (1.0 - ls)


def manufactured_dividend(shares: float, gross_dividend: float, pct: float = 1.0) -> float:
    """Amount the borrower pays the lender in lieu of a dividend = shares x gross x pct."""
    return shares * gross_dividend * pct


@dataclass(frozen=True)
class CollateralMove:
    required: float
    collateral_after: float
    transfer: float  # positive: borrower posts more; negative: lender returns


def mark_collateral(
    shares: float, price: float, margin: float, current: float, min_transfer: float = 0.0
) -> CollateralMove:
    """Daily mark: top up whenever collateral is below loan x margin; return excess only when it
    exceeds ``min_transfer``. Collateral is therefore never below the requirement after a mark."""
    required = shares * price * margin
    if required > current:
        return CollateralMove(required, required, required - current)
    excess = current - required
    if excess > 0 and excess >= max(min_transfer, 1e-12):
        return CollateralMove(required, required, -excess)
    return CollateralMove(required, current, 0.0)


def collateral_path(
    shares: float,
    prices: Sequence[float],
    margin: float,
    min_transfer: float = 0.0,
) -> list[CollateralMove]:
    """Collateral moves along a price path, starting fully collateralised at ``prices[0]``."""
    current = shares * prices[0] * margin
    out = []
    for p in prices[1:]:
        m = mark_collateral(shares, p, margin, current, min_transfer)
        out.append(m)
        current = m.collateral_after
    return out


# --------------------------------------------------------------------------- recalls and costs


def recall_options(
    shares: float,
    price: float,
    old_fee: float,
    new_fee: float,
    days: int,
    basis: int,
    buyin_premium: float,
    buyin_impact: float,
    internal_cost: float,
) -> dict[str, float]:
    """Cost of handling a recall under three choices (all fees/costs are decimals per year or pct).

    - ``reborrow``: extra fee over ``days`` = loan value x (new - old) x days / basis.
    - ``buy_in``: shares x price x (buy-in premium + market impact).
    - ``internalise``: loan value x internal cost x days / basis (cover from internal inventory).
    """
    lv = shares * price
    return {
        "reborrow": lv * (new_fee - old_fee) * days / basis,
        "buy_in": lv * (buyin_premium + buyin_impact),
        "internalise": lv * internal_cost * days / basis,
    }


@dataclass(frozen=True)
class ShortCost:
    fee: float
    dividends: float

    @property
    def total(self) -> float:
        return self.fee + self.dividends


def short_cost_drag(
    shares: float, price: float, fee: float, days: int, basis: int, dividends_per_share: float = 0.0
) -> ShortCost:
    """Carry cost of a short beyond price PnL: borrow fee + manufactured dividends.

    Assumes the cash proceeds earn the benchmark through the rebate, so only the fee is a net cost.
    """
    return ShortCost(
        fee=loan_fee(shares * price, fee, days, basis),
        dividends=manufactured_dividend(shares, dividends_per_share),
    )


# --------------------------------------------------------------------------- fee curve


def fee_from_utilisation(utilisation: float, gc_fee_bps: float, steepness: float) -> float:
    """Stylised fee (bps) from utilisation u: gc x (1 + steepness x u^2 / (1 - u)); u capped at 0.99.

    Convex and increasing: little pricing power at low utilisation, a spike as supply runs out.
    Illustrative curve, not market data.
    """
    u = min(max(utilisation, 0.0), 0.99)
    return gc_fee_bps * (1.0 + steepness * u * u / (1.0 - u))


def squeeze_utilisation(
    supply: float, demand: float, recall_pct: float, demand_multiplier: float
) -> float:
    """Utilisation after a squeeze: demand x multiplier / (supply x (1 - recall)), capped at 0.99."""
    return min(demand * demand_multiplier / (supply * (1.0 - recall_pct)), 0.99)

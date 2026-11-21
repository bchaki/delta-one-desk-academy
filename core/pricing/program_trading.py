"""Program (basket) trading: square-root impact and a principal risk-bid teaching model.

Teaching model only. Real desks use proprietary impact, correlation and inventory models.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


def sqrt_impact_bps(k: float, daily_vol: float, qty: float, adv: float) -> float:
    """Square-root market impact in bps: k x sigma_daily x sqrt(Q / ADV) x 10,000.

    ``daily_vol`` is a decimal (0.02 = 2%). ``qty`` and ``adv`` in shares.
    """
    return k * daily_vol * math.sqrt(qty / adv) * 10_000.0


def risk_charge_bps(daily_vol: float, horizon_days: float, risk_aversion: float) -> float:
    """Risk charge in bps = vol x sqrt(horizon) x risk aversion x 10,000 (single position)."""
    return daily_vol * math.sqrt(horizon_days) * risk_aversion * 10_000.0


@dataclass(frozen=True)
class BasketLeg:
    qty: float
    price: float
    adv: float
    daily_vol: float

    @property
    def notional(self) -> float:
        return self.qty * self.price


def basket_daily_vol(legs: Sequence[BasketLeg], rho: float) -> float:
    """Daily vol of the basket as a fraction of notional with a single pairwise correlation.

    sigma_p^2 = sum w_i^2 s_i^2 + rho sum_{i != j} w_i w_j s_i s_j. Uses absolute weights and
    long-only legs; a long/short basket would need signed weights.
    """
    total = sum(leg.notional for leg in legs)
    w = np.array([leg.notional / total for leg in legs])
    s = np.array([leg.daily_vol for leg in legs])
    ws = w * s
    var = float(np.sum(ws**2) + rho * (np.sum(ws) ** 2 - np.sum(ws**2)))
    return math.sqrt(var)


@dataclass(frozen=True)
class RiskBid:
    notional: float
    half_spread_bps: float
    impact_bps: float
    risk_charge_bps: float
    basket_vol: float
    horizon_days: float

    @property
    def total_bps(self) -> float:
        """Principal risk bid = half spread + impact + risk charge."""
        return self.half_spread_bps + self.impact_bps + self.risk_charge_bps

    @property
    def total_amount(self) -> float:
        return self.total_bps / 10_000.0 * self.notional


def principal_risk_bid(
    legs: Sequence[BasketLeg],
    half_spread_bps: float,
    impact_k: float,
    rho: float,
    horizon_days: float,
    risk_aversion: float,
) -> RiskBid:
    """Principal risk bid for a basket.

    half spread (input) + notional-weighted square-root impact + risk charge
    (basket vol x sqrt(horizon) x risk aversion). The risk charge uses basket (diversified) vol.
    """
    notional = sum(leg.notional for leg in legs)
    impact = (
        sum(
            leg.notional * sqrt_impact_bps(impact_k, leg.daily_vol, leg.qty, leg.adv)
            for leg in legs
        )
        / notional
    )
    vol = basket_daily_vol(legs, rho)
    risk = vol * math.sqrt(horizon_days) * risk_aversion * 10_000.0
    return RiskBid(notional, half_spread_bps, impact, risk, vol, horizon_days)


def win_pnl_moments(bid: RiskBid) -> tuple[float, float]:
    """Mean and standard deviation of PnL if the desk wins the trade (currency units).

    The bid pays for half spread and impact, which the desk then incurs, so expected PnL is the
    risk charge. Std = basket vol x sqrt(horizon) x notional (market move while liquidating).
    """
    mean = bid.risk_charge_bps / 10_000.0 * bid.notional
    std = bid.basket_vol * math.sqrt(bid.horizon_days) * bid.notional
    return mean, std


def simulate_win_pnl(bid: RiskBid, n: int = 10_000, seed: int = 0) -> np.ndarray:
    """Simulated PnL outcomes (normal market move) if the desk wins; deterministic per ``seed``."""
    mean, std = win_pnl_moments(bid)
    rng = np.random.default_rng(seed)
    return mean + std * rng.standard_normal(n)

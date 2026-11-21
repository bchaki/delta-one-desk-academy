"""Exchange margin for futures: a SPAN-like scan, a VaR-style alternative and variation margin.

Teaching model. Real exchange methodologies (and the move to VaR-style models) are more detailed.
All positions are assumed to be in one reporting currency.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from core import config
from core.margin import MarginResult


@dataclass(frozen=True)
class FuturePos:
    """A futures position: signed quantity in contracts, price in index points."""

    product: str
    expiry: str
    qty: float
    price: float
    multiplier: float

    @property
    def notional(self) -> float:
        """Signed notional = qty x price x multiplier."""
        return self.qty * self.price * self.multiplier


def scan_grid(range_pct: float, points: int) -> np.ndarray:
    """Price scenarios from -range to +range (fractions), ``points`` evenly spaced."""
    return np.linspace(-range_pct, range_pct, points)


def calendar_matching(positions: Sequence[FuturePos]) -> tuple[float, float]:
    """For one product: (matched notional, net signed notional) after pairing longs against shorts
    across expiries. Matched notional = min(long notional, short notional)."""
    long_n = sum(p.notional for p in positions if p.qty > 0)
    short_n = -sum(p.notional for p in positions if p.qty < 0)
    return min(long_n, short_n), long_n - short_n


def span_like_margin(positions: Sequence[FuturePos]) -> MarginResult:
    """SPAN-like margin.

    1. Per product, match offsetting longs/shorts across expiries and charge
       ``calendar_spread_charge_pct`` x matched notional (removed from the scan).
    2. Scan the remaining net notional over a price grid: scan risk = worst loss, never below 0.
    3. Inter-commodity credit for opposite net positions in configured pairs:
       credit = credit rate x min(scan A, scan B).

    gross = sum of scan risks + calendar charges; credits = inter-commodity credits; net floors at 0.
    """
    p = config.margin().exchange
    by_product: dict[str, list[FuturePos]] = {}
    for pos in positions:
        by_product.setdefault(pos.product, []).append(pos)

    scans: dict[str, float] = {}
    nets: dict[str, float] = {}
    cal_charge = 0.0
    for prod, ps in by_product.items():
        matched, net = calendar_matching(ps)
        cal_charge += p.calendar_spread_charge_pct * matched
        grid = scan_grid(p.scan_range_pct[prod], p.scan_points)
        scans[prod] = max(float(np.max(-net * grid)), 0.0)
        nets[prod] = net

    credits = 0.0
    credit_detail: dict[str, float] = {}
    for pair, rate in p.inter_index_credit.items():
        a, b = pair.split("|")
        if a in nets and b in nets and nets[a] * nets[b] < 0:
            c = rate * min(scans[a], scans[b])
            credit_detail[pair] = c
            credits += c

    detail = {f"scan:{k}": v for k, v in scans.items()}
    detail["calendar_spread_charges"] = cal_charge
    detail.update({f"credit:{k}": v for k, v in credit_detail.items()})
    return MarginResult(gross=sum(scans.values()) + cal_charge, credits=credits, detail=detail)


def portfolio_pnl_history(
    returns: Mapping[str, np.ndarray], notionals: Mapping[str, float]
) -> np.ndarray:
    """Historical daily portfolio PnL = sum_p notional_p x return_p,t (aligned return series)."""
    return sum(notionals[k] * np.asarray(returns[k]) for k in notionals)


def var_margin(daily_pnl: Sequence[float], confidence: float, horizon_days: float) -> float:
    """VaR-style margin = -quantile_{1-confidence}(daily PnL) x sqrt(horizon). Never negative.

    Simplified: square-root-of-time scaling of one-day historical VaR, no liquidity or procyclicality add-ons.
    """
    q = float(np.quantile(np.asarray(daily_pnl), 1.0 - confidence))
    return max(-q, 0.0) * math.sqrt(horizon_days)


# --------------------------------------------------------------------------- variation margin


def variation_margin_flows(qty: float, multiplier: float, prices: Sequence[float]) -> np.ndarray:
    """Daily variation margin received (+) / paid (-) by a position of ``qty`` contracts:
    qty x multiplier x (P_t - P_{t-1}). Length = len(prices) - 1."""
    return qty * multiplier * np.diff(np.asarray(prices, dtype=float))


def vm_funding_cost(
    flows: Sequence[float], rate: float, basis: int = 360, symmetric: bool = True
) -> float:
    """Financing cost (+) / income (-) of the cumulative variation margin balance, one day per flow.

    Symmetric: -sum(balance_t) x rate / basis (cash received earns the rate). Asymmetric: only
    negative balances (cash paid out and funded) cost money.
    """
    bal = np.cumsum(np.asarray(flows, dtype=float))
    if symmetric:
        return float(-np.sum(bal) * rate / basis)
    return float(np.sum(np.maximum(-bal, 0.0)) * rate / basis)

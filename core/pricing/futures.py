"""Index futures analytics: implied repo, no-arbitrage band, calendar spreads and roll cost.

Dividends in the continuous-compounding functions are ``(t_i, D_i)`` pairs: ``t_i`` the ex-date
in years from now, ``D_i`` the dividend in index points (or per share).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from scipy.optimize import brentq

from core.config import TradingCosts

Divs = Sequence[tuple[float, float]]


def model_forward(spot: float, r: float, divs: Divs, t: float) -> float:
    """Forward with discrete dividends and continuous rate r: F = S e^{rT} - sum D_i e^{r (T - t_i)}.

    Dividends after ``t`` are ignored.
    """
    fv_divs = sum(d * math.exp(r * (t - ti)) for ti, d in divs if ti <= t)
    return spot * math.exp(r * t) - fv_divs


def implied_repo_simple(spot: float, fut: float, fv_divs: float, days: int, basis: int) -> float:
    """Simple implied repo: r = ((F + FV(divs)) / S - 1) x basis / days.

    ``fv_divs`` is the dividends valued at expiry. Simplified: simple interest, no dividend
    reinvestment path, no costs; the root-finding version below is exact for the continuous model.
    """
    return ((fut + fv_divs) / spot - 1.0) * basis / days


def implied_repo(
    spot: float, fut: float, divs: Divs, t: float, lo: float = -0.5, hi: float = 1.0
) -> float:
    """Continuously-compounded implied financing rate r such that model_forward(S, r, divs, T) = F.

    Solved with Brent's method on [lo, hi]. The model forward is increasing in r for T > 0 and
    sensible dividends, so the root is unique. Raises ``ValueError`` if not bracketed.
    """
    if t <= 0:
        raise ValueError("t must be positive")

    def g(r: float) -> float:
        return model_forward(spot, r, divs, t) - fut

    if g(lo) * g(hi) > 0:
        raise ValueError("implied repo not bracketed in [lo, hi]")
    return float(brentq(g, lo, hi, xtol=1e-14))


def round_trip_cost_bps(
    costs: TradingCosts, impact_bps: float = 0.0, stamp_bps: float = 0.0
) -> float:
    """Index-arbitrage cost in bps of notional: stock entry and exit, futures entry only.

    = 2 x (stock commission + stock half spread) + (futures commission + futures half spread)
      + market impact + stamp duty / FTT. The futures leg cash-settles at expiry, so it has no exit
    cost. Teaching model: all inputs are config values or user inputs.
    """
    stock = 2.0 * (costs.stock_commission_bps + costs.stock_half_spread_bps)
    fut = costs.futures_commission_bps + costs.futures_half_spread_bps
    return stock + fut + impact_bps + stamp_bps


@dataclass(frozen=True)
class NoArbBand:
    """No-arbitrage band for the futures price, in index points."""

    lower: float
    upper: float
    mid: float

    @property
    def width(self) -> float:
        return self.upper - self.lower


class ArbSignal(StrEnum):
    CASH_AND_CARRY = "cash_and_carry"  # futures rich: buy stock, sell futures
    REVERSE = "reverse_cash_and_carry"  # futures cheap: short stock, buy futures
    NONE = "none"


def no_arbitrage_band(
    spot: float,
    divs: Divs,
    t: float,
    funding_long: float,
    rebate_short: float,
    cost_bps: float,
) -> NoArbBand:
    """No-arbitrage band for a futures price.

    upper = FV(r_long) + costs: the desk funds stock purchases at ``funding_long`` and sells
    futures. lower = FV(r_short) - costs: the desk shorts stock and earns the cash rebate
    ``rebate_short`` = r - b (benchmark minus borrow fee), then buys futures. Costs are
    ``cost_bps`` of spot converted to index points. Mid uses the average of the two rates.
    """
    cost_pts = spot * cost_bps / 10_000.0
    upper = model_forward(spot, funding_long, divs, t) + cost_pts
    lower = model_forward(spot, rebate_short, divs, t) - cost_pts
    mid = model_forward(spot, 0.5 * (funding_long + rebate_short), divs, t)
    return NoArbBand(lower=lower, upper=upper, mid=mid)


def arb_signal(market: float, band: NoArbBand) -> tuple[ArbSignal, float]:
    """Which arbitrage (if any) is open, and the locked-in edge in index points.

    Edge = F - upper for cash-and-carry, lower - F for reverse; zero inside the band.
    """
    if market > band.upper:
        return ArbSignal.CASH_AND_CARRY, market - band.upper
    if market < band.lower:
        return ArbSignal.REVERSE, band.lower - market
    return ArbSignal.NONE, 0.0


def calendar_spread_fair(spot: float, divs: Divs, t_near: float, t_far: float, r: float) -> float:
    """Fair calendar spread FV_far - FV_near in index points (continuous rate ``r``)."""
    return model_forward(spot, r, divs, t_far) - model_forward(spot, r, divs, t_near)


def implied_calendar_repo(
    f_near: float, f_far: float, dividends_between: float, t_near: float, t_far: float
) -> float:
    """Financing rate implied by a calendar spread (simple): (F_far - F_near + D) / (F_near x dT).

    ``dividends_between`` are the index points going ex between the two expiries.
    """
    return (f_far - f_near + dividends_between) / (f_near * (t_far - t_near))


def roll_cost_bps_per_year(f_near: float, f_far: float, dt: float) -> float:
    """Gross roll cost of staying long, in bps per year of exposure: (F_far - F_near) / F_near / dT."""
    return (f_far - f_near) / f_near / dt * 10_000.0


def roll_richness_bps_per_year(f_near: float, f_far: float, fair_spread: float, dt: float) -> float:
    """Roll cost above fair carry, bps/year: (spread - fair spread) / F_near / dT. Positive = expensive roll."""
    return (f_far - f_near - fair_spread) / f_near / dt * 10_000.0


def futures_pnl(qty: float, multiplier: float, price0: float, price1: float) -> float:
    """PnL of ``qty`` contracts (+ long): qty x multiplier x (P1 - P0), in contract currency."""
    return qty * multiplier * (price1 - price0)

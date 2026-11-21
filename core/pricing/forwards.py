"""Forward and futures fair value on an equity or index.

Notation: S spot, F forward/futures, r funding rate, q dividend yield, T years to expiry,
DF discount factor, PVD present value of dividends. Rich/cheap is market minus fair value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from core.dividends import Dividend, pv_dividends
from core.rates import DiscountCurve


def forward_continuous(spot: float, r: float, q: float, t: float) -> float:
    """F = S exp((r - q) T), r and q continuously compounded, T in years.

    Simplified: dividend yield is continuous and constant; the discrete version below is the
    desk standard for single stocks and for indices with a known dividend calendar.
    """
    return spot * math.exp((r - q) * t)


def forward_discrete(spot: float, pv_divs: float, df_expiry: float) -> float:
    """F = (S - sum_i D_i DF(t_i)) / DF(T): spot less PV of dividends, grown at the funding rate."""
    return (spot - pv_divs) / df_expiry


def forward_from_dividends(
    spot: float,
    divs: list[Dividend],
    curve: DiscountCurve,
    valuation_date: date,
    expiry: date,
) -> float:
    """Discrete-dividend forward to ``expiry`` using ``curve`` for both PVD and DF(T)."""
    pvd = pv_dividends(divs, curve, valuation_date, expiry)
    return forward_discrete(spot, pvd, curve.df_date(expiry))


@dataclass(frozen=True)
class ForwardResult:
    """Basis analysis of a market futures price against fair value (index points)."""

    spot: float
    market: float
    fair_value: float
    t: float

    @property
    def basis(self) -> float:
        """Market basis = F - S."""
        return self.market - self.spot

    @property
    def fair_basis(self) -> float:
        """Fair basis = FV - S."""
        return self.fair_value - self.spot

    @property
    def rich_cheap(self) -> float:
        """Rich (+) / cheap (-) = F - FV, in index points."""
        return self.market - self.fair_value

    @property
    def rich_cheap_bps_annualised(self) -> float:
        """Rich/cheap as annualised bps of financing on spot: (F - FV) / S / T x 10,000."""
        return self.rich_cheap / self.spot / self.t * 10_000.0


def analyse_future(spot: float, market: float, fair_value: float, t: float) -> ForwardResult:
    """Package spot, market and fair value into a :class:`ForwardResult`. ``t`` must be positive."""
    if t <= 0:
        raise ValueError("t must be positive")
    return ForwardResult(spot=spot, market=market, fair_value=fair_value, t=t)

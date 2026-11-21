"""Overnight rate compounding, discount curves and funds transfer pricing (FTP).

Conventions: rates are decimals (0.04 = 4%), annualised under the stated basis (360 or 365).
Year fractions on curves are ACT/365F from the curve's valuation date.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

from core import config
from core.conventions import CalendarName, add_business_days, is_business_day
from core.types import Currency

# --------------------------------------------------------------------------- simple interest


def simple_interest(principal: float, rate: float, days: int, basis: int) -> float:
    """Simple interest = principal x rate x days / basis (same currency as principal)."""
    return principal * rate * days / basis


def convert_basis(rate: float, from_basis: int, to_basis: int) -> float:
    """Restate a simple rate quoted on ``from_basis`` on ``to_basis``: r x to / from.

    Example: 4.00% ACT/360 is 4.00% x 365/360 = 4.0556% ACT/365.
    """
    return rate * to_basis / from_basis


def funding_rate(benchmark_rate: float, ccy: Currency) -> float:
    """Desk funding rate = overnight benchmark + FTP spread (bps from ``config/desk.yaml``)."""
    return benchmark_rate + config.desk().ftp_spread_bps[ccy] / 10_000.0


# --------------------------------------------------------------------------- compounding


def _weights(dates: Sequence[date], end: date, cal: CalendarName) -> list[int]:
    """Calendar days each fixing applies: from its date to the next business day (capped at ``end``)."""
    out = []
    for d in dates:
        nxt = add_business_days(d, 1, cal)
        out.append((min(nxt, end) - d).days)
    return out


def _business_dates(start: date, end: date, cal: CalendarName) -> list[date]:
    out = []
    cur = start
    while cur < end:
        if is_business_day(cur, cal):
            out.append(cur)
        cur = date.fromordinal(cur.toordinal() + 1)
    return out


def compound_overnight(
    fixings: Mapping[date, float],
    start: date,
    end: date,
    cal: CalendarName,
    basis: int,
    lookback: int = 0,
    observation_shift: bool = False,
) -> float:
    """Compounded-in-arrears overnight rate over [start, end), annualised on ``basis``.

    R = [prod(1 + r_i d_i / basis) - 1] x basis / d

    where r_i is the fixing for business day i and d_i the calendar days it applies (to the
    next business day, so Friday carries 3 days). ``d`` is the calendar days of the period.

    - ``lookback = L``: the rate for day i is the fixing L business days earlier; the weights d_i
      and the denominator ``d`` stay those of the accrual period.
    - ``observation_shift = True`` (with ``lookback = L``): both rates and weights come from the
      observation period shifted back L business days, and ``d`` is that period's calendar days.

    Simplified: no rounding of the compounded rate, no rate floors, no index-publication lag.
    """
    if end <= start:
        raise ValueError("end must be after start")
    if lookback < 0:
        raise ValueError("lookback must be >= 0")
    accrual = _business_dates(start, end, cal)
    if not accrual:
        raise ValueError("no business days in the accrual period")

    if observation_shift:
        obs = [add_business_days(d, -lookback, cal) for d in accrual]
        obs_end = add_business_days(end, -lookback, cal)
        weights = _weights(obs, obs_end, cal)
        rate_dates = obs
        period_days = (obs_end - obs[0]).days
    else:
        weights = _weights(accrual, end, cal)
        rate_dates = [add_business_days(d, -lookback, cal) for d in accrual]
        period_days = (end - start).days

    factor = 1.0
    for rd, w in zip(rate_dates, weights, strict=True):
        try:
            r = fixings[rd]
        except KeyError as e:
            raise KeyError(f"missing overnight fixing for {rd}") from e
        factor *= 1.0 + r * w / basis
    return (factor - 1.0) * basis / period_days


def simple_average_overnight(
    fixings: Mapping[date, float], start: date, end: date, cal: CalendarName
) -> float:
    """Day-weighted simple average of overnight fixings over [start, end) (no compounding).

    = sum(r_i d_i) / d. Always <= the compounded rate when rates are positive.
    """
    accrual = _business_dates(start, end, cal)
    weights = _weights(accrual, end, cal)
    total = sum(fixings[d] * w for d, w in zip(accrual, weights, strict=True))
    return total / (end - start).days


# --------------------------------------------------------------------------- discount curve


@dataclass(frozen=True)
class DiscountCurve:
    """Discount curve through (year fraction, DF) points, log-linear in DF.

    Beyond the last pillar the last continuously-compounded zero rate is held flat.
    ``valuation_date`` is time 0 with DF = 1.
    """

    valuation_date: date
    times: tuple[float, ...]
    dfs: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.times) != len(self.dfs) or not self.times:
            raise ValueError("times and dfs must be non-empty and equal length")
        if any(t <= 0 for t in self.times) or list(self.times) != sorted(self.times):
            raise ValueError("times must be positive and increasing")
        if any(d <= 0 for d in self.dfs):
            raise ValueError("discount factors must be positive")

    @staticmethod
    def t(valuation_date: date, d: date) -> float:
        """ACT/365F year fraction from the valuation date."""
        return (d - valuation_date).days / 365.0

    def df(self, t: float) -> float:
        """Discount factor at year fraction ``t`` (log-linear interpolation)."""
        if t <= 0:
            return 1.0
        ts = np.concatenate(([0.0], self.times))
        lg = np.concatenate(([0.0], np.log(self.dfs)))
        if t <= ts[-1]:
            return float(math.exp(np.interp(t, ts, lg)))
        z_last = -lg[-1] / ts[-1]
        return float(math.exp(-z_last * t))

    def df_date(self, d: date) -> float:
        """Discount factor to calendar date ``d``."""
        return self.df(self.t(self.valuation_date, d))

    def zero_rate(self, t: float) -> float:
        """Continuously-compounded zero rate to ``t``: -ln(DF) / t."""
        return -math.log(self.df(t)) / t

    def forward_rate(self, t1: float, t2: float) -> float:
        """Simple forward rate between ``t1`` and ``t2`` (ACT/365F): (DF1/DF2 - 1) / (t2 - t1)."""
        return (self.df(t1) / self.df(t2) - 1.0) / (t2 - t1)

    @classmethod
    def from_zero_rates(
        cls, valuation_date: date, times: Sequence[float], zeros: Sequence[float]
    ) -> DiscountCurve:
        """Build from continuously-compounded zero rates: DF = exp(-z t)."""
        return cls(
            valuation_date,
            tuple(times),
            tuple(math.exp(-z * t) for z, t in zip(zeros, times, strict=True)),
        )

    @classmethod
    def from_deposit_rates(
        cls,
        valuation_date: date,
        points: Sequence[tuple[date, float]],
        basis: int = 360,
    ) -> DiscountCurve:
        """Bootstrap from simple money-market (deposit) rates: DF = 1 / (1 + r x days / basis).

        Simplified: single-period deposits only, no swap pillars or convexity.
        """
        pts = sorted(points)
        times = tuple((d - valuation_date).days / 365.0 for d, _ in pts)
        dfs = tuple(1.0 / (1.0 + r * (d - valuation_date).days / basis) for d, r in pts)
        return cls(valuation_date, times, dfs)


def flat_curve(
    valuation_date: date, zero_rate: float, horizon_years: float = 10.0
) -> DiscountCurve:
    """Flat continuously-compounded curve, convenient for tests and sandboxes."""
    return DiscountCurve.from_zero_rates(valuation_date, [horizon_years], [zero_rate])

"""Dividend schedules, present values, index dividend points, implied dividends and tax.

Amounts are per share in the stock's currency. Percentages are decimals unless a name ends in
``_pct`` in config (config percentages are in percent points, e.g. 15.0 = 15%).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from core import config
from core.conventions import add_months
from core.rates import DiscountCurve


@dataclass(frozen=True)
class Dividend:
    """A single gross cash dividend per share."""

    ex_date: date
    pay_date: date
    amount: float


def generate_schedule(
    first_ex: date,
    per_year: int,
    amount: float,
    n: int,
    pay_lag_days: int = 14,
) -> list[Dividend]:
    """``n`` equally spaced dividends starting at ``first_ex``, ``12 / per_year`` months apart."""
    if per_year not in (1, 2, 4, 12):
        raise ValueError("per_year must be 1, 2, 4 or 12")
    step = 12 // per_year
    out = []
    for k in range(n):
        ex = add_months(first_ex, k * step)
        out.append(Dividend(ex, date.fromordinal(ex.toordinal() + pay_lag_days), amount))
    return out


def annual_yield(price: float, annual_dividend: float) -> float:
    """Dividend yield = annual dividend / price."""
    return annual_dividend / price


def pv_dividends(
    divs: Iterable[Dividend],
    curve: DiscountCurve,
    from_date: date,
    to_date: date,
    use_pay_date: bool = False,
) -> float:
    """PV of dividends with ex-date in (from_date, to_date]: sum D_i x DF(t_i).

    ``t_i`` is the ex-date by default (the stock drops on the ex-date, which is what the
    forward price must reflect); set ``use_pay_date`` to discount from the payment date.
    Simplified: dividends are treated as known; credit/forecast uncertainty is not modelled.
    """
    total = 0.0
    for d in divs:
        if from_date < d.ex_date <= to_date:
            t_date = d.pay_date if use_pay_date else d.ex_date
            total += d.amount * curve.df_date(t_date)
    return total


def index_dividend_points(
    dividends: Iterable[tuple[float, float]],
    divisor: float,
) -> float:
    """Index dividend points = sum(D_i x index_shares_i) / divisor.

    Each item is ``(dividend per share, index shares)`` where index shares already include
    free float and capping factors. The result is in index points.
    """
    return sum(d * w for d, w in dividends) / divisor


# --------------------------------------------------------------------------- implied dividends


def implied_pv_dividends_from_forward(spot: float, forward: float, df_to_expiry: float) -> float:
    """PV of dividends implied by a forward: PVD = S - F x DF(T).

    Follows from F = (S - PVD) / DF(T).
    """
    return spot - forward * df_to_expiry


def implied_dividend_yield(spot: float, forward: float, rate: float, t: float) -> float:
    """Continuous dividend yield implied by a forward: q = r - ln(F / S) / T.

    From F = S exp((r - q) T). ``rate`` is continuously compounded.
    """
    return rate - math.log(forward / spot) / t


def implied_forward_from_put_call(
    call: float, put: float, strike: float, df_to_expiry: float
) -> float:
    """Forward implied by put-call parity: C - P = DF(T) (F - K), so F = K + (C - P) / DF(T)."""
    return strike + (call - put) / df_to_expiry


def implied_pv_dividends_from_put_call(
    spot: float, call: float, put: float, strike: float, df_to_expiry: float
) -> float:
    """PV of dividends from put-call parity: PVD = S - K x DF(T) - (C - P)."""
    return spot - strike * df_to_expiry - (call - put)


def implied_dividends_from_futures_strip(
    expiries_cum_points: Sequence[float],
) -> list[float]:
    """Annual dividend points from a strip of cumulative dividend-future prices.

    Dividend futures settle to the dividend points of one calendar year, so a strip of annual
    contracts already gives each year directly; this helper differences cumulative quotes
    (``[sum to year 1, sum to year 2, ...]``) into per-year values.
    """
    out = []
    prev = 0.0
    for c in expiries_cum_points:
        out.append(c - prev)
        prev = c
    return out


# --------------------------------------------------------------------------- tax and pass-through


def net_dividend(gross: float, wht_pct: float) -> float:
    """Net dividend = gross x (1 - wht), ``wht_pct`` in percent points (15.0 = 15%)."""
    return gross * (1.0 - wht_pct / 100.0)


def withholding_rate_pct(market: str, treaty: bool = False) -> float:
    """Illustrative withholding rate (percent points) for ``market`` from config."""
    r = config.withholding().rates[market]
    return r.treaty_pct if treaty else r.statutory_pct


def swap_dividend_amount(gross_per_share: float, shares: float, pass_through: float) -> float:
    """Dividend equivalent in a swap equity leg: gross x shares x pass-through (1.0 = 100% gross).

    A long client receives this from the desk; a short client pays it. 0.85 / 0.70 model net
    pass-through when the desk can only reclaim part of the withholding.
    """
    return gross_per_share * shares * pass_through


def dividend_leakage(
    gross_per_share: float, shares: float, wht_pct: float, pass_through: float
) -> float:
    """Desk gain (+) / loss (-) on dividends for a long swap hedged with stock.

    The desk receives the net dividend on its hedge stock and pays ``pass_through x gross`` to
    the client: leakage = shares x (gross (1 - wht) - pass_through x gross).
    """
    received = shares * net_dividend(gross_per_share, wht_pct)
    paid = swap_dividend_amount(gross_per_share, shares, pass_through)
    return received - paid

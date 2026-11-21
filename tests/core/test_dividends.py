import math
from datetime import date

import pytest

from core import dividends as dv
from core.rates import flat_curve

V = date(2026, 11, 21)


def test_generate_schedule_quarterly():
    """Quarterly from 10 Dec 2026: 10 Dec, 10 Mar, 10 Jun, 10 Sep, each paying 14 days later."""
    s = dv.generate_schedule(date(2026, 12, 10), 4, 0.5, 4)
    assert [d.ex_date for d in s] == [
        date(2026, 12, 10),
        date(2027, 3, 10),
        date(2027, 6, 10),
        date(2027, 9, 10),
    ]
    assert s[0].pay_date == date(2026, 12, 24)
    with pytest.raises(ValueError):
        dv.generate_schedule(V, 3, 1.0, 2)


def test_pv_dividends_window_and_dates():
    """1.00 ex 10 Mar 2027 (109 days out) at flat 4%: DF = exp(-.04 x 109/365) = 0.988126.
    An ex-date on or before the valuation date, or after the horizon, is excluded."""
    curve = flat_curve(V, 0.04)
    d = dv.Dividend(date(2027, 3, 10), date(2027, 3, 24), 1.0)
    old = dv.Dividend(date(2026, 11, 21), date(2026, 12, 5), 5.0)
    late = dv.Dividend(date(2028, 1, 1), date(2028, 1, 15), 5.0)
    got = dv.pv_dividends([d, old, late], curve, V, date(2027, 12, 31))
    assert got == pytest.approx(math.exp(-0.04 * 109 / 365))
    assert got == pytest.approx(0.988126, abs=1e-6)
    pay = dv.pv_dividends([d], curve, V, date(2027, 12, 31), use_pay_date=True)
    assert pay == pytest.approx(math.exp(-0.04 * 123 / 365))


def test_index_dividend_points():
    """(2.0 x 500 + 1.0 x 1000) / divisor 100 = 20 index points."""
    assert dv.index_dividend_points([(2.0, 500), (1.0, 1000)], 100) == pytest.approx(20.0)


def test_implied_from_forward():
    """S=100, F=101, DF=0.98: PVD = 100 - 101 x 0.98 = 1.02. Yield q = .04 - ln(1.01) = 3.00497%."""
    assert dv.implied_pv_dividends_from_forward(100, 101, 0.98) == pytest.approx(1.02)
    assert dv.implied_dividend_yield(100, 101, 0.04, 1.0) == pytest.approx(0.04 - math.log(1.01))


def test_put_call_parity_dividends():
    """K=100, DF=0.98, C-P=1.96: F = 100 + 1.96/0.98 = 102. With S=101: PVD = 101 - 98 - 1.96 = 1.04,
    consistent with F = (S - PVD)/DF = 99.96/0.98 = 102."""
    assert dv.implied_forward_from_put_call(5.96, 4.0, 100, 0.98) == pytest.approx(102.0)
    pvd = dv.implied_pv_dividends_from_put_call(101, 5.96, 4.0, 100, 0.98)
    assert pvd == pytest.approx(1.04)
    assert (101 - pvd) / 0.98 == pytest.approx(102.0)


def test_futures_strip_differences():
    """Cumulative 3, 5.5, 8.5 -> per year 3, 2.5, 3."""
    assert dv.implied_dividends_from_futures_strip([3, 5.5, 8.5]) == pytest.approx([3, 2.5, 3])


def test_tax_and_pass_through():
    """100 gross at 15% WHT = 85 net. US statutory 30%, treaty 15% (config)."""
    assert dv.net_dividend(100, 15.0) == pytest.approx(85.0)
    assert dv.withholding_rate_pct("US") == 30.0
    assert dv.withholding_rate_pct("US", treaty=True) == 15.0
    assert dv.swap_dividend_amount(1.0, 1000, 0.85) == pytest.approx(850.0)


def test_dividend_leakage():
    """2.00 gross x 1,000 sh. 30% WHT, 100% pass-through: receive 1,400, pay 2,000 -> -600.
    15% WHT with 85% pass-through: receive 1,700, pay 1,700 -> 0."""
    assert dv.dividend_leakage(2.0, 1000, 30.0, 1.0) == pytest.approx(-600.0)
    assert dv.dividend_leakage(2.0, 1000, 15.0, 0.85) == pytest.approx(0.0)

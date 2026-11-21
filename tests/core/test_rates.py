import math
from datetime import date

import pytest

from core.conventions import CalendarName
from core.rates import (
    DiscountCurve,
    compound_overnight,
    convert_basis,
    flat_curve,
    funding_rate,
    simple_average_overnight,
    simple_interest,
)
from core.types import Currency

US = CalendarName.US
START, END = date(2026, 11, 16), date(2026, 11, 23)
FIX = {
    date(2026, 11, 13): 0.039,
    date(2026, 11, 16): 0.04,
    date(2026, 11, 17): 0.04,
    date(2026, 11, 18): 0.04,
    date(2026, 11, 19): 0.04,
    date(2026, 11, 20): 0.041,
}


def test_compound_in_arrears():
    """Mon-Thu 4.00% for 1 day each, Fri 4.10% for 3 days (to Monday), basis 360, 7 days:
    factor = (1 + .04/360)^4 x (1 + .041 x 3/360) = 1.0004445185 x 1.000341667 = 1.0007863374
    R = 0.0007863374 x 360 / 7 = 4.04402%."""
    r = compound_overnight(FIX, START, END, US, 360)
    assert r == pytest.approx(0.0404402, abs=2e-7)


def test_simple_below_compounded():
    """Simple average = (4 x 0.04 + 3 x 0.041) / 7 = 0.283 / 7 = 4.042857%, below compounded."""
    s = simple_average_overnight(FIX, START, END, US)
    assert s == pytest.approx(0.283 / 7)
    assert s < compound_overnight(FIX, START, END, US, 360)


def test_lookback_without_shift():
    """Lookback 1 BD: Mon uses Fri 13th (3.90%), Tue-Fri use the prior day's 4.00%; weights are the
    accrual period's (1,1,1,1,3), denominator 7:
    factor = (1 + .039/360)(1 + .04/360)^3 (1 + .04 x 3/360)."""
    f = (1 + 0.039 / 360) * (1 + 0.04 / 360) ** 3 * (1 + 0.04 * 3 / 360)
    got = compound_overnight(FIX, START, END, US, 360, lookback=1)
    assert got == pytest.approx((f - 1) * 360 / 7)


def test_observation_shift():
    """Shift 1 BD: observation period Fri 13th to Fri 20th. Weights Fri 13th = 3, then 1,1,1,1;
    rates 3.90% then 4.00% x4; denominator 7:
    factor = (1 + .039 x 3/360)(1 + .04/360)^4."""
    f = (1 + 0.039 * 3 / 360) * (1 + 0.04 / 360) ** 4
    got = compound_overnight(FIX, START, END, US, 360, lookback=1, observation_shift=True)
    assert got == pytest.approx((f - 1) * 360 / 7)


def test_zero_rates_compound_to_zero():
    fix = dict.fromkeys(FIX, 0.0)
    assert compound_overnight(fix, START, END, US, 360) == 0.0


def test_missing_fixing_and_bad_inputs():
    with pytest.raises(KeyError):
        compound_overnight({}, START, END, US, 360)
    with pytest.raises(ValueError):
        compound_overnight(FIX, END, START, US, 360)
    with pytest.raises(ValueError):
        compound_overnight(FIX, START, END, US, 360, lookback=-1)


def test_simple_interest_and_basis():
    """USD 10m at 4% for 90 days ACT/360 = 10m x .04 x 90/360 = 100,000. 4% ACT/360 = 4.0556% ACT/365."""
    assert simple_interest(10_000_000, 0.04, 90, 360) == pytest.approx(100_000)
    assert convert_basis(0.04, 360, 365) == pytest.approx(0.04 * 365 / 360)


def test_funding_rate():
    """SOFR 4.00% + USD FTP 35 bps = 4.35%."""
    assert funding_rate(0.04, Currency.USD) == pytest.approx(0.0435)


def test_flat_curve_df():
    """Flat 4% continuous: DF(1y) = exp(-0.04) = 0.960789; forward 1y->2y simple = e^0.04 - 1."""
    c = flat_curve(date(2026, 11, 21), 0.04)
    assert c.df(1.0) == pytest.approx(math.exp(-0.04))
    assert c.zero_rate(2.0) == pytest.approx(0.04)
    assert c.forward_rate(1.0, 2.0) == pytest.approx(math.exp(0.04) - 1)
    assert c.df(0.0) == 1.0


def test_deposit_bootstrap():
    """90-day deposit at 4% ACT/360: DF = 1 / (1 + .04 x 90/360) = 1/1.01 = 0.990099."""
    v = date(2026, 11, 21)
    c = DiscountCurve.from_deposit_rates(v, [(date(2027, 2, 19), 0.04)])
    assert c.df_date(date(2027, 2, 19)) == pytest.approx(1 / 1.01)


def test_loglinear_interpolation_and_extrapolation():
    """Pillars DF(1)=0.96, DF(2)=0.90. DF(1.5) = sqrt(.96 x .90) = 0.929516; DF(0.5) = sqrt(.96);
    beyond the last pillar the last zero rate is held, so DF(4) = 0.90^2 = 0.81."""
    c = DiscountCurve(date(2026, 11, 21), (1.0, 2.0), (0.96, 0.90))
    assert c.df(1.5) == pytest.approx(math.sqrt(0.96 * 0.90))
    assert c.df(0.5) == pytest.approx(math.sqrt(0.96))
    assert c.df(4.0) == pytest.approx(0.81)


def test_curve_validation():
    v = date(2026, 11, 21)
    with pytest.raises(ValueError):
        DiscountCurve(v, (2.0, 1.0), (0.9, 0.95))
    with pytest.raises(ValueError):
        DiscountCurve(v, (1.0,), (0.9, 0.8))
    with pytest.raises(ValueError):
        DiscountCurve(v, (1.0,), (-0.1,))

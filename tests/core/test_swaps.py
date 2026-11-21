from collections import defaultdict
from datetime import date

import pytest

from core.corporate_actions import split
from core.dividends import Dividend
from core.pricing import swaps as sw
from core.types import Currency, Direction

ZERO = defaultdict(float)
FLAT4 = defaultdict(lambda: 0.04)
D16, D18, D23, D30 = date(2026, 11, 16), date(2026, 11, 18), date(2026, 11, 23), date(2026, 11, 30)
DIV = [Dividend(D18, date(2026, 11, 25), 0.50)]


def terms(direction=Direction.LONG, **kw):
    base = dict(direction=direction, shares=1000, initial_price=100.0, spread_bps=50.0)
    base.update(kw)
    return sw.SwapTerms(**base)


def test_long_period_cashflows():
    """Long 1,000 sh @100 (notional 100,000), benchmark 0, spread 50 bps, 7 days ACT/360, price
    100 -> 102, 0.50 dividend ex 18 Nov at 100% pass-through:
    price +2,000; dividend +500; funding -100,000 x 0.005 x 7/360 = -9.72; net +2,490.28."""
    p = sw.period_cashflows(terms(), D16, D23, 100, 102, ZERO, DIV)
    assert p.price_cf == 2000.0
    assert p.dividend_cf == 500.0
    assert p.funding_cf == -9.72
    assert p.net_cf == 2490.28
    assert p.funding_notional == 100_000


def test_short_period_cashflows():
    """Same inputs, short client: price -2,000, dividend -500, funding receives N (R - s) tau =
    100,000 x (0 - 0.005) x 7/360 = -9.72 (spread above benchmark makes the client pay); net -2,509.72."""
    p = sw.period_cashflows(terms(Direction.SHORT), D16, D23, 100, 102, ZERO, DIV)
    assert (p.price_cf, p.dividend_cf, p.funding_cf) == (-2000.0, -500.0, -9.72)
    assert p.net_cf == -2509.72


def test_net_pass_through():
    """85% pass-through on the 0.50 dividend of 1,000 shares = 425."""
    p = sw.period_cashflows(terms(pass_through=0.85), D16, D23, 100, 102, ZERO, DIV)
    assert p.dividend_cf == 425.0


def test_schedule_reset_vs_fixed_funding_notional():
    """Two periods, prices 100 -> 102 -> 101. Reset swap funds 1,000 x 102 = 102,000 in period 2;
    the fixed-notional swap keeps 100,000. Period 2 price CF = 1,000 x (101 - 102) = -1,000."""
    dates = [D16, D23, D30]
    prices = {D16: 100.0, D23: 102.0, D30: 101.0}
    reset = sw.build_schedule(terms(), dates, prices, ZERO)
    fixed = sw.build_schedule(terms(notional_reset=False), dates, prices, ZERO)
    assert reset.periods[1].funding_notional == pytest.approx(102_000)
    assert fixed.periods[1].funding_notional == pytest.approx(100_000)
    assert reset.periods[1].price_cf == -1000.0
    assert reset.total_net == pytest.approx(sum(p.net_cf for p in reset.periods))
    assert len(reset.to_records()) == 2
    with pytest.raises(ValueError):
        sw.build_schedule(terms(), [D16], prices, ZERO)


def test_mark_to_market():
    """Valuation 18 Nov, price 101, last reset 16 Nov at 100: price +1,000, the 0.50 dividend has
    gone ex (+500), funding 100,000 x 0.005 x 2/360 = -2.78 -> 1,497.22. Zero on a reset date."""
    resets = [D16, D23]
    got = sw.mark_to_market(terms(), resets, D18, 101.0, {D23: 102.0}, ZERO, DIV)
    assert got == 1497.22
    assert sw.mark_to_market(terms(), resets, D16, 100.0, {}, ZERO, DIV) == 0.0


def test_partial_unwind_and_ca():
    """Unwind 25% of 1,000 sh -> 250 unwound, 750 remain. A 2-for-1 split doubles shares, halves
    the reference price: 1,000 @ 100 -> 2,000 @ 50, notional unchanged."""
    assert sw.unwind(1000, 0.25) == (250, 750)
    with pytest.raises(ValueError):
        sw.unwind(1000, 1.5)
    sh, px, cash = sw.apply_corporate_action(1000, 100, split(2.0))
    assert (sh, px, cash) == pytest.approx((2000, 50, 0))
    assert sh * px == pytest.approx(1000 * 100)


def test_desk_economics_long_is_spread_minus_ftp():
    """Long swap, 100% pass-through, no WHT, reset notional: desk keeps N (s - FTP) tau =
    100,000 x (0.0050 - 0.0035) x 7/360 = 2.92, whatever the stock does or the benchmark is."""
    e = sw.desk_economics(terms(), D16, D23, 100, 105, FLAT4, DIV, ftp_bps=35)
    assert e.spread_edge == pytest.approx(2.9167, abs=1e-4)
    assert e.total == pytest.approx(e.spread_edge, abs=0.02)


def test_desk_economics_short_is_spread_minus_borrow():
    """Short swap: desk earns N (s - b) tau = 100,000 x (0.0050 - 0.0030) x 7/360 = 3.89."""
    e = sw.desk_economics(
        terms(Direction.SHORT), D16, D23, 100, 95, FLAT4, DIV, ftp_bps=35, borrow_bps=30
    )
    assert e.spread_edge == pytest.approx(3.8889, abs=1e-4)
    assert e.total == pytest.approx(e.spread_edge, abs=0.02)


def test_dividend_leakage_hits_desk():
    """Long swap, 30% withholding on the hedge but 100% pass-through to the client:
    leakage = 1,000 x 0.50 x (0.70 - 1.00) = -150 on top of the spread edge."""
    e = sw.desk_economics(terms(), D16, D23, 100, 100, FLAT4, DIV, ftp_bps=35, wht_pct=30.0)
    assert e.total == pytest.approx(e.spread_edge - 150.0, abs=0.02)


def test_spread_build_up():
    """Long USD: FTP 35 + BS 8 + capital 12 + XVA 10 + hedge 4 + margin 5 = 74 bps.
    Short: borrow (30) replaces FTP -> 69 bps."""
    assert sw.ftp_component_bps(Currency.USD) == 35
    assert sw.hedge_cost_component_bps(6.6, 1.0) == pytest.approx(6.6)
    long_ = sw.spread_build_up(Direction.LONG, 35, 30, 8, 12, 10, 4, 5)
    short = sw.spread_build_up(Direction.SHORT, 35, 30, 8, 12, 10, 4, 5)
    assert long_.total_bps == 74
    assert short.total_bps == 69
    assert "Borrow" in short.components and "Funding (FTP)" not in short.components
    assert sw.borrow_component_bps(30) == 30

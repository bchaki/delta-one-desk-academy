import math
from datetime import date

import pytest

from core import config
from core.dividends import Dividend
from core.pricing import forwards as fw
from core.pricing import futures as fu
from core.pricing import trf
from core.rates import flat_curve


def test_forward_continuous():
    """S=100, r=4%, q=2%, T=1: F = 100 e^{0.02} = 102.0201."""
    assert fw.forward_continuous(100, 0.04, 0.02, 1.0) == pytest.approx(102.0201, abs=1e-4)


def test_forward_discrete():
    """S=100, PVD=1.9, DF=e^{-0.04}=0.960789: F = 98.1 / 0.960789 = 102.1035."""
    assert fw.forward_discrete(100, 1.9, math.exp(-0.04)) == pytest.approx(102.1035, abs=1e-3)


def test_forward_from_dividends_uses_curve():
    """Dividend 2.00 ex 10 Mar 2027, expiry 19 Mar 2027 (118 days), flat 4%:
    PVD = 2 e^{-.04 x 109/365}; F = (100 - PVD) e^{.04 x 118/365}."""
    v = date(2026, 11, 21)
    curve = flat_curve(v, 0.04)
    divs = [Dividend(date(2027, 3, 10), date(2027, 3, 24), 2.0)]
    pvd = 2 * math.exp(-0.04 * 109 / 365)
    expected = (100 - pvd) * math.exp(0.04 * 118 / 365)
    assert fw.forward_from_dividends(100, divs, curve, v, date(2027, 3, 19)) == pytest.approx(
        expected
    )


def test_forward_result_rich_cheap():
    """S=100, FV=100.5, F=100.8, T=0.25: basis 0.8, fair basis 0.5, rich 0.3 pts =
    0.3/100/0.25 x 10,000 = 120 bps annualised."""
    r = fw.analyse_future(100, 100.8, 100.5, 0.25)
    assert r.basis == pytest.approx(0.8)
    assert r.fair_basis == pytest.approx(0.5)
    assert r.rich_cheap == pytest.approx(0.3)
    assert r.rich_cheap_bps_annualised == pytest.approx(120.0)
    with pytest.raises(ValueError):
        fw.analyse_future(100, 100, 100, 0)


def test_property_zero_rate_zero_div_forward_equals_spot():
    assert fu.model_forward(123.4, 0.0, [], 0.7) == pytest.approx(123.4)


def test_implied_repo_simple():
    """S=100, F=100.9, FV(divs)=0.5, 90 days ACT/360: ((100.9 + 0.5)/100 - 1) x 360/90 = 5.6%."""
    assert fu.implied_repo_simple(100, 100.9, 0.5, 90, 360) == pytest.approx(0.056)


def test_implied_repo_roundtrip():
    """Price a future at r=5% with dividends 1.0 at t=.25 and .5, then solve back for r."""
    divs = [(0.25, 1.0), (0.5, 1.0)]
    f = 100 * math.exp(0.05) - math.exp(0.05 * 0.75) - math.exp(0.05 * 0.5)
    assert fu.model_forward(100, 0.05, divs, 1.0) == pytest.approx(f)
    assert fu.implied_repo(100, f, divs, 1.0) == pytest.approx(0.05, abs=1e-10)
    with pytest.raises(ValueError):
        fu.implied_repo(100, 1e6, divs, 1.0)
    with pytest.raises(ValueError):
        fu.implied_repo(100, f, divs, 0.0)


def test_round_trip_cost_bps():
    """Config: stock 1.0 commission + 2.0 half spread each way, futures 0.1 + 0.5:
    2 x 3.0 + 0.6 = 6.6 bps; adding 1.0 impact = 7.6 bps."""
    c = config.desk().trading_costs
    assert fu.round_trip_cost_bps(c) == pytest.approx(6.6)
    assert fu.round_trip_cost_bps(c, impact_bps=1.0) == pytest.approx(7.6)


def test_no_arb_band_and_signal():
    """S=100, T=1, no dividends, long funding 5%, short rebate 3.5%, 10 bps costs (0.10 pt):
    upper = 100 e^{.05} + 0.10 = 105.2271; lower = 100 e^{.035} - 0.10 = 103.4620."""
    band = fu.no_arbitrage_band(100, [], 1.0, 0.05, 0.035, 10)
    assert band.upper == pytest.approx(105.2271, abs=1e-4)
    assert band.lower == pytest.approx(103.4620, abs=1e-4)
    assert band.lower < band.mid < band.upper
    assert band.width == pytest.approx(band.upper - band.lower)
    sig, edge = fu.arb_signal(105.5, band)
    assert sig is fu.ArbSignal.CASH_AND_CARRY
    assert edge == pytest.approx(105.5 - band.upper)
    sig, edge = fu.arb_signal(103.0, band)
    assert sig is fu.ArbSignal.REVERSE
    assert edge == pytest.approx(band.lower - 103.0)
    assert fu.arb_signal(104.5, band) == (fu.ArbSignal.NONE, 0.0)


def test_calendar_spread_and_roll():
    """S=100, r=5%, no divs, T 0.25 and 0.5: fair spread = 100 (e^{.025} - e^{.0125}) = 1.2737.
    Roll cost for F 100 -> 101.3 over 0.25y = 1.3%/0.25 = 520 bps/yr; richness over fair
    = (1.3 - 1.2737)/100/0.25 x 10,000 = 10.54 bps/yr."""
    fair = fu.calendar_spread_fair(100, [], 0.25, 0.5, 0.05)
    assert fair == pytest.approx(1.2737, abs=1e-3)
    assert fu.roll_cost_bps_per_year(100, 101.3, 0.25) == pytest.approx(520.0)
    assert fu.roll_richness_bps_per_year(100, 101.3, fair, 0.25) == pytest.approx(10.54, abs=0.02)


def test_implied_calendar_repo():
    """F_near 100, F_far 101.3, 0.2 pts of dividends between, dT=0.25: (1.3 + 0.2)/(100 x 0.25) = 6%."""
    assert fu.implied_calendar_repo(100, 101.3, 0.2, 0.25, 0.5) == pytest.approx(0.06)


def test_futures_pnl():
    """Long 10 ES (multiplier 50) from 5,000.00 to 5,010.25: 10 x 50 x 10.25 = 5,125 USD."""
    assert fu.futures_pnl(10, 50, 5000.0, 5010.25) == pytest.approx(5125.0)
    assert fu.futures_pnl(-10, 50, 5000.0, 5010.25) == pytest.approx(-5125.0)


def test_trf_spread_basis_roundtrip():
    """S=100, benchmark 4%, spread 50 bps, tau 0.25, FV(divs) 0.5:
    basis = 100 x 0.045 x 0.25 - 0.5 = 0.625; inverse returns 50 bps."""
    basis = trf.trf_spread_to_price_basis(100, 50, 0.04, 0.25, 0.5)
    assert basis == pytest.approx(0.625)
    assert trf.price_basis_to_trf_spread_bps(100, 100 + basis, 0.04, 0.25, 0.5) == pytest.approx(
        50.0
    )


def test_trf_funding_and_swap_equivalent():
    """USD 1m, 4% + 50 bps, 3 days ACT/360: 1,000,000 x 0.045 x 3/360 = 375. Swap = TRF + premium."""
    assert trf.trf_funding_amount(1_000_000, 0.04, 50, 3) == pytest.approx(375.0)
    assert trf.swap_equivalent_spread_bps(50, 12) == 62

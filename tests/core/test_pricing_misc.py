import math

import numpy as np
import pytest

from core import indices as ix
from core.pricing import adr, etf
from core.pricing import dividend_derivs as dd
from core.pricing import program_trading as pt


def test_nav_and_premium():
    """Holdings 1,000 @ 50 and 2,000 @ 25 plus 10,000 cash = 110,000; 1,000 ETF shares -> NAV 110.
    ETF at 110.33 is a 0.30% premium."""
    nav = etf.nav_per_share({"A": 1000, "B": 2000}, {"A": 50.0, "B": 25.0}, 10_000, 1000)
    assert nav == pytest.approx(110.0)
    assert etf.premium_discount(110.33, nav) == pytest.approx(0.003)


def test_etf_arbitrage_create_redeem_none():
    """iNAV 100, CU 50,000 sh (CU value 5,000,000), ETF 100.30 = 30 bps premium. Fee 5,000 = 10 bps,
    basket 5 bps, ETF half-spread 2 bps: threshold 17 bps, edge 13 bps = 6,500 per CU.
    At 99.70 (30 bps discount) the trade is a redemption; at 100.10 nothing is open."""
    a = etf.etf_arbitrage(100.30, 100.0, 50_000, 5_000, 5, 2)
    assert a.action is etf.EtfAction.CREATE
    assert a.threshold_bps == pytest.approx(17.0)
    assert a.edge_bps == pytest.approx(13.0)
    assert a.pnl_per_creation_unit == pytest.approx(6_500.0)
    assert etf.etf_arbitrage(99.70, 100.0, 50_000, 5_000, 5, 2).action is etf.EtfAction.REDEEM
    n = etf.etf_arbitrage(100.10, 100.0, 50_000, 5_000, 5, 2)
    assert n.action is etf.EtfAction.NONE and n.pnl_per_creation_unit == 0.0


def test_adr_parity_band():
    """Local 50 EUR, 2 shares per ADR, EURUSD 1.10 -> FV 110.00. Fee 0.05 + 8 bps of 110 (0.088)
    = 0.138 each side: band [109.862, 110.138]. ADR at 110.30 is rich by 0.162."""
    assert adr.adr_fair_value(50, 2, 1.10) == pytest.approx(110.0)
    band = adr.adr_band(50, 2, 1.10, 0.05, 8)
    assert band.lower == pytest.approx(109.862)
    assert band.upper == pytest.approx(110.138)
    act, edge = adr.adr_arbitrage(110.30, band)
    assert act is adr.AdrAction.ISSUE and edge == pytest.approx(0.162)
    act, edge = adr.adr_arbitrage(109.50, band)
    assert act is adr.AdrAction.CANCEL and edge == pytest.approx(0.362)
    assert adr.adr_arbitrage(110.0, band) == (adr.AdrAction.NONE, 0.0)


def test_dividend_derivatives():
    """1,000 per point, strike 100, realised 104 -> +4,000. PV: (102 - 100) x 1,000 x 0.97 = 1,940.
    Strip: 1,000 x (2 x .97 + (-2) x .94) = 60. 40% cancellation of a 100 forecast: realised 60
    -> -40,000. Market 92 vs forecast 100: -8 pts, -8%."""
    assert dd.dividend_swap_pnl(1000, 100, 104) == 4000
    assert dd.dividend_swap_pv(1000, 100, 102, 0.97) == pytest.approx(1940)
    assert dd.dividend_strip_pv(1000, [100, 100], [102, 98], [0.97, 0.94]) == pytest.approx(60)
    assert dd.cancellation_pnl(1000, 100, 100, 0.4) == pytest.approx(-40_000)
    assert dd.implied_vs_forecast(92, 100) == pytest.approx((-8, -0.08))
    with pytest.raises(ValueError):
        dd.cancellation_pnl(1000, 100, 100, 1.2)


def test_tracker_note():
    """1,000,000 x 1.10 x (1 - 1%)^2 = 1,078,110."""
    assert dd.tracker_note_value(1_000_000, 0.10, 0.01, 2) == pytest.approx(1_078_110)


def test_sqrt_impact_and_risk_charge():
    """k=0.7, sigma 2%, Q/ADV = 1%: 0.7 x 0.02 x 0.1 x 10,000 = 14 bps.
    Risk charge sigma 1%, 4 days, aversion 0.5: 0.01 x 2 x 0.5 x 10,000 = 100 bps."""
    assert pt.sqrt_impact_bps(0.7, 0.02, 1_000, 100_000) == pytest.approx(14.0)
    assert pt.risk_charge_bps(0.01, 4, 0.5) == pytest.approx(100.0)


def test_basket_risk_bid():
    """Two legs of 1,000,000 each, sigma 2%, rho 0.5, Q/ADV = 4% (impact each 0.7 x .02 x 0.2 x 1e4 = 28):
    basket vol = sqrt(0.0003) = 1.7321%; risk charge (1 day, aversion 0.5) = 86.60 bps;
    bid = 3 + 28 + 86.60 = 117.60 bps = 23,520.51 on 2,000,000."""
    legs = [pt.BasketLeg(10_000, 100.0, 250_000, 0.02), pt.BasketLeg(20_000, 50.0, 500_000, 0.02)]
    bid = pt.principal_risk_bid(legs, 3.0, 0.7, 0.5, 1.0, 0.5)
    assert bid.basket_vol == pytest.approx(math.sqrt(0.0003))
    assert bid.impact_bps == pytest.approx(28.0)
    assert bid.risk_charge_bps == pytest.approx(86.6025, abs=1e-3)
    assert bid.total_bps == pytest.approx(117.6025, abs=1e-3)
    assert bid.total_amount == pytest.approx(23_520.51, abs=0.01)


def test_win_pnl_distribution():
    """Expected PnL if the desk wins = risk charge = 86.6025 bps x 2m = 17,320.51; std = 1.7321% x 2m
    = 34,641. Simulation is deterministic per seed and centred near the mean."""
    legs = [pt.BasketLeg(10_000, 100.0, 250_000, 0.02), pt.BasketLeg(20_000, 50.0, 500_000, 0.02)]
    bid = pt.principal_risk_bid(legs, 3.0, 0.7, 0.5, 1.0, 0.5)
    mean, std = pt.win_pnl_moments(bid)
    assert mean == pytest.approx(17_320.51, abs=0.01)
    assert std == pytest.approx(34_641.0, abs=1.0)
    a = pt.simulate_win_pnl(bid, 50_000, seed=1)
    assert np.array_equal(a, pt.simulate_win_pnl(bid, 50_000, seed=1))
    assert a.mean() == pytest.approx(mean, abs=std * 0.02)


# ------------------------------------------------------------------ indices


def test_index_level_and_divisor_invariance():
    """Prices 10, 20; shares 100, 50; float 1, 0.5: value 1,000 + 500 = 1,500; divisor 10 -> 150.
    Stock A issues 20 more shares: value 1,700; D' = 10 x 1,700/1,500 = 11.3333; level stays 150."""
    p, f, c = [10.0, 20.0], [1.0, 0.5], [1.0, 1.0]
    assert ix.index_level(p, [100, 50], f, c, 10) == pytest.approx(150)
    old = ix.index_value(p, [100, 50], f, c)
    new = ix.index_value(p, [120, 50], f, c)
    d2 = ix.adjust_divisor(10, old, new)
    assert d2 == pytest.approx(11.3333, abs=1e-4)
    assert ix.index_level(p, [120, 50], f, c, d2) == pytest.approx(150)


def test_weighting_schemes_and_capping():
    """Market caps 50/30/20 with a 40% cap: A capped at 40%, 10% excess split 60:40 ->
    [0.40, 0.36, 0.24]. Capping factors [0.667, 1, 1] reproduce those weights."""
    w = ix.weights_cap([50, 30, 20], [1, 1, 1])
    assert w == pytest.approx([0.5, 0.3, 0.2])
    capped = ix.apply_cap(w, 0.4)
    assert capped == pytest.approx([0.4, 0.36, 0.24])
    cf = ix.capping_factors(w, capped)
    assert cf == pytest.approx([2 / 3, 1, 1])
    reweighted = w * cf / (w * cf).sum()
    assert reweighted == pytest.approx(capped)
    with pytest.raises(ValueError):
        ix.apply_cap([0.5, 0.5], 0.4)
    assert ix.weights_price([10, 30]) == pytest.approx([0.25, 0.75])
    assert ix.weights_equal(4) == pytest.approx([0.25] * 4)
    assert ix.weights_float_cap([10, 20], [100, 50], [1, 0.5]) == pytest.approx([2 / 3, 1 / 3])


def test_apply_cap_cascade():
    """Cap 0.35 on [0.5, 0.4, 0.05, 0.05]: first pass caps A, B rises above 0.35 and is capped too:
    [0.35, 0.35, 0.15, 0.15]."""
    w = ix.apply_cap([0.5, 0.4, 0.05, 0.05], 0.35)
    assert w == pytest.approx([0.35, 0.35, 0.15, 0.15])
    assert w.sum() == pytest.approx(1.0)


def test_inclusion_demand():
    """20bn tracked x 0.5% = 100m; at 50 -> 2m shares; ADV 4m -> 0.5 days; impact
    0.7 x 2% x sqrt(0.5) x 10,000 = 98.99 bps."""
    d = ix.inclusion_demand(20e9, 0.005, 50.0, 4e6, 0.7, 0.02)
    assert d.notional == pytest.approx(100e6)
    assert d.shares == pytest.approx(2e6)
    assert d.days_of_adv == pytest.approx(0.5)
    assert d.impact_bps == pytest.approx(98.99, abs=0.01)


def test_total_return_step():
    """4,000 -> 4,040 plus 2 dividend points: TR x (4,042/4,000); 8,000 -> 8,084. Net of 15% WHT:
    8,000 x (4,040 + 1.7)/4,000 = 8,083.4."""
    assert ix.total_return_step(8000, 4000, 4040, 2) == pytest.approx(8084)
    assert ix.total_return_step(8000, 4000, 4040, 2, wht=0.15) == pytest.approx(8083.4)

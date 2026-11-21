import math

import numpy as np
import pytest

from core.margin import MarginResult, csa, exchange, pb_house, portfolio_margin, regt, simm_lite
from core.margin.exchange import FuturePos


def test_margin_result_never_negative():
    assert MarginResult(gross=100, credits=250).net == 0.0
    assert MarginResult(gross=100, credits=40).net == 60


# ------------------------------------------------------------------ exchange


def test_scan_single_product():
    """Long 10 ES at 5,000 x 50 = 2.5m notional; scan range 7%: worst loss = 2.5m x 7% = 175,000."""
    m = exchange.span_like_margin([FuturePos("ES", "Dec", 10, 5000, 50)])
    assert m.net == pytest.approx(175_000)
    assert m.credits == 0


def test_calendar_spread_charge_replaces_scan():
    """Long 10 Dec / short 10 Sep ES: matched 2.5m, net 0 -> no scan risk; charge 1% x 2.5m = 25,000."""
    m = exchange.span_like_margin(
        [FuturePos("ES", "Dec", 10, 5000, 50), FuturePos("ES", "Sep", -10, 5000, 50)]
    )
    assert m.gross == pytest.approx(25_000)
    assert m.detail["calendar_spread_charges"] == pytest.approx(25_000)


def test_inter_index_credit_for_hedge():
    """Long 2.5m ES (scan 7% = 175,000) vs short 2.5m D1US30 (scan 7.5% = 187,500): credit = 80% x
    min(175,000, 187,500) = 140,000; net = 362,500 - 140,000 = 222,500. Same direction -> no credit."""
    hedge = [FuturePos("ES", "Dec", 10, 5000, 50), FuturePos("D1US30", "Dec", -25, 1000, 100)]
    m = exchange.span_like_margin(hedge)
    assert m.gross == pytest.approx(362_500)
    assert m.credits == pytest.approx(140_000)
    assert m.net == pytest.approx(222_500)
    same = exchange.span_like_margin(
        [FuturePos("ES", "Dec", 10, 5000, 50), FuturePos("D1US30", "Dec", 25, 1000, 100)]
    )
    assert same.credits == 0 and same.net == pytest.approx(362_500)


def test_var_margin_and_history():
    """PnL history -100..100 (201 values): 1% quantile = -98 -> VaR 98; two-day horizon x sqrt(2) = 138.59."""
    pnl = list(range(-100, 101))
    assert exchange.var_margin(pnl, 0.99, 1) == pytest.approx(98.0)
    assert exchange.var_margin(pnl, 0.99, 2) == pytest.approx(98 * math.sqrt(2))
    assert exchange.var_margin([5.0, 6.0, 7.0], 0.99, 1) == 0.0
    h = exchange.portfolio_pnl_history(
        {"A": np.array([0.01, -0.02]), "B": np.array([0.0, 0.01])}, {"A": 1e6, "B": -5e5}
    )
    assert h == pytest.approx([10_000, -25_000])


def test_variation_margin():
    """10 ES (x50), prices 5,000 / 5,010 / 4,995 / 5,005: flows +5,000, -7,500, +5,000; cumulative
    5,000 / -2,500 / 2,500. Symmetric funding at 4% /360: -(5,000)(0.04/360) = -0.56 (income);
    asymmetric (only the -2,500 balance costs): 2,500 x 0.04/360 = 0.28."""
    f = exchange.variation_margin_flows(10, 50, [5000, 5010, 4995, 5005])
    assert f == pytest.approx([5000, -7500, 5000])
    assert exchange.vm_funding_cost(f, 0.04) == pytest.approx(-5000 * 0.04 / 360)
    assert exchange.vm_funding_cost(f, 0.04, symmetric=False) == pytest.approx(2500 * 0.04 / 360)


# ------------------------------------------------------------------ SIMM-lite / schedule


def test_bucket_and_equity_delta_margin():
    """Bucket 1, s = [100, -40], RW 25: WS = [2,500, -1,000]; rho 0.15:
    K = sqrt(2,500^2 + 1,000^2 + 2 x 0.15 x 2,500 x -1,000) = sqrt(6,500,000) = 2,549.51."""
    assert simm_lite.weighted_sensitivity(25, 100) == 2500
    assert simm_lite.bucket_margin([2500, -1000], 0.15) == pytest.approx(2549.51, abs=0.01)


def test_cross_bucket_aggregation():
    """Bucket 1 s=[100] (WS 2,500), bucket 2 s=[-50] (RW 32, WS -1,600), gamma 0.18:
    IM = sqrt(2,500^2 + 1,600^2 + 2 x 0.18 x 2,500 x -1,600) = sqrt(7,370,000) = 2,714.77."""
    m = simm_lite.equity_delta_margin({1: [100], 2: [-50]})
    assert m.net == pytest.approx(2714.77, abs=0.01)
    assert m.gross == pytest.approx(4100)
    assert m.credits == pytest.approx(4100 - 2714.77, abs=0.01)


def test_residual_bucket_not_diversified():
    """Residual bucket 12 (RW 70) with s=[10]: K = 700 is added on top of the diversified amount."""
    m = simm_lite.equity_delta_margin({1: [100], 12: [10]})
    assert m.net == pytest.approx(2500 + 700)


def test_schedule_netting_benefit():
    """Long 10m and short 10m swaps with one client: gross 20m, net 0 -> NGR 0. Gross IM 15% x 20m = 3.0m;
    net IM = 3.0m x 0.4 = 1.2m. Fully one-way (net = gross): no netting benefit."""
    m = simm_lite.schedule_im(20e6, 0.0)
    assert m.gross == pytest.approx(3.0e6)
    assert m.net == pytest.approx(1.2e6)
    one_way = simm_lite.schedule_im(20e6, 20e6)
    assert one_way.net == pytest.approx(3.0e6)
    assert simm_lite.schedule_im(0, 0).net == 0


# ------------------------------------------------------------------ Reg T / PM / PB


def test_regt():
    """Long 1m, short 500k: initial = 0.5 x 1m + 0.5 x 500k = 750k; maintenance = 250k + 150k = 400k;
    allowed gross leverage = 1.5m / 750k = 2.0x."""
    init, maint = regt.regt_requirements(1e6, 5e5)
    assert init.net == pytest.approx(750_000)
    assert maint.net == pytest.approx(400_000)
    assert regt.gross_leverage_allowed(1e6, 5e5) == pytest.approx(2.0)
    assert regt.gross_leverage_allowed(0, 0) is None


def test_portfolio_margin_offsets_and_floor():
    """Long 1m single name (grid 15%) vs short 1m index (grid 8%): worst loss 150k - 80k = 70k, versus
    standalone 150k + 80k = 230k. Long index alone: 80k."""
    pm = portfolio_margin
    hedged = pm.portfolio_margin([pm.PMPosition("X", 1e6), pm.PMPosition("IDX", -1e6, True)])
    assert hedged.net == pytest.approx(70_000)
    assert hedged.gross == pytest.approx(230_000)
    assert hedged.credits == pytest.approx(160_000)
    assert pm.portfolio_margin([pm.PMPosition("IDX", 1e6, True)]).net == pytest.approx(80_000)


def test_pb_house_addons():
    """Long 5m, equity 10m, vol 2%, ADV 250,000 sh at price 10 (500,000 sh = 2 days):
    base = 3 x 0.02 x sqrt(3) = 10.392% -> 519,615; concentration 0.5 x (5m - 2m) = 1.5m;
    liquidity 5% x 1 extra day x 5m = 250,000; directionality (net/gross = 1) 5% x 5m = 250,000."""
    pos = pb_house.PBPosition("A", 5e6, 10.0, 250_000, 0.02)
    m = pb_house.pb_house_margin([pos], 10e6)
    assert m.base == pytest.approx(5e6 * 3 * 0.02 * math.sqrt(3))
    assert m.concentration == pytest.approx(1.5e6)
    assert m.liquidity == pytest.approx(250_000)
    assert m.directionality == pytest.approx(250_000)
    assert m.squeeze == 0
    assert m.total == pytest.approx(m.base + 2.0e6)
    assert m.addons == pytest.approx(2.0e6)
    assert m.by_position["A"] == pytest.approx(m.base + 1.5e6 + 250_000)


def test_pb_house_squeeze_and_hedged_book():
    """Short with 20% short interest (> 15%) adds 10% x |MV|. A balanced long/short book has no
    directionality add-on. The concentrated book is far above simple Reg T margin on the same
    exposure only once add-ons apply."""
    short = pb_house.PBPosition("S", -1e6, 10.0, 1e9, 0.01, short_interest=0.20)
    long_ = pb_house.PBPosition("L", 1e6, 10.0, 1e9, 0.01)
    m = pb_house.pb_house_margin([short, long_], 100e6)
    assert m.squeeze == pytest.approx(100_000)
    assert m.directionality == 0
    assert pb_house.base_rate(0.001) == 0.10  # floored at min base


# ------------------------------------------------------------------ CSA


def test_csa_calls_mta_rounding():
    """Threshold 1m (cpty), MTA 250k, rounding 100k, held 2.0m. E=3.1m: required 2.1m, call 100k < MTA -> 0.
    E=3.5m: call 500k. E=3.57m: call 570k rounds UP to 600k. E=2.35m: required 1.35m, excess 650k rounds
    DOWN to a 600k return."""
    t = csa.CsaTerms(threshold_cpty=1e6, mta=250e3, rounding=100e3)
    assert csa.collateral_call(3.1e6, 2.0e6, t).amount == 0
    assert csa.collateral_call(3.5e6, 2.0e6, t).amount == pytest.approx(500e3)
    assert csa.collateral_call(3.57e6, 2.0e6, t).amount == pytest.approx(600e3)
    assert csa.collateral_call(2.35e6, 2.0e6, t).amount == pytest.approx(-600e3)
    assert (
        csa.collateral_call(1.0e6, 0.0, t).amount == 0
    )  # at the threshold: nothing required, nothing held
    assert csa.collateral_call(1.0e6, 1.0e6, t).amount == pytest.approx(
        -1.0e6
    )  # held 1m is returned


def test_csa_independent_amount_and_desk_threshold():
    """IA from the counterparty 500k with zero exposure: required 500k. Desk owes 2m with desk
    threshold 0.5m: required = -(2m - 0.5m) = -1.5m, desk should have posted 1.5m."""
    assert csa.required_collateral(0, csa.CsaTerms(independent_amount_cpty=500e3)) == 500e3
    assert csa.required_collateral(-2e6, csa.CsaTerms(threshold_desk=0.5e6)) == pytest.approx(
        -1.5e6
    )
    assert csa.required_collateral(0, csa.CsaTerms(independent_amount_desk=1e5)) == -1e5


def test_collateral_value_and_path():
    """1m at 2% haircut + 500k cash = 980k + 500k = 1.48m. Path with zero threshold and 2% haircut:
    each call posts amount x 0.98 of value; the second call tops up what is still missing."""
    assert csa.collateral_value([(1e6, 0.02), (5e5, 0.0)]) == pytest.approx(1.48e6)
    path = csa.call_path([1e6, 2e6], csa.CsaTerms(), haircut=0.02)
    assert path[0].amount == pytest.approx(1e6)
    assert path[1].raw == pytest.approx(2e6 - 0.98e6)


def test_dispute():
    """Desk calls 600k, counterparty computes 450k: transfer the undisputed 450k, 150k disputed.
    Opposite signs: nothing undisputed."""
    d = csa.dispute(600e3, 450e3)
    assert (d.undisputed, d.disputed) == (450e3, 150e3)
    o = csa.dispute(100e3, -50e3)
    assert o.undisputed == 0 and o.disputed == 150e3

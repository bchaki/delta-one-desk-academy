import math

import numpy as np
import pytest

from core.financing import balance_sheet as bs
from core.financing import internalisation as it
from core.financing import repo, sbl, xva_lite
from core.types import Direction

# ------------------------------------------------------------------ SBL


def test_sbl_accruals_and_split():
    """Loan 1,000,000, margin 1.02 -> collateral 1,020,000. Fee 3% for 10 days /360 = 833.33.
    Rebate = 5% - 3% = 2% on 1,020,000 for 10 days = 566.67. 80/20 split of the fee: 666.67 / 166.67."""
    assert sbl.collateral_required(1_000_000, 1.02) == pytest.approx(1_020_000)
    assert sbl.default_margin(False) == 1.02 and sbl.default_margin(True) == 1.05
    assert sbl.loan_fee(1_000_000, 0.03, 10, 360) == pytest.approx(833.33, abs=0.005)
    r = sbl.rebate_rate(0.05, 0.03)
    assert r == pytest.approx(0.02)
    assert sbl.cash_rebate(1_020_000, r, 10, 360) == pytest.approx(566.67, abs=0.005)
    lender, agent = sbl.revenue_split(833.33)
    assert lender == pytest.approx(666.664) and agent == pytest.approx(166.666)
    assert sbl.rebate_rate(0.04, 0.06) == pytest.approx(
        -0.02
    )  # negative rebate on a hard-to-borrow


def test_manufactured_dividend():
    """1,000 shares x 0.50 gross x 100% = 500; at 85% = 425."""
    assert sbl.manufactured_dividend(1000, 0.5) == 500
    assert sbl.manufactured_dividend(1000, 0.5, 0.85) == pytest.approx(425)


def test_collateral_marking_path():
    """10,000 sh, margin 1.02, prices 100 -> 110 -> 95. Required 1,122,000 then 969,000.
    Day 1 tops up +102,000; day 2 returns 153,000. With a 200,000 minimum transfer the 153,000
    excess is kept, and collateral stays above the requirement."""
    p = sbl.collateral_path(10_000, [100, 110, 95], 1.02)
    assert [m.transfer for m in p] == pytest.approx([102_000, -153_000])
    assert [m.collateral_after for m in p] == pytest.approx([1_122_000, 969_000])
    q = sbl.collateral_path(10_000, [100, 110, 95], 1.02, min_transfer=200_000)
    assert q[1].transfer == 0 and q[1].collateral_after == pytest.approx(1_122_000)
    assert all(m.collateral_after >= m.required - 1e-9 for m in q)


def test_recall_options():
    """Loan 1,000,000 (10,000 @ 100). Re-borrow fee 3% -> 15% for 30 days: 1,000,000 x 12% x 30/360 =
    10,000. Buy-in 2% premium + 15 bps impact = 21,500. Internalise at 5 bps: 41.67."""
    c = sbl.recall_options(10_000, 100, 0.03, 0.15, 30, 360, 0.02, 0.0015, 0.0005)
    assert c["reborrow"] == pytest.approx(10_000)
    assert c["buy_in"] == pytest.approx(21_500)
    assert c["internalise"] == pytest.approx(41.67, abs=0.005)


def test_short_cost_drag():
    """10,000 @ 100 short, fee 3% for 30 days = 2,500, dividend 0.50 -> 5,000: total 7,500."""
    c = sbl.short_cost_drag(10_000, 100, 0.03, 30, 360, 0.5)
    assert (c.fee, c.dividends, c.total) == (pytest.approx(2500), 5000, pytest.approx(7500))


def test_fee_curve_and_squeeze():
    """GC 30 bps, steepness 4: u=0 -> 30; u=0.5 -> 30 x (1 + 4 x 0.25/0.5) = 90. Fees rise with u.
    Supply 100, demand 60: recall 50% and demand x1.5 -> 90/50 = 1.8, capped at 0.99."""
    assert sbl.fee_from_utilisation(0.0, 30, 4) == 30
    assert sbl.fee_from_utilisation(0.5, 30, 4) == pytest.approx(90)
    assert sbl.fee_from_utilisation(0.8, 30, 4) > sbl.fee_from_utilisation(0.5, 30, 4)
    assert sbl.squeeze_utilisation(100, 60, 0.5, 1.5) == 0.99
    assert sbl.squeeze_utilisation(100, 60, 0.0, 1.0) == pytest.approx(0.6)


# ------------------------------------------------------------------ repo


def test_repo_basics():
    """MV 1,000,000, 5% haircut -> cash 950,000; 7 days at 4.5% /360 = 831.25."""
    assert repo.repo_cash(1_000_000, 0.05) == pytest.approx(950_000)
    assert repo.default_haircut("large_cap") == 0.08
    assert repo.repo_interest(950_000, 0.045, 7, 360) == pytest.approx(831.25)


def test_gc_special_term_and_margin_call():
    """Benchmark 4.00% + 5 bps GC = 4.05%; special with a 200 bps fee: 4.05% - 2.00% = 2.05%.
    Term 0.5y at +10 bps/yr = 4.05%. MV falls to 900,000: required cash 855,000 vs 950,000 lent ->
    95,000 call."""
    assert repo.gc_rate(0.04) == pytest.approx(0.0405)
    assert repo.special_rate(0.04, 200) == pytest.approx(0.0205)
    assert repo.term_rate(0.04, 0.5) == pytest.approx(0.0405)
    assert repo.term_rate(0.04, 1.0, 20) == pytest.approx(0.0420)
    assert repo.repo_margin_call(900_000, 950_000, 0.05) == pytest.approx(95_000)


def test_funding_comparison():
    """10m long book, 30 days /360, benchmark 4%, FTP 35, haircut 8%, repo +5 bps, swap +50 bps:
    unsecured 10m x 4.35% /12 = 36,250; repo 9.2m x 4.05%/12 + 0.8m x 4.35%/12 = 31,050 + 2,900 = 33,950;
    swap 10m x 4.50% /12 = 37,500."""
    c = repo.funding_cost_comparison(10e6, 0.04, 30, 360, 35, 0.08, 5, 50)
    assert c["unsecured"] == pytest.approx(36_250)
    assert c["repo"] == pytest.approx(33_950)
    assert c["swap"] == pytest.approx(37_500)


# ------------------------------------------------------------------ internalisation


def test_internalisation():
    """Name A: short 100,000, longs 200,000 x 50% reusable + 30,000 inventory = 130,000 supply -> fully
    covered. Name B (price 40): short 80,000, longs 20,000 x 50% + 20,000 = 30,000 cover, 50,000 street;
    saving = 30,000 x 40 x (500 - 10) bps x 30/360 = 4,900."""
    a = it.NameInput("A", 50.0, 100_000, 200_000, 30_000, 100.0)
    b = it.NameInput("B", 40.0, 80_000, 20_000, 20_000, 500.0)
    ra = it.internalise_name(a, 0.5, 10, 30, 360)
    rb = it.internalise_name(b, 0.5, 10, 30, 360)
    assert ra.internal_cover == 100_000 and ra.street_borrow == 0
    assert rb.internal_cover == 30_000 and rb.street_borrow == 50_000
    assert rb.savings == pytest.approx(4_900)
    rows, total, coverage = it.internalise_book([a, b], 0.5, 10, 30, 360)
    assert total == pytest.approx(ra.savings + rb.savings)
    demand = 100_000 * 50 + 80_000 * 40
    assert coverage == pytest.approx((100_000 * 50 + 30_000 * 40) / demand)
    assert len(rows) == 2
    zero = it.internalise_name(it.NameInput("Z", 10, 0, 0, 0, 100), 0.5, 10, 30, 360)
    assert zero.savings_bps == 0.0


# ------------------------------------------------------------------ balance sheet


def test_balance_sheet_and_capital():
    """TRS notional 10m, index SF 0.20, alpha 1.4: EAD = 1.4 x (0 + 2m) = 2.8m. Leverage exposure with
    the 10m hedge = 12.8m -> LR capital 4% = 512,000. RWA = 2.8m x 100% (hedge fund) + 10m x 100% = 12.8m
    -> CET1 capital 12% = 1,536,000 (binding). BS charge = 1.28 x 8 = 10.24 bps; capital charge
    = 1.536m x 10% / 10m = 153.6 bps."""
    ead = bs.sa_ccr_ead(0, 0, 10e6, 0.20)
    assert ead == pytest.approx(2.8e6)
    le = bs.leverage_exposure_swap_with_hedge(ead, 10e6)
    assert le == pytest.approx(12.8e6)
    rw = bs.rwa(ead, 1.0) + bs.rwa(10e6, 1.0)
    cap = bs.capital_required(le, rw, 0.04, 0.12)
    assert cap == pytest.approx(1.536e6)
    assert bs.balance_sheet_charge_bps(le, 10e6, 8) == pytest.approx(10.24)
    assert bs.capital_charge_bps(cap, 10e6, 0.10) == pytest.approx(153.6)
    assert bs.leverage_exposure_margin_loan(5e6) == 5e6
    assert bs.sa_ccr_ead(1e6, 0.4e6, 10e6, 0.2, alpha=1.0) == pytest.approx(0.6e6 + 2e6)


def test_client_profitability():
    """Revenue 100k - funding 40k - BS 10k = 50k; capital 500k -> RoC 10%; economic profit
    = 50k - 500k x 10% = 0."""
    p = bs.client_profitability(100e3, 40e3, 10e3, 500e3, 0.10)
    assert p.net_contribution == pytest.approx(50e3)
    assert p.return_on_capital == pytest.approx(0.10)
    assert p.economic_profit == pytest.approx(0.0)
    assert bs.client_profitability(10, 0, 0, 0, 0.1).return_on_capital == 0.0


# ------------------------------------------------------------------ XVA


def test_cva_hand_calc():
    """EE 100 at t = 0.5 and 1.0, CDS 100 bps, LGD 60%, r = 0: hazard = 1%/0.6 = 1.6667%,
    S(1) = exp(-0.016667) = 0.983471, so CVA = 0.6 x 100 x (1 - 0.983471) = 0.9917."""
    cva = xva_lite.cva(np.array([100.0, 100.0]), np.array([0.5, 1.0]), 100, 0.6)
    assert cva == pytest.approx(0.6 * 100 * (1 - math.exp(-0.01 / 0.6)), abs=1e-9)
    assert cva == pytest.approx(0.9917, abs=1e-3)


def test_fva_kva_mva():
    """EE 100 over dt 0.5 each, funding 60 bps: 0.006 x 100 x 1.0 = 0.60. KVA with RW 1, CET1 12%,
    hurdle 10%: 0.10 x 12 x 1.0 = 1.20. MVA: IM 1m x 40 bps x 2y = 8,000."""
    ee, t = np.array([100.0, 100.0]), np.array([0.5, 1.0])
    assert xva_lite.fva(ee, t, 60) == pytest.approx(0.60)
    assert xva_lite.kva(ee, t, 1.0, 0.12, 0.10) == pytest.approx(1.20)
    assert xva_lite.mva(1e6, 2.0, 40) == pytest.approx(8_000)
    assert xva_lite.xva_charge_bps(25_000, 10e6, 1.0) == pytest.approx(25.0)


def test_exposure_simulation_properties():
    """Exposure is non-negative and deterministic per seed; a CSA lowers PFE; exposure is zero on
    reset steps; a short has exposure when the stock rises."""
    kw = dict(notional=10e6, vol=0.25, maturity=1.0, n_steps=12, reset_every=3, n_paths=2_000)
    a = xva_lite.simulate_exposure(direction=Direction.LONG, seed=3, **kw)
    b = xva_lite.simulate_exposure(direction=Direction.LONG, seed=3, **kw)
    assert np.array_equal(a.pfe, b.pfe)
    assert (a.ee >= 0).all() and a.peak_pfe > 0 and a.epe > 0
    assert a.ee[2] == 0 and a.ee[5] == 0  # reset steps 3, 6, ...
    csa = xva_lite.simulate_exposure(direction=Direction.LONG, seed=3, mpor_steps=1, **kw)
    assert csa.peak_pfe < a.peak_pfe
    short = xva_lite.simulate_exposure(direction=Direction.SHORT, seed=3, **kw)
    assert short.peak_pfe > 0
    thr = xva_lite.simulate_exposure(
        direction=Direction.LONG, seed=3, mpor_steps=1, threshold=1e6, **kw
    )
    assert thr.peak_pfe >= csa.peak_pfe
    zero_lag = xva_lite.simulate_exposure(direction=Direction.LONG, seed=3, mpor_steps=0, **kw)
    assert zero_lag.peak_pfe == 0.0
    big_lag = xva_lite.simulate_exposure(direction=Direction.LONG, seed=3, mpor_steps=50, **kw)
    assert big_lag.peak_pfe == pytest.approx(a.peak_pfe)


def test_swap_rwa():
    """EAD 23.8m at 0.2 = 4.76m; hedge 50m at 0.25 = 12.5m; total 17.26m."""
    from core.financing import balance_sheet as bs

    assert bs.swap_rwa(23.8e6, 0.2, 50e6, 0.25) == pytest.approx(17.26e6)

"""Tests for the Phase 6 strategy engines (hand calculations in the docstrings)."""

import math

import numpy as np
import pandas as pd
import pytest

from core.strategies import (
    adr_arb,
    basis,
    dividend,
    etf_arb,
    flow,
    index_events,
    meanrev,
    pairs,
    pnl_gen,
    sbl_strats,
)


def test_threshold_backtest():
    """Signal 0, 5, 20, 12, 1, 0 (bps). Entry 10, exit 2, cost 3: short at 20, exit at 1: 19 - 3 = 16 bps.
    On 1,000,000: 1,600. Negative side mirrors: -20 -> -1 is also 16."""
    idx = pd.date_range("2026-01-01", periods=6, freq="B")
    t = meanrev.threshold_backtest(pd.Series([0, 5, 20, 12, 1, 0.0], idx), 10, 2, 3)
    assert len(t) == 1 and t.pnl.iloc[0] == pytest.approx(1600) and t.days.iloc[0] == 2
    t2 = meanrev.threshold_backtest(pd.Series([0, -20, -12, -1, 0, 0.0], idx), 10, 2, 3)
    assert t2.side.iloc[0] == "long signal" and t2.pnl_signal.iloc[0] == pytest.approx(16)
    assert len(meanrev.threshold_backtest(pd.Series([1, 2, 3.0], idx[:3]), 10, 2, 3)) == 0


def test_threshold_backtest_open_position_closed_on_last_day():
    """Signal 0, 15, 12, 11: never inside the exit band, so the trade closes on the last day at 11: (15-11)-1 = 3 bps."""
    idx = pd.date_range("2026-01-01", periods=4, freq="B")
    t = meanrev.threshold_backtest(pd.Series([0, 15, 12, 11.0], idx), 10, 2, 1)
    assert t.pnl_signal.iloc[0] == pytest.approx(3)


def test_sweep_entry_orders_trades():
    """A wider entry threshold can only reduce the number of trades."""
    rng = np.random.default_rng(0)
    s = pd.Series(rng.normal(0, 10, 400), pd.date_range("2026-01-01", periods=400, freq="B"))
    sw = meanrev.sweep_entry(s, [5, 10, 20, 40], 1, 1)
    assert list(sw.trades) == sorted(sw.trades, reverse=True)
    assert meanrev.sweep_entry(s, [1000], 1, 1).trades.iloc[0] == 0


def test_basis_formulas():
    """50m, spread 60, FTP 35, BS 10, 360 days: 50m x 15 bps = 75,000. Futures: 60 - 20 - 0.05 x 35 = 38.25."""
    assert basis.swap_financing_pnl(50e6, 60, 35, 10, 360) == pytest.approx(75_000)
    assert basis.futures_hedge_net_bps(60, 20, 0.05, 35) == pytest.approx(38.25)
    hc = basis.hedge_choice(60, 35, 10, 20, 0.05)
    assert (
        hc["stock"] == 15 and hc["futures"] == pytest.approx(38.25) and hc["best_is_futures"] == 1.0
    )
    assert basis.hedge_choice(60, 35, 10, 50, 0.05)["best_is_futures"] == 0.0
    assert basis.funding_shock_pnl(10e6, 25, 180) == pytest.approx(-12_500)
    st = basis.sensitivity_table(10e6, 60, 10, [30, 50, 70])
    assert list(st.pnl.round(0)) == [20_000, 0, -20_000]


def test_implied_spread_series():
    """dev_bps 0.5 with t = 0.25: 10 + 0.5/0.25 = 12 bps."""
    d = pd.DataFrame({"dev_bps": [0.5], "t": [0.25]})
    assert basis.implied_financing_spread_series(d).iloc[0] == pytest.approx(12)


def test_dividend_formulas():
    """Long 1,000 at 20 settling 17.5: -2,500. A 30% cancellation of forecast 20 vs strike 18: 14 - 18 = -4 per unit."""
    assert dividend.future_pnl(1000, 20, 17.5) == -2500
    cs = dividend.cancellation_stress(100, 18, 20, [0, 0.3])
    assert cs.pnl.iloc[1] == pytest.approx(-400) and cs.pnl.iloc[0] == pytest.approx(200)
    assert dividend.hedge_note_exposure(1000, 20, 2, 0.25) == pytest.approx(10_000)


def test_flow_economics():
    """Agency 5 bps on 10m = 5,000. Risk trade: spread 8, hedge 3 on 10m = 5,000; vol 1.5% x sqrt(4) x 10m = 300,000."""
    assert flow.agency_pnl(10e6, 5) == pytest.approx(5000)
    r = flow.risk_trade_ev(10e6, 8, 3, 0.015, 4)
    assert r["expected"] == pytest.approx(5000) and r["one_sigma_risk"] == pytest.approx(300_000)
    assert flow.risk_trade_ev(1, 1, 1, 0.0, 1)["ratio"] == math.inf


def test_flow_simulation_is_deterministic_and_internalises():
    """Same seed = same answer; a balanced flow hedges less than a one-way flow."""
    a, b = flow.simulate(3), flow.simulate(3)
    assert a.total == b.total and a.total_spread > 0
    one_way = flow.simulate(3, buy_bias=0.45)
    assert flow.internalisation_rate(one_way.daily) < flow.internalisation_rate(a.daily)
    assert a.total == pytest.approx(a.total_spread - a.total_hedge_cost + a.total_price_pnl)


def test_sbl_strategy_formulas():
    """Lendable 100m x 40% utilisation x 50 bps x 180/360 = 100,000; lender 85,000, agent 15,000. Upgrade: 20m x 12 bps x 90/360 = 6,000."""
    r = sbl_strats.lending_revenue(100e6, 0.4, 50, 180)
    assert r["gross"] == pytest.approx(100_000) and r["lender"] == pytest.approx(85_000)
    assert sbl_strats.collateral_upgrade_revenue(20e6, 12, 90) == pytest.approx(6000)
    rk = sbl_strats.recall_cost_ranking(100_000, 50, 0.01, 0.05, 30, 0.02, 0.01, 0.005)
    assert rk[0][0] == "internalise" and rk[-1][0] == "buy_in"
    curve = sbl_strats.utilisation_revenue_curve(100e6, 30, 2)
    assert curve.fee_bps.is_monotonic_increasing


def test_event_formulas():
    """Buy 5m ahead of an add, +40 bps move, 10 bps impact, 2 bps cost: 5m x 28 bps = 14,000. MOC: 1m shares x 50 x (6 - 2) bps = 20,000."""
    assert index_events.preposition_pnl(5e6, 40, 10, 2) == pytest.approx(14_000)
    assert index_events.moc_facilitation_pnl(1e6, 50, 6, 2) == pytest.approx(20_000)
    assert index_events.crowded_unwind_bps(100_000, 1e6, 0.02, 1.0, 3.0) == pytest.approx(
        3 * 0.02 * math.sqrt(0.1) * 1e4
    )


def test_pairs_statistics():
    """A simulated cointegrated pair (A = B x noise AR(1) with phi 0.9) has a negative ADF and half-life ~ ln2/-ln(0.9) = 6.6; a pure random walk pair does not pass."""
    rng = np.random.default_rng(1)
    n = 800
    b = np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    e = np.zeros(n)
    for i in range(1, n):
        e[i] = 0.9 * e[i - 1] + rng.normal(0, 0.01)
    a = b * np.exp(e)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame({"A": a, "B": b}, index=idx)
    st = pairs.pair_stats(df, "A", "B")
    assert st.cointegrated and 4 < st.half_life < 10 and abs(st.beta - 1) < 0.2
    rw = pd.DataFrame(
        {
            "A": np.exp(np.cumsum(rng.normal(0, 0.01, n))),
            "B": np.exp(np.cumsum(rng.normal(0, 0.01, n))),
        },
        index=idx,
    )
    assert pairs.half_life(np.cumsum(rng.normal(0, 1, n))) > 20
    assert pairs.pair_stats(rw, "A", "B").adf > pairs.pair_stats(df, "A", "B").adf
    sc = pairs.screen_pairs(df.assign(C=rw.A), ["A", "B", "C"], 2)
    assert len(sc) == 2 and sc.adf.iloc[0] <= sc.adf.iloc[1]
    bt = pairs.backtest(df, "A", "B")
    assert len(bt) > 5 and bt.pnl.sum() > 0
    assert pairs.half_life(np.array([1.0, 2.0, 3.0, 4.0])) == math.inf


def test_pnl_gen_math():
    """Notional 100m, FTP 35, leverage multiple 1.5, BS 8 bps, capital 4%, CoE 10%, revenue 600,000:
    funding 350,000; BS 100m x 1.5 x 8bp = 120,000; capital 6m; net 130,000; EP = 130,000 - 600,000 = -470,000."""
    r = pnl_gen.net_contribution(600_000, 100e6, 35, 1.5, 8, 0.04, 0.10)
    assert r["funding"] == pytest.approx(350_000) and r["balance_sheet"] == pytest.approx(120_000)
    assert r["net_contribution"] == pytest.approx(130_000) and r[
        "economic_profit"
    ] == pytest.approx(-470_000)
    bva = pnl_gen.budget_vs_actual(
        pd.Series({"a": 90.0, "b": 10.0}), pd.Series({"a": 100.0, "c": 0.0})
    )
    assert (
        bva.variance["a"] == -10
        and bva.variance_pct["a"] == pytest.approx(-0.1)
        and math.isnan(bva.variance_pct["c"])
    )


def test_world_integration(world):
    """Every engine runs on the synthetic world and is deterministic."""
    m = world.market
    assert len(etf_arb.premium_series_bps(m, "D1UX")) == len(m.days)
    assert etf_arb.threshold_bps(5000, 1e6, 3, 2, 2.0) > etf_arb.threshold_bps(5000, 1e6, 3, 2, 1.0)
    assert len(etf_arb.backtest(m, "D1UX", 0, 5, 2)) > 0
    a = next(iter(m.universe.adrs))
    assert len(adr_arb.deviation_series_bps(m, a)) == len(m.days)
    assert adr_arb.band_bps(0.02, 100.0, 10) == pytest.approx(12)
    assert len(adr_arb.backtest(m, a, 10)) > 0
    assert dividend.year_backtest(m, 2025)["worst_mtm"] <= 0
    ev = index_events.event_study(m, "D1 US 30")
    assert {"pre_bps", "post_bps"} <= set(ev.columns)
    assert len(index_events.membership_changes(m, "D1 US 30")) >= 2
    sp = sbl_strats.specials_screen(m, world.as_of, 5)
    assert len(sp) == 5 and sp.revenue_pa.is_monotonic_decreasing
    from core.pnl.explain import ledgers

    _, clean = ledgers(world.book, m)
    start, end = m.days[-251], world.as_of
    src = pnl_gen.revenue_by_source(clean, start, end)
    sub = pnl_gen.revenue_by_subbook(clean, start, end)
    assert src.sum() == pytest.approx(sub.sum())
    assert len(pnl_gen.revenue_by_tier(clean, world.book, start, end)) >= 1
    assert pnl_gen.swap_notional_usd(world.book, m, end) > 0

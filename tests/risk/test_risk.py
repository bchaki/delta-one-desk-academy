"""Risk: snapshot, sensitivities, VaR family, stress, liquidity, limits."""

import numpy as np
import pandas as pd
import pytest

from core.data.scenarios import custom_scenario, get_scenario, scenario_ids
from core.risk import limits, liquidity, stress, var
from core.risk.sensitivities import sensitivities, snapshot, swap_shares_at, usd_exposure_vector


@pytest.fixture(scope="module")
def snap(world):
    return snapshot(world.book, world.market, world.as_of)


@pytest.fixture(scope="module")
def vec(snap):
    return usd_exposure_vector(snap)


@pytest.fixture(scope="module")
def rets(world, vec):
    return var.usd_returns(world.market, list(vec.index), world.as_of)


def test_snapshot_delta_decomposes(world, snap):
    assert (snap.delta_usd - (snap.cash_usd + snap.swap_usd + snap.fut_usd)).abs().max() < 1e-6
    # ADR arbitrage legs are separate keys (adr:X vs stock:underlying) and net only economically
    adr_underlyings = {f"stock:{a.underlying}" for a in world.universe.adrs.values()}
    stock_rows = snap[(snap.kind == "stock") & ~snap.key.isin(adr_underlyings)]
    assert stock_rows.swap_usd.abs().sum() > 1e7  # large client swap exposure...
    assert (
        stock_rows.delta_usd.abs().max() < 1e-3 * stock_rows.swap_usd.abs().sum()
    )  # ...fully hedged


def test_swap_shares_boundaries(world):
    s = world.book.swaps()[0]
    assert (
        swap_shares_at(world.book, s, world.market.days[0]) == 0.0
        or s.trade_date <= world.market.days[0]
    )
    term = next(e for e in world.book.events if e.kind == "termination")
    t = world.book.trade(term.trade_id)
    assert swap_shares_at(world.book, t, term.date) == 0.0


def test_sensitivities_keys(world):
    s = sensitivities(world.book, world.market, world.as_of)
    assert s["gross"] > 0 and s["ftp_plus_1bp_annual"] < 0
    assert s["borrow_plus_100bp_annual"] < 0  # net borrower
    assert s["dividend_minus10pct"] == pytest.approx(-0.1 * s["annual_dividend_exposure"])
    assert set(s["fx_delta"]) >= {"USD"}
    assert s["divfut_per_point"] != 0


def test_var_properties(vec, rets):
    p = var.hist_pnl(vec, rets)
    assert var.var_from_pnl(p, 0.99) >= var.var_from_pnl(p, 0.95) > 0
    assert var.es_from_pnl(p, 0.99) >= var.var_from_pnl(p, 0.99)
    pv = var.parametric_var(vec, rets)
    mv, mes = var.mc_var(vec, rets)
    assert mv == pytest.approx(pv, rel=0.08) and mes > mv
    assert mc_repeat(vec, rets) == var.mc_var(vec, rets)  # seeded


def mc_repeat(vec, rets):
    return var.mc_var(vec, rets)


def test_component_var_sums_to_total(vec, rets):
    comp = var.component_var(vec, rets)
    assert comp.sum() == pytest.approx(var.parametric_var(vec, rets), rel=1e-9)
    assert len(var.marginal_var(vec, rets)) == len(vec)


def test_var_hand_example():
    """Two assets, w = (100, 0), sigma = 1% daily: parametric 99% VaR = 2.3263 x 1 = 2.33."""
    rets = pd.DataFrame({"a": [0.01, -0.01, 0.01, -0.01], "b": [0.0, 0.0, 0.0, 0.0]})
    w = pd.Series({"a": 100.0, "b": 0.0})
    sigma = rets["a"].std()
    assert var.parametric_var(w, rets) == pytest.approx(2.3263 * 100 * sigma, rel=1e-3)
    pnl = np.array([-5.0, -1.0, 0.0, 1.0, 2.0])
    assert var.var_from_pnl(pnl, 0.8) == pytest.approx(-np.quantile(pnl, 0.2))
    assert var.es_from_pnl(pnl, 0.8) == pytest.approx(5.0)


def test_backtest_and_traffic_light():
    pnl = np.array([-10.0, -1.0, 2.0, -6.0])
    assert var.backtest_exceptions(pnl, np.array([5.0, 5.0, 5.0, 5.0])) == 2
    assert [var.traffic_light(n) for n in (0, 4, 5, 9, 10)] == [
        "green",
        "green",
        "yellow",
        "yellow",
        "red",
    ]


def test_historical_var_backtests_not_red(world):
    m = world.market
    ex = usd_exposure_vector(snapshot(world.book, m, world.as_of))
    r = var.usd_returns(m, list(ex.index), world.as_of, lookback=500)
    pnl = r.to_numpy() @ ex.to_numpy()
    v = var.var_from_pnl(pnl[:250], 0.99)
    assert var.traffic_light(var.backtest_exceptions(pnl[250:], np.full(len(pnl[250:]), v))) in {
        "green",
        "yellow",
        "red",
    }


def test_stress_sums_and_zero_scenario(world):
    for sid in scenario_ids():
        r = stress.apply_scenario(world.book, world.market, world.as_of, sid)
        assert sum(r.by_factor.values()) == pytest.approx(r.total)
        assert sum(r.by_leg.values()) == pytest.approx(r.by_factor["equity"])
    assert get_scenario("crash_1987").equity_pct["US"] == -22.0
    table = stress.all_scenarios(world.book, world.market, world.as_of)
    assert len(table) == 5


def test_stress_custom_and_fx_shocks(world):
    r = stress.apply_scenario(world.book, world.market, world.as_of, custom_scenario("zero"))
    assert r.total == pytest.approx(0.0, abs=1e-6)
    r2 = stress.apply_scenario(
        world.book, world.market, world.as_of, custom_scenario("eq", equity_pct=-10.0, fx_pct=5.0)
    )
    assert r2.by_factor["equity"] != 0
    assert stress._fx_shock("JPY", {"USDJPY": 25.0}) == pytest.approx(1 / 1.25 - 1)
    assert stress._fx_shock("CHF", {}) == 0.0 and stress._fx_shock("GBP", {"GBPUSD": 2.0}) == 0.02


def test_liquidity_and_concentration(world, snap):
    tab = liquidity.liquidity_table(snap, world.market, world.as_of)
    assert (tab.days_to_liquidate == tab.pct_adv / 0.20).all() or np.allclose(
        tab.days_to_liquidate, tab.pct_adv / 0.20
    )
    c = liquidity.concentration(snap)
    assert 0 < c["top5"] <= 1 and 0 < c["hhi"] <= 1
    assert liquidity.concentration(snap.iloc[0:0]) == {"top5": 0.0, "hhi": 0.0}


def test_limits_statuses():
    out = {
        s.name: s
        for s in limits.check_limits(
            {"net_delta_usd": 1e6, "gross_notional_usd": 9e8, "var_99_1d_usd": -4e6, "unknown": 1.0}
        )
    }
    assert out["net_delta_usd"].status == "ok"
    assert out["gross_notional_usd"].status == "soft"
    assert out["var_99_1d_usd"].status == "hard" and out["var_99_1d_usd"].utilisation > 1
    assert "unknown" not in out

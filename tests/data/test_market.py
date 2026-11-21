"""Synthetic market: determinism, structure and the invariants the lessons rely on."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from core.data.market import HISTORY_END, HISTORY_START, build_market, trading_days
from core.types import Benchmark, Currency


def test_trading_days_are_common_business_days():
    days = trading_days()
    assert days[0] >= HISTORY_START and days[-1] <= HISTORY_END
    assert all(d.weekday() < 5 for d in days)
    assert date(2025, 12, 25) not in days and date(2026, 7, 3) not in days  # holidays dropped
    assert len(days) > 650


def test_deterministic_and_seed_sensitive():
    a = build_market(7)
    build_market.cache_clear()
    b = build_market(7)
    assert a is not b
    pd.testing.assert_frame_equal(a.prices, b.prices)
    pd.testing.assert_frame_equal(a.index_level, b.index_level)
    c = build_market(8)
    assert not np.allclose(a.index_level["D1 US 30"], c.index_level["D1 US 30"])


def test_universe_shape(world):
    u = world.market.universe
    assert len(u.stocks) == 61 and len(u.adrs) == 5 and len(u.indices) == 2 and len(u.etfs) == 2


def test_index_levels_clean_and_start_at_base(world):
    m = world.market
    assert not m.index_level.isna().any().any()
    assert m.index_level.iloc[0].tolist() == [1000.0, 1000.0]
    assert m.index_level.pct_change().abs().max().max() < 0.12  # no divisor/jump artefacts


def test_divisor_only_changes_on_events(world):
    """Divisor steps at rebalances and the merger deletion, not at random days."""
    m = world.market
    for name, hist in m.index_divisor.items():
        dates = [d for d, _ in hist]
        assert dates == sorted(dates) and len(dates) >= 5
    us = [d for d, _ in m.index_divisor["D1 US 30"]]
    assert date(2026, 3, 17) in us  # NEVE removed the day after the cash merger


def test_corporate_actions_present(world):
    kinds = {c.kind for c in world.market.corporate_actions}
    assert {"split", "rights", "spin_off", "cash_merger", "index_delete", "index_add"} <= kinds


def test_split_halves_price_and_doubles_quantity_factor(world):
    m = world.market
    plan = m.universe.ca_plan
    i = m.days.index(next(c.date for c in m.corporate_actions if c.kind == "split"))
    before, after = m.prices[plan.split_ticker].iloc[i - 1], m.prices[plan.split_ticker].iloc[i]
    assert 0.35 < after / before < 0.65
    assert m.cumqf[plan.split_ticker].iloc[i] == pytest.approx(
        2 * m.cumqf[plan.split_ticker].iloc[i - 1]
    )


def test_merger_converges_to_offer_then_delists(world):
    m = world.market
    plan = m.universe.ca_plan
    ev = {c.kind: c for c in m.corporate_actions if c.ticker == plan.merger_ticker}
    offer = ev["cash_merger"].terms["offer"]
    assert m.prices.at[pd.Timestamp(ev["cash_merger"].date), plan.merger_ticker] == pytest.approx(
        offer
    )
    assert m.prices[plan.merger_ticker].iloc[-1] != m.prices[plan.merger_ticker].iloc[-1]  # NaN


def test_futures_converge_to_index_at_expiry(world):
    """At expiry T-t = 0 so fair value = spot and the deviation term is multiplied by 0."""
    m = world.market
    for (name, exp), ser in m.futures.items():
        ts = pd.Timestamp(exp)
        if ts in ser.index and ts in m.index_level.index:
            assert ser.loc[ts] == pytest.approx(m.index_level.at[ts, name], rel=1e-9)


def test_rates_follow_policy_paths(world):
    m = world.market
    s = m.fixings[Benchmark.SOFR]
    assert s.loc["2024-01-10"] == pytest.approx(0.046, abs=2e-4)
    assert s.loc["2026-10-01"] == pytest.approx(0.034, abs=2e-4)
    assert m.fixings[Benchmark.TONA].loc["2023-12-01"] < 0.005


def test_fx_helpers(world):
    m = world.market
    d = m.days[100]
    assert m.fx_usd_per(Currency.USD, d) == 1.0
    assert m.fx_rate(Currency.EUR, Currency.USD, d) == pytest.approx(
        m.fx.at[pd.Timestamp(d), "EURUSD"]
    )
    assert m.fx_rate(Currency.JPY, Currency.EUR, d) == pytest.approx(
        1 / m.fx.at[pd.Timestamp(d), "USDJPY"] / m.fx.at[pd.Timestamp(d), "EURUSD"]
    )
    assert m.fx_usd_per(Currency.CHF, d) == pytest.approx(1 / m.fx.at[pd.Timestamp(d), "USDCHF"])


def test_curve_and_lookups(world):
    m = world.market
    d = m.days[200]
    c = m.curve(Benchmark.SOFR, d)
    assert c.df_date(d) == pytest.approx(1.0)
    assert 0 < c.df_date(date(2027, 6, 1)) < 1
    assert m.clamp(date(1990, 1, 1)) == m.days[0]
    assert m.clamp(date(2100, 1, 1)) == m.days[-1]
    tick = next(iter(m.universe.stocks))
    assert m.stock_adv(tick, d) > 0 and m.shares_outstanding(tick, d) > 0
    exps = m.front_expiries("D1 US 30", d)
    assert exps == sorted(exps) and len(exps) == 4
    assert m.futures_price("D1 US 30", exps[0], d) > 0
    assert m.index_dividends_between("D1 Europe 20", date(2024, 1, 1), date(2024, 12, 31))
    assert m.fixing(Benchmark.SOFR, d) > 0 and m.fixings_dict(Benchmark.SOFR)


def test_dividend_episodes(world):
    m = world.market
    kinds = {e.kind for e in m.dividends}
    assert {"regular", "special", "cut", "cancelled"} <= kinds
    assert all(e.amount == 0 for e in m.dividends if e.kind == "cancelled")
    eu = m.div_futures[2025]
    pre, post = eu.loc["2025-02-03"], eu.loc["2025-05-07"]
    assert post < pre  # the cancellation episode cuts the dividend-future price


def test_squeeze_episode(world):
    m = world.market
    t = m.squeeze_ticker
    fee = m.borrow_fee_bps[t]
    assert fee.max() >= 4000 and m.utilisation[t].max() > 0.9
    assert any(r.ticker == t for r in m.recalls)


def test_adr_and_etf_track_underlyings(world):
    m = world.market
    a = next(iter(m.universe.adrs.values()))
    ratio = m.adr_prices[a.adr_ticker] / (
        m.prices[a.underlying]
        * a.ratio
        * pd.Series(
            [m.fx_usd_per(m.universe.stocks[a.underlying].ccy, d) for d in m.days],
            index=m.prices.index,
        )
    )
    assert ratio.between(0.97, 1.03).all()
    assert not m.etf_prices.isna().any().any()


def test_trf_spread_series_exists(world):
    t = world.market.trf_spread_bps
    assert t.notna().sum().min() > 400
    assert t.abs().max().max() < 1500

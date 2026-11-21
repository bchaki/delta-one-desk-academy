"""Tests for index arbitrage and roll strategy engines."""

from datetime import date

import pandas as pd
import pytest

from core.strategies import cash_carry as cc
from core.strategies import common as cm
from core.strategies import roll as rl


def _dev(values, spot=1000.0, expiry=date(2026, 3, 20)):
    idx = pd.date_range("2026-03-02", periods=len(values), freq="B")
    return pd.DataFrame(
        {
            "dev": values,
            "dev_bps": [v / spot * 1e4 for v in values],
            "spot": spot,
            "expiry": expiry,
        },
        index=idx,
    )


def test_trade_pnl_points():
    """Rich 2.0 -> 0.1 with 0.2 cost: 1.7. Cheap -2.0 -> -0.1 with 0.2 cost: 1.7."""
    assert cc.trade_pnl_points(2.0, 0.1, 0.2) == pytest.approx(1.7)
    assert cc.trade_pnl_points(-2.0, -0.1, 0.2) == pytest.approx(1.7)


def test_arb_backtest_single_rich_trade():
    """Spot 1,000; entry threshold 15 bps = 1.5 pts, exit 5 bps = 0.5 pts. Deviations 0, 0.4, 2.0, 1.0, 0.1, 0.
    Enter at 2.0, exit at 0.1: gross 1.9 pts. Cost 2 bps = 0.2 pts, slippage 1 bp each way = 0.2 pts.
    10 contracts x 50: gross 950, costs 100, slippage 100, net 750."""
    r = cc.arb_backtest(_dev([0, 0.4, 2.0, 1.0, 0.1, 0]), 15, 5, 2, 1, 10, 50)
    assert len(r.trades) == 1
    assert r.gross == pytest.approx(950)
    assert r.costs == pytest.approx(100)
    assert r.slippage == pytest.approx(100)
    assert r.net == pytest.approx(750)


def test_arb_backtest_reverse_and_no_trade():
    """A cheap deviation of -2.0 converging to -0.1 earns the same 1.9 points; small deviations never trigger."""
    r = cc.arb_backtest(_dev([0, -2.0, -1.0, -0.1, 0]), 15, 5, 0, 0, 1, 1)
    assert r.trades.side.iloc[0] == "reverse"
    assert r.gross == pytest.approx(1.9)
    assert len(cc.arb_backtest(_dev([0, 0.5, 0.4, 0.3]), 15, 5, 0).trades) == 0


def test_arb_backtest_closes_on_expiry_change_and_last_day():
    """A position open when the expiry changes exits at the previous day's deviation; one open on the last day exits there."""
    d = _dev([2.0, 2.0, 1.5, 1.5])
    d["expiry"] = [date(2026, 3, 20)] * 2 + [date(2026, 6, 19)] * 2
    r = cc.arb_backtest(d, 15, 5, 0)
    assert len(r.trades) >= 1
    assert r.trades.exit.iloc[0] == d.index[1]


def test_trade_stats_and_drawdown():
    """PnL [3, -1, 2]: total 4, mean 1.33, hit rate 2/3, worst -1. Cumulative [3, 2, 4] has drawdown 1."""
    s = cm.trade_stats(pd.Series([3.0, -1.0, 2.0]))
    assert s["total"] == 4 and s["worst"] == -1 and s["hit_rate"] == pytest.approx(2 / 3)
    assert cm.trade_stats(pd.Series([], dtype=float))["trades"] == 0
    assert cm.max_drawdown(pd.Series([3.0, 2.0, 4.0])) == 1.0
    assert cm.max_drawdown(pd.Series([], dtype=float)) == 0.0


def test_roll_helpers():
    """Near 5,000, far 5,030: a long pays 30 points; 10 contracts x 50 = -15,000. Per-roll cost of 400 bps pa over 4 rolls: 100."""
    assert rl.roll_cost_points(5000, 5030) == 30
    assert rl.roll_pnl(10, 50, 5000, 5030) == -15_000
    assert rl.annual_roll_drag(400, 4) == 100


def test_world_series(world):
    """On the synthetic world the front-future deviation series is well-formed and the rolls are tabulated."""
    dev = cm.futures_deviation_series(world.market, "D1 US 30")
    assert len(dev) > 300 and {"dev", "dev_bps", "fair"} <= set(dev.columns)
    assert dev.dev_bps.abs().max() < 200
    ev = rl.roll_events(world.market, "D1 US 30")
    assert len(ev) >= 8 and (ev.f_far > 0).all()
    r = cc.arb_backtest(dev, 10, 3, 3, 0.5)
    assert r.net == pytest.approx(r.gross - r.costs - r.slippage)

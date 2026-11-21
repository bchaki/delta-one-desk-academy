"""Book, ledger, PnL explain and seeded breaks: reconciliation to the cent."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from core.booking.models import CashEquityTrade, EquitySwapTrade
from core.data.book import generate_book
from core.data.world import build_world
from core.pnl import attribution as attr
from core.pnl.explain import explain_series, pnl_explain
from core.pnl.ledger import COMPONENTS, compute_ledger, true_book
from core.types import Direction, money


def test_book_shape(world):
    b = world.book
    assert len(b.clients) == 15
    prods = {t.product for t in b.trades}
    assert {
        "equity_swap",
        "future",
        "cash_equity",
        "etf",
        "sbl",
        "repo",
        "dividend_future",
    } <= prods
    assert len(b.swaps()) >= 45
    assert {e.kind for e in b.events} >= {
        "reset",
        "dividend",
        "termination",
        "partial_unwind",
        "amendment",
    }
    assert {x.kind for x in b.breaks} == {
        "missed_dividend",
        "wrong_fixing",
        "wrong_spread",
        "wrong_entity",
        "stale_price",
    }


def test_book_deterministic():
    a, b = generate_book(7), generate_book(7)
    assert [t.model_dump() for t in a.trades] == [t.model_dump() for t in b.trades]
    c = generate_book(8)
    assert [t.trade_id for t in a.trades] != [t.trade_id for t in c.trades] or a.trades[
        0
    ] != c.trades[0]


def test_trade_ids_unique(world):
    ids = [t.trade_id for t in world.book.trades]
    assert len(ids) == len(set(ids))


def test_every_swap_has_hedge(world):
    b = world.book
    linked = {t.linked_trade_id for t in b.trades if t.linked_trade_id}
    assert all(s.trade_id in linked for s in b.swaps() if s.trade_id[0] == "S")


def test_hedged_swaps_net_price_to_zero(world):
    """Swap price+fx PnL and its hedges' price+fx PnL cancel (the desk is flat delta on a swap).

    Hand calc for one day: client long 1,000 sh, P 100 -> 101. Desk swap leg = -1,000 x 1 = -1,000;
    hedge long 1,000 sh = +1,000; net 0. Execution slippage is a separate component.
    """
    led = world.clean
    b = world.book
    checked = 0
    for s in b.swaps():
        if not s.underlying.startswith("stock:"):
            continue
        ids = [s.trade_id] + [
            t.trade_id
            for t in b.trades
            if t.linked_trade_id == s.trade_id and isinstance(t, CashEquityTrade)
        ]
        net = sum(led.by_trade[i].get(c, np.zeros(1)).sum() for i in ids for c in ("price", "fx"))
        gross = sum(np.abs(led.by_trade[s.trade_id].get("price", np.zeros(1))).sum() for _ in [0])
        assert abs(net) < 1e-6 * max(gross, 1.0) + 1.0, s.trade_id
        checked += 1
    assert checked > 30


def test_ledger_totals_consistent(world):
    led = world.booked
    by_trade_total = sum(a.sum() for comps in led.by_trade.values() for a in comps.values())
    assert by_trade_total == pytest.approx(led.total().sum(), rel=1e-9)
    frame = led.frame()
    assert frame.usd.sum() == pytest.approx(led.total().sum(), rel=1e-9)
    assert set(frame.component) <= set(COMPONENTS)


def test_missed_dividend_impact_by_hand(world):
    """Impact = -(hedge qty) x (dividend per share) x FX on the ex date (cash the booking never saw)."""
    b = next(x for x in world.book.breaks if x.kind == "missed_dividend")
    t = world.book.trade(b.trade_id)
    ccy = world.universe.stocks[t.ticker].ccy
    expected = -t.qty * b.detail["amount_per_share"] * world.market.fx_usd_per(ccy, b.date)
    assert b.pnl_impact == pytest.approx(expected, abs=0.01)
    assert b.pnl_impact < 0


def test_wrong_spread_impact_sign_and_size(world):
    b = next(x for x in world.book.breaks if x.kind == "wrong_spread")
    assert b.pnl_impact < 0  # booked 15 bps too low on a long swap: desk under-accrues
    s = world.book.trade(b.trade_id)
    years = (world.market.days[-1] - s.trade_date).days / 365
    ub = s.shares * s.initial_price * 15e-4 * years * world.market.fx_usd_per(s.ccy, s.trade_date)
    assert abs(b.pnl_impact) < 1.6 * ub  # same order as 15 bps x notional x years


def test_wrong_entity_has_no_pnl_but_fails_validation(world):
    from core.booking.validation import validate_swap

    b = next(x for x in world.book.breaks if x.kind == "wrong_entity")
    assert b.pnl_impact == 0.0
    s = world.book.trade(b.trade_id)
    issues = validate_swap(s, world.book.client_of(s))
    assert any(i.field == "legal_entity" and i.severity == "error" for i in issues)
    fixed = true_book(world.book).trade(b.trade_id)
    assert not [
        i for i in validate_swap(fixed, world.book.client_of(fixed)) if i.field == "legal_entity"
    ]


def test_stale_price_reverses_next_day(world):
    b = next(x for x in world.book.breaks if x.kind == "stale_price")
    i = world.market.days.index(b.date)
    booked, clean = world.booked.total(), world.clean.total()
    d0, d1 = booked[i] - clean[i], booked[i + 1] - clean[i + 1]
    # other breaks (daily carry on the wrong spread / fixing) add a few dollars on the same day
    assert d0 == pytest.approx(b.pnl_impact, rel=1e-3)
    assert d1 == pytest.approx(-d0, rel=1e-3)


def test_unexplained_equals_sum_of_break_impacts(world):
    """Over the full history, Unexplained = missed dividend + wrong fixing + wrong spread (stale nets to 0)."""
    m = world.market
    e = pnl_explain(world.booked, world.clean, m.days[0] - timedelta(days=1), m.days[-1])
    expected = sum(b.pnl_impact for b in world.book.breaks if b.kind != "stale_price")
    assert e.unexplained == pytest.approx(expected, abs=0.1)
    assert e.reconciles()


def test_explain_components_are_cents_and_reconcile(world):
    m = world.market
    for start, end in [
        (m.days[-30], m.days[-1]),
        (m.days[100], m.days[300]),
        (m.days[-2], m.days[-1]),
    ]:
        e = pnl_explain(world.booked, world.clean, start, end)
        assert all(v == money(v) for v in e.components.values())
        assert e.reconciles()
        assert money(sum(e.components.values()) + e.unexplained) == pytest.approx(
            e.total, abs=0.006
        )


def test_explain_by_book_and_series(world):
    m = world.market
    e = pnl_explain(world.booked, world.clean, m.days[-60], m.days[-1], by_book="Equity Swaps")
    assert e.reconciles()
    s = explain_series(world.booked, world.clean)
    assert len(s) == len(m.days)
    assert np.allclose(s[list(COMPONENTS) + ["unexplained"]].sum(axis=1), s.total, atol=0.011)


def test_no_breaks_no_unexplained(world):
    m = world.market
    clean_b = compute_ledger(true_book(world.book), m, apply_breaks=False)
    e = pnl_explain(clean_b, world.clean, m.days[0] - timedelta(days=1), m.days[-1])
    assert e.unexplained == 0.0


def test_attribution_sums(world):
    m = world.market
    s, e = m.days[0] - timedelta(days=1), m.days[-1]
    total = world.booked.total().sum()
    bb = attr.by_book(world.booked, s, e)
    assert bb["total"].sum() == pytest.approx(total, rel=1e-9)
    bt = attr.by_trade(world.booked, s, e)
    assert bt["total"].sum() == pytest.approx(total, rel=1e-9)
    assert (
        len(attr.by_ticker(world.booked, s, e)) > 20
    )  # futures and dividend futures carry no ticker
    best, worst = attr.top_movers(world.booked, s, e, 3)
    assert len(best) == 3 and best.iloc[0] >= worst.iloc[0]
    assert len(attr.by_client(world.booked, world.book, s, e)) > 5


def test_world_cache_and_clamp():
    w1, w2 = build_world(7), build_world(7, date(2100, 1, 1))
    assert w1.market is w2.market and w1.as_of == w2.as_of == w1.market.days[-1]
    early = build_world(7, date(2025, 1, 4))
    assert early.as_of == date(2024, 12, 30)  # 31 Dec-3 Jan are holidays on at least one calendar
    assert w1.universe is w1.market.universe


def test_directions_and_pass_through(world):
    swaps = world.book.swaps()
    assert {s.direction for s in swaps} == {Direction.LONG, Direction.SHORT}
    assert all(0 < s.pass_through <= 1 for s in swaps)
    assert all(isinstance(s, EquitySwapTrade) for s in swaps)
    assert isinstance(world.book.trade(swaps[0].trade_id), EquitySwapTrade)
    assert pd.Timestamp(swaps[0].trade_date) in world.market.prices.index

"""Booking: models, validation, lifecycle, cash flows."""

from datetime import date

import numpy as np
import pytest

from core.booking import cashflows as cf
from core.booking import lifecycle as lc
from core.booking.models import (
    Amendment,
    CAAdjustment,
    CSAModel,
    PartialUnwind,
    Termination,
)
from core.booking.validation import parse_swap_ticket, validate_future
from core.data.accessors import (
    day_index,
    price_array,
    split_underlying,
    underlying_ccy,
    underlying_dividends,
    underlying_price,
    underlying_series,
)
from core.types import Currency, Direction


def _swap_dict(world, **over):
    c = world.book.clients["C08"]  # US asset manager
    tick = next(t for t, s in world.universe.stocks.items() if s.ccy is Currency.USD)
    d = world.market.days[300]
    base = dict(
        trade_id="T1",
        trade_date=d,
        effective_date=d,
        book="Equity Swaps",
        counterparty_id=c.id,
        legal_entity=c.legal_entity,
        underlying=f"stock:{tick}",
        direction=Direction.LONG,
        shares=1000.0,
        initial_price=100.0,
        spread_bps=35.0,
        benchmark="SOFR",
        reset_months=1,
        pass_through=1.0,
        isda_ref="ISDA-X",
        ccy="USD",
        day_count_basis=360,
    )
    base.update(over)
    return base, c


def test_valid_ticket_has_no_errors(world):
    d, c = _swap_dict(world)
    trade, issues = parse_swap_ticket(d, c)
    assert trade is not None and not [i for i in issues if i.severity == "error"]


@pytest.mark.parametrize(
    ("over", "field"),
    [
        ({"spread_bps": 450.0}, "spread_bps"),
        ({"shares": -5.0}, "shares"),
        ({"pass_through": 1.2}, "pass_through"),
        ({"reset_months": 2}, "reset_months"),
        ({"isda_ref": " "}, "isda_ref"),
        ({"benchmark": "ESTR"}, "benchmark"),
        ({"legal_entity": "Someone Else Ltd"}, "legal_entity"),
    ],
)
def test_ticket_errors(world, over, field):
    d, c = _swap_dict(world, **over)
    _, issues = parse_swap_ticket(d, c)
    assert any(i.field == field and i.severity == "error" for i in issues)


def test_ticket_weekend_and_dates(world):
    d, c = _swap_dict(world, effective_date=date(2025, 6, 7))
    _, issues = parse_swap_ticket(d, c)
    assert any(i.field == "effective_date" for i in issues)
    d, c = _swap_dict(world, effective_date=date(2020, 1, 6))
    _, issues = parse_swap_ticket(d, c)
    assert any("before the trade date" in i.message for i in issues)


def test_ticket_client_rules(world):
    d, _ = _swap_dict(world)
    _, issues = parse_swap_ticket(d, None)
    assert any(i.field == "counterparty_id" for i in issues)
    nocsa = world.book.clients["C08"].model_copy(update={"csa": CSAModel(in_force=False)})
    _, issues = parse_swap_ticket(d, nocsa)
    assert any(i.field == "csa" for i in issues)
    nonus = world.book.clients["C09"]
    d2, _ = _swap_dict(world, counterparty_id=nonus.id, legal_entity=nonus.legal_entity)
    _, issues = parse_swap_ticket(d2, nonus)
    assert any(i.field == "flag_871m" and i.severity == "error" for i in issues)
    d3, _ = _swap_dict(
        world, counterparty_id=nonus.id, legal_entity=nonus.legal_entity, flag_871m=True
    )
    assert not [i for i in parse_swap_ticket(d3, nonus)[1] if i.field == "flag_871m"]
    d4, c = _swap_dict(world, flag_871m=True)
    assert any(i.severity == "warning" for i in parse_swap_ticket(d4, c)[1])


def test_short_below_borrow_warns(world):
    d, c = _swap_dict(world, direction=Direction.SHORT, borrow_bps=80.0, spread_bps=50.0)
    _, issues = parse_swap_ticket(d, c)
    assert any(i.severity == "warning" and i.field == "spread_bps" for i in issues)


def test_pydantic_type_error_becomes_issue(world):
    d, c = _swap_dict(world, shares="many")
    trade, issues = parse_swap_ticket(d, c)
    assert trade is None and issues[0].severity == "error"


def test_validate_future(world):
    t = next(t for t in world.book.trades if t.product == "future")
    assert validate_future(t) == []
    bad = t.model_copy(update={"qty": 0, "price": -1.0, "expiry": date(2020, 1, 1)})
    assert len(validate_future(bad)) == 3


def test_csa_terms_roundtrip():
    terms = CSAModel(threshold_cpty=1e6, mta=2.5e5, ia_cpty=5e5).terms()
    assert (
        terms.threshold_cpty == 1e6 and terms.mta == 2.5e5 and terms.independent_amount_cpty == 5e5
    )


def test_reset_dates_and_next_trading_day():
    ds = lc.reset_dates(date(2024, 1, 15), date(2024, 5, 1), 1)
    assert ds[0] == date(2024, 2, 15) and len(ds) == 3
    assert lc.next_trading_day(date(2024, 3, 30)) == date(
        2024, 4, 2
    )  # Easter weekend then Easter Monday
    assert lc.reset_dates(date(2026, 6, 1), date(2030, 1, 1), 3)[-1] <= date(2026, 11, 20)


def test_state_and_series(world):
    s = next(
        s
        for s in world.book.swaps()
        if s.direction is Direction.LONG and s.underlying.startswith("stock")
    )
    d0 = world.market.days.index(s.trade_date)
    day = world.market.days[d0 + 10]
    evs = [
        PartialUnwind(trade_id=s.trade_id, date=day, shares_unwound=s.shares / 4, price=1.0),
        Amendment(
            trade_id=s.trade_id, date=day, field="spread_bps", old_value=s.spread_bps, new_value=1.0
        ),
        CAAdjustment(
            trade_id=s.trade_id, date=world.market.days[d0 + 12], qty_factor=2.0, price_factor=0.5
        ),
    ]
    st = lc.process_events(s, evs)
    assert (
        st.shares == pytest.approx(s.shares * 0.75 * 2)
        and st.spread_bps == 1.0
        and st.status == "live"
    )
    series = lc.shares_series(s, evs, world.market.days)
    assert series[d0] == 0 and series[d0 + 1] == s.shares
    assert series[d0 + 11] == pytest.approx(s.shares * 0.75) and series[d0 + 13] == pytest.approx(
        s.shares * 1.5
    )
    spr = lc.spread_series(s, evs, world.market.days)
    assert spr[d0 + 10] == s.spread_bps and spr[d0 + 11] == 1.0
    term = lc.process_events(s, [Termination(trade_id=s.trade_id, date=day, price=1.0)])
    assert term.status == "terminated" and term.shares == 0
    assert lc.initial_state(s).shares == s.shares
    assert lc.apply_event(lc.initial_state(s), evs[1]).spread_bps == 1.0


def test_cashflows_signs_and_periods(world):
    """A long swap whose stock rose: desk pays equity performance (negative), receives funding (positive)."""
    m = world.market
    for s in world.book.swaps():
        if (
            s.direction is not Direction.LONG
            or not s.underlying.startswith("stock")
            or s.status != "live"
        ):
            continue
        flows = cf.swap_cashflows(s, m, m.days[-1], world.book.events_for(s.trade_id))
        if len(flows) < 6:
            continue
        funding = [f for f in flows if f.type == "funding"]
        assert all(f.amount > 0 for f in funding)  # client pays R + s on a positive base
        perf = [f for f in flows if f.type == "equity_performance"]
        first = perf[0]
        up = underlying_price(m, s.underlying, first.date) > s.initial_price
        assert (first.amount < 0) == up
        assert first.payer.value in {"CLIENT", "DESK"} and first.ccy == s.ccy
        return
    pytest.fail("no suitable swap")


def test_cashflows_stop_at_termination_and_unwind(world):
    m = world.market
    term = next(e for e in world.book.events if e.kind == "termination")
    s = world.book.trade(term.trade_id)
    flows = cf.swap_cashflows(s, m, m.days[-1], world.book.events_for(s.trade_id))
    assert flows and max(f.date for f in flows) <= term.date
    unwound = next(e for e in world.book.events if e.kind == "partial_unwind")
    s2 = world.book.trade(unwound.trade_id)
    flows2 = cf.swap_cashflows(s2, m, m.days[-1], world.book.events_for(s2.trade_id))
    assert any(f.date == unwound.date for f in flows2)
    assert cf.terms_of(s2).shares == s2.shares


def test_accessors(world):
    m = world.market
    kind, name = split_underlying("index:D1 US 30")
    assert (kind, name) == ("index", "D1 US 30")
    with pytest.raises(ValueError):
        split_underlying("bond:X")
    assert underlying_series(m, "index:D1 US 30").iloc[0] == 1000.0
    assert underlying_ccy(m, "index:D1 Europe 20") is Currency.EUR
    assert underlying_ccy(m, f"stock:{next(iter(m.universe.stocks))}") in Currency
    assert underlying_dividends(m, "index:D1 US 30")
    t = next(
        t
        for t, s in m.universe.stocks.items()
        if s.dividend.annual_yield > 0.02 and s.listed_from is None
    )
    divs = underlying_dividends(m, f"stock:{t}")
    assert divs and all(d.amount > 0 for d in divs)
    assert day_index(m)[m.days[5]] == 5
    assert np.isfinite(price_array(m, t)[0])

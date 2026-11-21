"""Cash-flow schedule for a booked swap, built from the pricing engine and the synthetic market."""

from __future__ import annotations

from datetime import date

from core.booking.lifecycle import reset_dates
from core.booking.models import (
    Cashflow,
    EquitySwapTrade,
    LifecycleEvent,
    PartialUnwind,
    Termination,
)
from core.conventions import CalendarName
from core.data.accessors import underlying_dividends, underlying_price
from core.data.market import CAL_BY_BENCH, MarketHistory
from core.pricing import swaps as sw
from core.types import Side


def terms_of(trade: EquitySwapTrade) -> sw.SwapTerms:
    return sw.SwapTerms(
        direction=trade.direction,
        shares=trade.shares,
        initial_price=trade.initial_price,
        spread_bps=trade.spread_bps,
        benchmark_basis=trade.day_count_basis,
        pass_through=trade.pass_through,
        notional_reset=trade.notional_reset,
        calendar=CAL_BY_BENCH.get(trade.benchmark, CalendarName.US),
    )


def swap_cashflows(
    trade: EquitySwapTrade,
    mkt: MarketHistory,
    as_of: date,
    events: list[LifecycleEvent] | None = None,
) -> list[Cashflow]:
    """Client-perspective cash flows converted to desk-perspective ``Cashflow`` rows up to ``as_of``.

    Splits periods at partial unwinds and stops at termination. Rows: equity performance,
    dividend and funding per period; ``amount`` is positive when the DESK receives. Periods that end
    after ``as_of`` are not included (use ``swaps.mark_to_market`` for the accrued stub).
    """
    evs = sorted((e for e in (events or []) if e.trade_id == trade.trade_id), key=lambda e: e.date)
    end = min(as_of, mkt.days[-1])
    term = next((e.date for e in evs if isinstance(e, Termination)), None)
    stop = min(end, term) if term else end
    boundaries = [trade.trade_date] + reset_dates(trade.trade_date, stop, trade.reset_months)
    boundaries += [e.date for e in evs if isinstance(e, PartialUnwind) and e.date <= stop]
    if term and term <= end:
        boundaries.append(term)
    boundaries = sorted(set(boundaries))
    terms = terms_of(trade)
    fixings = mkt.fixings_dict(trade.benchmark)
    divs = underlying_dividends(mkt, trade.underlying)
    shares = trade.shares
    flows: list[Cashflow] = []
    for a, b in zip(boundaries[:-1], boundaries[1:], strict=True):
        for e in evs:
            if isinstance(e, PartialUnwind) and e.date == a:
                shares -= e.shares_unwound
        if shares <= 0:
            break
        s0 = (
            trade.initial_price
            if a == trade.trade_date
            else underlying_price(mkt, trade.underlying, a)
        )
        s1 = underlying_price(mkt, trade.underlying, b)
        p = sw.period_cashflows(terms, a, b, s0, s1, fixings, divs, shares=shares)
        status = "settled"
        for typ, amt in (
            ("equity_performance", p.price_cf),
            ("dividend", p.dividend_cf),
            ("funding", p.funding_cf),
        ):
            flows.append(
                Cashflow(
                    date=b,
                    trade_id=trade.trade_id,
                    type=typ,
                    amount=-amt,
                    ccy=trade.ccy,
                    payer=Side.CLIENT if -amt > 0 else Side.DESK,
                    status=status,
                )
            )
    return flows

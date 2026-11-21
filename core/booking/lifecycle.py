"""Swap lifecycle: reset schedule, event application and share-count series."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, replace
from datetime import date

import numpy as np

from core.booking.models import (
    Amendment,
    CAAdjustment,
    EquitySwapTrade,
    LifecycleEvent,
    PartialUnwind,
    Termination,
)
from core.conventions import add_months
from core.data.market import trading_days


def next_trading_day(d: date) -> date:
    """First synthetic trading day on or after ``d`` (clamped to the history)."""
    days = trading_days()
    i = bisect_left(days, d)
    return days[min(i, len(days) - 1)]


def reset_dates(start: date, end: date, months: int) -> list[date]:
    """Reset dates after ``start`` up to ``end``: start + k x months, rolled following to a trading day."""
    out: list[date] = []
    k = 1
    while True:
        target = add_months(start, k * months)
        d = next_trading_day(target)
        if d > end or target > trading_days()[-1]:
            break
        if not out or d != out[-1]:
            out.append(d)
        k += 1
    return out


@dataclass(frozen=True)
class SwapState:
    shares: float
    status: str  # live / terminated
    spread_bps: float
    last_event: date


def initial_state(trade: EquitySwapTrade) -> SwapState:
    return SwapState(trade.shares, "live", trade.spread_bps, trade.trade_date)


def apply_event(state: SwapState, ev: LifecycleEvent) -> SwapState:
    """Apply one lifecycle event to the state of a swap."""
    if isinstance(ev, PartialUnwind):
        return replace(state, shares=state.shares - ev.shares_unwound, last_event=ev.date)
    if isinstance(ev, Termination):
        return replace(state, shares=0.0, status="terminated", last_event=ev.date)
    if isinstance(ev, CAAdjustment):
        return replace(state, shares=state.shares * ev.qty_factor, last_event=ev.date)
    if isinstance(ev, Amendment) and ev.field == "spread_bps":
        return replace(state, spread_bps=ev.new_value, last_event=ev.date)
    return replace(state, last_event=ev.date)


def process_events(trade: EquitySwapTrade, events: list[LifecycleEvent]) -> SwapState:
    """State after all of a trade's events in date order."""
    state = initial_state(trade)
    for ev in sorted((e for e in events if e.trade_id == trade.trade_id), key=lambda e: e.date):
        state = apply_event(state, ev)
    return state


def shares_series(
    trade: EquitySwapTrade, events: list[LifecycleEvent], days: tuple[date, ...]
) -> np.ndarray:
    """Share count at the START of each trading day (events dated before the day have applied)."""
    out = np.zeros(len(days))
    evs = sorted((e for e in events if e.trade_id == trade.trade_id), key=lambda e: e.date)
    shares = trade.shares
    k = 0
    for i, d in enumerate(days):
        while k < len(evs) and evs[k].date < d:
            e = evs[k]
            if isinstance(e, PartialUnwind):
                shares -= e.shares_unwound
            elif isinstance(e, Termination):
                shares = 0.0
            elif isinstance(e, CAAdjustment):
                shares *= e.qty_factor
            k += 1
        out[i] = shares if d > trade.trade_date else 0.0
    return out


def spread_series(
    trade: EquitySwapTrade, events: list[LifecycleEvent], days: tuple[date, ...]
) -> np.ndarray:
    """Spread (bps) in force at the start of each trading day (amendments apply from the next day)."""
    out = np.full(len(days), trade.spread_bps)
    for e in sorted((e for e in events if e.trade_id == trade.trade_id), key=lambda e: e.date):
        if isinstance(e, Amendment) and e.field == "spread_bps":
            out[[i for i, d in enumerate(days) if d > e.date]] = e.new_value
    return out

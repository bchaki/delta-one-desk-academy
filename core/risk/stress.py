"""Scenario stress: apply config/scenarios.yaml shocks to the desk's positions (USD, desk side).

Shocks: equity % by region on stock/index/ETF/ADR exposure; FX % on non-USD translation (quoted
pair; JPY uses USDJPY inverted); dividend % on the 12-month dividend exposure; borrow fee change
on live borrows for ONE month of carry; single-name % on the squeezed ticker. Rates are not shocked
because the book is funding-neutral by construction (see Rates module for the exceptions).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from core import config
from core.booking.models import SblTrade
from core.config import Scenario
from core.data.book import Book
from core.data.market import MarketHistory
from core.risk.sensitivities import snapshot
from core.types import Currency


@dataclass(frozen=True)
class StressResult:
    scenario: str
    total: float
    by_factor: dict[str, float]
    by_leg: dict[str, float]  # hedges (cash+futures) vs client swaps


def _fx_shock(ccy: str, fx_pct: dict[str, float]) -> float:
    c = Currency(ccy)
    if c is Currency.EUR:
        return fx_pct.get("EURUSD", 0.0) / 100
    if c is Currency.GBP:
        return fx_pct.get("GBPUSD", 0.0) / 100
    if c is Currency.JPY:
        x = fx_pct.get("USDJPY", 0.0) / 100
        return 1 / (1 + x) - 1
    return 0.0


def apply_scenario(book: Book, m: MarketHistory, d: date, scenario: str | Scenario) -> StressResult:
    """Revalue the desk under a scenario id or a ``Scenario`` object. ``sum(by_factor) == total``."""
    sc = config.scenarios().scenarios[scenario] if isinstance(scenario, str) else scenario
    snap = snapshot(book, m, d)
    eq = fx = div = single = 0.0
    legs = {"hedges": 0.0, "client_swaps": 0.0}
    for _, r in snap.iterrows():
        shock = sc.equity_pct.get(r.region, 0.0) / 100
        hedge, swap = r.cash_usd + r.fut_usd, r.swap_usd
        eq += (hedge + swap) * shock
        legs["hedges"] += hedge * shock
        legs["client_swaps"] += swap * shock
        s_fx = _fx_shock(r.ccy, sc.fx_pct)
        fx += r.delta_usd * (1 + shock) * s_fx
        if r.kind == "stock" and r.key.split(":")[1] == m.squeeze_ticker:
            single += r.delta_usd * sc.single_name_pct / 100
        if r.kind == "stock":
            st = m.universe.stocks[r.key.split(":")[1]]
            div += r.delta_usd * st.dividend.annual_yield * sc.div_pct.get(r.region, 0.0) / 100
    borrow = 0.0
    for t in book.trades:
        if isinstance(t, SblTrade) and t.trade_date <= d and (t.end_date is None or t.end_date > d):
            tier = m.universe.stocks[t.ticker].borrow.tier
            notional = (
                t.shares
                * float(m.prices[t.ticker].ffill().at[pd.Timestamp(d)])
                * m.fx_usd_per(t.ccy, d)
            )
            borrow += (
                (-1 if t.side == "borrow" else 1)
                * notional
                * sc.borrow_bps.get(tier, 0.0)
                / 1e4
                / 12
            )
    by = {"equity": eq, "fx": fx, "dividends": div, "borrow": borrow, "single_name": single}
    return StressResult(sc.name, sum(by.values()), by, legs)


def all_scenarios(book: Book, m: MarketHistory, d: date) -> pd.DataFrame:
    rows = []
    for sid in config.scenarios().scenarios:
        r = apply_scenario(book, m, d, sid)
        rows.append({"scenario": r.scenario, "total": r.total, **r.by_factor})
    return pd.DataFrame(rows).set_index("scenario")

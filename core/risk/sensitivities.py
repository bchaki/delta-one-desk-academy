"""Positions snapshot and first-order sensitivities (USD, desk side, positive = long to the desk).

Exposure sources per key: ``cash`` (hedge and arbitrage inventory), ``swap`` (the desk's side of
client swaps: short what the client is long) and ``fut`` (index futures). A fully hedged swap shows
net delta ~ 0 and large gross.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from core.booking.lifecycle import process_events
from core.booking.models import (
    CashEquityTrade,
    DividendFutureTrade,
    EtfTrade,
    FutureTrade,
    SblTrade,
    Termination,
)
from core.data.book import Book
from core.data.market import MarketHistory
from core.types import Currency, Direction

COLS = [
    "key",
    "kind",
    "region",
    "sector",
    "ccy",
    "qty",
    "cash_usd",
    "swap_usd",
    "fut_usd",
    "delta_usd",
    "beta",
    "beta_delta_usd",
]


def _px(m: MarketHistory, series: pd.Series, d: date) -> float:
    return float(series.ffill().at[pd.Timestamp(d)])


def swap_shares_at(book: Book, swap, d: date) -> float:
    """Shares outstanding on a swap at the close of ``d`` (zero before it starts or after it ends)."""
    if swap.trade_date > d:
        return 0.0
    evs = [e for e in book.events_for(swap.trade_id) if e.date <= d]
    if any(isinstance(e, Termination) for e in evs):
        return 0.0
    return process_events(swap, evs).shares


def snapshot(book: Book, m: MarketHistory, d: date) -> pd.DataFrame:
    """Net exposure by underlying at the close of ``d``."""
    u = m.universe
    cash: dict[str, float] = {}
    for t in book.trades:
        if isinstance(t, CashEquityTrade | EtfTrade) and t.trade_date <= d:
            cash[t.ticker] = cash.get(t.ticker, 0.0) + t.qty
    swap_q: dict[str, float] = {}
    for s in book.swaps():
        sh = swap_shares_at(book, s, d)
        if sh:
            sign = 1 if s.direction is Direction.LONG else -1
            swap_q[s.underlying] = swap_q.get(s.underlying, 0.0) - sign * sh
    fut_q: dict[tuple[str, date], float] = {}
    for t in book.trades:
        if isinstance(t, FutureTrade) and t.trade_date <= d < t.expiry:
            fut_q[(t.index, t.expiry)] = fut_q.get((t.index, t.expiry), 0.0) + t.qty

    rows: dict[str, dict] = {}

    def row(key, kind, region, sector, ccy, beta):
        return rows.setdefault(
            key,
            dict(
                key=key,
                kind=kind,
                region=region,
                sector=sector,
                ccy=ccy.value,
                qty=0.0,
                cash_usd=0.0,
                swap_usd=0.0,
                fut_usd=0.0,
                beta=beta,
            ),
        )

    for tick, q in cash.items():
        if abs(q) < 1e-9:
            continue
        if tick in u.stocks:
            st = u.stocks[tick]
            r = row(f"stock:{tick}", "stock", st.region, st.sector, st.ccy, st.beta)
            r["cash_usd"] += q * _px(m, m.prices[tick], d) * m.fx_usd_per(st.ccy, d)
            r["qty"] += q
        elif tick in u.adrs:
            a = u.adrs[tick]
            st = u.stocks[a.underlying]
            r = row(f"adr:{tick}", "adr", st.region, st.sector, Currency.USD, st.beta)
            r["cash_usd"] += q * _px(m, m.adr_prices[tick], d)
            r["qty"] += q
        else:
            e = u.etfs[tick]
            idx = u.indices[e.index]
            reg = "US" if "US" in idx.name else "EU"
            r = row(f"etf:{tick}", "etf", reg, "Index", idx.ccy, 1.0)
            r["cash_usd"] += q * _px(m, m.etf_prices[tick], d) * m.fx_usd_per(idx.ccy, d)
            r["qty"] += q
    for und, q in swap_q.items():
        kind, _, name = und.partition(":")
        if kind == "stock":
            st = u.stocks[name]
            r = row(und, "stock", st.region, st.sector, st.ccy, st.beta)
            r["swap_usd"] += q * _px(m, m.prices[name], d) * m.fx_usd_per(st.ccy, d)
        else:
            idx = u.indices[name]
            r = row(und, "index", "US" if "US" in name else "EU", "Index", idx.ccy, 1.0)
            r["swap_usd"] += q * _px(m, m.index_level[name], d) * m.fx_usd_per(idx.ccy, d)
        r["qty"] += q
    for (name, exp), q in fut_q.items():
        idx = u.indices[name]
        mult = next(
            t.multiplier for t in book.trades if isinstance(t, FutureTrade) and t.index == name
        )
        r = row(f"index:{name}", "index", "US" if "US" in name else "EU", "Index", idx.ccy, 1.0)
        r["fut_usd"] += (
            q * mult * float(m.futures[(name, exp)].at[pd.Timestamp(d)]) * m.fx_usd_per(idx.ccy, d)
        )
        r["qty"] += q
    df = pd.DataFrame(list(rows.values()))
    if df.empty:
        return pd.DataFrame(columns=COLS)
    df["delta_usd"] = df.cash_usd + df.swap_usd + df.fut_usd
    df["beta_delta_usd"] = df.delta_usd * df.beta
    return df[COLS].sort_values("key").reset_index(drop=True)


def sensitivities(book: Book, m: MarketHistory, d: date) -> dict[str, float | dict[str, float]]:
    """First-order sensitivities at the close of ``d`` (USD unless stated).

    * ``net_delta`` / ``gross`` / ``beta_delta``: sums over the snapshot (gross = sum of |exposure| of
      hedge inventory and futures).
    * ``fx_delta``: USD change for a +1% move of each currency against USD.
    * ``ftp_plus_1bp_annual``: annual PnL change for +1 bp on the funding transfer price, on the
      long inventory funded at FTP.
    * ``dividend_minus10pct``: PnL if forecast dividends on the net stock position fall 10%
      (12-month horizon).
    * ``borrow_plus_100bp_annual``: annual PnL change if every live borrow and loan fee moves +100 bp.
    * ``divfut_per_point``: PnL per +1 index point on every dividend future.
    """
    snap = snapshot(book, m, d)
    out: dict = {}
    out["net_delta"] = float(snap.delta_usd.sum())
    out["gross"] = float((snap.cash_usd.abs() + snap.fut_usd.abs()).sum())
    out["beta_delta"] = float(snap.beta_delta_usd.sum())
    out["fx_delta"] = {c: float(g.delta_usd.sum()) * 0.01 for c, g in snap.groupby("ccy")}
    long_inv = float(snap.cash_usd.clip(lower=0).sum())
    out["ftp_plus_1bp_annual"] = -long_inv * 1e-4
    annual_div = 0.0
    for _, r in snap[snap.kind == "stock"].iterrows():
        st = m.universe.stocks[r.key.split(":")[1]]
        annual_div += r.delta_usd * st.dividend.annual_yield
    out["annual_dividend_exposure"] = annual_div
    out["dividend_minus10pct"] = -0.10 * annual_div
    borrow = 0.0
    for t in book.trades:
        if isinstance(t, SblTrade) and t.trade_date <= d and (t.end_date is None or t.end_date > d):
            notional = t.shares * _px(m, m.prices[t.ticker], d) * m.fx_usd_per(t.ccy, d)
            borrow += (-1 if t.side == "borrow" else 1) * notional * 0.01
    out["borrow_plus_100bp_annual"] = borrow
    pts = 0.0
    for t in book.trades:
        if isinstance(t, DividendFutureTrade) and t.trade_date <= d and t.year >= d.year:
            pts += t.units * m.fx_usd_per(t.ccy, d)
    out["divfut_per_point"] = pts
    return out


def usd_exposure_vector(snap: pd.DataFrame) -> pd.Series:
    """Delta by key in USD (the vector VaR and stress act on)."""
    return snap.set_index("key").delta_usd

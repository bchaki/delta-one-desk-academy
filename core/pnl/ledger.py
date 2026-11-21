"""Daily desk PnL ledger in USD, by component, book and trade.

Convention: positive = gain to the desk. All flows are from the DESK's side. Components:

* ``price``      position x (P_t - P_t-1) x FX_t on the previous day's end position
* ``fx``         position x P_t-1 x (FX_t - FX_t-1) (translation of local-currency inventory)
* ``execution``  traded qty x (close - execution price) on the trade date (slippage / spread paid)
* ``dividends``  gross dividends received on hedges less dividends passed through on client swaps
* ``funding``    swap funding legs less hedge funding (FTP on longs, short-proceeds rebate on shorts)
* ``sbl_repo``   borrow fees paid, loan fees received, repo funding saving
* ``fees``       sales credit paid on the trade date, amendment upfronts received
* ``div_derivs`` dividend futures / swaps mark-to-market

Simplifications (documented in the lesson): swaps accrue daily on the benchmark fixing of the
previous trading day (not compounded in arrears as in the legal confirmation); index swaps are
hedged with futures whose basis carries the financing, so no separate hedge funding leg is
accrued; dividends are gross (withholding tax is covered in the Dividends module).

Seeded breaks change the BOOKED ledger only; ``true_book`` reverts the spread and entity breaks
to give the clean ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from core import config
from core.booking.lifecycle import shares_series, spread_series
from core.booking.models import (
    Amendment,
    CashEquityTrade,
    DividendFutureTrade,
    EtfTrade,
    FutureTrade,
    RepoTrade,
    SblTrade,
    SeededBreak,
)
from core.data.accessors import underlying_dividends
from core.data.book import Book
from core.data.market import BASIS_BY_BENCH, MarketHistory
from core.pricing.swaps import ftp_component_bps
from core.types import Currency, Direction

COMPONENTS = ("price", "fx", "execution", "dividends", "funding", "sbl_repo", "fees", "div_derivs")


@dataclass
class Ledger:
    days: tuple[date, ...]
    by_book: dict[tuple[str, str], np.ndarray] = field(default_factory=dict)  # (book, component)
    by_trade: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)
    by_ticker: dict[str, np.ndarray] = field(default_factory=dict)

    def add(self, book: str, comp: str, trade_id: str, arr: np.ndarray, ticker: str | None = None):
        n = len(self.days)
        self.by_book.setdefault((book, comp), np.zeros(n))
        self.by_book[(book, comp)] = self.by_book[(book, comp)] + arr
        t = self.by_trade.setdefault(trade_id, {})
        t[comp] = t.get(comp, np.zeros(n)) + arr
        if ticker:
            self.by_ticker[ticker] = self.by_ticker.get(ticker, np.zeros(n)) + arr

    def frame(self) -> pd.DataFrame:
        """Long frame: date, book, component, usd."""
        rows = []
        idx = pd.DatetimeIndex(self.days)
        for (book, comp), arr in self.by_book.items():
            rows.append(pd.DataFrame({"date": idx, "book": book, "component": comp, "usd": arr}))
        return (
            pd.concat(rows, ignore_index=True)
            if rows
            else pd.DataFrame(columns=["date", "book", "component", "usd"])
        )

    def total(self) -> np.ndarray:
        n = len(self.days)
        return sum(self.by_book.values(), np.zeros(n))

    def component_total(self, comp: str) -> np.ndarray:
        n = len(self.days)
        return sum((a for (_, c), a in self.by_book.items() if c == comp), np.zeros(n))


def true_book(book: Book) -> Book:
    """Revert the booking errors (spread, legal entity) to the term-sheet values."""
    out = book
    for b in book.breaks:
        if b.kind == "wrong_entity":
            out = out.replace_trade(
                out.trade(b.trade_id).model_copy(
                    update={"legal_entity": str(b.detail["true_entity"])}
                )
            )
        elif b.kind == "wrong_spread":
            out = out.replace_trade(
                out.trade(b.trade_id).model_copy(
                    update={"spread_bps": float(b.detail["term_sheet_spread_bps"])}
                )
            )
    return out


def _fx_arr(m: MarketHistory, ccy: Currency) -> np.ndarray:
    return np.array([m.fx_usd_per(ccy, d) for d in m.days])


def _security_series(m: MarketHistory, ticker: str) -> tuple[np.ndarray, Currency]:
    if ticker in m.prices.columns:
        s = m.prices[ticker]
        ccy = m.universe.stocks[ticker].ccy
    elif ticker in m.adr_prices.columns:
        s = m.adr_prices[ticker]
        ccy = Currency.USD
    else:
        s = m.etf_prices[ticker]
        etf = m.universe.etfs[ticker]
        ccy = m.universe.indices[etf.index].ccy
    return s.ffill().to_numpy(), ccy


def _diff(x: np.ndarray) -> np.ndarray:
    out = np.zeros_like(x, dtype=float)
    out[1:] = x[1:] - x[:-1]
    return out


def _lag(x: np.ndarray) -> np.ndarray:
    out = np.zeros_like(x, dtype=float)
    out[1:] = x[:-1]
    return out


def compute_ledger(book: Book, m: MarketHistory, apply_breaks: bool = False) -> Ledger:
    """Build the desk ledger. ``apply_breaks=True`` layers the seeded breaks onto the books."""
    days = m.days
    n = len(days)
    didx = {d: i for i, d in enumerate(days)}
    led = Ledger(days)
    cal_days = np.zeros(n)
    cal_days[1:] = [(days[i] - days[i - 1]).days for i in range(1, n)]
    brk = {b.kind: b for b in book.breaks} if apply_breaks else {}
    ftp = config.desk()

    # ------------------------------------------------------------ positions in tradable securities
    qty_traded: dict[str, np.ndarray] = {}
    sec_trades: dict[str, list] = {}
    for t in book.trades:
        if isinstance(t, CashEquityTrade | EtfTrade):
            sec_trades.setdefault(t.ticker, []).append(t)
    for tick, trs in sec_trades.items():
        px, ccy = _security_series(m, tick)
        fx = _fx_arr(m, ccy)
        q = np.zeros(n)
        for t in trs:
            i = didx[t.trade_date]
            q[i] += t.qty
            e = np.zeros(n)
            e[i] = t.qty * (px[i] - t.price) * fx[i]
            led.add(t.book, "execution", t.trade_id, e, tick)
        qty_traded[tick] = q
        px_used = px.copy()
        if "stale_price" in brk and brk["stale_price"].ticker == tick:
            i = didx[brk["stale_price"].date]
            px_used[i] = px[i - 1]
        # price and fx pnl are split by trade book proportional to each trade's own position
        for t in trs:
            qt = np.zeros(n)
            qt[didx[t.trade_date]] = t.qty
            qs = _lag(np.cumsum(qt))
            price_pnl = qs * _diff(px_used) * fx
            fx_pnl = qs * _lag(px_used) * _diff(fx)
            led.add(t.book, "price", t.trade_id, price_pnl, tick)
            led.add(t.book, "fx", t.trade_id, fx_pnl, tick)
        # dividends on the hedge position
        for e in m.dividends:
            if e.ticker != tick or e.amount <= 0 or e.ex_date not in didx:
                continue
            i = didx[e.ex_date]
            for t in trs:
                if t.trade_date < e.ex_date and isinstance(t, CashEquityTrade):
                    held = _lag(np.cumsum(_unit(n, didx[t.trade_date], t.qty)))[i]
                    if (
                        "missed_dividend" in brk
                        and brk["missed_dividend"].trade_id == t.trade_id
                        and brk["missed_dividend"].date == e.ex_date
                    ):
                        continue
                    arr = np.zeros(n)
                    arr[i] = held * e.amount * fx[i]
                    led.add(t.book, "dividends", t.trade_id, arr, tick)

    # ------------------------------------------------------------ futures
    for t in book.trades:
        if not isinstance(t, FutureTrade):
            continue
        ser = m.futures[(t.index, t.expiry)].reindex(pd.DatetimeIndex(days)).to_numpy()
        fx = _fx_arr(m, t.ccy)
        i0 = didx[t.trade_date]
        exp_i = didx.get(t.expiry, n - 1)
        px = np.where(np.isnan(ser), 0.0, ser)
        pnl = np.zeros(n)
        for i in range(i0 + 1, min(exp_i, n - 1) + 1):
            pnl[i] = t.qty * t.multiplier * (px[i] - px[i - 1]) * fx[i]
        e = np.zeros(n)
        e[i0] = t.qty * t.multiplier * (px[i0] - t.price) * fx[i0]
        led.add(t.book, "execution", t.trade_id, e)
        led.add(t.book, "price", t.trade_id, pnl)

    # ------------------------------------------------------------ dividend futures
    for t in book.trades:
        if not isinstance(t, DividendFutureTrade):
            continue
        ser = m.div_futures[t.year].reindex(pd.DatetimeIndex(days)).to_numpy()
        fx = _fx_arr(m, t.ccy)
        i0 = didx[t.trade_date]
        pnl = np.zeros(n)
        prev = t.strike
        for i in range(i0, n):
            cur = ser[i]
            if np.isnan(cur):
                break
            pnl[i] = t.units * (cur - prev) * fx[i]
            prev = cur
        led.add(t.book, "div_derivs", t.trade_id, pnl)

    # ------------------------------------------------------------ swaps
    for s in book.swaps():
        _swap_ledger(led, book, m, s, brk, ftp, cal_days, didx)

    # ------------------------------------------------------------ financing trades
    for t in book.trades:
        if isinstance(t, SblTrade):
            _sbl_ledger(led, m, t, cal_days, didx)
        elif isinstance(t, RepoTrade):
            _repo_ledger(led, m, t, cal_days, didx, ftp)
    return led


def _unit(n: int, i: int, q: float) -> np.ndarray:
    a = np.zeros(n)
    a[i] = q
    return a


def _swap_ledger(led, book, m, s, brk, ftp, cal_days, didx) -> None:
    n = len(m.days)
    days = m.days
    kind, _, name = s.underlying.partition(":")
    series = (m.prices[name] if kind == "stock" else m.index_level[name]).ffill().to_numpy()
    fx = _fx_arr(m, s.ccy)
    evs = book.events_for(s.trade_id)
    sh = shares_series(s, evs, days)
    sgn = 1 if s.direction is Direction.LONG else -1
    spread = spread_series(s, evs, days)
    # price and fx: desk is on the other side of the client
    px_prev = _lag(series)
    led.add(s.book, "price", s.trade_id, -sgn * sh * _diff(series) * fx, name)
    led.add(s.book, "fx", s.trade_id, -sgn * sh * px_prev * _diff(fx), name)
    # dividends passed through (desk pays on long, receives on short)
    for dv in underlying_dividends(m, s.underlying):
        if dv.ex_date in didx:
            i = didx[dv.ex_date]
            arr = np.zeros(n)
            arr[i] = -sgn * sh[i] * dv.amount * s.pass_through * fx[i]
            if arr[i] != 0:
                led.add(s.book, "dividends", s.trade_id, arr, name)
    # funding legs
    notional = sh * px_prev if s.notional_reset else sh * s.initial_price
    fixings = m.fixings[s.benchmark]
    basis = BASIS_BY_BENCH[s.benchmark]
    rate = np.zeros(n)
    for i in range(1, n):
        rate[i] = float(fixings.loc[pd.Timestamp(days[i - 1])])
    swap_rate = rate.copy()
    if "wrong_fixing" in brk and brk["wrong_fixing"].trade_id == s.trade_id:
        b = brk["wrong_fixing"]
        j = didx[b.date]
        swap_rate[max(j - 20, 1) : j + 1] = float(b.detail["booked_rate"])
    acc = cal_days / basis
    swap_leg = sgn * notional * acc * (swap_rate + sgn * spread / 1e4) * fx
    led.add(s.book, "funding", s.trade_id, swap_leg, name)
    if kind == "stock":
        if sgn > 0:
            hedge_leg = -notional * acc * (rate + ftp_component_bps(s.ccy) / 1e4) * fx
        else:
            hedge_leg = notional * acc * rate * fx
        led.add(s.book, "funding", s.trade_id, hedge_leg, name)
    # fees: sales credit on trade date, amendment upfront
    fee = np.zeros(n)
    fee[didx[s.trade_date]] -= s.sales_credit * fx[didx[s.trade_date]]
    for e in evs:
        if isinstance(e, Amendment) and e.date in didx:
            fee[didx[e.date]] += e.upfront * fx[didx[e.date]]
    led.add(s.book, "fees", s.trade_id, fee, name)


def _price_series(m: MarketHistory, ticker: str) -> np.ndarray:
    return m.prices[ticker].ffill().to_numpy()


def _sbl_ledger(led, m, t: SblTrade, cal_days, didx) -> None:
    n = len(m.days)
    px = _price_series(m, t.ticker)
    fx = _fx_arr(m, t.ccy)
    i0 = didx[t.trade_date]
    i1 = didx[t.end_date] if t.end_date else n - 1
    live = np.zeros(n)
    live[i0 + 1 : i1 + 1] = 1.0
    sgn = -1 if t.side == "borrow" else 1  # desk pays on borrow, receives on loan
    arr = sgn * live * t.shares * _lag(px) * fx * (t.fee_bps / 1e4) * cal_days / 360.0
    led.add(t.book, "sbl_repo", t.trade_id, arr, t.ticker)


def _repo_ledger(led, m, t: RepoTrade, cal_days, didx, ftp) -> None:
    """Repo funds part of the hedge inventory: saves FTP, pays the repo spread (both over the benchmark)."""
    n = len(m.days)
    px = _price_series(m, t.ticker)
    fx = _fx_arr(m, t.ccy)
    i0 = didx[t.trade_date]
    live = np.zeros(n)
    live[i0 + 1 :] = 1.0
    cash = t.qty * _lag(px) * (1 - t.haircut) * fx
    net_bps = ftp_component_bps(t.ccy) - t.spread_bps
    arr = live * cash * (net_bps / 1e4) * cal_days / 360.0
    led.add(t.book, "sbl_repo", t.trade_id, arr, t.ticker)


def break_impacts(book: Book, m: MarketHistory) -> list[SeededBreak]:
    """Seeded breaks with ``pnl_impact`` = booked ledger minus true ledger for that break, in USD."""
    out = []
    for b in book.breaks:
        single = Book(book.seed, book.clients, book.trades, book.events, [b])
        booked = compute_ledger(single, m, apply_breaks=True)
        base = compute_ledger(true_book(single), m, apply_breaks=False)
        diff = booked.total() - base.total()
        # a stale mark reverses next day, so its impact is measured on the break date only
        impact = float(diff[m.days.index(b.date)] if b.kind == "stale_price" else diff.sum())
        out.append(b.model_copy(update={"pnl_impact": round(impact, 2)}))
    return out

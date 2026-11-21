"""PnL attribution: slice the ledger by book, client, ticker or component (USD, desk side)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from core.data.book import Book
from core.pnl.ledger import Ledger


def _w(led: Ledger, start: date, end: date) -> np.ndarray:
    return np.array([start < d <= end for d in led.days])


def by_book(led: Ledger, start: date, end: date) -> pd.DataFrame:
    """Rows = books, columns = components, values = USD over ``(start, end]``."""
    w = _w(led, start, end)
    rec: dict[str, dict[str, float]] = {}
    for (bk, comp), arr in led.by_book.items():
        rec.setdefault(bk, {})[comp] = float(arr[w].sum())
    df = pd.DataFrame(rec).T.fillna(0.0)
    df["total"] = df.sum(axis=1)
    return df.sort_values("total", ascending=False)


def by_client(led: Ledger, book: Book, start: date, end: date) -> pd.Series:
    """Swap-book PnL per client (swap legs only, with each swap's hedges attributed to its client)."""
    w = _w(led, start, end)
    out: dict[str, float] = {}
    for tid, comps in led.by_trade.items():
        tr = book.trade(tid)
        client = book.client_of(tr)
        if client is None:
            continue
        out[client.name] = out.get(client.name, 0.0) + sum(
            float(a[w].sum()) for a in comps.values()
        )
    return pd.Series(out).sort_values(ascending=False)


def by_ticker(led: Ledger, start: date, end: date) -> pd.Series:
    w = _w(led, start, end)
    return pd.Series({k: float(a[w].sum()) for k, a in led.by_ticker.items()}).sort_values(
        ascending=False
    )


def by_trade(led: Ledger, start: date, end: date) -> pd.DataFrame:
    w = _w(led, start, end)
    rows = []
    for tid, comps in led.by_trade.items():
        row = {"trade_id": tid, **{c: float(a[w].sum()) for c, a in comps.items()}}
        row["total"] = sum(v for k, v in row.items() if k != "trade_id")
        rows.append(row)
    return pd.DataFrame(rows).fillna(0.0).set_index("trade_id")


def top_movers(led: Ledger, start: date, end: date, n: int = 5) -> tuple[pd.Series, pd.Series]:
    """(best n, worst n) tickers by PnL over the window."""
    s = by_ticker(led, start, end)
    return s.head(n), s.tail(n).sort_values()

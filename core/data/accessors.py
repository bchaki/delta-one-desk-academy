"""Helpers to read an underlying ("stock:TICK" or "index:NAME") from a :class:`MarketHistory`."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from core.data.market import MarketHistory
from core.dividends import Dividend
from core.types import Currency


def split_underlying(u: str) -> tuple[str, str]:
    kind, _, name = u.partition(":")
    if kind not in ("stock", "index"):
        raise ValueError(f"bad underlying {u!r}")
    return kind, name


def underlying_series(m: MarketHistory, u: str) -> pd.Series:
    kind, name = split_underlying(u)
    return m.prices[name] if kind == "stock" else m.index_level[name]


def underlying_price(m: MarketHistory, u: str, d: date) -> float:
    return float(underlying_series(m, u).at[pd.Timestamp(d)])


def underlying_ccy(m: MarketHistory, u: str) -> Currency:
    kind, name = split_underlying(u)
    return m.universe.stocks[name].ccy if kind == "stock" else m.universe.indices[name].ccy


def underlying_dividends(m: MarketHistory, u: str) -> list[Dividend]:
    """Gross dividends per share (stocks) or index points (indices), by ex-date."""
    kind, name = split_underlying(u)
    if kind == "index":
        return list(m.index_div_events[name])
    return [
        Dividend(e.ex_date, e.pay_date, e.amount)
        for e in m.dividends
        if e.ticker == name and e.amount > 0
    ]


def day_index(m: MarketHistory) -> dict[date, int]:
    return {d: i for i, d in enumerate(m.days)}


def price_array(m: MarketHistory, ticker: str) -> np.ndarray:
    return m.prices[ticker].to_numpy()

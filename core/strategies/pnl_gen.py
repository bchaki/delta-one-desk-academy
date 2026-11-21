"""PnL generation capstone: a year of desk revenue by source, tier and sub-book, net of costs.

Revenue is taken from the synthetic ledger (clean model) over the last ``n`` trading days. The mapping
from ledger components to revenue sources is stated explicitly below. Costs (funding, balance sheet,
capital) come from ``core.financing.balance_sheet`` applied to average gross swap notional. Figures
are illustrative: the synthetic book has fictional clients and prices.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from core.data.book import Book
from core.data.market import MarketHistory
from core.pnl.explain import _window
from core.pnl.ledger import Ledger

SOURCE_OF = {
    "funding": "Financing spread",
    "execution": "Bid/offer and execution",
    "sbl_repo": "Borrow and lending",
    "dividends": "Dividends",
    "div_derivs": "Dividends",
    "fees": "Fees",
    "price": "Basis and arbitrage / risk",
    "fx": "Basis and arbitrage / risk",
}


def revenue_by_source(clean: Ledger, start: date, end: date) -> pd.Series:
    """Revenue by source over ``(start, end]``, USD, using ``SOURCE_OF`` to group ledger components."""
    w = _window(clean, start, end)
    out: dict[str, float] = {}
    for (_, comp), arr in clean.by_book.items():
        out[SOURCE_OF[comp]] = out.get(SOURCE_OF[comp], 0.0) + float(arr[w].sum())
    return pd.Series(out).sort_values(ascending=False)


def revenue_by_subbook(clean: Ledger, start: date, end: date) -> pd.Series:
    """Revenue by sub-book (the book name) over ``(start, end]``."""
    w = _window(clean, start, end)
    out: dict[str, float] = {}
    for (b, _), arr in clean.by_book.items():
        out[b] = out.get(b, 0.0) + float(arr[w].sum())
    return pd.Series(out).sort_values(ascending=False)


def revenue_by_tier(clean: Ledger, book: Book, start: date, end: date) -> pd.Series:
    """Revenue by client tier (1 = largest): sums the trade ledger by the counterparty's tier."""
    w = _window(clean, start, end)
    out: dict[int, float] = {}
    for tid, comps in clean.by_trade.items():
        c = book.client_of(book.trade(tid))
        if c is None:
            continue
        tier = c.tier
        out[tier] = out.get(tier, 0.0) + float(sum(a[w].sum() for a in comps.values()))
    return pd.Series(out).sort_index()


def swap_notional_usd(book: Book, m: MarketHistory, d: date) -> float:
    """Gross USD notional of live equity swaps at ``d`` (shares x price x FX)."""
    total = 0.0
    for t in book.swaps():
        if (
            t.trade_date <= d
            and (t.end_date is None or t.end_date > d)
            and t.underlying.startswith("stock:")
        ):
            tk = t.underlying.split(":", 1)[1]
            total += abs(t.shares) * m.price(tk, d) * m.fx_usd_per(t.ccy, d)
    return total


def net_contribution(
    revenue: float,
    avg_notional: float,
    ftp_bps: float,
    bs_leverage_multiple: float,
    bs_cost_bps: float,
    capital_ratio: float,
    cost_of_equity: float,
) -> dict[str, float]:
    """Cost lines for a year: funding on the hedge, balance sheet, capital.

    ``funding = notional x FTP``; ``balance sheet = notional x leverage multiple x bps``; ``capital =
    notional x multiple x ratio``; ``capital cost = capital x cost of equity``. Net contribution =
    revenue - funding - balance sheet; economic profit also subtracts the cost of capital.
    """
    funding = avg_notional * ftp_bps / 1e4
    bsc = avg_notional * bs_leverage_multiple * bs_cost_bps / 1e4
    cap = avg_notional * bs_leverage_multiple * capital_ratio
    net = revenue - funding - bsc
    return {
        "funding": funding,
        "balance_sheet": bsc,
        "capital": cap,
        "net_contribution": net,
        "economic_profit": net - cap * cost_of_equity,
        "return_on_capital": net / cap if cap else np.nan,
    }


def budget_vs_actual(actual: pd.Series, budget: pd.Series) -> pd.DataFrame:
    """Variance table: actual, budget, variance and variance in % of budget."""
    df = pd.DataFrame({"actual": actual, "budget": budget}).fillna(0.0)
    df["variance"] = df.actual - df.budget
    df["variance_pct"] = np.where(df.budget != 0, df.variance / df.budget.abs(), np.nan)
    return df


__all__ = [
    "budget_vs_actual",
    "net_contribution",
    "revenue_by_source",
    "revenue_by_subbook",
    "revenue_by_tier",
    "swap_notional_usd",
]

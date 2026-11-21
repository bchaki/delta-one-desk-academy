"""PnL explain: components from the clean model, total from the booked ledger, residual = Unexplained.

Positive = gain to the desk, USD. Components are rounded to cents with ``money()`` and the
``unexplained`` line is the residual of the ROUNDED components, so the lines add up to the total
exactly: ``sum(components) + unexplained == total`` to the cent.

What it teaches: the booked total includes any booking error (a missed dividend, a wrong spread, a
wrong fixing, a stale mark). The clean model does not, so the error lands in Unexplained, and a
persistent Unexplained is the signal to go and look for a break.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from core.data.book import Book
from core.data.market import MarketHistory
from core.pnl.ledger import COMPONENTS, Ledger, compute_ledger, true_book
from core.types import money


@dataclass(frozen=True)
class PnLExplain:
    start: date
    end: date
    components: dict[str, float]
    total: float
    unexplained: float

    @property
    def explained(self) -> float:
        return money(sum(self.components.values()))

    def reconciles(self) -> bool:
        """True when the rounded components plus unexplained equal the total to the cent."""
        return abs(money(sum(self.components.values()) + self.unexplained) - self.total) < 5e-3


def _window(led: Ledger, start: date, end: date) -> np.ndarray:
    return np.array([start < d <= end for d in led.days])


def pnl_explain(
    booked: Ledger, clean: Ledger, start: date, end: date, by_book: str | None = None
) -> PnLExplain:
    """Explain PnL over ``(start, end]``.

    ``booked`` is the ledger with the seeded breaks, ``clean`` the one without. Total comes from
    the booked ledger; components from the clean ledger. Optionally restrict to one book.
    """
    w = _window(clean, start, end)
    comps: dict[str, float] = {}
    for c in COMPONENTS:
        arr = sum(
            (a for (b, k), a in clean.by_book.items() if k == c and (by_book in (None, b))),
            np.zeros(len(clean.days)),
        )
        comps[c] = money(float(arr[w].sum()))
    tot_arr = sum(
        (a for (b, _), a in booked.by_book.items() if by_book in (None, b)),
        np.zeros(len(booked.days)),
    )
    total = money(float(tot_arr[w].sum()))
    unexplained = money(total - sum(comps.values()))
    return PnLExplain(start, end, comps, total, unexplained)


def explain_series(booked: Ledger, clean: Ledger) -> pd.DataFrame:
    """Daily explain table: one row per day, each component, unexplained and total (USD)."""
    rows = []
    for i, d in enumerate(booked.days):
        comps = {
            c: money(float(sum((a[i] for (_, k), a in clean.by_book.items() if k == c), 0.0)))
            for c in COMPONENTS
        }
        total = money(float(sum(a[i] for a in booked.by_book.values())))
        rows.append(
            {"date": d, **comps, "unexplained": money(total - sum(comps.values())), "total": total}
        )
    return pd.DataFrame(rows).set_index("date")


def ledgers(book: Book, m: MarketHistory) -> tuple[Ledger, Ledger]:
    """(booked, clean) ledgers for a book."""
    return compute_ledger(book, m, apply_breaks=True), compute_ledger(true_book(book), m, False)

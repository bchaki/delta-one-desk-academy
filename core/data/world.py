"""The synthetic world: market + book + ledgers, cached on ``(seed, as_of)``.

Everything the pages need comes from ``build_world``. ``as_of`` clamps to the history window; the
default is the last synthetic trading day (2026-11-20).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import cache

from core.data.book import Book, generate_book
from core.data.market import MarketHistory, build_market
from core.pnl.explain import ledgers
from core.pnl.ledger import Ledger, break_impacts

DEFAULT_SEED = 7


@dataclass
class World:
    seed: int
    as_of: date
    market: MarketHistory
    book: Book
    booked: Ledger
    clean: Ledger

    @property
    def universe(self):
        return self.market.universe


@cache
def _base(seed: int) -> tuple[MarketHistory, Book, Ledger, Ledger]:
    m = build_market(seed)
    book = generate_book(seed)
    book = book.with_breaks(break_impacts(book, m))
    booked, clean = ledgers(book, m)
    return m, book, booked, clean


def build_world(seed: int = DEFAULT_SEED, as_of: date | None = None) -> World:
    """Deterministic world for ``(seed, as_of)``. Heavy objects are built once per seed."""
    m, book, booked, clean = _base(seed)
    d = m.clamp(as_of or m.days[-1])
    return World(seed, d, m, book, booked, clean)

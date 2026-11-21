"""Internalisation: cover shorts from client longs and desk inventory before borrowing in the street."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class NameInput:
    ticker: str
    price: float
    client_short_shares: float
    client_long_shares: float
    desk_inventory_shares: float
    street_fee_bps: float


@dataclass(frozen=True)
class NameResult:
    ticker: str
    short_demand: float
    internal_supply: float
    internal_cover: float
    street_borrow: float
    savings: float  # currency units over the period
    savings_bps: float  # of short notional, annualised


def internalise_name(
    n: NameInput,
    rehyp_fraction: float,
    internal_cost_bps: float,
    days: int,
    basis: int,
) -> NameResult:
    """Internal cover = min(short demand, rehypothecable client longs + desk inventory).

    ``rehyp_fraction`` is the share of client longs the desk may reuse (rehypothecation limits).
    Savings = covered notional x (street fee - internal cost) x days / basis; the remainder is
    borrowed externally at the street fee.
    """
    supply = n.client_long_shares * rehyp_fraction + n.desk_inventory_shares
    cover = min(n.client_short_shares, supply)
    street = n.client_short_shares - cover
    saved = cover * n.price * (n.street_fee_bps - internal_cost_bps) / 10_000.0 * days / basis
    short_notional = n.client_short_shares * n.price
    sav_bps = (
        cover * n.price * (n.street_fee_bps - internal_cost_bps) / short_notional
        if short_notional
        else 0.0
    )
    return NameResult(n.ticker, n.client_short_shares, supply, cover, street, saved, sav_bps)


def internalise_book(
    names: Sequence[NameInput],
    rehyp_fraction: float,
    internal_cost_bps: float,
    days: int,
    basis: int,
) -> tuple[list[NameResult], float, float]:
    """Run :func:`internalise_name` over a book. Returns (rows, total savings, coverage ratio)."""
    rows = [internalise_name(n, rehyp_fraction, internal_cost_bps, days, basis) for n in names]
    demand = sum(r.short_demand * n.price for r, n in zip(rows, names, strict=True))
    cover = sum(r.internal_cover * n.price for r, n in zip(rows, names, strict=True))
    return rows, sum(r.savings for r in rows), (cover / demand if demand else 0.0)

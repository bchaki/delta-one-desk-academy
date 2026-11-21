"""ADR parity and arbitrage band."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


def adr_fair_value(local_price: float, ratio: float, fx: float) -> float:
    """ADR fair value = local price x ratio x FX.

    ``ratio`` is local shares per ADR; ``fx`` is ADR-currency per 1 unit of local currency
    (USD per EUR for EURUSD; for JPY pass 1 / USDJPY).
    """
    return local_price * ratio * fx


@dataclass(frozen=True)
class AdrBand:
    fair_value: float
    lower: float
    upper: float


class AdrAction(StrEnum):
    ISSUE = "sell_adr_buy_local_issue"  # ADR rich
    CANCEL = "buy_adr_cancel_sell_local"  # ADR cheap
    NONE = "none"


def adr_band(
    local_price: float,
    ratio: float,
    fx: float,
    conversion_fee_per_adr: float,
    cost_bps: float,
) -> AdrBand:
    """Arbitrage band around parity: FV +/- (depositary conversion fee + cost bps of FV).

    ``cost_bps`` covers both bid/asks, FX spread and commissions. Fees are per ADR in ADR currency.
    Simplified: symmetric costs, no settlement-timing or borrow cost on the local leg.
    """
    fv = adr_fair_value(local_price, ratio, fx)
    cost = conversion_fee_per_adr + fv * cost_bps / 10_000.0
    return AdrBand(fair_value=fv, lower=fv - cost, upper=fv + cost)


def adr_arbitrage(adr_price: float, band: AdrBand) -> tuple[AdrAction, float]:
    """Open arbitrage (if any) and the edge per ADR after costs."""
    if adr_price > band.upper:
        return AdrAction.ISSUE, adr_price - band.upper
    if adr_price < band.lower:
        return AdrAction.CANCEL, band.lower - adr_price
    return AdrAction.NONE, 0.0

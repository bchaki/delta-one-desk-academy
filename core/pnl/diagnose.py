"""Sizing the usual booking and market-data errors, to match an unexplained PnL to a cause.

All amounts are desk-side: positive = a gain to the desk compared with the correct booking. A
booking error shows up in the booked ledger but not in the clean model, so its impact is what
lands in ``Unexplained``. These functions give the expected size for each suspect.
"""

from __future__ import annotations

from core.types import money


def unexplained(total: float, components: list[float]) -> float:
    """Residual of the cents-rounded components: ``money(total - sum(money(c)))``.

    Components are rounded first, so the lines always add to the total to the cent.
    """
    return money(total - sum(money(c) for c in components))


def spread_error_impact(
    notional: float, booked_bps: float, correct_bps: float, days: int, basis: int = 360
) -> float:
    """Desk PnL effect of booking the swap spread at ``booked_bps`` instead of ``correct_bps``.

    On a long client swap the client pays the spread, so booking it too low costs the desk
    notional x (booked - correct) x days / basis. A short swap reverses the sign.
    """
    return notional * (booked_bps - correct_bps) / 1e4 * days / basis


def missed_dividend_impact(shares: float, gross_per_share: float) -> float:
    """Desk PnL effect of a dividend that was paid on the hedge but never booked.

    The desk's ledger omits the receipt, so booked PnL is lower than the clean model by
    ``shares x gross``. The sign is negative (a shortfall against the correct figure).
    """
    return -shares * gross_per_share


def fixing_error_impact(
    notional: float, booked_rate: float, correct_rate: float, days: int, basis: int = 360
) -> float:
    """Desk effect of a wrong benchmark fixing on the client's funding leg of a long swap.

    The client pays benchmark + spread to the desk, so a booked rate above the correct one gives
    the desk a gain: notional x (booked - correct) x days / basis (decimals).
    """
    return notional * (booked_rate - correct_rate) * days / basis


def stale_mark_impact(shares: float, stale_price: float, right_price: float) -> float:
    """Desk PnL effect of marking a long hedge at ``stale_price`` instead of ``right_price``."""
    return shares * (stale_price - right_price)


def classify(amount: float, candidates: dict[str, float], tolerance: float = 1.0) -> str | None:
    """Name of the candidate whose expected impact is within ``tolerance`` of ``amount`` (or ``None``).

    The nearest wins when several match. Use it after sizing each suspect from the clues.
    """
    best = None
    best_gap = tolerance
    for name, impact in candidates.items():
        gap = abs(amount - impact)
        if gap <= best_gap:
            best, best_gap = name, gap
    return best

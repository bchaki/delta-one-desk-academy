"""Market-data controls for marks and the end-of-day process.

Pure functions that flag suspicious prices and size the impact of a wrong mark. They teach the
checks a TDA runs before PnL is signed off: unchanged prices, large moves, source disagreements.
"""

from __future__ import annotations

from collections.abc import Sequence


def stale_flags(prices: Sequence[float]) -> list[int]:
    """Indices ``i >= 1`` where ``prices[i] == prices[i-1]`` exactly (a possibly stale mark).

    An exact repeat in a float series is rare for a liquid stock, so it is a useful first flag; it
    is not proof, since a halted or very illiquid name can genuinely close unchanged.
    """
    return [i for i in range(1, len(prices)) if prices[i] == prices[i - 1]]


def move_flags(prices: Sequence[float], threshold: float) -> list[int]:
    """Indices where the one-day return exceeds ``threshold`` in absolute value (decimal)."""
    return [i for i in range(1, len(prices)) if abs(prices[i] / prices[i - 1] - 1.0) > threshold]


def source_breaks(
    primary: Sequence[float], secondary: Sequence[float], tolerance_bps: float
) -> list[tuple[int, float]]:
    """(index, difference in bps of the primary) where two price sources disagree by more than the tolerance."""
    if len(primary) != len(secondary):
        raise ValueError("series must have the same length")
    out = []
    for i, (a, b) in enumerate(zip(primary, secondary, strict=True)):
        diff = (b / a - 1.0) * 1e4
        if abs(diff) > tolerance_bps:
            out.append((i, diff))
    return out


def mark_impact(shares: float, wrong_price: float, right_price: float, fx: float = 1.0) -> float:
    """PnL error from marking ``shares`` at ``wrong_price`` instead of ``right_price``.

    Positive = the booked PnL is overstated (a gain too large for a long position). ``fx`` converts
    to the reporting currency.
    """
    return shares * (wrong_price - right_price) * fx

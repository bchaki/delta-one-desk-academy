"""US broker margin under Reg T / FINRA minimums (simplified, parameters from config/margin.yaml)."""

from __future__ import annotations

from core import config
from core.margin import MarginResult


def regt_requirements(long_mv: float, short_mv: float) -> tuple[MarginResult, MarginResult]:
    """Returns ``(initial, maintenance)`` margin for gross long and short market values.

    Initial = 50% x long MV + (150% - 100%) x short MV (the short proceeds count as the first 100%).
    Maintenance = 25% x long MV + 30% x short MV. Simplified: no minimum equity, no concentrated or
    low-priced security rules, no day-trading rules. ``short_mv`` is the absolute short value.
    """
    p = config.margin().regt
    initial = p.initial_pct * long_mv + (p.short_initial_pct - 1.0) * short_mv
    maint = p.maintenance_long_pct * long_mv + p.short_maintenance_pct * short_mv
    return (
        MarginResult(initial, 0.0, {"long": p.initial_pct * long_mv}),
        MarginResult(maint, 0.0, {"long": p.maintenance_long_pct * long_mv}),
    )


def gross_leverage_allowed(long_mv: float, short_mv: float) -> float | None:
    """Gross exposure per unit of equity allowed for a book of this shape: (L + S) / initial margin."""
    initial, _ = regt_requirements(long_mv, short_mv)
    if initial.net == 0:
        return None
    return (long_mv + short_mv) / initial.net

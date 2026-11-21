"""Cost of exposure: what it costs to hold the same index or stock exposure in different wrappers.

Convention: costs are measured as the cost *in excess of the benchmark rate*, i.e. what an investor
gives up relative to holding cash and receiving the equity total return. Positive = a cost to the
investor. All inputs are in bps; amounts are in the notional's currency.

Formula for one instrument over ``days`` on day-count ``basis``::

    running   = notional x (financing spread + fee + dividend leakage) x days / basis / 10,000
    trading   = notional x (one-way trading cost x 2 x round trips + one-off) / 10,000
    total     = running + trading
    total_bps_pa = total / notional x basis / days x 10,000

Simplified: constant spreads, no market impact beyond the supplied trading cost, no tax. The full
version would add instrument-specific margin funding and tax by investor type.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExposureCost:
    """Cost of one wrapper over a holding period (currency units, investor perspective)."""

    name: str
    running: float
    trading: float
    total: float
    total_bps_pa: float


def exposure_cost(
    name: str,
    notional: float,
    days: int,
    basis: int,
    financing_spread_bps: float,
    fee_bps_pa: float = 0.0,
    leakage_bps_pa: float = 0.0,
    one_way_trading_bps: float = 0.0,
    round_trips: float = 1.0,
    one_off_bps: float = 0.0,
) -> ExposureCost:
    """Cost of holding ``notional`` of exposure for ``days`` in one wrapper.

    ``round_trips`` counts entries and exits: one means in once and out once (two one-way costs);
    a futures position that rolls each quarter adds a round trip per roll. ``one_off_bps`` carries
    stamp duty, creation fees or a premium paid on entry.
    """
    if days <= 0 or basis <= 0 or notional <= 0:
        raise ValueError("notional, days and basis must be positive")
    running = notional * (financing_spread_bps + fee_bps_pa + leakage_bps_pa) / 1e4 * days / basis
    trading = notional * (one_way_trading_bps * 2.0 * round_trips + one_off_bps) / 1e4
    total = running + trading
    return ExposureCost(name, running, trading, total, total / notional * basis / days * 1e4)


def breakeven_days(
    fixed_a_bps: float, pa_a_bps: float, fixed_b_bps: float, pa_b_bps: float, basis: int = 360
) -> float | None:
    """Holding period (days) at which wrappers A and B cost the same, or ``None`` if never.

    Each wrapper costs ``fixed + pa x days / basis`` in bps of notional. Setting them equal gives
    ``days = (fixed_a - fixed_b) / (pa_b - pa_a) x basis``. A positive answer exists only when the
    wrapper with the higher fixed cost has the lower running cost.
    """
    d_pa = pa_b_bps - pa_a_bps
    if d_pa == 0:
        return None
    days = (fixed_a_bps - fixed_b_bps) / d_pa * basis
    return days if days > 0 else None

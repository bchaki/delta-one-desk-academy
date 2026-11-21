"""US-style portfolio margin: worst loss across a price grid (simplified).

Single names and broad indices each have their own grid half-width; within each group all
underlyings move together, so long single names against short index positions offset only partly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from core import config
from core.margin import MarginResult


@dataclass(frozen=True)
class PMPosition:
    ticker: str
    market_value: float  # signed: + long, - short
    is_index: bool = False


def portfolio_margin(positions: Sequence[PMPosition]) -> MarginResult:
    """Portfolio margin = max(worst loss over the grid, floor).

    Grid scenario s in [-1, 1] (``grid_points`` evenly spaced) moves indices by s x index range and
    single names by s x single-name range. PnL(s) = sum MV_i x move_i. ``gross`` is the sum of standalone
    worst losses; ``credits`` the benefit of offsets, so ``net`` is the portfolio margin.
    """
    p = config.margin().portfolio_margin
    s = np.linspace(-1.0, 1.0, p.grid_points)
    pnl = np.zeros_like(s)
    standalone = 0.0
    gross_mv = 0.0
    for pos in positions:
        rng = p.index_range_pct if pos.is_index else p.single_name_range_pct
        leg = pos.market_value * rng * s
        pnl += leg
        standalone += max(float(np.max(-leg)), 0.0)
        gross_mv += abs(pos.market_value)
    worst = max(float(np.max(-pnl)), 0.0)
    floor = p.min_margin_pct * gross_mv
    net = max(worst, floor)
    return MarginResult(
        gross=standalone,
        credits=max(standalone - net, 0.0),
        detail={
            "worst_loss": worst,
            "floor": floor,
            "worst_scenario": float(s[int(np.argmax(-pnl))]),
        },
    )

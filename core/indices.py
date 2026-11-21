"""Index construction: level, divisor, weighting schemes, capping, inclusion demand, total return."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from core.pricing.program_trading import sqrt_impact_bps


def index_value(
    prices: Sequence[float],
    shares: Sequence[float],
    free_float: Sequence[float],
    cap_factor: Sequence[float],
) -> float:
    """Adjusted total market capitalisation = sum(P_i x shares_i x free float_i x cap factor_i)."""
    return float(
        sum(
            p * s * f * c for p, s, f, c in zip(prices, shares, free_float, cap_factor, strict=True)
        )
    )


def index_level(
    prices: Sequence[float],
    shares: Sequence[float],
    free_float: Sequence[float],
    cap_factor: Sequence[float],
    divisor: float,
) -> float:
    """Index level = sum(P_i x shares_i x free float_i x cap factor_i) / divisor."""
    return index_value(prices, shares, free_float, cap_factor) / divisor


def adjust_divisor(old_divisor: float, old_value: float, new_value: float) -> float:
    """New divisor that keeps the level unchanged across a constituent change.

    D' = D x (value after change) / (value before change), both at the same prices. Since the level
    is value / divisor, value'/D' = value/D.
    """
    return old_divisor * new_value / old_value


# --------------------------------------------------------------------------- weights


def weights_float_cap(
    prices: Sequence[float], shares: Sequence[float], free_float: Sequence[float]
) -> np.ndarray:
    """Free-float market-cap weights."""
    cap = np.array(prices) * np.array(shares) * np.array(free_float)
    return cap / cap.sum()


def weights_cap(prices: Sequence[float], shares: Sequence[float]) -> np.ndarray:
    """Full market-cap weights."""
    cap = np.array(prices) * np.array(shares)
    return cap / cap.sum()


def weights_price(prices: Sequence[float]) -> np.ndarray:
    """Price-weighted: w_i = P_i / sum P."""
    p = np.array(prices, dtype=float)
    return p / p.sum()


def weights_equal(n: int) -> np.ndarray:
    return np.full(n, 1.0 / n)


def apply_cap(weights: Sequence[float], cap: float, max_iter: int = 100) -> np.ndarray:
    """Cap single weights at ``cap`` and redistribute the excess pro rata to uncapped names.

    Iterates until no weight exceeds ``cap``. Requires ``cap >= 1/n`` to be feasible.
    """
    w = np.array(weights, dtype=float)
    if cap * len(w) < 1.0 - 1e-12:
        raise ValueError("cap is infeasible: cap x n < 1")
    capped = np.zeros(len(w), dtype=bool)
    for _ in range(max_iter):
        over = (w > cap + 1e-15) & ~capped
        if not over.any():
            break
        capped |= over
        w[capped] = cap
        free = ~capped
        remaining = 1.0 - cap * capped.sum()
        w[free] = w[free] / w[free].sum() * remaining
    return w


def capping_factors(uncapped: Sequence[float], capped: Sequence[float]) -> np.ndarray:
    """Capping factors (<= 1) that turn uncapped weights into capped ones.

    factor_i proportional to capped_i / uncapped_i, normalised so the largest factor is 1.
    """
    ratio = np.array(capped) / np.array(uncapped)
    return ratio / ratio.max()


# --------------------------------------------------------------------------- inclusion demand


@dataclass(frozen=True)
class InclusionDemand:
    shares: float
    notional: float
    days_of_adv: float
    impact_bps: float


def inclusion_demand(
    tracked_aum: float,
    new_weight: float,
    price: float,
    adv: float,
    impact_k: float,
    daily_vol: float,
) -> InclusionDemand:
    """Index funds' buying on inclusion: shares = tracked AUM x new weight / price.

    Expressed in days of ADV, with square-root impact k x sigma x sqrt(shares / ADV). Negative
    ``new_weight`` is not supported; model a deletion as the same demand to sell.
    """
    notional = tracked_aum * new_weight
    shares = notional / price
    days = shares / adv
    return InclusionDemand(
        shares, notional, days, sqrt_impact_bps(impact_k, daily_vol, shares, adv)
    )


# --------------------------------------------------------------------------- total return


def total_return_step(
    prev_tr_level: float,
    price_level_prev: float,
    price_level_new: float,
    div_points: float,
    wht: float = 0.0,
) -> float:
    """One-step total return index: TR' = TR x (P' + D x (1 - wht)) / P.

    ``div_points`` are index dividend points going ex over the step; ``wht`` = 0 gives gross total
    return, a positive withholding rate gives net total return.
    """
    return prev_tr_level * (price_level_new + div_points * (1.0 - wht)) / price_level_prev

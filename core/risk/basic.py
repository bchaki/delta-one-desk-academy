"""Hand-checkable risk building blocks (USD or any single currency, loss reported as a positive number).

These are the closed-form pieces behind the book-level engine in ``var.py`` and ``sensitivities.py``.
They exist so every idea (delta, beta, VaR scaling, diversification, expected shortfall, liquidation
time) can be reproduced by hand. Simplified: normal returns, delta only, independent of the sample.
"""

from __future__ import annotations

import math

from scipy.stats import norm


def delta_exposure(shares: float, price: float, fx: float = 1.0) -> float:
    """Delta in reporting currency = shares x price x FX (long positive)."""
    return shares * price * fx


def beta_adjusted(delta: float, beta: float) -> float:
    """Beta-adjusted delta = delta x beta, the equivalent index exposure."""
    return delta * beta


def fx_translation_pnl(local_value: float, fx_move_pct: float) -> float:
    """PnL in reporting currency from a ``fx_move_pct`` change in the local currency's value.

    local_value is the position's value in the reporting currency before the move.
    """
    return local_value * fx_move_pct / 100.0


def parametric_var_1d(exposure: float, daily_vol: float, conf: float = 0.99) -> float:
    """One-asset normal VaR = z(conf) x |exposure| x daily volatility (decimal)."""
    return float(norm.ppf(conf)) * abs(exposure) * daily_vol


def two_asset_var(
    e1: float, e2: float, vol1: float, vol2: float, rho: float, conf: float = 0.99
) -> float:
    """Two-position normal VaR = z x sqrt((e1 s1)^2 + (e2 s2)^2 + 2 rho e1 e2 s1 s2).

    Signed exposures: a hedge has the opposite sign, so with rho near 1 the positions offset.
    """
    var = (e1 * vol1) ** 2 + (e2 * vol2) ** 2 + 2.0 * rho * e1 * e2 * vol1 * vol2
    return float(norm.ppf(conf)) * math.sqrt(max(var, 0.0))


def scale_var(var_1d: float, days: float) -> float:
    """Square-root-of-time scaling: VaR_T = VaR_1d x sqrt(T). Assumes independent daily returns."""
    return var_1d * math.sqrt(days)


def es_normal(exposure: float, daily_vol: float, conf: float = 0.975) -> float:
    """Normal expected shortfall = |E| x sigma x phi(z) / (1 - conf)."""
    z = float(norm.ppf(conf))
    return abs(exposure) * daily_vol * float(norm.pdf(z)) / (1.0 - conf)


def days_to_liquidate(shares: float, adv: float, participation: float = 0.20) -> float:
    """Days to sell a position at ``participation`` of average daily volume: |shares| / (p x ADV)."""
    return abs(shares) / (participation * adv)


def hhi(weights: list[float]) -> float:
    """Herfindahl index of absolute weights normalised to sum to one: 1/n (even) to 1 (one name)."""
    total = sum(abs(w) for w in weights)
    return sum((abs(w) / total) ** 2 for w in weights)


def dividend_exposure_pnl(delta: float, annual_yield: float, pct_change: float) -> float:
    """PnL for a ``pct_change`` % move in forecast dividends on a net stock delta over 12 months.

    = delta x annual yield x pct / 100. A desk long stock via hedges loses when dividends fall; a
    fully passed-through swap book has none of this exposure.
    """
    return delta * annual_yield * pct_change / 100.0


def funding_sensitivity(long_inventory: float, bp: float = 1.0) -> float:
    """Annual PnL change for ``bp`` basis points higher funding on ``long_inventory``: -inventory x bp / 10,000."""
    return -long_inventory * bp / 1e4

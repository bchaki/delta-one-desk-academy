"""Pairs and stat arb: hedge ratio, cointegration test, half-life, z-score trading.

Spread = log(A) - beta x log(B) with beta from OLS. The Engle-Granger style test is an ADF regression
of the spread's change on its lagged level; the statistic is the t-value on the lag. Critical value for
two series without trend is about -3.34 at 5% (MacKinnon); we use it as a rule of thumb, not a
publication-grade test. Simplified: no lags in the ADF, no multiple-testing correction, no costs of
borrow. A flow desk rarely runs this, but clients do and the vocabulary is common.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.strategies import meanrev as mr

ADF_CRITICAL_5PCT = -3.34


def hedge_ratio(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """OLS of log A on log B: returns (beta, intercept)."""
    x, y = np.log(b), np.log(a)
    beta, alpha = np.polyfit(x, y, 1)
    return float(beta), float(alpha)


def spread(a: pd.Series, b: pd.Series) -> pd.Series:
    """Residual spread of log A on log B."""
    beta, alpha = hedge_ratio(a.to_numpy(), b.to_numpy())
    return (np.log(a) - beta * np.log(b) - alpha).rename("spread")


def adf_stat(x: np.ndarray) -> float:
    """t-statistic on phi in dx_t = c + phi x_{t-1} + e (no augmentation lags)."""
    dx, lag = np.diff(x), x[:-1]
    X = np.column_stack([np.ones_like(lag), lag])
    coef, *_ = np.linalg.lstsq(X, dx, rcond=None)
    resid = dx - X @ coef
    s2 = resid @ resid / (len(dx) - 2)
    var = s2 * np.linalg.inv(X.T @ X)[1, 1]
    return float(coef[1] / math.sqrt(var))


def half_life(x: np.ndarray) -> float:
    """Mean-reversion half-life in observations: ``-ln 2 / ln(phi)`` from an AR(1) fit; inf if phi >= 1."""
    lag, cur = x[:-1], x[1:]
    phi = float(np.polyfit(lag, cur, 1)[0])
    if phi >= 1 - 1e-9:
        return math.inf
    if phi <= 0:
        return 0.0
    return -math.log(2.0) / math.log(phi)


def zscores(s: pd.Series, window: int = 60) -> pd.Series:
    """Rolling z-score of the spread (mean and std over ``window`` observations)."""
    return ((s - s.rolling(window).mean()) / s.rolling(window).std()).dropna().rename("z")


@dataclass(frozen=True)
class PairStats:
    a: str
    b: str
    beta: float
    adf: float
    half_life: float
    cointegrated: bool


def pair_stats(prices: pd.DataFrame, a: str, b: str) -> PairStats:
    """Hedge ratio, ADF statistic, half-life and the 5% verdict for a pair of price columns."""
    s = spread(prices[a], prices[b])
    beta, _ = hedge_ratio(prices[a].to_numpy(), prices[b].to_numpy())
    t = adf_stat(s.to_numpy())
    return PairStats(a, b, beta, t, half_life(s.to_numpy()), t < ADF_CRITICAL_5PCT)


def screen_pairs(prices: pd.DataFrame, tickers: list[str], top: int = 10) -> pd.DataFrame:
    """Rank every pair in ``tickers`` by ADF statistic (most negative first).

    Illustrates multiple testing: screen enough pairs and some will look cointegrated by chance.
    """
    rows = []
    for i, a in enumerate(tickers):
        for b in tickers[i + 1 :]:
            p = pair_stats(prices, a, b)
            rows.append(
                {
                    "a": a,
                    "b": b,
                    "beta": p.beta,
                    "adf": p.adf,
                    "half_life": p.half_life,
                    "cointegrated": p.cointegrated,
                }
            )
    return pd.DataFrame(rows).sort_values("adf").head(top).reset_index(drop=True)


def backtest(
    prices: pd.DataFrame,
    a: str,
    b: str,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    cost_z: float = 0.1,
    window: int = 60,
    notional: float = 1_000_000.0,
) -> pd.DataFrame:
    """Trade z-score of the pair spread: short the spread above +entry, long below -entry.

    PnL is in z units converted at the spread's rolling std: ``pnl = z_move x std x notional`` in return
    terms; ``cost_z`` is a round-trip cost in z units. Teaching approximation: constant beta over the
    whole sample (look-ahead in beta, flagged on the page).
    """
    s = spread(prices[a], prices[b])
    z = zscores(s, window)
    t = mr.threshold_backtest(z, entry_z, exit_z, cost_z, 1.0)
    if len(t):
        sd = float(s.std())
        t["pnl"] = t["pnl_signal"] * sd * notional
    return t

"""Value-at-risk and expected shortfall on the desk's delta vector (USD, 1-day, loss as a positive number).

Methods: historical simulation, parametric (variance-covariance, normal), Monte Carlo (normal, seeded).
Simplifications: delta-only P&L (no convexity), returns are USD returns of the local price times the
FX rate, equal-weighted lookback. The full version adds vega, full revaluation and filtered
historical simulation.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from scipy.stats import norm

from core.data.market import MarketHistory


def usd_returns(m: MarketHistory, keys: list[str], d: date, lookback: int = 250) -> pd.DataFrame:
    """Daily USD log returns for ``keys`` over the ``lookback`` trading days up to ``d``."""
    i1 = m.days.index(m.clamp(d))
    i0 = max(i1 - lookback, 0)
    idx = pd.DatetimeIndex(m.days[i0 : i1 + 1])
    cols = {}
    for k in keys:
        kind, _, name = k.partition(":")
        if kind == "stock":
            ccy = m.universe.stocks[name].ccy
            s = m.prices[name]
        elif kind == "index":
            ccy = m.universe.indices[name].ccy
            s = m.index_level[name]
        elif kind == "adr":
            ccy = None
            s = m.adr_prices[name]
        else:
            ccy = m.universe.indices[m.universe.etfs[name].index].ccy
            s = m.etf_prices[name]
        s = s.ffill().loc[idx]
        if ccy is not None:
            fx = pd.Series([m.fx_usd_per(ccy, x.date()) for x in idx], index=idx)
            s = s * fx
        cols[k] = np.log(s).diff().iloc[1:]
    return pd.DataFrame(cols).fillna(0.0)


def hist_pnl(exposure: pd.Series, rets: pd.DataFrame) -> np.ndarray:
    """Historical-simulation PnL vector: returns applied to today's exposures (USD)."""
    return rets[exposure.index].to_numpy() @ exposure.to_numpy()


def var_from_pnl(pnl: np.ndarray, conf: float = 0.99) -> float:
    """VaR = -quantile(PnL, 1 - conf). Loss reported positive."""
    return float(-np.quantile(pnl, 1 - conf))


def es_from_pnl(pnl: np.ndarray, conf: float = 0.975) -> float:
    """Expected shortfall: mean loss in the worst (1 - conf) tail (>= VaR at the same level)."""
    q = np.quantile(pnl, 1 - conf)
    tail = pnl[pnl <= q]
    return float(-tail.mean())


def parametric_var(exposure: pd.Series, rets: pd.DataFrame, conf: float = 0.99) -> float:
    """z_conf x sqrt(w' Sigma w) with Sigma the sample covariance of daily returns."""
    w = exposure.to_numpy()
    cov = rets[exposure.index].cov().to_numpy()
    return float(norm.ppf(conf) * np.sqrt(max(w @ cov @ w, 0.0)))


def mc_var(
    exposure: pd.Series, rets: pd.DataFrame, conf: float = 0.99, n: int = 20000, seed: int = 11
) -> tuple[float, float]:
    """Monte Carlo VaR and ES from multivariate normal draws with the sample covariance."""
    rng = np.random.default_rng(seed)
    cov = rets[exposure.index].cov().to_numpy()
    draws = rng.multivariate_normal(np.zeros(len(exposure)), cov, size=n, method="svd")
    pnl = draws @ exposure.to_numpy()
    return var_from_pnl(pnl, conf), es_from_pnl(pnl, conf)


def marginal_var(exposure: pd.Series, rets: pd.DataFrame, conf: float = 0.99) -> pd.Series:
    """d VaR / d exposure_i (parametric): z x (Sigma w)_i / sigma_p. USD of VaR per USD of exposure."""
    w = exposure.to_numpy()
    cov = rets[exposure.index].cov().to_numpy()
    sigma = np.sqrt(max(w @ cov @ w, 1e-18))
    return pd.Series(norm.ppf(conf) * (cov @ w) / sigma, index=exposure.index)


def component_var(exposure: pd.Series, rets: pd.DataFrame, conf: float = 0.99) -> pd.Series:
    """Component VaR_i = w_i x marginal_i. Components sum to parametric VaR (Euler allocation)."""
    return exposure * marginal_var(exposure, rets, conf)


def backtest_exceptions(daily_pnl: np.ndarray, var_series: np.ndarray) -> int:
    """Number of days the loss exceeded the VaR forecast."""
    return int(np.sum(-daily_pnl > var_series))


def traffic_light(exceptions: int) -> str:
    """Basel-style zone for 250 days at 99%: green 0-4, yellow 5-9, red 10+."""
    if exceptions <= 4:
        return "green"
    return "yellow" if exceptions <= 9 else "red"

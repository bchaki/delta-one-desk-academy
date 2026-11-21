"""Counterparty exposure and a simplified XVA.

Exposure is simulated on a TRS with periodic notional resets. All functions are deterministic for a
given ``seed``. Simplified: GBM underlying, flat hazard and rates, no wrong-way risk, no netting set,
no close-out frictions beyond a margin period of risk gap.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from core.types import Direction


@dataclass(frozen=True)
class ExposureProfile:
    times: np.ndarray  # years, length n_steps
    ee: np.ndarray  # expected (positive) exposure of the desk to the client
    pfe: np.ndarray  # potential future exposure at ``quantile``
    quantile: float

    @property
    def peak_pfe(self) -> float:
        return float(self.pfe.max())

    @property
    def epe(self) -> float:
        """Average expected exposure over the life."""
        return float(self.ee.mean())


def simulate_exposure(
    notional: float,
    vol: float,
    maturity: float,
    n_steps: int,
    reset_every: int,
    direction: Direction,
    n_paths: int = 5_000,
    seed: int = 0,
    mpor_steps: int | None = None,
    threshold: float = 0.0,
    quantile: float = 0.95,
) -> ExposureProfile:
    """Simulate the desk's exposure to the client on a TRS.

    The client MTM since the last reset is ``sign x N x (S_t / S_reset - 1)`` and resets to zero on
    reset steps. The desk is exposed when the client owes: owed = max(-client MTM, 0).

    - ``mpor_steps=None``: no CSA, exposure = owed.
    - ``mpor_steps=m``: collateral equals the MTM of m steps ago less ``threshold``, so
      exposure = max(owed_t - max(owed_{t-m} - threshold, 0), 0) (gap risk over the margin period).
    """
    rng = np.random.default_rng(seed)
    dt = maturity / n_steps
    z = rng.standard_normal((n_paths, n_steps))
    log_ret = -0.5 * vol**2 * dt + vol * math.sqrt(dt) * z
    s = np.exp(np.cumsum(log_ret, axis=1))  # S_t / S_0
    s_full = np.concatenate([np.ones((n_paths, 1)), s], axis=1)

    owed = np.zeros((n_paths, n_steps))
    last_reset = 0
    for t in range(1, n_steps + 1):
        if t % reset_every == 0:  # settled at the reset: nothing owed, next period starts here
            last_reset = t
            continue
        mtm = direction.sign * notional * (s_full[:, t] / s_full[:, last_reset] - 1.0)
        owed[:, t - 1] = np.maximum(-mtm, 0.0)

    if mpor_steps is None:
        exposure = owed
    else:
        lagged = np.zeros_like(owed)
        if mpor_steps == 0:
            lagged = owed
        elif mpor_steps < n_steps:
            lagged[:, mpor_steps:] = owed[:, :-mpor_steps]
        collateral = np.maximum(lagged - threshold, 0.0)
        exposure = np.maximum(owed - collateral, 0.0)
    times = dt * np.arange(1, n_steps + 1)
    return ExposureProfile(
        times, exposure.mean(axis=0), np.quantile(exposure, quantile, axis=0), quantile
    )


def cva(
    ee: np.ndarray, times: np.ndarray, cds_spread_bps: float, lgd: float, rate: float = 0.0
) -> float:
    """CVA = LGD x sum_i EE_i x DF_i x (S(t_{i-1}) - S(t_i)), flat hazard h = spread / LGD.

    Survival S(t) = exp(-h t); discounting at a flat continuous ``rate``. Result in the notional's
    currency. Simplified: independent exposure and default, discretised at the profile's grid.
    """
    h = cds_spread_bps / 10_000.0 / lgd
    surv = np.exp(-h * np.concatenate([[0.0], times]))
    marginal = surv[:-1] - surv[1:]
    df = np.exp(-rate * times)
    return float(lgd * np.sum(ee * df * marginal))


def fva(ee: np.ndarray, times: np.ndarray, funding_spread_bps: float, rate: float = 0.0) -> float:
    """FVA (cost) = funding spread x sum EE_i x DF_i x dt_i: the cost of funding uncollateralised exposure."""
    dts = np.diff(np.concatenate([[0.0], times]))
    return float(funding_spread_bps / 10_000.0 * np.sum(ee * np.exp(-rate * times) * dts))


def kva(
    ee: np.ndarray,
    times: np.ndarray,
    risk_weight: float,
    cet1_ratio: float,
    hurdle: float,
    rate: float = 0.0,
) -> float:
    """KVA = hurdle x sum (EE_i x RW x CET1 ratio) x DF_i x dt_i: the cost of holding capital against exposure."""
    dts = np.diff(np.concatenate([[0.0], times]))
    cap = ee * risk_weight * cet1_ratio
    return float(hurdle * np.sum(cap * np.exp(-rate * times) * dts))


def mva(avg_initial_margin: float, maturity: float, funding_spread_bps: float) -> float:
    """MVA (cost) = average posted IM x funding spread x maturity (flat IM profile approximation)."""
    return avg_initial_margin * funding_spread_bps / 10_000.0 * maturity


def xva_charge_bps(total_xva: float, notional: float, tenor_years: float) -> float:
    """Spread-equivalent XVA charge in bps per year = total XVA / notional / tenor x 10,000."""
    return total_xva / notional / tenor_years * 10_000.0

"""Futures roll and calendar spreads: what rolling costs, and when the roll is rich or cheap.

A long that rolls sells the near contract and buys the next. Roll cost in points is ``far - near``;
the financing the market charges inside it is ``(far - near + dividends between) / (near x dT)``. The
roll is rich when the spread exceeds the fair carry spread. Simplified: one flat rate per roll date,
no open-interest data (not modelled in the synthetic world), no roll-week liquidity effects.
"""

from __future__ import annotations

import math

import pandas as pd

from core.data.market import BENCH_BY_CCY, MarketHistory
from core.pricing import futures as fu
from core.strategies.common import _ccy


def roll_cost_points(near: float, far: float) -> float:
    """Points a long pays to roll: ``far - near`` (positive = cost, negative = the roll earns)."""
    return far - near


def roll_pnl(contracts: float, multiplier: float, near: float, far: float) -> float:
    """Currency cost (negative PnL) of rolling ``contracts`` long: ``-(far - near) x multiplier x contracts``."""
    return -roll_cost_points(near, far) * multiplier * contracts


def roll_events(
    m: MarketHistory, index: str, days_before: int = 5, funding_spread: float = 0.0010
) -> pd.DataFrame:
    """Roll table: one row per near expiry, evaluated ``days_before`` trading days ahead.

    Columns: ``roll_date``, ``near``, ``far``, ``f_near``, ``f_far``, ``spread``, ``fair_spread``,
    ``richness`` (points), ``cost_bps_pa`` (gross roll cost) and ``richness_bps_pa``.
    """
    bench = BENCH_BY_CCY[_ccy(index)]
    exps = sorted(e for (i, e) in m.futures if i == index)
    rows = []
    for near, far in zip(exps[:-1], exps[1:], strict=True):
        pre = [d for d in m.days if d < near]
        if len(pre) <= days_before:
            continue
        d = pre[-days_before]
        ts = pd.Timestamp(d)
        s_near, s_far = m.futures[(index, near)], m.futures[(index, far)]
        if ts not in s_near.index or ts not in s_far.index:
            continue
        spot = float(m.index_level.at[ts, index])
        r = math.log(1.0 + m.fixing(bench, d)) + funding_spread
        tn, tf = (near - d).days / 365.0, (far - d).days / 365.0
        dn = [
            ((x.ex_date - d).days / 365.0, x.amount)
            for x in m.index_dividends_between(index, d, near)
        ]
        df = [
            ((x.ex_date - d).days / 365.0, x.amount)
            for x in m.index_dividends_between(index, d, far)
        ]
        fair = fu.model_forward(spot, r, df, tf) - fu.model_forward(spot, r, dn, tn)
        fn, ff = float(s_near.loc[ts]), float(s_far.loc[ts])
        dt = tf - tn
        rows.append(
            {
                "roll_date": ts,
                "near": near,
                "far": far,
                "f_near": fn,
                "f_far": ff,
                "spread": ff - fn,
                "fair_spread": fair,
                "richness": ff - fn - fair,
                "cost_bps_pa": fu.roll_cost_bps_per_year(fn, ff, dt),
                "richness_bps_pa": fu.roll_richness_bps_per_year(fn, ff, fair, dt),
            }
        )
    return pd.DataFrame(rows).set_index("roll_date") if rows else pd.DataFrame()


def annual_roll_drag(cost_bps_pa: float, rolls_per_year: float = 4.0) -> float:
    """Reminder identity: the gross roll cost is already an annualised rate, so holding a long all year
    pays ``cost_bps_pa`` regardless of how many rolls it takes. ``rolls_per_year`` only scales the
    per-roll cost in bps: ``cost_bps_pa / rolls_per_year``.
    """
    return cost_bps_pa / rolls_per_year


__all__ = ["annual_roll_drag", "roll_cost_points", "roll_events", "roll_pnl"]

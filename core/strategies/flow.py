"""Client flow and inventory: how flow turns into PnL, and risk versus agency.

A flow desk earns the bid/offer on client trades, keeps what it can internalise (net opposing flow
without hedging), pays costs to hedge the residual and carries inventory risk while it holds
positions. All figures are in USD on a seeded simulation; this is a teaching model of the economics,
not a forecast. Simplified: one stock, normal flow, inventory hedged when it breaches a limit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


def agency_pnl(notional: float, commission_bps: float) -> float:
    """Agency: commission only, no risk: ``notional x bps / 10,000``."""
    return notional * commission_bps / 1e4


def risk_trade_ev(
    notional: float, spread_bps: float, hedge_cost_bps: float, vol_daily: float, hold_days: float
) -> dict[str, float]:
    """Risk trade: expected PnL = spread - hedge cost; one-sigma price risk = ``vol x sqrt(days) x notional``."""
    ev = notional * (spread_bps - hedge_cost_bps) / 1e4
    sd = notional * vol_daily * math.sqrt(hold_days)
    return {"expected": ev, "one_sigma_risk": sd, "ratio": ev / sd if sd else math.inf}


@dataclass(frozen=True)
class FlowSim:
    daily: pd.DataFrame
    total_spread: float
    total_hedge_cost: float
    total_price_pnl: float

    @property
    def total(self) -> float:
        return self.total_spread - self.total_hedge_cost + self.total_price_pnl


def simulate(
    seed: int,
    days: int = 250,
    mean_trade: float = 2_000_000.0,
    trades_per_day: int = 6,
    spread_bps: float = 8.0,
    hedge_cost_bps: float = 3.0,
    daily_vol: float = 0.015,
    inventory_limit: float = 5_000_000.0,
    buy_bias: float = 0.0,
) -> FlowSim:
    """Simulate client flow against one name.

    Each day ``trades_per_day`` client trades of normal size arrive (sign +1 = client buys from the desk;
    ``buy_bias`` shifts the probability). The desk earns ``spread_bps`` on each. Inventory (desk
    position, USD) moves opposite to client flow and earns the price move. When ``|inventory|`` exceeds
    ``inventory_limit`` the excess is hedged at ``hedge_cost_bps``. Internalisation = the share of
    notional that never needs hedging.
    """
    rng = np.random.default_rng(seed)
    inv = 0.0
    rows = []
    for d in range(days):
        signs = np.where(rng.random(trades_per_day) < 0.5 + buy_bias, 1.0, -1.0)
        sizes = np.abs(rng.normal(mean_trade, mean_trade / 2, trades_per_day))
        flow = float((signs * sizes).sum())
        gross = float(sizes.sum())
        inv -= flow  # client buys -> desk goes short
        ret = rng.normal(0.0, daily_vol)
        price_pnl = inv * ret
        hedged = max(abs(inv) - inventory_limit, 0.0)
        inv = math.copysign(min(abs(inv), inventory_limit), inv)
        rows.append(
            {
                "day": d,
                "gross": gross,
                "net_flow": flow,
                "inventory": inv,
                "hedged": hedged,
                "spread": gross * spread_bps / 1e4,
                "hedge_cost": hedged * hedge_cost_bps / 1e4,
                "price_pnl": price_pnl,
            }
        )
    df = pd.DataFrame(rows).set_index("day")
    return FlowSim(
        df, float(df.spread.sum()), float(df.hedge_cost.sum()), float(df.price_pnl.sum())
    )


def internalisation_rate(df: pd.DataFrame) -> float:
    """Share of gross client notional that did not have to be hedged: ``1 - hedged / gross``."""
    return 1.0 - float(df.hedged.sum() / df.gross.sum())

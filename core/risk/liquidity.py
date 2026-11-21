"""Liquidity and concentration of hedge inventory (the positions the desk would have to trade)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from core.data.market import MarketHistory


def liquidity_table(
    snap: pd.DataFrame, m: MarketHistory, d: date, participation: float = 0.20
) -> pd.DataFrame:
    """Stock inventory: ``pct_adv`` = |shares| / ADV; ``days_to_liquidate`` = |shares| / (participation x ADV).

    ADV is in shares per day (``Stock.adv`` scaled by the cumulative quantity factor). Swaps are client
    positions and are excluded: only cash inventory is liquidated.
    """
    rows = []
    ts = pd.Timestamp(d)
    for _, r in snap[snap.kind == "stock"].iterrows():
        tick = r.key.split(":")[1]
        shares = r.cash_usd / (
            float(m.prices[tick].ffill().at[ts]) * m.fx_usd_per(m.universe.stocks[tick].ccy, d)
        )
        adv = m.stock_adv(tick, m.clamp(d))
        rows.append(
            {
                "ticker": tick,
                "shares": shares,
                "pct_adv": abs(shares) / adv,
                "days_to_liquidate": abs(shares) / (participation * adv),
                "cash_usd": r.cash_usd,
            }
        )
    return pd.DataFrame(
        rows, columns=["ticker", "shares", "pct_adv", "days_to_liquidate", "cash_usd"]
    )


def concentration(snap: pd.DataFrame) -> dict[str, float]:
    """Top-5 share of gross cash inventory and the Herfindahl index (sum of squared shares, 1/n..1)."""
    g = snap.cash_usd.abs()
    tot = float(g.sum())
    if tot == 0:
        return {"top5": 0.0, "hhi": 0.0}
    sh = (g / tot).sort_values(ascending=False)
    return {"top5": float(sh.head(5).sum()), "hhi": float(np.sum(sh**2))}

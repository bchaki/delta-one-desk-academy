"""Securities lending strategies: finding specials, lending revenue, recalls and collateral upgrades.

Fees are bps a year on loan value (ACT/360, basis 360). Revenue is shared with the beneficial owner by
the agent split. Simplified: fee held flat over the period, no recall risk in the revenue estimate.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from core.data.market import MarketHistory
from core.financing import sbl


def lending_revenue(
    lendable_value: float,
    utilisation: float,
    fee_bps: float,
    days: int,
    lender_share: float = 0.85,
    basis: int = 360,
) -> dict[str, float]:
    """Revenue on a lendable inventory: ``value x utilisation x fee x days/basis``; split lender/agent."""
    gross = lendable_value * utilisation * fee_bps / 1e4 * days / basis
    lender, agent = sbl.revenue_split(gross, lender_share)
    return {"gross": gross, "lender": lender, "agent": agent}


def utilisation_revenue_curve(
    lendable_value: float, gc_fee_bps: float, steepness: float, days: int = 360
) -> pd.DataFrame:
    """Revenue as utilisation rises: convex fee x rising volume. Shows where pricing power sits."""
    us = [i / 100 for i in range(5, 100, 5)]
    rows = []
    for u in us:
        fee = sbl.fee_from_utilisation(u, gc_fee_bps, steepness)
        rows.append(
            {
                "utilisation": u,
                "fee_bps": fee,
                "revenue": lending_revenue(lendable_value, u, fee, days)["gross"],
            }
        )
    return pd.DataFrame(rows).set_index("utilisation")


def specials_screen(m: MarketHistory, d: date, top: int = 10) -> pd.DataFrame:
    """Rank names by annual lending revenue potential: lendable value x utilisation x fee.

    Lendable value = shares outstanding x lendable_pct x price (synthetic profile). Columns: ``fee_bps``,
    ``utilisation`` (latest), ``lendable_value``, ``revenue_pa``.
    """
    ts = pd.Timestamp(d)
    rows = []
    for t, s in m.universe.stocks.items():
        if s.listed_from and s.listed_from > d:
            continue
        px = m.price(t, d)
        lendable = m.shares_outstanding(t, d) * s.borrow.lendable_pct * px
        fee = float(m.borrow_fee_bps[t].loc[ts])
        u = float(m.utilisation[t].loc[ts])
        rows.append(
            {
                "ticker": t,
                "fee_bps": fee,
                "utilisation": u,
                "lendable_value": lendable,
                "revenue_pa": lendable * u * fee / 1e4,
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values("revenue_pa", ascending=False)
        .head(top)
        .reset_index(drop=True)
    )


def collateral_upgrade_revenue(
    notional: float, fee_bps: float, days: int, basis: int = 360
) -> float:
    """Revenue from lending high-quality collateral against lower-quality: ``notional x fee x days/basis``."""
    return notional * fee_bps / 1e4 * days / basis


def recall_cost_ranking(
    shares: float,
    price: float,
    old_fee: float,
    new_fee: float,
    days: int,
    buyin_premium: float,
    buyin_impact: float,
    internal_cost: float,
    basis: int = 360,
) -> list[tuple[str, float]]:
    """The three recall responses sorted cheapest first (uses ``core.financing.sbl.recall_options``)."""
    opts = sbl.recall_options(
        shares, price, old_fee, new_fee, days, basis, buyin_premium, buyin_impact, internal_cost
    )
    return sorted(opts.items(), key=lambda kv: kv[1])

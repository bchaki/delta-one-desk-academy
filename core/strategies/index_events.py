"""Index rebalance and event trading: adds, deletes, pre-positioning and facilitation at the close.

Event study on the synthetic index membership history: for each add or delete, return from
``lead`` trading days before the effective date to the effective date's close, and the reversal
over the next ``lag`` days. Positive return on an add = the pre-position paid. Simplified: closes,
no impact on the synthetic prices from the trade itself, effective date taken from the membership
change date; the full version uses announcement dates and a demand model.
"""

from __future__ import annotations

import pandas as pd

from core.data.market import MarketHistory
from core.pricing.program_trading import sqrt_impact_bps


def membership_changes(m: MarketHistory, index: str) -> pd.DataFrame:
    """Adds and deletes from the membership history: columns ``date``, ``ticker``, ``kind``."""
    hist = m.index_members[index]
    rows = []
    for (_, prev), (d, cur) in zip(hist[:-1], hist[1:], strict=True):
        rows += [{"date": d, "ticker": t, "kind": "add"} for t in sorted(set(cur) - set(prev))]
        rows += [{"date": d, "ticker": t, "kind": "delete"} for t in sorted(set(prev) - set(cur))]
    return pd.DataFrame(rows, columns=["date", "ticker", "kind"])


def event_study(m: MarketHistory, index: str, lead: int = 5, lag: int = 5) -> pd.DataFrame:
    """Return from ``lead`` days before to the effective date, and the next ``lag`` days, in bps."""
    ch = membership_changes(m, index)
    days = list(m.prices.index)
    out = []
    for r in ch.itertuples():
        ts = pd.Timestamp(r.date)
        if ts not in m.prices.index:
            continue
        i = days.index(ts)
        if i - lead < 0 or i + lag >= len(days):
            continue
        p = m.prices[r.ticker]
        pre = float(p.iloc[i] / p.iloc[i - lead] - 1) * 1e4
        post = float(p.iloc[i + lag] / p.iloc[i] - 1) * 1e4
        out.append(
            {"date": ts, "ticker": r.ticker, "kind": r.kind, "pre_bps": pre, "post_bps": post}
        )
    return pd.DataFrame(out, columns=["date", "ticker", "kind", "pre_bps", "post_bps"])


def preposition_pnl(
    notional: float, pre_move_bps: float, impact_bps: float, cost_bps: float, side: int = 1
) -> float:
    """PnL of buying (``side`` 1) or shorting (-1) ahead: ``notional x (side x move - impact - cost)/10,000``."""
    return notional * (side * pre_move_bps - impact_bps - cost_bps) / 1e4


def crowded_unwind_bps(
    shares: float, adv: float, daily_vol: float, k: float, crowd_multiplier: float
) -> float:
    """Exit impact when many hold the same pre-position: square-root impact scaled by ``crowd_multiplier``."""
    return sqrt_impact_bps(k, daily_vol, shares, adv) * crowd_multiplier


def moc_facilitation_pnl(
    shares: float, price: float, fee_bps: float, hedge_slippage_bps: float
) -> float:
    """Desk guarantees the closing price to an index fund: earns ``fee`` and pays hedge slippage vs the close.

    ``pnl = shares x price x (fee - slippage) / 10,000``. Slippage is the average hedge price versus
    the close, positive = worse for the desk.
    """
    return shares * price * (fee_bps - hedge_slippage_bps) / 1e4

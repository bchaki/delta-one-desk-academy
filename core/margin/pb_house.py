"""Prime brokerage house margin: a base rate plus add-ons (teaching model, config/margin.yaml).

Base = max(min base, vol multiplier x daily vol x sqrt(horizon)) x |MV|. Add-ons: concentration,
liquidity (position / ADV), directionality (net / gross) and squeeze risk (shorts with high short interest).
The point of the add-ons: a concentrated book can look safe under simple margin (the Archegos lesson).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from core import config


@dataclass(frozen=True)
class PBPosition:
    ticker: str
    market_value: float  # signed
    price: float
    adv_shares: float
    daily_vol: float
    short_interest: float = 0.0  # fraction of free float


@dataclass(frozen=True)
class PBMargin:
    base: float
    concentration: float
    liquidity: float
    directionality: float
    squeeze: float
    by_position: dict[str, float]

    @property
    def addons(self) -> float:
        return self.concentration + self.liquidity + self.directionality + self.squeeze

    @property
    def total(self) -> float:
        return self.base + self.addons


def base_rate(daily_vol: float) -> float:
    """Base margin rate = max(min base, vol multiplier x daily vol x sqrt(horizon days))."""
    p = config.margin().pb_house
    return max(p.min_base_pct, p.vol_multiplier * daily_vol * math.sqrt(p.horizon_days))


def pb_house_margin(positions: Sequence[PBPosition], equity: float) -> PBMargin:
    """House margin for a book given client ``equity`` (net liquidating value).

    - concentration: rate x max(|MV| - threshold x equity, 0)
    - liquidity: min(per-day add-on x max(days of ADV - threshold, 0), cap) x |MV|
    - directionality (book level): if |net| / gross > threshold, pct x |net MV|
    - squeeze (shorts): if short interest > threshold, pct x |MV|
    """
    p = config.margin().pb_house
    base = conc = liq = squeeze = 0.0
    by_pos: dict[str, float] = {}
    net = gross = 0.0
    for pos in positions:
        mv = abs(pos.market_value)
        b = base_rate(pos.daily_vol) * mv
        c = p.concentration_addon_rate * max(mv - p.concentration_threshold_pct * equity, 0.0)
        shares = mv / pos.price
        days = shares / pos.adv_shares
        pct = min(
            p.liquidity_addon_per_day * max(days - p.liquidity_days_threshold, 0.0),
            p.liquidity_addon_cap,
        )
        lq = pct * mv
        sq = (
            p.squeeze_addon_pct * mv
            if pos.market_value < 0 and pos.short_interest > p.squeeze_short_interest_threshold
            else 0.0
        )
        base += b
        conc += c
        liq += lq
        squeeze += sq
        by_pos[pos.ticker] = b + c + lq + sq
        net += pos.market_value
        gross += mv
    direc = 0.0
    if gross > 0 and abs(net) / gross > p.directionality_threshold:
        direc = p.directionality_addon_pct * abs(net)
    return PBMargin(base, conc, liq, direc, squeeze, by_pos)

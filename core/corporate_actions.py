"""Corporate action adjustment factors.

Each function returns a :class:`CAAdjustment`. Applying it to a position leaves the position's
value (stock + cash + new securities) unchanged when the event is processed correctly. Unless
noted, factors assume the holder is entitled to (and takes up) the event.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CAAdjustment:
    """Adjustment to a position of one old share.

    new qty = qty x qty_factor; new price = price x price_factor; cash = qty x cash_per_old_share;
    new_asset_ratio units of a new security (price new_asset_price) per old share.
    """

    qty_factor: float = 1.0
    price_factor: float = 1.0
    cash_per_old_share: float = 0.0
    new_asset_ratio: float = 0.0
    new_asset_price: float = 0.0


def value_per_old_share(price: float, adj: CAAdjustment) -> float:
    """Value after the event of one pre-event share: P x pf x qf + cash + ratio x new price."""
    return (
        price * adj.price_factor * adj.qty_factor
        + adj.cash_per_old_share
        + adj.new_asset_ratio * adj.new_asset_price
    )


def split(new_per_old: float) -> CAAdjustment:
    """Stock split of ``new_per_old`` new shares per old (2.0 = 2-for-1, 0.1 = 1-for-10 reverse).

    qty x ratio, price / ratio.
    """
    if new_per_old <= 0:
        raise ValueError("ratio must be positive")
    return CAAdjustment(qty_factor=new_per_old, price_factor=1.0 / new_per_old)


def rights_issue_terp(price_cum: float, subscription_price: float, new_per_old: float) -> float:
    """Theoretical ex-rights price: TERP = (P + ratio x K) / (1 + ratio)."""
    return (price_cum + new_per_old * subscription_price) / (1.0 + new_per_old)


def rights_issue(price_cum: float, subscription_price: float, new_per_old: float) -> CAAdjustment:
    """Rights issue adjustment, holder takes up the rights (value-neutral).

    price factor = TERP / P; quantity factor = P / TERP so notional is unchanged. Real exchange
    and swap terms differ in how they round and whether quantity or price carries the change.
    """
    terp = rights_issue_terp(price_cum, subscription_price, new_per_old)
    return CAAdjustment(qty_factor=price_cum / terp, price_factor=terp / price_cum)


def special_dividend(price_cum: float, amount: float) -> CAAdjustment:
    """Special dividend treated as an adjustment: price factor (P - D) / P, cash D per share."""
    return CAAdjustment(price_factor=(price_cum - amount) / price_cum, cash_per_old_share=amount)


def spin_off(price_cum: float, spin_value_per_old_share: float, new_per_old: float) -> CAAdjustment:
    """Spin-off: parent price factor (P - v) / P, plus ``new_per_old`` spun-off shares per parent
    share worth ``v`` in total (so the spun-off price is v / new_per_old)."""
    return CAAdjustment(
        price_factor=(price_cum - spin_value_per_old_share) / price_cum,
        new_asset_ratio=new_per_old,
        new_asset_price=spin_value_per_old_share / new_per_old,
    )


def cash_merger(offer_price: float) -> CAAdjustment:
    """Cash takeover: the position is closed and ``offer_price`` per share is received."""
    return CAAdjustment(qty_factor=0.0, cash_per_old_share=offer_price)


def stock_merger(
    target_price: float, acquirer_price: float, exchange_ratio: float, cash_per_share: float = 0.0
) -> CAAdjustment:
    """Stock (or mixed) merger: ``exchange_ratio`` acquirer shares + cash per target share.

    qty x ratio, price x (A / P). Value after = ratio x A + cash. Value is preserved only when
    the target traded exactly at the deal value; otherwise the merger-arb spread shows up as PnL.
    """
    return CAAdjustment(
        qty_factor=exchange_ratio,
        price_factor=acquirer_price / target_price,
        cash_per_old_share=cash_per_share,
    )


def apply_to_position(
    qty: float, price: float, adj: CAAdjustment
) -> tuple[float, float, float, float]:
    """Return ``(new_qty, new_price, cash, new_asset_qty)`` for a position of ``qty`` at ``price``."""
    return (
        qty * adj.qty_factor,
        price * adj.price_factor,
        qty * adj.cash_per_old_share,
        qty * adj.new_asset_ratio,
    )

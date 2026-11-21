"""CSA collateral calls: threshold, minimum transfer amount, independent amount, rounding, haircuts.

Exposure is the desk's MTM on the trade(s): positive when the counterparty owes the desk. A positive
call means the counterparty must post; a negative call is a return to the counterparty.
Simplified: single currency, no valuation-time lag, no interest on collateral.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CsaTerms:
    threshold_cpty: float = 0.0  # unsecured amount before the counterparty posts
    threshold_desk: float = 0.0
    mta: float = 0.0
    independent_amount_cpty: float = 0.0  # IA the counterparty posts regardless of MTM
    independent_amount_desk: float = 0.0
    rounding: float = 0.0


def collateral_value(assets: Sequence[tuple[float, float]]) -> float:
    """Value after haircuts of collateral held: sum market value x (1 - haircut)."""
    return sum(mv * (1.0 - h) for mv, h in assets)


def required_collateral(exposure: float, terms: CsaTerms) -> float:
    """Collateral the desk should hold (negative = should have posted).

    = max(E - threshold_cpty, 0) - max(-E - threshold_desk, 0) + IA_cpty - IA_desk.
    """
    return (
        max(exposure - terms.threshold_cpty, 0.0)
        - max(-exposure - terms.threshold_desk, 0.0)
        + terms.independent_amount_cpty
        - terms.independent_amount_desk
    )


@dataclass(frozen=True)
class CallResult:
    exposure: float
    required: float
    held: float
    raw: float
    amount: float  # signed after MTA and rounding: + counterparty posts, - desk returns


def collateral_call(exposure: float, held_value: float, terms: CsaTerms) -> CallResult:
    """Call/return = required - held, ignored below the MTA. Calls round up, returns round down
    to the rounding multiple (the standard convention in favour of the party holding the risk)."""
    required = required_collateral(exposure, terms)
    raw = required - held_value
    if abs(raw) < terms.mta or raw == 0:
        return CallResult(exposure, required, held_value, raw, 0.0)
    if terms.rounding > 0:
        step = terms.rounding
        amount = math.ceil(raw / step) * step if raw > 0 else -math.floor(-raw / step) * step
    else:
        amount = raw
    return CallResult(exposure, required, held_value, raw, amount)


def call_path(
    exposures: Sequence[float], terms: CsaTerms, haircut: float = 0.0
) -> list[CallResult]:
    """Margin calls along an exposure path, assuming every call is settled in haircut cash-equivalent.

    Posting ``amount`` of market value adds ``amount x (1 - haircut)`` of collateral value.
    """
    held = 0.0
    out = []
    for e in exposures:
        r = collateral_call(e, held, terms)
        out.append(r)
        held += r.amount * (1.0 - haircut)
    return out


@dataclass(frozen=True)
class DisputeResult:
    undisputed: float
    disputed: float


def dispute(own_call: float, counterparty_call: float) -> DisputeResult:
    """Standard practice: transfer the undisputed amount (the smaller call), then resolve the rest.

    Both calls signed as above; the undisputed amount is the one both sides agree to at minimum.
    """
    if own_call * counterparty_call <= 0:
        return DisputeResult(0.0, abs(own_call - counterparty_call))
    undisputed = math.copysign(min(abs(own_call), abs(counterparty_call)), own_call)
    return DisputeResult(undisputed, abs(own_call - counterparty_call))

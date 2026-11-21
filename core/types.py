"""Shared enums, aliases and the money-rounding helper used across ``core``."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum

Date = date


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"


class DayCount(StrEnum):
    ACT360 = "ACT/360"
    ACT365F = "ACT/365F"
    THIRTY360 = "30/360"
    ACTACT = "ACT/ACT"


class Benchmark(StrEnum):
    SOFR = "SOFR"
    ESTR = "ESTR"
    SONIA = "SONIA"
    TONA = "TONA"
    SARON = "SARON"


class Direction(StrEnum):
    """Direction of the *client* (or position holder) exposure."""

    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def sign(self) -> int:
        return 1 if self is Direction.LONG else -1


class Side(StrEnum):
    """Whose side a cash flow is from."""

    CLIENT = "CLIENT"
    DESK = "DESK"


def money(x: float, ndigits: int = 2) -> float:
    """Round an amount to ``ndigits`` decimals using banker's rounding (half-even).

    Goes through ``Decimal(repr(x))`` so that e.g. 2.675 is treated as the decimal
    the caller wrote, not its binary approximation. Used at the cash-flow and booking
    boundary only; analytics stay in float64.
    """
    q = Decimal(1).scaleb(-ndigits)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_EVEN))

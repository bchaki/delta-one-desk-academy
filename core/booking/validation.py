"""Booking validation rules for swap and futures tickets (the "Trade ticket" sandbox)."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from core.booking.models import Client, EquitySwapTrade, FutureTrade, ValidationIssue
from core.conventions import is_business_day
from core.data.market import BENCH_BY_CCY, CAL_BY_BENCH
from core.types import Benchmark, Direction

SPREAD_MIN_BPS, SPREAD_MAX_BPS = 0.0, 300.0
VALID_RESET_MONTHS = (1, 3, 6, 12)


def validate_swap(trade: EquitySwapTrade, client: Client | None) -> list[ValidationIssue]:
    """Business rules for an equity swap ticket. Errors block booking; warnings need a second look."""
    out: list[ValidationIssue] = []

    def err(f: str, msg: str) -> None:
        out.append(ValidationIssue(field=f, severity="error", message=msg))

    def warn(f: str, msg: str) -> None:
        out.append(ValidationIssue(field=f, severity="warning", message=msg))

    cal = CAL_BY_BENCH[trade.benchmark]
    if not is_business_day(trade.effective_date, cal):
        err(
            "effective_date",
            f"{trade.effective_date} is not a business day on the {cal.value} calendar",
        )
    if trade.effective_date < trade.trade_date:
        err("effective_date", "effective date is before the trade date")
    if trade.shares <= 0 or trade.initial_price <= 0:
        err("shares", "quantity and initial price must be positive")
    if not SPREAD_MIN_BPS <= trade.spread_bps <= SPREAD_MAX_BPS:
        err(
            "spread_bps",
            f"spread {trade.spread_bps:.1f} bps is outside {SPREAD_MIN_BPS:.0f}-{SPREAD_MAX_BPS:.0f} bps",
        )
    elif (
        trade.direction is Direction.SHORT
        and trade.borrow_bps
        and trade.spread_bps < trade.borrow_bps
    ):
        warn(
            "spread_bps", "short spread is below the borrow cost: the desk pays to carry this trade"
        )
    if not 0 < trade.pass_through <= 1.0:
        err("pass_through", "dividend pass-through must be within (0%, 100%]")
    if trade.reset_months not in VALID_RESET_MONTHS:
        err("reset_months", f"reset frequency must be one of {VALID_RESET_MONTHS} months")
    if BENCH_BY_CCY[trade.ccy] is not trade.benchmark and not isinstance(
        trade.benchmark, Benchmark
    ):
        err("benchmark", "benchmark not recognised")
    elif BENCH_BY_CCY[trade.ccy] is not trade.benchmark:
        err("benchmark", f"{trade.benchmark.value} does not match currency {trade.ccy.value}")
    if not trade.isda_ref.strip():
        err("isda_ref", "missing ISDA / CSA reference")
    if client is None:
        err("counterparty_id", "unknown counterparty")
        return out
    if not client.csa.in_force:
        err("csa", f"no CSA in force for {client.name}: the trade cannot be margined")
    if trade.legal_entity != client.legal_entity:
        err(
            "legal_entity",
            f"legal entity {trade.legal_entity!r} does not match the counterparty's "
            f"{client.legal_entity!r}",
        )
    needs_871m = trade.underlying.startswith("stock:") and client.domicile != "US" and _is_us(trade)
    if needs_871m and not trade.flag_871m:
        err("flag_871m", "US underlying with a non-US client: the 871(m) flag must be set")
    if trade.flag_871m and not needs_871m:
        warn("flag_871m", "871(m) flag set but the trade does not look in scope")
    return out


def _is_us(trade: EquitySwapTrade) -> bool:
    return trade.ccy.value == "USD"


def validate_future(trade: FutureTrade) -> list[ValidationIssue]:
    out: list[ValidationIssue] = []
    if trade.qty == 0:
        out.append(
            ValidationIssue(field="qty", severity="error", message="quantity must be non-zero")
        )
    if trade.price <= 0:
        out.append(
            ValidationIssue(field="price", severity="error", message="price must be positive")
        )
    if trade.expiry < trade.trade_date:
        out.append(
            ValidationIssue(
                field="expiry", severity="error", message="contract expires before the trade date"
            )
        )
    return out


def parse_swap_ticket(
    data: dict[str, Any], client: Client | None
) -> tuple[EquitySwapTrade | None, list[ValidationIssue]]:
    """Build a swap from raw ticket fields; pydantic type errors become validation issues."""
    try:
        trade = EquitySwapTrade(**data)
    except ValidationError as e:
        return None, [
            ValidationIssue(
                field=str(err["loc"][0]) if err["loc"] else "ticket",
                severity="error",
                message=err["msg"],
            )
            for err in e.errors()
        ]
    return trade, validate_swap(trade, client)

"""Pydantic data models: clients, CSA terms, the trade union, lifecycle events, cash flows, breaks."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from core.margin.csa import CsaTerms
from core.types import Benchmark, Currency, Direction, Side


class _M(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CSAModel(_M):
    threshold_cpty: float = 0.0
    threshold_desk: float = 0.0
    mta: float = 0.0
    ia_cpty: float = 0.0
    ia_desk: float = 0.0
    rounding: float = 0.0
    in_force: bool = True
    eligible_collateral: tuple[str, ...] = ("cash",)
    haircuts: dict[str, float] = Field(default_factory=lambda: {"cash": 0.0})

    def terms(self) -> CsaTerms:
        return CsaTerms(
            threshold_cpty=self.threshold_cpty,
            threshold_desk=self.threshold_desk,
            mta=self.mta,
            independent_amount_cpty=self.ia_cpty,
            independent_amount_desk=self.ia_desk,
            rounding=self.rounding,
        )


ClientType = Literal["hedge_fund", "asset_manager", "pension", "insurer", "internal"]
MarginMethod = Literal["exchange", "simm", "schedule", "reg_t", "portfolio", "pb_house"]


class Client(_M):
    id: str
    name: str
    type: ClientType
    tier: int  # 1 = best credit / most strategic
    domicile: Literal["US", "non-US"]
    legal_entity: str
    csa: CSAModel
    margin_method: MarginMethod


class TradeBase(_M):
    trade_id: str
    trade_date: date
    effective_date: date
    book: str
    counterparty_id: str | None = None
    legal_entity: str | None = None
    sales_credit: float = 0.0  # currency units paid out of PnL on the trade date
    status: Literal["live", "terminated", "matured"] = "live"
    package_id: str | None = None
    linked_trade_id: str | None = None  # hedge -> the client trade it hedges
    end_date: date | None = None  # last day a financing trade (SBL, repo, swap) is live


class EquitySwapTrade(TradeBase):
    product: Literal["equity_swap"] = "equity_swap"
    underlying: str  # "stock:TICK" or "index:NAME"
    direction: Direction  # client direction
    shares: float
    initial_price: float
    spread_bps: float
    benchmark: Benchmark
    reset_months: int = 1
    pass_through: float = 1.0
    notional_reset: bool = True
    flag_871m: bool = False
    isda_ref: str = ""
    ccy: Currency = Currency.USD
    borrow_bps: float = 0.0
    day_count_basis: int = 360


class FutureTrade(TradeBase):
    product: Literal["future"] = "future"
    index: str
    expiry: date
    qty: int
    price: float
    multiplier: float
    ccy: Currency


class CashEquityTrade(TradeBase):
    product: Literal["cash_equity"] = "cash_equity"
    ticker: str
    qty: float
    price: float
    ccy: Currency
    purpose: str = "swap_hedge"


class EtfTrade(TradeBase):
    product: Literal["etf"] = "etf"
    ticker: str
    qty: float
    price: float
    ccy: Currency


class SblTrade(TradeBase):
    product: Literal["sbl"] = "sbl"
    ticker: str
    side: Literal["borrow", "loan"]
    shares: float
    fee_bps: float
    collateral: Literal["cash", "non_cash"] = "cash"
    margin: float = 1.02
    ccy: Currency = Currency.USD
    ref_price: float = 0.0


class RepoTrade(TradeBase):
    product: Literal["repo"] = "repo"
    ticker: str
    qty: float
    price: float
    haircut: float
    spread_bps: float
    term_days: int | None = None
    ccy: Currency = Currency.USD


class DividendFutureTrade(TradeBase):
    product: Literal["dividend_future"] = "dividend_future"
    instrument: Literal["future", "swap"] = "future"
    index: str = "D1 Europe 20"
    year: int
    units: float  # currency per index point, signed (+ long dividends)
    strike: float
    ccy: Currency = Currency.EUR


Trade = Annotated[
    EquitySwapTrade
    | FutureTrade
    | CashEquityTrade
    | EtfTrade
    | SblTrade
    | RepoTrade
    | DividendFutureTrade,
    Field(discriminator="product"),
]


# --------------------------------------------------------------------------- lifecycle


class Reset(_M):
    kind: Literal["reset"] = "reset"
    trade_id: str
    date: date
    price: float
    benchmark_rate: float


class DividendPayment(_M):
    kind: Literal["dividend"] = "dividend"
    trade_id: str
    date: date
    amount: float  # per share (or index points) gross


class CAAdjustment(_M):
    kind: Literal["ca_adjustment"] = "ca_adjustment"
    trade_id: str
    date: date
    qty_factor: float
    price_factor: float
    cash_per_share: float = 0.0


class PartialUnwind(_M):
    kind: Literal["partial_unwind"] = "partial_unwind"
    trade_id: str
    date: date
    shares_unwound: float
    price: float


class Termination(_M):
    kind: Literal["termination"] = "termination"
    trade_id: str
    date: date
    price: float


class Amendment(_M):
    kind: Literal["amendment"] = "amendment"
    trade_id: str
    date: date
    field: str
    old_value: float
    new_value: float
    upfront: float = 0.0


LifecycleEvent = Annotated[
    Reset | DividendPayment | CAAdjustment | PartialUnwind | Termination | Amendment,
    Field(discriminator="kind"),
]


class Cashflow(_M):
    date: date
    trade_id: str
    type: str
    amount: float  # positive = received by the desk
    ccy: Currency
    payer: Side
    status: Literal["projected", "fixed", "settled"] = "settled"


BreakKind = Literal[
    "missed_dividend", "wrong_fixing", "wrong_spread", "wrong_entity", "stale_price"
]


class SeededBreak(_M):
    kind: BreakKind
    trade_id: str
    date: date
    ticker: str | None = None
    pnl_impact: float = 0.0  # booked ledger minus true, USD, on the break date(s)
    clue: str = ""
    detail: dict[str, float | str] = Field(default_factory=dict)


class ValidationIssue(_M):
    field: str
    severity: Literal["error", "warning"]
    message: str

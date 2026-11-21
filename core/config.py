"""Typed, validated loaders for ``config/*.yaml``.

Every file carries ``as_of``, ``source`` and ``verify``. The UI shows these next to any
illustrative parameter ("Illustrative, verify against the official source").
"""

from __future__ import annotations

from datetime import date
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from core.conventions import CalendarName
from core.types import Benchmark, Currency, DayCount

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
ILLUSTRATIVE_LABEL = "Illustrative, verify against the official source"


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class IllustrativeParams(_Base):
    """Header shared by every config file."""

    as_of: date
    source: str
    verify: bool = True

    @property
    def label(self) -> str:
        return f"{ILLUSTRATIVE_LABEL} (as of {self.as_of.isoformat()})"


# ------------------------------------------------------------------ conventions


class BenchmarkConvention(_Base):
    ccy: Currency
    day_count: DayCount
    name: str


class MarketConvention(_Base):
    name: str
    ccy: Currency
    calendar: CalendarName
    benchmark: Benchmark
    settlement_days: int
    settlement_note: str
    hours: str
    open_auction: str
    close_auction: str
    tick_regime: str
    transaction_tax_bps: float
    transaction_tax_note: str


class ConventionsConfig(IllustrativeParams):
    benchmarks: dict[Benchmark, BenchmarkConvention]
    markets: dict[str, MarketConvention]


# ------------------------------------------------------------------ contracts


class FutureSpec(_Base):
    name: str
    exchange: str
    ccy: Currency
    multiplier: float
    tick: float
    cycle_months: list[int]
    last_trading_day: str
    settlement: str
    hours: str
    index_key: str | None = None

    @property
    def tick_value(self) -> float:
        """Currency value of one tick = tick x multiplier."""
        return self.tick * self.multiplier


class ContractsConfig(IllustrativeParams):
    contracts: dict[str, FutureSpec]


# ------------------------------------------------------------------ margin


class ExchangeMarginParams(_Base):
    scan_range_pct: dict[str, float]
    scan_points: int
    calendar_spread_charge_pct: float
    inter_index_credit: dict[str, float]
    var_confidence: float
    var_horizon_days: int


class RegTParams(_Base):
    initial_pct: float
    maintenance_long_pct: float
    short_initial_pct: float
    short_maintenance_pct: float


class PortfolioMarginParams(_Base):
    index_range_pct: float
    single_name_range_pct: float
    grid_points: int
    min_margin_pct: float


class PBHouseParams(_Base):
    vol_multiplier: float
    horizon_days: int
    min_base_pct: float
    concentration_threshold_pct: float
    concentration_addon_rate: float
    liquidity_days_threshold: float
    liquidity_addon_per_day: float
    liquidity_addon_cap: float
    directionality_threshold: float
    directionality_addon_pct: float
    squeeze_short_interest_threshold: float
    squeeze_addon_pct: float


class MarginConfig(IllustrativeParams):
    exchange: ExchangeMarginParams
    regt: RegTParams
    portfolio_margin: PortfolioMarginParams
    pb_house: PBHouseParams


class SimmEquityParams(_Base):
    risk_weight: dict[int, float]
    rho_intra: float
    gamma: float
    residual_bucket: int


class SimmSchedule(_Base):
    equity_swap_pct: float
    gross_weight: float


class SimmConfig(IllustrativeParams):
    equity_delta: SimmEquityParams
    schedule: SimmSchedule


# ------------------------------------------------------------------ tax and regulation


class WithholdingRate(_Base):
    statutory_pct: float
    treaty_pct: float
    note: str


class WithholdingConfig(IllustrativeParams):
    rates: dict[str, WithholdingRate]


class KeyDate(_Base):
    date: date
    event: str


class RegRule(_Base):
    id: str
    name: str
    region: str
    summary: str
    d1_impact: str
    source: str
    verify: bool
    key_dates: list[KeyDate]


class RegulationConfig(IllustrativeParams):
    rules: list[RegRule]


# ------------------------------------------------------------------ scenarios


class Scenario(_Base):
    name: str
    kind: str
    equity_pct: dict[str, float]
    vol_pts: float
    rates_bps: dict[str, float]
    fx_pct: dict[str, float]
    div_pct: dict[str, float]
    borrow_bps: dict[str, float]
    single_name_pct: float


class ScenariosConfig(IllustrativeParams):
    scenarios: dict[str, Scenario]


# ------------------------------------------------------------------ desk


class TradingCosts(_Base):
    stock_commission_bps: float
    stock_half_spread_bps: float
    futures_half_spread_bps: float
    futures_commission_bps: float
    impact_k: float
    risk_aversion: float
    liquidation_horizon_days: float


class BalanceSheetParams(_Base):
    cost_bps_per_year_on_exposure: float
    leverage_ratio_target: float
    cet1_ratio: float
    cost_of_equity: float
    hedge_inventory_rw: float
    counterparty_rw: dict[str, float]
    sa_ccr_alpha: float
    sa_ccr_equity_supervisory_factor: float
    sa_ccr_index_supervisory_factor: float


class XvaParams(_Base):
    cds_spread_bps: dict[str, float]
    lgd: float
    funding_spread_bps: float
    kva_hurdle: float
    mva_funding_bps: float


class SblParams(_Base):
    margin_domestic: float
    margin_cross_border: float
    lender_share: float
    agent_share: float
    fee_tier_bps: dict[str, float]
    reinvestment_spread_bps: float
    buyin_premium_pct: float


class RepoParams(_Base):
    haircut_by_quality: dict[str, float]
    gc_spread_bps: float
    special_spread_bps_per_fee_bps: float
    term_premium_bps_per_year: float


class LimitSpec(_Base):
    soft: float
    hard: float


class DeskConfig(IllustrativeParams):
    limits: dict[str, LimitSpec]
    ftp_spread_bps: dict[Currency, float]
    trading_costs: TradingCosts
    balance_sheet: BalanceSheetParams
    xva: XvaParams
    sbl: SblParams
    repo: RepoParams


# ------------------------------------------------------------------ loaders


def _load(name: str) -> dict:
    with (CONFIG_DIR / f"{name}.yaml").open() as f:
        return yaml.safe_load(f)


@cache
def conventions() -> ConventionsConfig:
    return ConventionsConfig(**_load("conventions"))


@cache
def contracts() -> ContractsConfig:
    return ContractsConfig(**_load("contracts"))


@cache
def margin() -> MarginConfig:
    return MarginConfig(**_load("margin"))


@cache
def simm() -> SimmConfig:
    return SimmConfig(**_load("simm_illustrative"))


@cache
def withholding() -> WithholdingConfig:
    return WithholdingConfig(**_load("withholding_tax"))


@cache
def regulation() -> RegulationConfig:
    return RegulationConfig(**_load("regulation"))


@cache
def scenarios() -> ScenariosConfig:
    return ScenariosConfig(**_load("scenarios"))


@cache
def desk() -> DeskConfig:
    return DeskConfig(**_load("desk"))


ALL_LOADERS = {
    "conventions": conventions,
    "contracts": contracts,
    "margin": margin,
    "simm_illustrative": simm,
    "withholding_tax": withholding,
    "regulation": regulation,
    "scenarios": scenarios,
    "desk": desk,
}

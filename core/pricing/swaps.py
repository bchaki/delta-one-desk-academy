"""Single-underlying equity swap / TRS: cash flows, mark-to-market, unwinds and desk hedge economics.

Sign convention: client cash flows are positive when the client RECEIVES cash. Desk figures are
the desk's own PnL (positive = gain to the desk). All amounts are in the underlying's currency.

Equity leg (long client receives, short client pays), per period [start, end):
    price = shares x (S_end - S_start);  dividends = gross x shares x pass-through (ex-date in (start, end])
Funding leg: with funding notional N and compounded overnight benchmark R over the period,
    long client pays  N x (R + spread) x tau;  short client receives  N x (R - spread) x tau
where tau = days / basis. For a short, the spread includes the cost of borrow.

Simplifications: single underlying, equity leg settled each period, no payment lag or fixing lag.
``notional_reset=True`` funds the market value at each reset (shares x S_start); ``False`` keeps the
funding notional at the initial notional while the share count stays fixed. Deferred-settlement
(cumulative) variants would add an implicit financing of unpaid gains and losses.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from core import config
from core.conventions import CalendarName
from core.corporate_actions import CAAdjustment
from core.dividends import Dividend, net_dividend, swap_dividend_amount
from core.rates import compound_overnight
from core.types import Currency, Direction, money


@dataclass(frozen=True)
class SwapTerms:
    """Economic terms of a swap, from the client's point of view."""

    direction: Direction
    shares: float
    initial_price: float
    spread_bps: float
    benchmark_basis: int = 360
    pass_through: float = 1.0
    notional_reset: bool = True
    calendar: CalendarName = CalendarName.US

    @property
    def initial_notional(self) -> float:
        return self.shares * self.initial_price


@dataclass(frozen=True)
class PeriodCF:
    """Client cash flows for one period (positive = client receives), rounded to cents."""

    start: date
    end: date
    shares: float
    funding_notional: float
    start_price: float
    end_price: float
    benchmark_rate: float
    price_cf: float
    dividend_cf: float
    funding_cf: float

    @property
    def net_cf(self) -> float:
        """Sum of the rounded components, so rows always reconcile to the cent."""
        return round(self.price_cf + self.dividend_cf + self.funding_cf, 2)

    def as_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "shares": self.shares,
            "funding_notional": self.funding_notional,
            "start_price": self.start_price,
            "end_price": self.end_price,
            "benchmark_rate": self.benchmark_rate,
            "price_cf": self.price_cf,
            "dividend_cf": self.dividend_cf,
            "funding_cf": self.funding_cf,
            "net_cf": self.net_cf,
        }


def _dividends_in(divs: Sequence[Dividend], start: date, end: date) -> list[Dividend]:
    return [d for d in divs if start < d.ex_date <= end]


def period_cashflows(
    terms: SwapTerms,
    start: date,
    end: date,
    start_price: float,
    end_price: float,
    fixings: Mapping[date, float],
    dividends: Sequence[Dividend] = (),
    shares: float | None = None,
) -> PeriodCF:
    """Client cash flows over [start, end). Also used for a partial period to mark to market.

    ``shares`` overrides ``terms.shares`` (e.g. after a partial unwind or corporate action).
    """
    n_sh = terms.shares if shares is None else shares
    sign = terms.direction.sign
    rate = compound_overnight(fixings, start, end, terms.calendar, terms.benchmark_basis)
    tau = (end - start).days / terms.benchmark_basis
    fn = (
        n_sh * start_price
        if terms.notional_reset
        else terms.initial_notional * (n_sh / terms.shares)
    )
    price = sign * n_sh * (end_price - start_price)
    div = sign * sum(
        swap_dividend_amount(d.amount, n_sh, terms.pass_through)
        for d in _dividends_in(dividends, start, end)
    )
    funding = -sign * fn * tau * (rate + sign * terms.spread_bps / 10_000.0)
    return PeriodCF(
        start=start,
        end=end,
        shares=n_sh,
        funding_notional=fn,
        start_price=start_price,
        end_price=end_price,
        benchmark_rate=rate,
        price_cf=money(price),
        dividend_cf=money(div),
        funding_cf=money(funding),
    )


@dataclass(frozen=True)
class SwapSchedule:
    periods: tuple[PeriodCF, ...]

    @property
    def total_net(self) -> float:
        return round(sum(p.net_cf for p in self.periods), 2)

    def to_records(self) -> list[dict]:
        return [p.as_dict() for p in self.periods]


def build_schedule(
    terms: SwapTerms,
    dates: Sequence[date],
    prices: Mapping[date, float],
    fixings: Mapping[date, float],
    dividends: Sequence[Dividend] = (),
) -> SwapSchedule:
    """Cash-flow schedule between consecutive reset ``dates`` (first date is the trade start).

    The first period starts at ``terms.initial_price``; later periods start at the reset price.
    For early termination, pass ``dates`` ending on the termination date.
    """
    if len(dates) < 2:
        raise ValueError("need at least a start and an end date")
    periods = []
    for a, b in zip(dates[:-1], dates[1:], strict=True):
        s0 = terms.initial_price if a == dates[0] else prices[a]
        periods.append(period_cashflows(terms, a, b, s0, prices[b], fixings, dividends))
    return SwapSchedule(tuple(periods))


def mark_to_market(
    terms: SwapTerms,
    reset_dates: Sequence[date],
    valuation_date: date,
    price: float,
    prices: Mapping[date, float],
    fixings: Mapping[date, float],
    dividends: Sequence[Dividend] = (),
) -> float:
    """Client MTM since the last reset (positive = client is owed): the accrued, unsettled period.

    = price move since the last reset + dividends gone ex + funding accrued to ``valuation_date``.
    Zero on a reset date. Already-settled periods are not included.
    """
    last = max(d for d in reset_dates if d <= valuation_date)
    if last == valuation_date:
        return 0.0
    s0 = terms.initial_price if last == reset_dates[0] else prices[last]
    return period_cashflows(terms, last, valuation_date, s0, price, fixings, dividends).net_cf


def unwind(shares: float, fraction: float) -> tuple[float, float]:
    """Split ``shares`` into (unwound, remaining) for a partial unwind of ``fraction`` in [0, 1]."""
    if not 0 <= fraction <= 1:
        raise ValueError("fraction must be within [0, 1]")
    return shares * fraction, shares * (1.0 - fraction)


def apply_corporate_action(
    shares: float, reset_price: float, adj: CAAdjustment
) -> tuple[float, float, float]:
    """Adjust a swap's share count and reference price: ``(new shares, new price, cash)``.

    Cash is per the adjustment's ``cash_per_old_share`` x shares (paid to the long client).
    Notional is preserved for split / rights / spin-off adjustments.
    """
    return shares * adj.qty_factor, reset_price * adj.price_factor, shares * adj.cash_per_old_share


# --------------------------------------------------------------------------- desk economics


@dataclass(frozen=True)
class HedgePnL:
    """Desk hedge PnL for one period (positive = gain to the desk)."""

    stock: float
    dividends: float
    financing: float

    @property
    def total(self) -> float:
        return self.stock + self.dividends + self.financing


@dataclass(frozen=True)
class DeskEconomics:
    client: PeriodCF
    hedge: HedgePnL
    swap_pnl: float  # desk side of the swap = -client net
    total: float  # swap + hedge
    spread_edge: float  # fn x (spread - ftp or borrow) x tau, the target margin


def desk_hedge_pnl(
    terms: SwapTerms,
    start: date,
    end: date,
    start_price: float,
    end_price: float,
    fixings: Mapping[date, float],
    dividends: Sequence[Dividend],
    ftp_bps: float,
    borrow_bps: float = 0.0,
    wht_pct: float = 0.0,
) -> HedgePnL:
    """Desk hedge PnL.

    Long client: desk buys stock, funds at benchmark + FTP, receives net dividends (after
    ``wht_pct``). Short client: desk borrows and sells stock, earns the cash rebate
    (benchmark - borrow fee) on the proceeds and pays gross manufactured dividends.
    """
    rate = compound_overnight(fixings, start, end, terms.calendar, terms.benchmark_basis)
    tau = (end - start).days / terms.benchmark_basis
    sh = terms.shares
    divs = _dividends_in(dividends, start, end)
    gross = sum(d.amount for d in divs)
    if terms.direction is Direction.LONG:
        return HedgePnL(
            stock=sh * (end_price - start_price),
            dividends=sh * sum(net_dividend(d.amount, wht_pct) for d in divs),
            financing=-sh * start_price * (rate + ftp_bps / 10_000.0) * tau,
        )
    return HedgePnL(
        stock=-sh * (end_price - start_price),
        dividends=-sh * gross,
        financing=sh * start_price * (rate - borrow_bps / 10_000.0) * tau,
    )


def desk_economics(
    terms: SwapTerms,
    start: date,
    end: date,
    start_price: float,
    end_price: float,
    fixings: Mapping[date, float],
    dividends: Sequence[Dividend],
    ftp_bps: float,
    borrow_bps: float = 0.0,
    wht_pct: float = 0.0,
) -> DeskEconomics:
    """Desk PnL on swap + hedge for one period, plus the spread edge it should reduce to.

    With 100% pass-through, no withholding and a reset notional the total equals the edge:
    the equity and funding legs net against the hedge and the desk keeps the spread.
    """
    client = period_cashflows(terms, start, end, start_price, end_price, fixings, dividends)
    hedge = desk_hedge_pnl(
        terms, start, end, start_price, end_price, fixings, dividends, ftp_bps, borrow_bps, wht_pct
    )
    tau = (end - start).days / terms.benchmark_basis
    cost_bps = ftp_bps if terms.direction is Direction.LONG else borrow_bps
    edge = client.funding_notional * (terms.spread_bps - cost_bps) / 10_000.0 * tau
    swap_pnl = -client.net_cf
    return DeskEconomics(client, hedge, swap_pnl, swap_pnl + hedge.total, edge)


# --------------------------------------------------------------------------- spread build-up


@dataclass(frozen=True)
class SpreadBuildUp:
    """Client spread (bps over the benchmark) as the sum of named components."""

    direction: Direction
    components: dict[str, float] = field(default_factory=dict)

    @property
    def total_bps(self) -> float:
        return sum(self.components.values())


def ftp_component_bps(ccy: Currency) -> float:
    """Funding component for a long: the desk's FTP spread over the benchmark (config/desk.yaml)."""
    return config.desk().ftp_spread_bps[ccy]


def borrow_component_bps(borrow_fee_bps: float) -> float:
    """Borrow component for a short: the stock-loan fee in bps of notional per year."""
    return borrow_fee_bps


def hedge_cost_component_bps(round_trip_cost_bps: float, tenor_years: float) -> float:
    """Hedge execution cost spread over the swap's life: round-trip cost / tenor (bps per year)."""
    return round_trip_cost_bps / tenor_years


def spread_build_up(
    direction: Direction,
    ftp_bps: float,
    borrow_bps: float,
    balance_sheet_bps: float,
    capital_bps: float,
    xva_bps: float,
    hedge_cost_bps: float,
    margin_bps: float,
) -> SpreadBuildUp:
    """Client spread = funding (long) or borrow (short) + balance sheet + capital + XVA
    + hedge costs + target margin.

    Each argument comes from its own function: :func:`ftp_component_bps`,
    :func:`borrow_component_bps`, ``financing.balance_sheet`` charges, ``financing.xva_lite``,
    :func:`hedge_cost_component_bps` and the desk's target margin.
    """
    comps: dict[str, float] = {}
    if direction is Direction.LONG:
        comps["Funding (FTP)"] = ftp_bps
    else:
        comps["Borrow"] = borrow_bps
    comps["Balance sheet"] = balance_sheet_bps
    comps["Capital"] = capital_bps
    comps["XVA"] = xva_bps
    comps["Hedge costs"] = hedge_cost_bps
    comps["Target margin"] = margin_bps
    return SpreadBuildUp(direction, comps)

"""Synthetic desk book: clients, client swaps with full lifecycle, desk hedges, financing, seeded breaks.

The generator is a pure function of the seed. Trades hold the BOOKED values; seeded breaks describe
where a booked value (or a mark, fixing or missing dividend) differs from the truth.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from core import config
from core.booking.lifecycle import reset_dates
from core.booking.models import (
    Amendment,
    CashEquityTrade,
    Client,
    CSAModel,
    DividendFutureTrade,
    DividendPayment,
    EquitySwapTrade,
    EtfTrade,
    FutureTrade,
    LifecycleEvent,
    PartialUnwind,
    RepoTrade,
    Reset,
    SblTrade,
    SeededBreak,
    Termination,
    Trade,
)
from core.data.accessors import underlying_dividends
from core.data.market import (
    BASIS_BY_BENCH,
    BENCH_BY_CCY,
    CAL_BY_BENCH,
    MarketHistory,
    build_market,
)
from core.rates import compound_overnight
from core.types import Currency, Direction

CLIENT_SPECS = [
    ("C01", "Brightwater Partners", "hedge_fund", 1, "non-US", "pb_house"),
    ("C02", "Corvane Macro", "hedge_fund", 2, "non-US", "simm"),
    ("C03", "Dunmere Global", "hedge_fund", 2, "US", "pb_house"),
    ("C04", "Elmstead Long Short", "hedge_fund", 3, "non-US", "simm"),
    ("C05", "Fenwick Systematic", "hedge_fund", 1, "US", "portfolio"),
    ("C06", "Garnet Event Fund", "hedge_fund", 3, "non-US", "simm"),
    ("C07", "Harrowgate Capital", "hedge_fund", 2, "non-US", "pb_house"),
    ("C08", "Ivorydale Asset Management", "asset_manager", 1, "US", "simm"),
    ("C09", "Juniper Row Investments", "asset_manager", 1, "non-US", "simm"),
    ("C10", "Kestrel Fund Managers", "asset_manager", 2, "non-US", "schedule"),
    ("C11", "Lowmoor Advisers", "asset_manager", 2, "US", "schedule"),
    ("C12", "Marlowe Teachers Pension", "pension", 1, "non-US", "schedule"),
    ("C13", "Northgate Public Retirement", "pension", 1, "US", "schedule"),
    ("C14", "Orchard Mutual Insurance", "insurer", 1, "non-US", "schedule"),
    ("C15", "Structured Products Desk", "internal", 1, "US", "exchange"),
]
TIER_ADJ = {1: -8.0, 2: 0.0, 3: 12.0}


@dataclass
class Book:
    seed: int
    clients: dict[str, Client]
    trades: list[Trade]
    events: list[LifecycleEvent]
    breaks: list[SeededBreak]
    _by_id: dict[str, Trade] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._by_id = {t.trade_id: t for t in self.trades}

    def trade(self, trade_id: str) -> Trade:
        return self._by_id[trade_id]

    def swaps(self) -> list[EquitySwapTrade]:
        return [t for t in self.trades if isinstance(t, EquitySwapTrade)]

    def client_of(self, trade: Trade) -> Client | None:
        cid = trade.counterparty_id
        if cid is None and trade.linked_trade_id:
            return self.client_of(self.trade(trade.linked_trade_id))
        return self.clients.get(cid) if cid else None

    def events_for(self, trade_id: str) -> list[LifecycleEvent]:
        return [e for e in self.events if e.trade_id == trade_id]

    def with_breaks(self, breaks: list[SeededBreak]) -> Book:
        return Book(self.seed, self.clients, self.trades, self.events, breaks)

    def replace_trade(self, new: Trade) -> Book:
        trades = [new if t.trade_id == new.trade_id else t for t in self.trades]
        return Book(self.seed, self.clients, trades, self.events, self.breaks)


def make_clients(rng: np.random.Generator) -> dict[str, Client]:
    out = {}
    for cid, name, typ, tier, dom, method in CLIENT_SPECS:
        if typ == "hedge_fund":
            csa = CSAModel(
                threshold_cpty=0.0,
                threshold_desk=0.0,
                mta=500_000,
                ia_cpty=2_000_000,
                rounding=100_000,
                eligible_collateral=("cash", "gov_bonds"),
                haircuts={"cash": 0.0, "gov_bonds": 0.02},
            )
        elif typ == "asset_manager":
            csa = CSAModel(
                threshold_cpty=1_000_000,
                threshold_desk=1_000_000,
                mta=250_000,
                rounding=50_000,
                eligible_collateral=("cash", "gov_bonds"),
                haircuts={"cash": 0.0, "gov_bonds": 0.02},
            )
        elif typ in ("pension", "insurer"):
            csa = CSAModel(
                threshold_cpty=5_000_000,
                threshold_desk=5_000_000,
                mta=500_000,
                rounding=100_000,
                eligible_collateral=("cash",),
                haircuts={"cash": 0.0},
            )
        else:
            csa = CSAModel(
                threshold_cpty=50_000_000,
                threshold_desk=50_000_000,
                mta=1_000_000,
                rounding=1_000_000,
            )
        out[cid] = Client(
            id=cid,
            name=name,
            type=typ,
            tier=tier,
            domicile=dom,
            legal_entity=f"{name} {'Master Fund LP' if typ == 'hedge_fund' else 'Ltd'}",
            csa=csa,
            margin_method=method,
        )
    return out


def _slip(rng: np.random.Generator) -> float:
    return float(rng.uniform(0.0001, 0.0003))


def generate_book(seed: int = 7) -> Book:
    m = build_market(seed)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 20]))
    days, T = m.days, len(m.days)
    u = m.universe
    clients = make_clients(rng)
    cids = list(clients)
    trades: list[Trade] = []
    events: list[LifecycleEvent] = []
    counter = itertools.count(1)
    excluded = u.ca_plan.involved
    pool = [t for t in u.stocks if t not in excluded]

    def tid(prefix: str) -> str:
        return f"{prefix}{next(counter):04d}"

    def ts(d: date) -> pd.Timestamp:
        return pd.Timestamp(d)

    def swap_book(client: Client) -> str:
        return "Equity Swaps"

    # ------------------------------------------------------------------ swaps and their hedges
    swap_ends: dict[str, int] = {}  # trade id -> day index of termination (or T-1)

    def hedge_stock(
        swap: EquitySwapTrade, ticker: str, qty: float, idx: int, slip_sign: int
    ) -> None:
        d = days[idx]
        px = m.price(ticker, d)
        exec_px = px * (1 + slip_sign * _slip(rng))
        trades.append(
            CashEquityTrade(
                trade_id=tid("H"),
                trade_date=d,
                effective_date=d,
                book="Swap Hedges",
                ticker=ticker,
                qty=qty,
                price=round(exec_px, 4),
                ccy=u.stocks[ticker].ccy,
                purpose="swap_hedge",
                linked_trade_id=swap.trade_id,
                package_id=swap.package_id,
            )
        )

    def new_swap(
        client: Client,
        underlying: str,
        direction: Direction,
        idx: int,
        notional_usd: float,
        package: str | None = None,
        spread_override: float | None = None,
    ) -> EquitySwapTrade:
        d = days[idx]
        kind, _, name = underlying.partition(":")
        if kind == "stock":
            st = u.stocks[name]
            ccy = st.ccy
            px = m.price(name, d)
            borrow = float(m.borrow_fee_bps.at[ts(d), name])
            liq = 8.0 if st.adv * px * m.fx_usd_per(ccy, d) < 3e7 else 0.0
            ret = underlying_dividends(m, underlying)
            del ret
        else:
            ccy = u.indices[name].ccy
            px = float(m.index_level.at[ts(d), name])
            borrow, liq = 0.0, 0.0
        fx = m.fx_usd_per(ccy, d)
        shares = max(round(notional_usd / (px * fx), -2 if px < 1000 else 0), 1.0)
        bench = BENCH_BY_CCY[ccy]
        adj = TIER_ADJ[client.tier]
        spread = (30.0 + adj + liq) if direction is Direction.LONG else (borrow + 22.0 + adj)
        if spread_override is not None:
            spread = spread_override
        us_underlying = ccy is Currency.USD
        sw = EquitySwapTrade(
            trade_id=tid("S"),
            trade_date=d,
            effective_date=d,
            book=swap_book(client),
            counterparty_id=client.id,
            legal_entity=client.legal_entity,
            sales_credit=round(notional_usd * 0.00004, 2),
            package_id=package,
            underlying=underlying,
            direction=direction,
            shares=float(shares),
            initial_price=round(px, 4),
            spread_bps=round(spread, 1),
            benchmark=bench,
            reset_months=int(rng.choice([1, 1, 1, 3])),
            pass_through=1.0
            if client.type in ("hedge_fund", "internal")
            else float(rng.choice([0.85, 1.0])),
            notional_reset=bool(rng.random() > 0.1),
            flag_871m=bool(us_underlying and kind == "stock" and client.domicile != "US"),
            isda_ref=f"ISDA-{client.id}-{d.year}",
            ccy=ccy,
            borrow_bps=round(borrow, 1) if direction is Direction.SHORT else 0.0,
            day_count_basis=BASIS_BY_BENCH[bench],
        )
        trades.append(sw)
        swap_ends[sw.trade_id] = T - 1
        return sw

    def hedge_new_swap(sw: EquitySwapTrade, idx: int) -> None:
        kind, _, name = sw.underlying.partition(":")
        if kind == "stock":
            sign = 1 if sw.direction is Direction.LONG else -1
            hedge_stock(sw, name, sign * sw.shares, idx, +1 if sign > 0 else -1)
            if sign < 0:
                st = u.stocks[name]
                trades.append(
                    SblTrade(
                        trade_id=tid("B"),
                        trade_date=days[idx],
                        effective_date=days[idx],
                        book="Financing & SBL",
                        ticker=name,
                        side="borrow",
                        shares=sw.shares,
                        fee_bps=sw.borrow_bps,
                        collateral="cash",
                        margin=1.02 if st.country == "US" else 1.05,
                        ccy=st.ccy,
                        ref_price=m.price(name, days[idx]),
                        linked_trade_id=sw.trade_id,
                    )
                )

    def hedge_index(sw: EquitySwapTrade, start: int, end: int) -> None:
        """Hedge an index swap with futures, rolling three trading days before each expiry."""
        _, _, name = sw.underlying.partition(":")
        spec = config.contracts().contracts["D1US30" if "US" in name else "D1EU20"]
        sign = 1 if sw.direction is Direction.LONG else -1
        notional_local = sw.shares * sw.initial_price
        exps = sorted(e for (i, e) in m.futures if i == name)
        i = start
        cur = next(e for e in exps if (e - days[i]).days > 25)
        f_open = m.futures_price(name, cur, days[i])
        n = max(int(round(notional_local / (f_open * spec.multiplier))), 1)

        def add(idx: int, expiry: date, q: int, side: int) -> None:
            d = days[idx]
            f = m.futures_price(name, expiry, d)
            trades.append(
                FutureTrade(
                    trade_id=tid("F"),
                    trade_date=d,
                    effective_date=d,
                    book="Index Futures",
                    index=name,
                    expiry=expiry,
                    qty=q,
                    price=round(f * (1 + side * _slip(rng) * 0.2), 2),
                    multiplier=spec.multiplier,
                    ccy=spec.ccy,
                    linked_trade_id=sw.trade_id,
                    package_id=sw.package_id,
                )
            )

        add(i, cur, sign * n, +1 if sign > 0 else -1)
        while True:
            roll_idx = days.index(cur) - 3 if cur in days else None
            if roll_idx is None or roll_idx >= end:
                add(
                    min(end, T - 1), cur, -sign * n, -1 if sign > 0 else +1
                ) if end < T - 1 else None
                break
            nxt = next(e for e in exps if e > cur)
            add(roll_idx, cur, -sign * n, -1 if sign > 0 else +1)
            add(roll_idx, nxt, sign * n, +1 if sign > 0 else -1)
            cur = nxt
            if (cur - days[-1]).days > 0 and days.index(days[-1]) <= roll_idx:
                pass
            if cur > days[-1]:
                break

    # single-name swaps (long and short)
    n_long, n_short = 24, 12
    chosen = list(rng.choice(pool, size=n_long + n_short, replace=False))
    swap_specs: list[tuple[EquitySwapTrade, int]] = []
    for k, tk in enumerate(chosen):
        direction = Direction.LONG if k < n_long else Direction.SHORT
        pick = [c for c in cids if clients[c].type != "internal"]
        cid = str(rng.choice(pick))
        if direction is Direction.SHORT and clients[cid].type in ("pension", "insurer"):
            cid = str(rng.choice([c for c in cids if clients[c].type == "hedge_fund"]))
        idx = int(rng.integers(8, T - 70))
        notional = float(rng.uniform(4e6, 40e6))
        sw = new_swap(clients[cid], f"stock:{tk}", direction, idx, notional)
        hedge_new_swap(sw, idx)
        swap_specs.append((sw, idx))

    # a squeeze short: client short swap on the squeezed name, opened before the squeeze
    sq_idx = days.index(next(d for d in days if d >= date(2026, 1, 12))) - 25
    hf = clients["C04"]
    sqz = new_swap(hf, f"stock:{m.squeeze_ticker}", Direction.SHORT, sq_idx, 12e6)
    hedge_new_swap(sqz, sq_idx)
    swap_specs.append((sqz, sq_idx))

    # basket swaps (package)
    for b in range(3):
        cid = str(rng.choice(["C01", "C02", "C07", "C09"]))
        idx = int(rng.integers(20, T - 90))
        names = list(rng.choice([t for t in pool if t not in chosen], size=4, replace=False))
        pkg = f"PKG{b + 1:02d}"
        for j, tk in enumerate(names):
            direction = Direction.LONG if j < 3 else Direction.SHORT
            sw = new_swap(
                clients[cid],
                f"stock:{tk}",
                direction,
                idx,
                float(rng.uniform(2e6, 9e6)),
                package=pkg,
            )
            hedge_new_swap(sw, idx)
            swap_specs.append((sw, idx))

    # index swaps (futures hedged)
    index_specs = [
        ("C08", "D1 US 30", Direction.LONG, 30),
        ("C13", "D1 US 30", Direction.LONG, 140),
        ("C09", "D1 Europe 20", Direction.LONG, 60),
        ("C02", "D1 Europe 20", Direction.SHORT, 210),
    ]
    index_swaps: list[tuple[EquitySwapTrade, int]] = []
    for cid, name, direction, idx in index_specs:
        sw = new_swap(clients[cid], f"index:{name}", direction, idx, float(rng.uniform(20e6, 60e6)))
        index_swaps.append((sw, idx))
        swap_specs.append((sw, idx))

    # terminations, partial unwinds and amendments
    live_swaps = [s for s, _ in swap_specs if s.trade_id != sqz.trade_id]
    term_ids = list(rng.choice([s.trade_id for s in live_swaps], size=10, replace=False))
    unwind_ids = [
        x
        for x in rng.choice(
            [
                s.trade_id
                for s in live_swaps
                if s.direction is Direction.LONG
                and s.trade_id not in term_ids
                and s.underlying.startswith("stock:")
            ],
            size=4,
            replace=False,
        )
    ]
    amend_ids = list(
        rng.choice(
            [s.trade_id for s in live_swaps if s.trade_id not in term_ids], size=3, replace=False
        )
    )
    by_id = {s.trade_id: (s, i) for s, i in swap_specs}

    for sid in term_ids:
        sw, i0 = by_id[sid]
        t_idx = int(rng.integers(i0 + 25, T - 15)) if i0 + 25 < T - 15 else T - 15
        swap_ends[sid] = t_idx
        d = days[t_idx]
        kind, _, name = sw.underlying.partition(":")
        px = (
            float(m.prices.at[ts(d), name])
            if kind == "stock"
            else float(m.index_level.at[ts(d), name])
        )
        events.append(Termination(trade_id=sid, date=d, price=px))
        if kind == "stock":
            sign = 1 if sw.direction is Direction.LONG else -1
            hedge_stock(sw, name, -sign * sw.shares, t_idx, -1 if sign > 0 else +1)
            for k, t in enumerate(trades):
                if isinstance(t, SblTrade) and t.linked_trade_id == sid:
                    trades[k] = t.model_copy(update={"end_date": d})
        sw_new = sw.model_copy(update={"status": "terminated", "end_date": d})
        trades[[t.trade_id for t in trades].index(sid)] = sw_new
        by_id[sid] = (sw_new, i0)

    for sid in unwind_ids:
        sw, i0 = by_id[sid]
        u_idx = int(rng.integers(i0 + 20, T - 40))
        part = round(sw.shares * float(rng.uniform(0.25, 0.5)), -2)
        d = days[u_idx]
        _, _, name = sw.underlying.partition(":")
        events.append(
            PartialUnwind(trade_id=sid, date=d, shares_unwound=part, price=m.price(name, d))
        )
        hedge_stock(sw, name, -part, u_idx, -1)

    for sid in amend_ids:
        sw, i0 = by_id[sid]
        a_idx = int(rng.integers(i0 + 10, T - 30))
        events.append(
            Amendment(
                trade_id=sid,
                date=days[a_idx],
                field="spread_bps",
                old_value=sw.spread_bps,
                new_value=round(sw.spread_bps - 5.0, 1),
                upfront=round(float(rng.uniform(800, 4000)), 2),
            )
        )

    # index hedges (after terminations so end indices are known)
    for sw, idx in index_swaps:
        end_idx = swap_ends[sw.trade_id]
        hedge_index(sw, idx, end_idx)

    # ------------------------------------------------------------------ resets and dividends
    for sw in [t for t in trades if isinstance(t, EquitySwapTrade)]:
        end_idx = swap_ends[sw.trade_id]
        end_d = days[end_idx]
        fixings = m.fixings_dict(sw.benchmark)
        cal = CAL_BY_BENCH[sw.benchmark]
        prev = sw.trade_date
        underlying = sw.underlying
        kind, _, name = underlying.partition(":")
        for r in reset_dates(sw.trade_date, end_d, sw.reset_months):
            px = (
                float(m.prices.at[ts(r), name])
                if kind == "stock"
                else float(m.index_level.at[ts(r), name])
            )
            events.append(
                Reset(
                    trade_id=sw.trade_id,
                    date=r,
                    price=px,
                    benchmark_rate=compound_overnight(fixings, prev, r, cal, sw.day_count_basis),
                )
            )
            prev = r
        for dv in underlying_dividends(m, underlying):
            if sw.trade_date < dv.ex_date <= end_d:
                events.append(
                    DividendPayment(trade_id=sw.trade_id, date=dv.ex_date, amount=dv.amount)
                )

    # ------------------------------------------------------------------ financing, ETF, dividends, ADR
    long_hedges = [
        t
        for t in trades
        if isinstance(t, CashEquityTrade)
        and t.qty > 0
        and t.purpose == "swap_hedge"
        and swap_ends[t.linked_trade_id] == T - 1
        and t.trade_date < days[T - 80]
    ]
    for h in long_hedges[:6]:
        i0 = days.index(h.trade_date) + 5
        fee = max(15.0, 0.8 * float(m.borrow_fee_bps.at[ts(days[i0]), h.ticker]))
        trades.append(
            SblTrade(
                trade_id=tid("B"),
                trade_date=days[i0],
                effective_date=days[i0],
                book="Financing & SBL",
                ticker=h.ticker,
                side="loan",
                shares=round(0.4 * h.qty, -2),
                fee_bps=round(fee, 1),
                collateral="non_cash",
                margin=1.02,
                ccy=h.ccy,
                ref_price=m.price(h.ticker, days[i0]),
                linked_trade_id=h.trade_id,
            )
        )
    for h in long_hedges[6:9]:
        trades.append(
            RepoTrade(
                trade_id=tid("R"),
                trade_date=h.trade_date,
                effective_date=h.trade_date,
                book="Financing & SBL",
                ticker=h.ticker,
                qty=round(0.6 * h.qty, -2),
                price=h.price,
                haircut=config.desk().repo.haircut_by_quality["large_cap"],
                spread_bps=config.desk().repo.gc_spread_bps,
                term_days=None,
                ccy=h.ccy,
                linked_trade_id=h.trade_id,
            )
        )
    for k in range(6):
        etf = "D1UX" if k % 2 == 0 else "D1EX"
        idx = int(rng.integers(15, T - 20))
        d = days[idx]
        qty = float(rng.choice([-1, 1]) * rng.integers(20, 80) * 1000)
        px = float(m.etf_prices.at[ts(d), etf])
        e = u.etfs[etf]
        trades.append(
            EtfTrade(
                trade_id=tid("E"),
                trade_date=d,
                effective_date=d,
                book="ETF",
                ticker=etf,
                qty=qty,
                price=round(px * (1 + np.sign(qty) * _slip(rng)), 4),
                ccy=u.indices[e.index].ccy,
            )
        )
    for y, units, idx in [
        (2025, 120_000, 170),
        (2026, 160_000, 250),
        (2027, -90_000, 330),
        (2028, 80_000, 420),
    ]:
        idx = min(idx, T - 5)
        d = days[idx]
        series = m.div_futures[y]
        if pd.Timestamp(d) not in series.index:
            continue
        strike = float(series.loc[pd.Timestamp(d)])
        trades.append(
            DividendFutureTrade(
                trade_id=tid("D"),
                trade_date=d,
                effective_date=d,
                book="Dividends",
                year=y,
                units=float(units),
                strike=round(strike, 3),
            )
        )
    adr_list = list(u.adrs.values())
    for k, a in enumerate(adr_list[:4]):
        idx = int(rng.integers(30, T - 100))
        d = days[idx]
        sign = 1 if k % 2 == 0 else -1
        qty_adr = float(rng.integers(15, 60) * 1000)
        pkg = f"ADR{k + 1:02d}"
        local = u.stocks[a.underlying]
        close_idx = int(rng.integers(idx + 20, T - 10)) if k < 2 else None
        legs = [
            (
                a.adr_ticker,
                sign * qty_adr,
                Currency.USD,
                float(m.adr_prices.at[ts(d), a.adr_ticker]),
            ),
            (a.underlying, -sign * qty_adr * a.ratio, local.ccy, m.price(a.underlying, d)),
        ]
        for tick, q, ccy, px in legs:
            trades.append(
                CashEquityTrade(
                    trade_id=tid("A"),
                    trade_date=d,
                    effective_date=d,
                    book="ADR Arbitrage",
                    ticker=tick,
                    qty=q,
                    price=round(px * (1 + np.sign(q) * _slip(rng)), 4),
                    ccy=ccy,
                    purpose="adr_arb",
                    package_id=pkg,
                )
            )
        if close_idx is not None:
            cd = days[close_idx]
            for tick, q, ccy, _ in legs:
                px = (
                    float(m.adr_prices.at[ts(cd), tick])
                    if tick == a.adr_ticker
                    else m.price(tick, cd)
                )
                trades.append(
                    CashEquityTrade(
                        trade_id=tid("A"),
                        trade_date=cd,
                        effective_date=cd,
                        book="ADR Arbitrage",
                        ticker=tick,
                        qty=-q,
                        price=round(px * (1 - np.sign(q) * _slip(rng)), 4),
                        ccy=ccy,
                        purpose="adr_arb",
                        package_id=pkg,
                    )
                )

    book = Book(seed, clients, trades, events, [])
    breaks = _seed_breaks(book, m, rng, sqz)
    book = Book(seed, clients, book.trades, events, breaks)
    # apply the wrong legal entity to the booked trade
    for b in breaks:
        if b.kind == "wrong_entity":
            tr = book.trade(b.trade_id)
            book = book.replace_trade(
                tr.model_copy(update={"legal_entity": str(b.detail["booked_entity"])})
            )
        if b.kind == "wrong_spread":
            tr = book.trade(b.trade_id)
            book = book.replace_trade(
                tr.model_copy(update={"spread_bps": float(b.detail["booked_spread_bps"])})
            )
    return book


def _seed_breaks(
    book: Book, m: MarketHistory, rng: np.random.Generator, sqz: EquitySwapTrade
) -> list[SeededBreak]:
    days, T = m.days, len(m.days)
    late = list(days[T - 24 : T - 2])
    breaks: list[SeededBreak] = []
    live_at_end = [
        s
        for s in book.swaps()
        if s.status == "live"
        and s.trade_date < days[T - 40]
        and s.trade_id != sqz.trade_id
        and s.underlying.startswith("stock:")
    ]
    # 1. missed dividend on a long hedge
    ex_events = [e for e in m.dividends if late[0] <= e.ex_date <= late[-1] and e.amount > 0]
    if not ex_events:
        ex_events = [
            e for e in m.dividends if days[T - 140] <= e.ex_date <= late[-1] and e.amount > 0
        ]
    placed = False
    for e in reversed(ex_events):
        for t in book.trades:
            if (
                isinstance(t, CashEquityTrade)
                and t.ticker == e.ticker
                and t.qty > 0
                and t.purpose == "swap_hedge"
                and t.trade_date < e.ex_date
                and book.trade(t.linked_trade_id).status == "live"
            ):
                breaks.append(
                    SeededBreak(
                        kind="missed_dividend",
                        trade_id=t.trade_id,
                        date=e.ex_date,
                        ticker=e.ticker,
                        clue=f"Dividend of {e.amount:.4f} per share on {e.ticker} went ex on {e.ex_date} but the hedge position shows no dividend cash.",
                        detail={"amount_per_share": e.amount},
                    )
                )
                placed = True
                break
        if placed:
            break
    # 2. wrong reset fixing
    cand = [
        s
        for s in live_at_end
        if s.notional_reset and s.trade_id not in {b.trade_id for b in breaks}
    ]
    sw = cand[0]
    d2 = late[6]
    true_rate = m.fixing(
        sw.benchmark, d2 - timedelta(days=0) if d2 in m.fixings[sw.benchmark].index else d2
    )
    breaks.append(
        SeededBreak(
            kind="wrong_fixing",
            trade_id=sw.trade_id,
            date=d2,
            ticker=sw.underlying.split(":")[1],
            clue=f"The {sw.benchmark.value} fixing used for {sw.trade_id} on {d2} looks 100 bps off the published rate (the wrong rate is carried for the whole reset period).",
            detail={"true_rate": true_rate, "booked_rate": true_rate + 0.01},
        )
    )
    # 3. wrong spread (a recent long swap booked 15 bps below the term sheet)
    cand2 = [
        s
        for s in live_at_end
        if s.direction is Direction.LONG and s.trade_id not in {b.trade_id for b in breaks}
    ]
    sw3 = cand2[-1]
    breaks.append(
        SeededBreak(
            kind="wrong_spread",
            trade_id=sw3.trade_id,
            date=sw3.trade_date,
            ticker=sw3.underlying.split(":")[1],
            clue=f"Carry on {sw3.trade_id} is lower than the term sheet implies: booked spread {sw3.spread_bps - 15:.1f} bps vs agreed {sw3.spread_bps:.1f} bps.",
            detail={
                "term_sheet_spread_bps": sw3.spread_bps,
                "booked_spread_bps": round(sw3.spread_bps - 15.0, 1),
            },
        )
    )
    # 4. wrong legal entity
    cand4 = [s for s in live_at_end if s.trade_id not in {b.trade_id for b in breaks}]
    sw4 = cand4[len(cand4) // 2]
    cl = book.clients[sw4.counterparty_id]
    breaks.append(
        SeededBreak(
            kind="wrong_entity",
            trade_id=sw4.trade_id,
            date=sw4.trade_date,
            ticker=sw4.underlying.split(":")[1],
            clue=f"{sw4.trade_id} is mapped to a different legal entity than the client's ISDA counterparty ({cl.name}); margin calls will be sent to the wrong entity.",
            detail={"booked_entity": f"{cl.name} Fund II LP", "true_entity": cl.legal_entity},
        )
    )
    # 5. stale price on a held stock
    held: dict[str, float] = {}
    for t in book.trades:
        if (
            isinstance(t, CashEquityTrade)
            and t.purpose == "swap_hedge"
            and book.trade(t.linked_trade_id).status == "live"
        ):
            held[t.ticker] = held.get(t.ticker, 0.0) + abs(t.qty * t.price)
    ticker = max(held, key=held.get) if held else m.universe.indices["D1 US 30"].members[0]
    breaks.append(
        SeededBreak(
            kind="stale_price",
            trade_id="*",
            date=late[-3],
            ticker=ticker,
            clue=f"The {ticker} mark on {late[-3]} is identical to the previous close although the stock moved.",
            detail={},
        )
    )
    return breaks

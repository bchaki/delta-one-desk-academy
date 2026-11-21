"""Seeded synthetic market: three years of business days across all asset classes.

Everything is a pure function of the seed. Simplifications (documented for the Data Explorer):
all synthetic exchanges share one trading calendar (days that are business days on the US, TARGET,
UK and Japan calendars); all prices are fictional.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import cache

import numpy as np
import pandas as pd

from core import indices as ix
from core.conventions import CalendarName, add_months, business_days, is_business_day, third_friday
from core.data.universe import Universe, build_universe
from core.dividends import Dividend
from core.pricing.futures import model_forward
from core.pricing.trf import price_basis_to_trf_spread_bps
from core.rates import DiscountCurve
from core.types import Benchmark, Currency

HISTORY_START = date(2023, 11, 21)
HISTORY_END = date(2026, 11, 20)
_CALS = (CalendarName.US, CalendarName.TARGET, CalendarName.UK, CalendarName.JAPAN)

BENCH_BY_CCY = {
    Currency.USD: Benchmark.SOFR,
    Currency.EUR: Benchmark.ESTR,
    Currency.GBP: Benchmark.SONIA,
    Currency.JPY: Benchmark.TONA,
    Currency.CHF: Benchmark.SARON,
}
CAL_BY_BENCH = {
    Benchmark.SOFR: CalendarName.US,
    Benchmark.ESTR: CalendarName.TARGET,
    Benchmark.SONIA: CalendarName.UK,
    Benchmark.TONA: CalendarName.JAPAN,
    Benchmark.SARON: CalendarName.TARGET,
}
BASIS_BY_BENCH = {
    Benchmark.SOFR: 360,
    Benchmark.ESTR: 360,
    Benchmark.SONIA: 365,
    Benchmark.TONA: 365,
    Benchmark.SARON: 360,
}
INDEX_BENCH = {"D1 US 30": Benchmark.SOFR, "D1 Europe 20": Benchmark.ESTR}

# Stylised policy-rate paths (percent). Invented for teaching; not forecasts or history.
RATE_PATHS: dict[Benchmark, list[tuple[date, float]]] = {
    Benchmark.SOFR: [
        (date(2023, 1, 1), 4.60),
        (date(2024, 6, 17), 4.30),
        (date(2025, 1, 20), 3.90),
        (date(2025, 9, 15), 3.60),
        (date(2026, 4, 20), 3.40),
    ],
    Benchmark.ESTR: [
        (date(2023, 1, 1), 3.90),
        (date(2024, 6, 10), 3.50),
        (date(2025, 1, 27), 2.90),
        (date(2025, 9, 8), 2.20),
        (date(2026, 4, 13), 2.00),
    ],
    Benchmark.SONIA: [
        (date(2023, 1, 1), 4.60),
        (date(2024, 8, 5), 4.40),
        (date(2025, 2, 10), 4.10),
        (date(2025, 10, 6), 3.80),
        (date(2026, 5, 4), 3.60),
    ],
    Benchmark.TONA: [
        (date(2023, 1, 1), 0.10),
        (date(2024, 4, 1), 0.25),
        (date(2025, 1, 20), 0.50),
        (date(2025, 11, 3), 0.60),
        (date(2026, 6, 1), 0.75),
    ],
    Benchmark.SARON: [
        (date(2023, 1, 1), 1.50),
        (date(2024, 6, 24), 1.20),
        (date(2025, 1, 6), 0.50),
        (date(2025, 6, 23), 0.25),
    ],
}

# (label, start, end, cumulative global-factor move, volatility multiplier)
STRESS_EPISODES = [
    ("Episode A", date(2024, 8, 1), date(2024, 8, 9), -0.09, 2.5),
    ("Episode B", date(2025, 3, 10), date(2025, 4, 11), -0.18, 3.0),
    ("Episode C", date(2026, 2, 2), date(2026, 2, 20), -0.08, 2.0),
]
DIV_CANCEL_WINDOW = (date(2025, 3, 10), date(2025, 6, 30))  # EU dividend cancellation episode
SQUEEZE_START = date(2026, 1, 12)
FX_START = {"EURUSD": 1.09, "GBPUSD": 1.27, "USDJPY": 150.0, "USDCHF": 0.88}
FX_VOL = {"EURUSD": 0.06, "GBPUSD": 0.07, "USDJPY": 0.09, "USDCHF": 0.07}


@cache
def trading_days() -> tuple[date, ...]:
    """Common business days across the four calendars within the history window."""
    return tuple(
        d
        for d in business_days(HISTORY_START, HISTORY_END, CalendarName.US)
        if all(is_business_day(d, c) for c in _CALS)
    )


def _is_common_bd(d: date) -> bool:
    return all(is_business_day(d, c) for c in _CALS)


def _prev_common_bd(d: date) -> date:
    while not _is_common_bd(d):
        d -= timedelta(days=1)
    return d


@dataclass(frozen=True)
class DividendEvent:
    ticker: str
    ex_date: date
    pay_date: date
    amount: float  # actual gross per share (raw price terms); 0 if cancelled
    forecast: float  # analyst forecast per share
    kind: str  # regular, special, cut, cancelled


@dataclass(frozen=True)
class CorporateActionEvent:
    kind: str  # split, rights, spin_off, cash_merger, index_add, index_delete
    ticker: str
    date: date
    terms: dict


@dataclass(frozen=True)
class RecallEvent:
    date: date
    ticker: str
    pct: float


@dataclass
class MarketHistory:
    seed: int
    universe: Universe
    days: tuple[date, ...]
    prices: pd.DataFrame
    cumqf: pd.DataFrame
    dividends: list[DividendEvent]
    corporate_actions: list[CorporateActionEvent]
    fixings: dict[Benchmark, pd.Series]
    term_slope_bps: pd.Series
    fx: pd.DataFrame
    index_level: pd.DataFrame
    index_tr: pd.DataFrame
    index_divisor: dict[str, list[tuple[date, float]]]
    index_members: dict[str, list[tuple[date, tuple[str, ...]]]]
    index_div_events: dict[str, list[Dividend]]
    futures: dict[tuple[str, date], pd.Series]
    trf_spread_bps: pd.DataFrame
    div_futures: dict[int, pd.Series]
    borrow_fee_bps: pd.DataFrame
    utilisation: pd.DataFrame
    recalls: list[RecallEvent]
    adr_prices: pd.DataFrame
    etf_prices: pd.DataFrame
    shares0: dict[str, float] = field(default_factory=dict)
    squeeze_ticker: str = ""
    cap_factors: dict[str, dict[str, float]] = field(default_factory=dict)  # final cap factors

    # ------------------------------------------------------------------ lookups

    def clamp(self, d: date) -> date:
        """Latest trading day on or before ``d`` (within history)."""
        if d <= self.days[0]:
            return self.days[0]
        i = int(np.searchsorted(np.array(self.days), d, side="right")) - 1
        return self.days[min(i, len(self.days) - 1)]

    def price(self, ticker: str, d: date) -> float:
        return float(self.prices.at[pd.Timestamp(d), ticker])

    def fx_usd_per(self, ccy: Currency, d: date) -> float:
        """USD per one unit of ``ccy`` at the daily fixing."""
        ts = pd.Timestamp(d)
        if ccy is Currency.USD:
            return 1.0
        if ccy is Currency.EUR:
            return float(self.fx.at[ts, "EURUSD"])
        if ccy is Currency.GBP:
            return float(self.fx.at[ts, "GBPUSD"])
        if ccy is Currency.JPY:
            return 1.0 / float(self.fx.at[ts, "USDJPY"])
        return 1.0 / float(self.fx.at[ts, "USDCHF"])

    def fx_rate(self, ccy_from: Currency, ccy_to: Currency, d: date) -> float:
        return self.fx_usd_per(ccy_from, d) / self.fx_usd_per(ccy_to, d)

    def fixing(self, bench: Benchmark, d: date) -> float:
        """Overnight fixing (decimal) for date ``d`` on the benchmark's own calendar."""
        s = self.fixings[bench]
        return float(s.loc[pd.Timestamp(d)])

    def fixings_dict(self, bench: Benchmark) -> dict[date, float]:
        s = self.fixings[bench]
        return {ts.date(): float(v) for ts, v in s.items()}

    def curve(self, bench: Benchmark, d: date) -> DiscountCurve:
        """Simple term curve from deposits: overnight + slope x tenor (stylised)."""
        on = self.fixing(bench, d)
        slope = float(self.term_slope_bps.loc[pd.Timestamp(self.clamp(d))]) / 10_000.0
        basis = BASIS_BY_BENCH[bench]
        pts = []
        for months in (1, 3, 6, 12, 24):
            end = add_months(d, months)
            tau = months / 12.0
            pts.append((end, on + slope * tau))
        return DiscountCurve.from_deposit_rates(d, pts, basis)

    def stock_adv(self, ticker: str, d: date) -> float:
        return self.universe.stocks[ticker].adv * float(self.cumqf.at[pd.Timestamp(d), ticker])

    def shares_outstanding(self, ticker: str, d: date) -> float:
        return self.shares0[ticker] * float(self.cumqf.at[pd.Timestamp(d), ticker])

    def index_dividends_between(self, index: str, start: date, end: date) -> list[Dividend]:
        return [e for e in self.index_div_events[index] if start < e.ex_date <= end]

    def front_expiries(self, index: str, d: date, n: int = 4) -> list[date]:
        exps = sorted(e for (i, e) in self.futures if i == index and e >= d)
        return exps[:n]

    def futures_price(self, index: str, expiry: date, d: date) -> float:
        return float(self.futures[(index, expiry)].loc[pd.Timestamp(d)])


# --------------------------------------------------------------------------- generation helpers


def _garch(rng: np.random.Generator, n: int, base: float, mult: np.ndarray, a=0.08, b=0.90):
    z = rng.standard_t(5, n) / math.sqrt(5 / 3)
    out = np.empty(n)
    var = base**2
    for t in range(n):
        shock = math.sqrt(var) * z[t]
        out[t] = shock * mult[t]
        var = base**2 * (1 - a - b) + a * shock**2 + b * var
    return out


def _ou(
    rng: np.random.Generator, n: int, phi: float, sigma: float, mean: float = 0.0
) -> np.ndarray:
    x = np.empty(n)
    x[0] = mean
    e = rng.standard_normal(n)
    for t in range(1, n):
        x[t] = mean + phi * (x[t - 1] - mean) + sigma * e[t]
    return x


def _snap(days: tuple[date, ...], d: date) -> int:
    """Index of the first trading day on or after ``d`` (clamped)."""
    i = int(np.searchsorted(np.array(days), d, side="left"))
    return min(i, len(days) - 1)


def _rate_series(bench: Benchmark, rng: np.random.Generator) -> pd.Series:
    cal = CAL_BY_BENCH[bench]
    path = RATE_PATHS[bench]
    ds = business_days(HISTORY_START - timedelta(days=60), HISTORY_END + timedelta(days=10), cal)
    vals = []
    for d in ds:
        lvl = path[0][1]
        for pd_, v in path:
            if d >= pd_:
                lvl = v
        vals.append(lvl / 100.0)
    noise = rng.normal(0, 0.00003, len(ds))
    return pd.Series(np.array(vals) + noise, index=pd.DatetimeIndex(ds))


# --------------------------------------------------------------------------- main builder


@cache
def build_market(seed: int = 7) -> MarketHistory:
    uni = build_universe(seed)
    days = trading_days()
    T = len(days)
    didx = pd.DatetimeIndex(days)
    tickers = list(uni.stocks)
    N = len(tickers)
    col = {t: i for i, t in enumerate(tickers)}
    rngs = [np.random.default_rng(np.random.SeedSequence([seed, 10 + k])) for k in range(12)]
    plan = uni.ca_plan

    # ---- stress episodes
    vol_mult = np.ones(T)
    g_drift = np.zeros(T)
    for _, s, e, move, vm in STRESS_EPISODES:
        i0, i1 = _snap(days, s), _snap(days, e)
        vol_mult[i0 : i1 + 1] = vm
        g_drift[i0 : i1 + 1] += move / (i1 - i0 + 1)

    # ---- factors
    g = _garch(rngs[0], T, 0.008, vol_mult) + g_drift + 0.0004  # ~10% a year equity drift
    regions = ["US", "EU", "UK", "JP"]
    reg = {r: _garch(rngs[1], T, 0.005, vol_mult) for r in regions}
    from core.data.universe import SECTOR_LIST

    sec = {s: _garch(rngs[2], T, 0.008, np.ones(T)) for s in SECTOR_LIST}
    zid = rngs[3].standard_t(5, (T, N)) / math.sqrt(5 / 3)
    idio_vol = np.array([uni.stocks[t].idio_vol for t in tickers])
    beta = np.array([uni.stocks[t].beta for t in tickers])
    eps = np.empty((T, N))
    var = idio_vol**2
    for t in range(T):
        shock = np.sqrt(var) * zid[t]
        eps[t] = shock
        var = idio_vol**2 * 0.02 + 0.08 * shock**2 + 0.90 * var
    # earnings jumps: one random day per quarter per stock
    jumps = np.zeros((T, N))
    for n in range(N):
        for q0 in range(0, T, 63):
            d = int(rngs[4].integers(q0, min(q0 + 63, T)))
            jumps[d, n] = rngs[4].normal(0, 0.04)
    # single-name squeeze
    cands = [
        s
        for s in uni.stocks.values()
        if s.country == "US" and s.ticker not in plan.involved and s.ticker != "HLVN"
    ]
    squeeze_t = max(cands, key=lambda s: s.borrow.short_interest).ticker
    sq0 = _snap(days, SQUEEZE_START)
    extra = np.zeros((T, N))
    extra[sq0 : sq0 + 12, col[squeeze_t]] = 0.08
    extra[sq0 + 12 : sq0 + 16, col[squeeze_t]] = -0.12
    region_idx = np.array([regions.index(uni.stocks[t].region) for t in tickers])
    sector_idx = np.array([SECTOR_LIST.index(uni.stocks[t].sector) for t in tickers])
    reg_mat = np.vstack([reg[r] for r in regions])
    sec_mat = np.vstack([sec[s] for s in SECTOR_LIST])

    # ---- dividend schedule
    rd = rngs[5]
    special = {
        str(x): rd.uniform(0.02, 0.04)
        for x in rd.choice(
            [t for t in tickers if uni.stocks[t].dividend.annual_yield > 0.01],
            size=3,
            replace=False,
        )
    }
    cut_from = {
        str(x): date(2025, int(rd.integers(1, 12)), 1)
        for x in rd.choice(
            [t for t in tickers if uni.stocks[t].dividend.annual_yield > 0.01],
            size=4,
            replace=False,
        )
    }
    div_plan: dict[int, list[tuple[int, float, float, str]]] = {}
    future_div: list[tuple[str, date, float]] = []
    for tk in tickers:
        st = uni.stocks[tk]
        pol = st.dividend
        if pol.annual_yield <= 0:
            continue
        for yr in range(2023, 2033):
            for m in pol.ex_months:
                try:
                    d0 = date(yr, m, 10)
                except ValueError:
                    continue
                base = pol.annual_yield * st.price0 * (1.03 ** (yr - 2023)) / pol.per_year
                if d0 > HISTORY_END or d0 < HISTORY_START:
                    if d0 > HISTORY_END:
                        future_div.append((tk, d0, base))
                    continue
                if st.listed_from and d0 < st.listed_from:
                    continue
                ex = _snap(days, d0)
                kind, amt = "regular", base
                if tk in cut_from and d0 >= cut_from[tk]:
                    kind, amt = "cut", base * 0.5
                if (
                    st.region == "EU"
                    and st.country != "UK"
                    and DIV_CANCEL_WINDOW[0] <= days[ex] <= DIV_CANCEL_WINDOW[1]
                ):
                    kind, amt = "cancelled", 0.0
                div_plan.setdefault(ex, []).append((col[tk], amt, base, kind))
        if tk in special:
            ex = _snap(days, date(2025, 11, 12))
            div_plan.setdefault(ex, []).append(
                (col[tk], special[tk] * st.price0, special[tk] * st.price0, "special")
            )

    # ---- corporate action calendar (indices)
    split_i = _snap(days, plan.split_date)
    rights_i = _snap(days, plan.rights_date)
    spin_i = _snap(days, plan.spin_date)
    merge_i = _snap(days, plan.merger_date)
    ann_i = max(merge_i - 40, 1)
    ci_split, ci_rights = col[plan.split_ticker], col[plan.rights_ticker]
    ci_parent, ci_spin, ci_merge = (
        col[plan.spin_parent],
        col[plan.spin_ticker],
        col[plan.merger_ticker],
    )

    # ---- price loop
    price0 = np.array([uni.stocks[t].price0 for t in tickers], dtype=float)
    p = np.full((T, N), np.nan)
    qf = np.ones((T, N))
    listed = np.array([uni.stocks[t].listed_from is None for t in tickers])
    p[0] = np.where(listed, price0, np.nan)
    shares0 = {t: uni.stocks[t].shares_out for t in tickers}
    ca_events: list[CorporateActionEvent] = []
    div_events: list[DividendEvent] = []
    offer = 0.0
    merge_noise = rngs[6].standard_normal(T)
    for t in range(1, T):
        r = (
            beta * g[t]
            + reg_mat[region_idx, t]
            + sec_mat[sector_idx, t]
            + eps[t]
            + jumps[t]
            + extra[t]
        )
        pp = p[t - 1]
        newp = pp * (1 + r)
        q = qf[t - 1].copy()
        if t == split_i:
            newp[ci_split] = pp[ci_split] / plan.split_ratio * (1 + r[ci_split])
            q[ci_split] *= plan.split_ratio
            ca_events.append(
                CorporateActionEvent(
                    "split", plan.split_ticker, days[t], {"ratio": plan.split_ratio}
                )
            )
        if t == rights_i:
            P = pp[ci_rights]
            K = P * (1 - plan.rights_discount)
            terp = ix_terp = (P + plan.rights_ratio * K) / (1 + plan.rights_ratio)
            pf = ix_terp / P
            newp[ci_rights] = P * pf * (1 + r[ci_rights])
            q[ci_rights] /= pf
            ca_events.append(
                CorporateActionEvent(
                    "rights",
                    plan.rights_ticker,
                    days[t],
                    {
                        "ratio": plan.rights_ratio,
                        "subscription_price": K,
                        "terp": terp,
                        "cum_price": P,
                    },
                )
            )
        if t == spin_i:
            v = plan.spin_value_frac * pp[ci_parent]
            newp[ci_parent] = (pp[ci_parent] - v) * (1 + r[ci_parent])
            newp[ci_spin] = v / plan.spin_ratio
            listed[ci_spin] = True
            shares0[plan.spin_ticker] = (
                shares0[plan.spin_parent] * qf[t - 1][ci_parent] * plan.spin_ratio
            )
            ca_events.append(
                CorporateActionEvent(
                    "spin_off",
                    plan.spin_parent,
                    days[t],
                    {
                        "spin_ticker": plan.spin_ticker,
                        "value_per_share": v,
                        "ratio": plan.spin_ratio,
                    },
                )
            )
        if ann_i <= t < merge_i:
            if t == ann_i:
                offer = pp[ci_merge] * (1 + plan.merger_premium)
                ca_events.append(
                    CorporateActionEvent(
                        "cash_merger_announced",
                        plan.merger_ticker,
                        days[t],
                        {"offer": offer, "premium": plan.merger_premium},
                    )
                )
            newp[ci_merge] = (
                offer
                * (1 - 0.03 * (merge_i - t) / (merge_i - ann_i))
                * (1 + 0.001 * merge_noise[t])
            )
        if t == merge_i:
            newp[ci_merge] = offer
            ca_events.append(
                CorporateActionEvent("cash_merger", plan.merger_ticker, days[t], {"offer": offer})
            )
        if t > merge_i:
            newp[ci_merge] = np.nan
        for i, amt_base, f_base, kind in div_plan.get(t, []):
            if not np.isnan(newp[i]):
                amt = amt_base / q[i]
                newp[i] -= amt
                st = uni.stocks[tickers[i]]
                div_events.append(
                    DividendEvent(
                        tickers[i], days[t], days[t] + timedelta(days=14), amt, f_base / q[i], kind
                    )
                )
        newp = np.where(np.isnan(newp), np.nan, np.maximum(newp, 0.01 * price0))
        newp = np.where(listed | ~np.isnan(newp), newp, np.nan)
        p[t] = newp
        qf[t] = q
    prices = pd.DataFrame(p, index=didx, columns=tickers)
    cumqf = pd.DataFrame(qf, index=didx, columns=tickers)
    div_events.sort(key=lambda e: (e.ex_date, e.ticker))

    # ---- FX
    fx = {}
    for k, (name, s0) in enumerate(FX_START.items()):
        ret = rngs[7].normal(0, FX_VOL[name] / math.sqrt(252), T) * vol_mult**0.5
        fx[name] = s0 * np.exp(np.cumsum(ret) - ret[0])
    fx_df = pd.DataFrame(fx, index=didx)

    # ---- rates
    fixings = {b: _rate_series(b, rngs[8]) for b in Benchmark}
    slope = pd.Series(_ou(rngs[8], T, 0.995, 2.0, 25.0), index=didx)

    # ---- indices
    shares_t = {t: shares0[t] * cumqf[t].to_numpy() for t in tickers}
    ex_by_day: dict[int, dict[int, float]] = {}
    for e in div_events:
        ex_by_day.setdefault(_snap(days, e.ex_date), {})[col[e.ticker]] = e.amount

    index_level, index_tr = {}, {}
    index_divisor: dict[str, list[tuple[date, float]]] = {}
    index_members: dict[str, list[tuple[date, tuple[str, ...]]]] = {}
    index_div_events: dict[str, list[Dividend]] = {}
    final_cf: dict[str, dict[str, float]] = {}
    reb_days = set()
    for yr in range(2023, 2028):
        for m in (3, 6, 9, 12):
            tf = third_friday(yr, m)
            i = int(np.searchsorted(np.array(days), tf, side="right"))
            if 0 < i < T:
                reb_days.add(i)

    for name, idef in uni.indices.items():
        mem = list(idef.members)
        ff = {t: uni.stocks[t].free_float for t in tickers}
        cf = dict.fromkeys(mem, 1.0)

        def px(i: int, t: str) -> float:
            v = p[i, col[t]]
            return float(v) if not np.isnan(v) else float(p[min(i + 1, T - 1), col[t]])

        def value(i: int, members: list[str], cfs: dict[str, float]) -> float:
            return float(sum(px(i, t) * shares_t[t][i] * ff[t] * cfs[t] for t in members))

        def recap(i: int, members: list[str]) -> dict[str, float]:
            pr = [px(i, t) for t in members]
            sh = [shares_t[t][i] for t in members]
            fl = [ff[t] for t in members]
            w = ix.weights_float_cap(pr, sh, fl)
            wc = ix.apply_cap(w, idef.cap)
            f = ix.capping_factors(w, wc)
            return dict(zip(members, (float(x) for x in f), strict=True))

        cf = recap(0, mem)
        divisor = value(0, mem, cf) / idef.base_level
        index_divisor[name] = [(days[0], divisor)]
        index_members[name] = [(days[0], tuple(mem))]
        lvl = np.empty(T)
        tr = np.empty(T)
        div_pts = np.zeros(T)
        lvl[0] = idef.base_level
        tr[0] = idef.base_level
        for t in range(1, T):
            changed = False
            new_mem, new_cf = list(mem), dict(cf)
            if name == "D1 US 30" and t == spin_i:
                new_mem.append(plan.spin_ticker)
                new_cf[plan.spin_ticker] = 1.0
                ff[plan.spin_ticker] = ff[plan.spin_parent]
                mem, cf = new_mem, new_cf  # value-neutral add, no divisor change
                index_members[name].append((days[t], tuple(mem)))
                new_mem, new_cf = list(mem), dict(cf)
            if name == "D1 US 30" and t == merge_i + 1:
                new_mem = [m for m in new_mem if m != plan.merger_ticker]
                new_cf.pop(plan.merger_ticker, None)
                changed = True
                ca_events.append(
                    CorporateActionEvent(
                        "index_delete", plan.merger_ticker, days[t], {"index": name}
                    )
                )
                ca_events.append(
                    CorporateActionEvent(
                        "index_add", plan.spin_ticker, days[spin_i], {"index": name}
                    )
                )
            if t in reb_days:
                new_cf = recap(t - 1, new_mem)
                changed = True
            if changed:
                old_v = value(t - 1, mem, cf)
                new_v = value(t - 1, new_mem, new_cf)
                divisor = ix.adjust_divisor(divisor, old_v, new_v)
                mem, cf = new_mem, new_cf
                index_divisor[name].append((days[t], divisor))
                if name == "D1 US 30" and t == merge_i + 1:
                    index_members[name].append((days[t], tuple(mem)))
            lvl[t] = value(t, mem, cf) / divisor
            pts = (
                sum(
                    amt * shares_t[tickers[i]][t] * ff[tickers[i]] * cf[tickers[i]]
                    for i, amt in ex_by_day.get(t, {}).items()
                    if tickers[i] in cf
                )
                / divisor
            )
            div_pts[t] = pts
            tr[t] = tr[t - 1] * (lvl[t] + pts) / lvl[t - 1]
        index_level[name] = lvl
        index_tr[name] = tr
        # dividend events in index points: history from actuals, then forecasts at the final state
        ev: dict[date, float] = {}
        for t in range(T):
            if div_pts[t] != 0:
                ev[days[t]] = div_pts[t]
        last_sh = {t: shares_t[t][-1] for t in cf}
        fc_by_date: dict[date, float] = {}
        for tk, d0, base in future_div:
            if tk in cf:
                fc_by_date[d0] = fc_by_date.get(d0, 0.0) + (
                    base / cumqf[tk].iloc[-1] * last_sh[tk] * ff[tk] * cf[tk] / divisor
                )
        ev.update(fc_by_date)
        index_div_events[name] = [
            Dividend(d, d + timedelta(days=14), a) for d, a in sorted(ev.items())
        ]
        final_cf[name] = cf
    idx_level_df = pd.DataFrame(index_level, index=didx)
    idx_tr_df = pd.DataFrame(index_tr, index=didx)

    # ---- futures, TRF
    futures: dict[tuple[str, date], pd.Series] = {}
    trf_cols: dict[str, np.ndarray] = {}
    for name in uni.indices:
        bench = INDEX_BENCH[name]
        on = fixings[bench].reindex(didx).to_numpy()
        common = _ou(rngs[9], T, 0.97, 8.0, 5.0)
        evs = index_div_events[name]
        expiries = []
        for yr in range(2023, 2029):
            for m in (3, 6, 9, 12):
                e = _prev_common_bd(third_friday(yr, m))
                if e > HISTORY_START:
                    expiries.append(e)
        trf = np.full(T, np.nan)
        for e in expiries:
            lo = e - timedelta(days=400)
            idxs = [t for t in range(T) if lo <= days[t] <= e]
            if not idxs:
                continue
            idio = _ou(rngs[9], T, 0.9, 6.0, 0.0)
            vals = {}
            for t in idxs:
                d = days[t]
                tt = (e - d).days / 365.0
                r_c = math.log(1 + on[t]) + 0.0010
                divs = [((x.ex_date - d).days / 365.0, x.amount) for x in evs if d < x.ex_date <= e]
                s = lvl_t = float(idx_level_df[name].iloc[t])
                fair = model_forward(s, r_c, divs, tt)
                roll_boost = 2.0 if (e - d).days <= 7 else 1.0
                rich_bps = common[t] + idio[t] * roll_boost
                vals[didx[t]] = fair + rich_bps / 1e4 * lvl_t * tt
                if tt > 0 and (e == min(x for x in expiries if x >= d)):
                    fv_divs = sum(a * math.exp(r_c * (tt - ti)) for ti, a in divs)
                    trf[t] = price_basis_to_trf_spread_bps(
                        lvl_t, vals[didx[t]], on[t], (e - d).days / 360.0, fv_divs
                    )
            futures[(name, e)] = pd.Series(vals)
        trf_cols[name] = trf
    trf_df = pd.DataFrame(trf_cols, index=didx)

    # ---- dividend futures (Europe index): annual dividend points, years Y..Y+4
    eu_name = "D1 Europe 20"
    ev_all = index_div_events[eu_name]
    fc_pts_by_ex: dict[date, float] = {}
    actual_by_ex = {e.ex_date: e.amount for e in ev_all}
    # forecast (pre-cancellation) points in history: rescale by actual vs forecast ratio per ex date
    fc_by_ticker_date: dict[date, float] = {}
    for e in div_events:
        if e.ticker in uni.indices[eu_name].members:
            fc_by_ticker_date[e.ex_date] = fc_by_ticker_date.get(e.ex_date, 0.0) + e.forecast
    for d0, act in actual_by_ex.items():
        act_sum = sum(
            e.amount
            for e in div_events
            if e.ex_date == d0 and e.ticker in uni.indices[eu_name].members
        )
        fc_sum = fc_by_ticker_date.get(d0)
        fc_pts_by_ex[d0] = (
            act * (fc_sum / act_sum)
            if (fc_sum is not None and act_sum > 0)
            else (act if fc_sum is None else 0.0)
        )
    # cancelled dates: actual points are 0, so rebuild forecast points from forecast share
    ex_levels = {}
    for d0 in fc_by_ticker_date:
        mem_sum = sum(
            e.amount
            for e in div_events
            if e.ex_date == d0 and e.ticker in uni.indices[eu_name].members
        )
        ex_levels[d0] = (actual_by_ex.get(d0, 0.0), mem_sum)
    unit_pts: dict[date, float] = {}
    cf_eu = final_cf[eu_name]
    div_eu = index_divisor[eu_name][-1][1]
    for d0 in fc_by_ticker_date:
        pts = 0.0
        for e in div_events:
            if e.ex_date == d0 and e.ticker in cf_eu:
                pts += (
                    e.forecast
                    * shares_t[e.ticker][-1]
                    * uni.stocks[e.ticker].free_float
                    * cf_eu[e.ticker]
                    / div_eu
                )
        unit_pts[d0] = pts
    fc_events = dict(unit_pts)
    for d0, a in actual_by_ex.items():
        if d0 > HISTORY_END:
            fc_events.setdefault(d0, a)
    disc_rng = rngs[10]
    disc_base = _ou(disc_rng, T, 0.99, 0.004, 0.06)
    c0, c1 = _snap(days, DIV_CANCEL_WINDOW[0]), _snap(days, DIV_CANCEL_WINDOW[1])
    shock = np.zeros(T)
    for t in range(c0, T):
        shock[t] = 0.35 * math.exp(-(max(t - c1, 0)) / 120.0) if t >= c0 else 0.0
    disc_t = np.clip(disc_base + shock, 0.0, 0.8)
    div_futures: dict[int, pd.Series] = {}
    for Y in range(2024, 2032):
        vals = {}
        expiry_y = _prev_common_bd(third_friday(Y, 12))
        for t in range(T):
            d = days[t]
            if d.year > Y or Y - d.year > 4:
                continue
            realised = sum(
                a
                for dd, a in actual_by_ex.items()
                if dd.year == Y and dd <= d and dd <= HISTORY_END
            )
            remaining = sum(a for dd, a in fc_events.items() if dd.year == Y and dd > d)
            if d.year == Y and d >= expiry_y:
                vals[didx[t]] = sum(a for dd, a in actual_by_ex.items() if dd.year == Y)
            else:
                far = 1 + 0.15 * (Y - d.year)
                vals[didx[t]] = realised + remaining * (1 - min(disc_t[t] * far, 0.9))
        if vals:
            div_futures[Y] = pd.Series(vals)

    # ---- borrow fees, utilisation, recalls
    rb = rngs[11]
    fee0 = np.array([uni.stocks[t].borrow.fee_bps for t in tickers])
    util0 = np.array([uni.stocks[t].borrow.utilisation for t in tickers])
    ou = np.vstack([_ou(rb, T, 0.97, 0.10) for _ in range(N)]).T
    fee = fee0 * np.exp(ou)
    util = np.clip(util0 + 0.08 * ou, 0.01, 0.99)
    sqi = col[squeeze_t]
    prof = np.zeros(T)
    for t in range(sq0, min(sq0 + 40, T)):
        prof[t] = 1.0 if t <= sq0 + 16 else math.exp(-(t - sq0 - 16) / 8.0)
    fee[:, sqi] = np.maximum(fee[:, sqi], 4000.0 * prof)
    util[:, sqi] = np.clip(util[:, sqi] + 0.5 * prof, 0.01, 0.99)
    for e in div_events:  # fees tick up into record dates for special/hard-to-borrow names
        if uni.stocks[e.ticker].borrow.tier in ("special", "hard_to_borrow"):
            i = _snap(days, e.ex_date)
            fee[max(i - 4, 0) : i + 1, col[e.ticker]] *= 1.5
    recalls = []
    hard = [t for t in tickers if uni.stocks[t].borrow.tier != "GC"] or tickers[:5]
    for k in range(12):
        d = days[int(rb.integers(30, T - 5))]
        recalls.append(RecallEvent(d, str(rb.choice(hard)), round(float(rb.uniform(0.2, 0.6)), 2)))
    recalls.append(RecallEvent(days[min(sq0 + 6, T - 1)], squeeze_t, 0.5))
    recalls.sort(key=lambda r: r.date)

    # ---- ADRs and ETFs
    adr = {}
    for a in uni.adrs.values():
        st = uni.stocks[a.underlying]
        usd_per = np.array([_usd_per_array(st.ccy, fx_df, i) for i in range(T)])
        dev = _ou(rngs[3], T, 0.9, 0.0006, 0.0)
        adr[a.adr_ticker] = prices[a.underlying].to_numpy() * a.ratio * usd_per * (1 + dev)
    adr_df = pd.DataFrame(adr, index=didx)
    etf = {}
    for e in uni.etfs.values():
        prem = _ou(rngs[3], T, 0.85, 0.0008, 0.0) * vol_mult
        etf[e.ticker] = idx_tr_df[e.index].to_numpy() * e.scale * (1 + prem)
    etf_df = pd.DataFrame(etf, index=didx)

    return MarketHistory(
        seed=seed,
        universe=uni,
        days=days,
        prices=prices,
        cumqf=cumqf,
        dividends=div_events,
        corporate_actions=sorted(ca_events, key=lambda c: c.date),
        fixings=fixings,
        term_slope_bps=slope,
        fx=fx_df,
        index_level=idx_level_df,
        index_tr=idx_tr_df,
        index_divisor=index_divisor,
        index_members=index_members,
        index_div_events=index_div_events,
        futures=futures,
        trf_spread_bps=trf_df,
        div_futures=div_futures,
        borrow_fee_bps=pd.DataFrame(fee, index=didx, columns=tickers),
        utilisation=pd.DataFrame(util, index=didx, columns=tickers),
        recalls=recalls,
        adr_prices=adr_df,
        etf_prices=etf_df,
        shares0=shares0,
        cap_factors=final_cf,
        squeeze_ticker=squeeze_t,
    )


def _usd_per_array(ccy: Currency, fx_df: pd.DataFrame, i: int) -> float:
    row = fx_df.iloc[i]
    if ccy is Currency.USD:
        return 1.0
    if ccy is Currency.EUR:
        return float(row["EURUSD"])
    if ccy is Currency.GBP:
        return float(row["GBPUSD"])
    if ccy is Currency.JPY:
        return 1.0 / float(row["USDJPY"])
    return 1.0 / float(row["USDCHF"])

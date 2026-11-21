"""Synthetic universe: fictional stocks, ADRs, two indices and their ETFs.

Everything here is invented. Names are built from invented syllables and must not be read as real
firms. The universe is a pure function of the seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from core.types import Currency

SECTORS: dict[str, str] = {
    "Energy": "Energy",
    "Materials": "Materials",
    "Industrials": "Industrial",
    "Consumer Discretionary": "Motors",
    "Consumer Staples": "Foods",
    "Health Care": "Therapeutics",
    "Financials": "Financial",
    "Information Technology": "Systems",
    "Communication Services": "Media",
    "Utilities": "Power",
    "Real Estate": "Properties",
}
SECTOR_LIST = list(SECTORS)

# country -> (currency, region, number of stocks, dividends per year, ex-date months)
COUNTRIES: dict[str, tuple[Currency, str, int, int, tuple[int, ...]]] = {
    "US": (Currency.USD, "US", 30, 4, (2, 5, 8, 11)),
    "DE": (Currency.EUR, "EU", 5, 1, (5,)),
    "FR": (Currency.EUR, "EU", 5, 1, (5,)),
    "NL": (Currency.EUR, "EU", 4, 2, (5, 10)),
    "CH": (Currency.CHF, "EU", 2, 1, (4,)),
    "ES": (Currency.EUR, "EU", 2, 1, (7,)),
    "IT": (Currency.EUR, "EU", 2, 2, (5, 11)),
    "UK": (Currency.GBP, "UK", 6, 2, (4, 10)),
    "JP": (Currency.JPY, "JP", 4, 2, (3, 9)),
}

_PREFIX = [
    "Hal",
    "Bren",
    "Cas",
    "Dun",
    "Esk",
    "Gar",
    "Hex",
    "Iron",
    "Kes",
    "Lin",
    "Mar",
    "Nor",
    "Ors",
    "Pel",
    "Quil",
    "Roth",
    "Sav",
    "Tor",
    "Ul",
    "Vel",
    "Wex",
    "Yar",
    "Zan",
    "Ald",
    "Bor",
    "Cym",
    "Dra",
    "Elm",
    "Fen",
    "Gil",
    "Har",
    "Jun",
    "Kal",
    "Lor",
    "Mon",
    "Nev",
]
_SUFFIX = [
    "vorsen",
    "nick",
    "tellane",
    "marrow",
    "erfield",
    "rowick",
    "ley",
    "vale",
    "relmoor",
    "dale",
    "wyn",
    "gard",
    "ington",
    "mere",
    "fall",
    "stone",
    "burn",
    "croft",
    "holm",
    "thorpe",
]


@dataclass(frozen=True)
class DividendPolicy:
    per_year: int
    annual_yield: float
    ex_months: tuple[int, ...]


@dataclass(frozen=True)
class BorrowProfile:
    tier: str  # GC, warm, special, hard_to_borrow
    fee_bps: float
    utilisation: float
    short_interest: float  # fraction of free float
    lendable_pct: float  # fraction of shares outstanding available to lend


@dataclass(frozen=True)
class Stock:
    ticker: str
    name: str
    country: str
    ccy: Currency
    region: str
    exchange: str
    sector: str
    price0: float
    shares_out: float
    free_float: float
    adv: float  # shares per day
    idio_vol: float  # daily
    beta: float
    dividend: DividendPolicy
    borrow: BorrowProfile
    listed_from: date | None = None  # None = listed throughout (spin-offs list later)

    @property
    def daily_vol(self) -> float:
        """Approximate total daily vol implied by the factor model (see data.market)."""
        return float(np.sqrt((self.beta * 0.008) ** 2 + 0.005**2 + 0.008**2 + self.idio_vol**2))


@dataclass(frozen=True)
class ADR:
    adr_ticker: str
    underlying: str
    ratio: float  # local shares per ADR
    depositary_fee: float  # per ADR, USD


@dataclass(frozen=True)
class IndexDef:
    name: str
    ccy: Currency
    members: tuple[str, ...]
    cap: float
    base_level: float = 1000.0


@dataclass(frozen=True)
class ETF:
    ticker: str
    index: str
    cu_size: float
    creation_fee: float
    ter: float
    scale: float  # ETF price = index level x scale


@dataclass(frozen=True)
class CAPlan:
    """Planned corporate actions (dates are targets; the market snaps them to trading days)."""

    split_ticker: str
    split_date: date
    split_ratio: float  # new shares per old
    rights_ticker: str
    rights_date: date
    rights_ratio: float  # new shares per old
    rights_discount: float  # subscription price discount to cum price
    spin_parent: str
    spin_ticker: str
    spin_date: date
    spin_value_frac: float  # value of spun-off shares per parent share, as fraction of parent price
    spin_ratio: float  # spun-off shares per parent share
    merger_ticker: str
    merger_date: date
    merger_premium: float

    @property
    def involved(self) -> set[str]:
        return {
            self.split_ticker,
            self.rights_ticker,
            self.spin_parent,
            self.spin_ticker,
            self.merger_ticker,
        }


@dataclass(frozen=True)
class Universe:
    stocks: dict[str, Stock]
    adrs: dict[str, ADR]
    indices: dict[str, IndexDef]
    etfs: dict[str, ETF]
    ca_plan: CAPlan

    def by_country(self, country: str) -> list[Stock]:
        return [s for s in self.stocks.values() if s.country == country]


def _tier(rng: np.random.Generator) -> BorrowProfile:
    u = rng.random()
    if u < 0.70:
        return BorrowProfile(
            "GC",
            float(rng.uniform(15, 40)),
            float(rng.uniform(0.02, 0.15)),
            float(rng.uniform(0.005, 0.03)),
            float(rng.uniform(0.10, 0.25)),
        )
    if u < 0.88:
        return BorrowProfile(
            "warm",
            float(rng.uniform(80, 250)),
            float(rng.uniform(0.25, 0.55)),
            float(rng.uniform(0.03, 0.07)),
            float(rng.uniform(0.06, 0.15)),
        )
    if u < 0.96:
        return BorrowProfile(
            "special",
            float(rng.uniform(400, 1200)),
            float(rng.uniform(0.60, 0.85)),
            float(rng.uniform(0.08, 0.15)),
            float(rng.uniform(0.03, 0.08)),
        )
    return BorrowProfile(
        "hard_to_borrow",
        float(rng.uniform(2000, 5000)),
        float(rng.uniform(0.88, 0.98)),
        float(rng.uniform(0.16, 0.30)),
        float(rng.uniform(0.01, 0.04)),
    )


def make_stock(
    rng: np.random.Generator,
    ticker: str,
    name: str,
    country: str,
    sector: str,
    listed_from: date | None = None,
    price0: float | None = None,
) -> Stock:
    ccy, region, _, per_year, months = COUNTRIES[country]
    px = price0 if price0 is not None else float(np.exp(rng.uniform(np.log(25), np.log(350))))
    if ccy is Currency.JPY and price0 is None:
        px *= 100
    shares = float(np.exp(rng.uniform(np.log(2e8), np.log(3e9))))
    adv = shares * float(rng.uniform(0.002, 0.006))
    return Stock(
        ticker=ticker,
        name=name,
        country=country,
        ccy=ccy,
        region=region,
        exchange=f"{country} Main Market (synthetic)",
        sector=sector,
        price0=round(px, 2),
        shares_out=round(shares, -3),
        free_float=round(float(rng.uniform(0.5, 1.0)), 2),
        adv=round(adv, -2),
        idio_vol=float(rng.uniform(0.009, 0.015)),
        beta=round(float(rng.uniform(0.6, 1.5)), 2),
        dividend=DividendPolicy(per_year, round(float(rng.uniform(0.0, 0.045)), 4), months),
        borrow=_tier(rng),
        listed_from=listed_from,
    )


def build_universe(seed: int = 7) -> Universe:
    """Build the 60-stock universe (plus a spin-off listed later), 5 ADRs, 2 indices and 2 ETFs."""
    rng = np.random.default_rng(np.random.SeedSequence([seed, 1]))
    words: list[str] = []
    seen: set[str] = set()
    while len(words) < 70:
        w = str(rng.choice(_PREFIX)) + str(rng.choice(_SUFFIX))
        if w not in seen:
            seen.add(w)
            words.append(w)
    words[0] = "Halvorsen"
    tickers: set[str] = set()
    stocks: dict[str, Stock] = {}
    i = 0
    for country, (_, _, n, _, _) in COUNTRIES.items():
        for k in range(n):
            w = words[i]
            i += 1
            sector = "Industrials" if w == "Halvorsen" else SECTOR_LIST[(i + k) % len(SECTOR_LIST)]
            t = w[:4].upper()
            j = 4
            while t in tickers:
                j += 1
                t = (w[:3] + w[j - 1]).upper() if j < len(w) else (w[:2] + str(j)).upper()
            if w == "Halvorsen":
                t = "HLVN"
            tickers.add(t)
            stocks[t] = make_stock(rng, t, f"{w} {SECTORS[sector]}", country, sector)

    us = [s for s in stocks.values() if s.country == "US"]
    eu = [s for s in stocks.values() if s.region == "EU"]
    indices = {
        "D1 US 30": IndexDef("D1 US 30", Currency.USD, tuple(s.ticker for s in us), 0.10),
        "D1 Europe 20": IndexDef(
            "D1 Europe 20", Currency.EUR, tuple(s.ticker for s in eu[:20]), 0.10
        ),
    }
    non_us = [s for s in stocks.values() if s.country != "US"]
    adrs: dict[str, ADR] = {}
    for s in non_us[:: max(1, len(non_us) // 5)][:5]:
        adrs[s.ticker + "A"] = ADR(
            s.ticker + "A", s.ticker, float(rng.choice([1.0, 2.0, 0.5])), 0.02
        )
    etfs = {
        "D1UX": ETF("D1UX", "D1 US 30", 50_000, 5_000.0, 0.0010, 0.1),
        "D1EX": ETF("D1EX", "D1 Europe 20", 50_000, 4_000.0, 0.0012, 0.1),
    }

    # Corporate action plan: avoid HLVN (kept clean for worked examples) and ADR underlyings.
    rng2 = np.random.default_rng(np.random.SeedSequence([seed, 2]))
    avoid = {"HLVN"} | {a.underlying for a in adrs.values()}
    us_pool = [s.ticker for s in us if s.ticker not in avoid]
    eu_pool = [s.ticker for s in eu if s.ticker not in avoid]
    pick_us = [str(x) for x in rng2.choice(us_pool, size=3, replace=False)]
    rights_t = str(rng2.choice(eu_pool))
    parent = pick_us[1]
    spin_date = date(2025, 6, 23)
    spin_ticker = parent[:3] + "S"
    while spin_ticker in stocks:
        spin_ticker = spin_ticker[:2] + "Z" + spin_ticker[3:]
    parent_word = stocks[parent].name.split()[0]
    stocks[spin_ticker] = make_stock(
        rng2,
        spin_ticker,
        f"{parent_word} Spin-off Holdings",
        "US",
        stocks[parent].sector,
        listed_from=spin_date,
        price0=round(stocks[parent].price0 * 0.24, 2),
    )
    plan = CAPlan(
        split_ticker=pick_us[0],
        split_date=date(2024, 9, 16),
        split_ratio=2.0,
        rights_ticker=rights_t,
        rights_date=date(2025, 2, 10),
        rights_ratio=0.2,
        rights_discount=0.2,
        spin_parent=parent,
        spin_ticker=spin_ticker,
        spin_date=spin_date,
        spin_value_frac=0.12,
        spin_ratio=0.5,
        merger_ticker=pick_us[2],
        merger_date=date(2026, 3, 16),
        merger_premium=0.25,
    )
    return Universe(stocks=stocks, adrs=adrs, indices=indices, etfs=etfs, ca_plan=plan)

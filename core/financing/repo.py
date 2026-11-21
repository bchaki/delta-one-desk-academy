"""Equity repo: cash lent, interest, GC vs special rates, margin calls and funding comparison."""

from __future__ import annotations

from core import config


def repo_cash(market_value: float, haircut: float) -> float:
    """Cash lent against collateral = market value x (1 - haircut)."""
    return market_value * (1.0 - haircut)


def default_haircut(quality: str) -> float:
    """Illustrative haircut for an asset-quality bucket from ``config/desk.yaml``."""
    return config.desk().repo.haircut_by_quality[quality]


def repo_interest(cash: float, rate: float, days: int, basis: int) -> float:
    """Repo interest = cash x rate x days / basis."""
    return cash * rate * days / basis


def gc_rate(benchmark: float) -> float:
    """General-collateral repo rate = benchmark + GC spread (config)."""
    return benchmark + config.desk().repo.gc_spread_bps / 10_000.0


def special_rate(benchmark: float, borrow_fee_bps: float) -> float:
    """Special-collateral repo rate = GC rate + factor x fee (factor -1: the lender of cash pays
    away roughly the borrow fee), so hard-to-borrow collateral funds cheaper and can go negative."""
    f = config.desk().repo.special_spread_bps_per_fee_bps
    return gc_rate(benchmark) + f * borrow_fee_bps / 10_000.0


def term_rate(
    overnight: float, term_years: float, premium_bps_per_year: float | None = None
) -> float:
    """Term repo rate = overnight + term premium x term (simple, bps per year from config)."""
    p = (
        config.desk().repo.term_premium_bps_per_year
        if premium_bps_per_year is None
        else premium_bps_per_year
    )
    return overnight + p / 10_000.0 * term_years


def repo_margin_call(market_value: float, cash_lent: float, haircut: float) -> float:
    """Margin call on the cash borrower = cash lent - MV x (1 - haircut); negative means excess."""
    return cash_lent - repo_cash(market_value, haircut)


def funding_cost_comparison(
    notional: float,
    benchmark: float,
    days: int,
    basis: int,
    ftp_bps: float,
    haircut: float,
    repo_spread_bps: float,
    swap_spread_bps: float,
) -> dict[str, float]:
    """Cost of funding a long book of ``notional`` over ``days`` three ways.

    - ``unsecured``: notional x (benchmark + FTP).
    - ``repo``: (1 - haircut) x notional at benchmark + repo spread, plus the haircut portion
      funded unsecured at benchmark + FTP.
    - ``swap``: notional x (benchmark + swap spread) paid to the swap dealer.
    """
    f = days / basis
    unsecured = notional * (benchmark + ftp_bps / 1e4) * f
    cash = notional * (1.0 - haircut)
    repo = (
        cash * (benchmark + repo_spread_bps / 1e4) * f
        + (notional - cash) * (benchmark + ftp_bps / 1e4) * f
    )
    swap = notional * (benchmark + swap_spread_bps / 1e4) * f
    return {"unsecured": unsecured, "repo": repo, "swap": swap}

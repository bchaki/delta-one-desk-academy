"""Total return futures (TRF) quoted as a spread over an overnight benchmark.

A TRF pays the *total* return of the index (dividends included) against a funding leg of
benchmark + spread, so there is no dividend term in its financing. The spread can be restated
as an equivalent basis on the *price* index future for comparison with the usual futures.
Teaching model: simple interest, one period, no margin-financing differences.
"""

from __future__ import annotations


def trf_spread_to_price_basis(
    spot: float, spread_bps: float, benchmark: float, tau: float, fv_divs: float
) -> float:
    """Equivalent price-future basis F - S (index points) for a TRF spread.

    F - S = S x (benchmark + spread) x tau - FV(divs). ``tau`` is the period in years on the
    benchmark's day count; ``fv_divs`` are dividends valued at expiry, in index points.
    """
    return spot * (benchmark + spread_bps / 10_000.0) * tau - fv_divs


def price_basis_to_trf_spread_bps(
    spot: float, fut: float, benchmark: float, tau: float, fv_divs: float
) -> float:
    """TRF spread (bps over benchmark) equivalent to a price future at ``fut``.

    spread = ((F - S + FV(divs)) / (S x tau) - benchmark) x 10,000. Inverse of
    :func:`trf_spread_to_price_basis`.
    """
    return ((fut - spot + fv_divs) / (spot * tau) - benchmark) * 10_000.0


def trf_funding_amount(
    notional: float, benchmark: float, spread_bps: float, days: int, basis: int = 360
) -> float:
    """Funding leg amount owed by the long: notional x (benchmark + spread) x days / basis."""
    return notional * (benchmark + spread_bps / 10_000.0) * days / basis


def swap_equivalent_spread_bps(trf_spread_bps: float, swap_premium_bps: float) -> float:
    """Bilateral swap spread comparable to a TRF spread.

    swap spread = TRF spread + premium for what the cleared future does not carry
    (balance sheet, credit/XVA, bilateral margin). ``swap_premium_bps`` is an input; it can be
    negative when the swap benefits from netting the exchange does not give.
    """
    return trf_spread_bps + swap_premium_bps

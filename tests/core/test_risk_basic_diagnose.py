"""Tests for the hand-checkable risk and PnL-diagnosis helpers."""

import math

import pytest

from core.pnl import diagnose as dg
from core.risk import basic as rb


def test_delta_and_beta():
    """10,000 shares at 50 with EUR at 1.10: 550,000. Beta 1.2 gives 660,000."""
    d = rb.delta_exposure(10_000, 50, 1.10)
    assert d == pytest.approx(550_000)
    assert rb.beta_adjusted(d, 1.2) == pytest.approx(660_000)


def test_fx_translation():
    """1,000,000 of EUR position, EUR down 2%: -20,000."""
    assert rb.fx_translation_pnl(1e6, -2.0) == pytest.approx(-20_000)


def test_parametric_var_and_scaling():
    """VaR99 = 2.3263 x 10m x 1.5% = 348,951; ten days scales by sqrt(10)."""
    v = rb.parametric_var_1d(10e6, 0.015)
    assert v == pytest.approx(2.326348 * 10e6 * 0.015, rel=1e-5)
    assert rb.scale_var(v, 10) == pytest.approx(v * math.sqrt(10))


def test_two_asset_var_diversification():
    """Same-sign, rho 1: VaR adds. Opposite sign, rho 1: perfect hedge, VaR zero. rho 0: root-sum-squares."""
    one = rb.parametric_var_1d(1e6, 0.01)
    assert rb.two_asset_var(1e6, 1e6, 0.01, 0.01, 1.0) == pytest.approx(2 * one)
    assert rb.two_asset_var(1e6, -1e6, 0.01, 0.01, 1.0) == pytest.approx(0.0, abs=1e-6)
    assert rb.two_asset_var(1e6, 1e6, 0.01, 0.01, 0.0) == pytest.approx(one * math.sqrt(2))


def test_es_exceeds_var():
    """Normal ES at 97.5% for 1m, vol 1%: 10,000 x phi(1.96)/0.025 = 10,000 x 0.05845/0.025 = 23,380."""
    es = rb.es_normal(1e6, 0.01, 0.975)
    assert es == pytest.approx(23_380, rel=1e-3)
    assert es > rb.parametric_var_1d(1e6, 0.01, 0.975)


def test_liquidation_and_concentration():
    """500,000 shares, ADV 1,000,000, 20% participation: 2.5 days. Even weights of 4 names: HHI 0.25."""
    assert rb.days_to_liquidate(500_000, 1_000_000) == pytest.approx(2.5)
    assert rb.hhi([1, 1, 1, 1]) == pytest.approx(0.25)
    assert rb.hhi([5]) == pytest.approx(1.0)


def test_dividend_and_funding_sensitivity():
    """Delta 10m, yield 3%, dividends -10%: -30,000. Funding: 100m long, +1 bp: -10,000."""
    assert rb.dividend_exposure_pnl(10e6, 0.03, -10) == pytest.approx(-30_000)
    assert rb.funding_sensitivity(100e6) == pytest.approx(-10_000)


def test_unexplained_residual_of_rounded_components():
    """Components 0.004 and 0.004 each round to 0.00: with total 0.01, the residual is 0.01."""
    assert dg.unexplained(0.01, [0.004, 0.004]) == pytest.approx(0.01)
    assert dg.unexplained(100.0, [60.126, 39.874]) == pytest.approx(0.0)


def test_error_sizes():
    """Spread booked 30 not 40 on 25m for 30 days: -2,083.33. Dividend of 1.20 on 50,000 shares missed:
    -60,000. Fixing 4.10% booked not 4.00% on 10m for 7 days: +194.44. Stale 11.13 vs 11.35 on 50,000: -11,000."""
    assert dg.spread_error_impact(25e6, 30, 40, 30) == pytest.approx(-2083.33, abs=0.01)
    assert dg.missed_dividend_impact(50_000, 1.20) == pytest.approx(-60_000)
    assert dg.fixing_error_impact(10e6, 0.041, 0.040, 7) == pytest.approx(194.44, abs=0.01)
    assert dg.stale_mark_impact(50_000, 11.13, 11.35) == pytest.approx(-11_000)


def test_classify():
    """The amount -2,083 sits within 5 of the spread error; nothing within 5 of 500."""
    cands = {"wrong_spread": -2083.33, "missed_dividend": -60_000.0}
    assert dg.classify(-2083.0, cands, 5.0) == "wrong_spread"
    assert dg.classify(500.0, cands, 5.0) is None

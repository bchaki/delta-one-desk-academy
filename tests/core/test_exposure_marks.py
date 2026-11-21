"""Tests for cost-of-exposure and mark-control helpers."""

import pytest

from core.booking import marks
from core.pricing import exposure as ex


def test_exposure_cost_hand_calc():
    """10m, 90 days ACT/360, spread 20 bps, fee 5 bps, leakage 10 bps, 3 bps one-way, one round trip,
    1 bp one-off. Running = 10m x 35 bps x 90/360 = 8,750. Trading = 10m x (3 x 2 + 1) bps = 7,000.
    Total 15,750; annualised = 15,750 / 10m x 4 x 10,000 = 63 bps."""
    c = ex.exposure_cost("x", 10e6, 90, 360, 20, 5, 10, 3, 1.0, 1.0)
    assert c.running == pytest.approx(8750)
    assert c.trading == pytest.approx(7000)
    assert c.total == pytest.approx(15750)
    assert c.total_bps_pa == pytest.approx(63.0)


def test_exposure_validates():
    with pytest.raises(ValueError):
        ex.exposure_cost("x", 1e6, 0, 360, 10)


def test_breakeven_days():
    """A: fixed 10 bps, 5 bps/yr; B: fixed 2 bps, 25 bps/yr. 10 + 5t = 2 + 25t -> t = 0.4 years = 144 days."""
    assert ex.breakeven_days(10, 5, 2, 25) == pytest.approx(144.0)
    assert ex.breakeven_days(10, 25, 2, 5) is None  # A costs more fixed and more running: never
    assert ex.breakeven_days(1, 5, 2, 5) is None


def test_stale_and_move_flags():
    """A repeated price is flagged; a 6% move is flagged at a 5.5% threshold (the 5% first move is not)."""
    p = [10.0, 10.5, 10.5, 11.13, 11.13]
    assert marks.stale_flags(p) == [2, 4]
    assert marks.move_flags(p, 0.055) == [3]


def test_source_breaks():
    """Secondary 10.02 vs primary 10.00 is +20 bps: flagged at a 10 bps tolerance, not at 25."""
    assert marks.source_breaks([10.0, 10.0], [10.0, 10.02], 10) == [(1, pytest.approx(20.0))]
    assert marks.source_breaks([10.0], [10.02], 25) == []
    with pytest.raises(ValueError):
        marks.source_breaks([1.0], [1.0, 2.0], 5)


def test_mark_impact():
    """1,000 shares marked 101 instead of 100 overstates PnL by 1,000; with FX 1.1 by 1,100."""
    assert marks.mark_impact(1000, 101, 100) == 1000
    assert marks.mark_impact(1000, 101, 100, 1.1) == pytest.approx(1100)

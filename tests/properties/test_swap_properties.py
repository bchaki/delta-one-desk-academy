from collections import defaultdict
from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.dividends import Dividend
from core.pricing import swaps as sw
from core.types import Direction

START, END = date(2026, 11, 16), date(2026, 11, 23)


@settings(max_examples=75, deadline=None)
@given(
    shares=st.integers(100, 100_000),
    s0=st.floats(5, 500),
    move=st.floats(-0.3, 0.3),
    spread=st.floats(10, 200),
    ftp=st.floats(0, 100),
    rate=st.floats(0, 0.08),
    direction=st.sampled_from(list(Direction)),
)
def test_swap_legs_net_against_hedge_to_leave_the_spread(
    shares, s0, move, spread, ftp, rate, direction
):
    """Over one period the equity and funding legs net against the desk hedge, leaving only
    N x (spread - cost) x tau (no WHT, 100% pass-through, notional reset)."""
    fixings = defaultdict(lambda: rate)
    divs = [Dividend(date(2026, 11, 18), date(2026, 11, 25), 0.01 * s0)]
    t = sw.SwapTerms(direction, shares, s0, spread)
    e = sw.desk_economics(
        t, START, END, s0, s0 * (1 + move), fixings, divs, ftp_bps=ftp, borrow_bps=ftp
    )
    assert e.total == pytest.approx(e.spread_edge, abs=0.05)

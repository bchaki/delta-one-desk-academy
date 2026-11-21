import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core import indices as ix
from core.financing import sbl
from core.margin import exchange, simm_lite
from core.margin.exchange import FuturePos
from core.pricing import futures as fu

pos_float = st.floats(0.5, 1_000, allow_nan=False, allow_infinity=False)


@settings(max_examples=100, deadline=None)
@given(
    spot=pos_float,
    r=st.floats(-0.05, 0.15),
    divs=st.lists(st.tuples(st.floats(0.01, 2.0), st.floats(0, 10)), max_size=5),
)
def test_futures_converge_to_spot_at_expiry(spot, r, divs):
    """At T = 0 the model forward is the spot price, whatever the rate and the dividends still to come."""
    assert fu.model_forward(spot, r, divs, 0.0) == pytest.approx(spot)


@settings(max_examples=100, deadline=None)
@given(spot=pos_float, t=st.floats(0.01, 5.0))
def test_zero_rates_zero_dividends_forward_equals_spot(spot, t):
    assert fu.model_forward(spot, 0.0, [], t) == pytest.approx(spot)


@settings(max_examples=100, deadline=None)
@given(
    prices=st.lists(pos_float, min_size=2, max_size=8),
    data=st.data(),
)
def test_divisor_adjustment_leaves_level_unchanged(prices, data):
    """Changing a constituent's share count and adjusting the divisor keeps the level identical."""
    n = len(prices)
    shares = data.draw(st.lists(st.floats(1e3, 1e6), min_size=n, max_size=n))
    ff = data.draw(st.lists(st.floats(0.1, 1.0), min_size=n, max_size=n))
    cap = [1.0] * n
    divisor = data.draw(st.floats(1.0, 1e6))
    level = ix.index_level(prices, shares, ff, cap, divisor)
    new_shares = list(shares)
    i = data.draw(st.integers(0, n - 1))
    new_shares[i] *= data.draw(st.floats(0.2, 3.0))
    d2 = ix.adjust_divisor(
        divisor,
        ix.index_value(prices, shares, ff, cap),
        ix.index_value(prices, new_shares, ff, cap),
    )
    assert ix.index_level(prices, new_shares, ff, cap, d2) == pytest.approx(level, rel=1e-9)


@settings(max_examples=100, deadline=None)
@given(
    prices=st.lists(st.floats(1, 500), min_size=2, max_size=30),
    margin=st.sampled_from([1.02, 1.05]),
    min_transfer=st.floats(0, 1e6),
)
def test_sbl_collateral_never_below_requirement_after_a_mark(prices, margin, min_transfer):
    """After every mark collateral >= loan value x margin, with or without a minimum transfer."""
    for m in sbl.collateral_path(10_000, prices, margin, min_transfer):
        assert m.collateral_after >= m.required - 1e-6


@settings(max_examples=100, deadline=None)
@given(
    qtys=st.lists(st.integers(-200, 200), min_size=1, max_size=4),
    prods=st.lists(
        st.sampled_from(["ES", "SX5E", "DAX", "FTSE", "D1US30"]), min_size=4, max_size=4
    ),
)
def test_exchange_margin_is_never_negative(qtys, prods):
    positions = [
        FuturePos(prods[i], "Dec" if i % 2 else "Sep", q, 1000.0, 50.0) for i, q in enumerate(qtys)
    ]
    m = exchange.span_like_margin(positions)
    assert m.net >= 0 and m.gross >= 0 and m.credits >= 0


@settings(max_examples=50, deadline=None)
@given(qty=st.integers(1, 500))
def test_perfect_hedge_earns_spread_credit(qty):
    """Long ES against an equal-notional short D1US30: a credit is earned and net < sum of standalone."""
    n = qty * 5000 * 50
    hedge = [
        FuturePos("ES", "Dec", qty, 5000, 50),
        FuturePos("D1US30", "Dec", -n / (1000 * 100), 1000, 100),
    ]
    m = exchange.span_like_margin(hedge)
    assert m.credits > 0
    assert m.net < m.gross


@settings(max_examples=100, deadline=None)
@given(
    sens=st.dictionaries(
        st.integers(1, 12),
        st.lists(st.floats(-1e4, 1e4), min_size=1, max_size=4),
        min_size=1,
        max_size=5,
    )
)
def test_simm_lite_margin_is_non_negative_and_diversifies(sens):
    m = simm_lite.equity_delta_margin(sens)
    assert m.net >= 0
    assert m.net <= m.gross + 1e-6 or m.gross == 0

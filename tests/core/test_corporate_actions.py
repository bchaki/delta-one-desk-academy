import pytest

from core import corporate_actions as ca


def test_split_and_reverse_split():
    """2-for-1: 100 @ 50 -> 200 @ 25. 1-for-10 reverse: 100 @ 5 -> 10 @ 50. Value per old share unchanged."""
    adj = ca.split(2.0)
    assert ca.apply_to_position(100, 50, adj)[:2] == pytest.approx((200, 25))
    assert ca.value_per_old_share(50, adj) == pytest.approx(50)
    rev = ca.split(0.1)
    assert ca.apply_to_position(100, 5, rev)[:2] == pytest.approx((10, 50))
    with pytest.raises(ValueError):
        ca.split(0)


def test_rights_issue():
    """P=100, K=80, 1 new per 4 held (ratio .25): TERP = (100 + 20)/1.25 = 96. Price x 0.96,
    quantity x 1/0.96, notional unchanged."""
    assert ca.rights_issue_terp(100, 80, 0.25) == pytest.approx(96.0)
    adj = ca.rights_issue(100, 80, 0.25)
    assert adj.price_factor == pytest.approx(0.96)
    assert ca.value_per_old_share(100, adj) == pytest.approx(100.0)


def test_special_dividend():
    """P=100, special 5: price x 0.95, 5 cash per share, value 100 preserved."""
    adj = ca.special_dividend(100, 5)
    assert adj.price_factor == pytest.approx(0.95)
    assert ca.value_per_old_share(100, adj) == pytest.approx(100)


def test_spin_off():
    """P=100, spun-off value 10 as 0.5 new share per parent share: parent x 0.90, spin price 20,
    value = 90 + 0.5 x 20 = 100."""
    adj = ca.spin_off(100, 10, 0.5)
    assert adj.price_factor == pytest.approx(0.9)
    assert adj.new_asset_price == pytest.approx(20)
    assert ca.value_per_old_share(100, adj) == pytest.approx(100)
    assert ca.apply_to_position(1000, 100, adj) == pytest.approx((1000, 90, 0, 500))


def test_cash_merger():
    """Offer 55: position closes, 55 cash per share."""
    adj = ca.cash_merger(55)
    assert ca.apply_to_position(100, 53, adj) == pytest.approx((0, 53, 5500, 0))
    assert ca.value_per_old_share(53, adj) == pytest.approx(55)


def test_stock_merger_arb_spread():
    """2.5 acquirer shares (A=20) per target share = deal value 50. Target at 48: value after = 50,
    PnL +2 per share (the arb spread). Target at 50: value preserved."""
    adj = ca.stock_merger(48, 20, 2.5)
    assert ca.value_per_old_share(48, adj) == pytest.approx(50)
    adj2 = ca.stock_merger(50, 20, 2.5)
    assert ca.value_per_old_share(50, adj2) == pytest.approx(50)
    mixed = ca.stock_merger(50, 20, 2.0, cash_per_share=10)
    assert ca.value_per_old_share(50, mixed) == pytest.approx(50)

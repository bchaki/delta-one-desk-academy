import pytest

from core import config
from core.types import Benchmark, DayCount


@pytest.mark.parametrize("name", list(config.ALL_LOADERS))
def test_every_config_loads_with_as_of_and_verify(name):
    """Each config file validates and carries an as_of date, a source and a verify flag."""
    cfg = config.ALL_LOADERS[name]()
    assert cfg.as_of.year == 2026
    assert cfg.source
    assert isinstance(cfg.verify, bool)
    assert "Illustrative, verify against the official source" in cfg.label


def test_benchmark_day_counts():
    """SOFR/ESTR/SARON are ACT/360; SONIA/TONA are ACT/365F (SPEC section 2)."""
    b = config.conventions().benchmarks
    assert b[Benchmark.SOFR].day_count is DayCount.ACT360
    assert b[Benchmark.ESTR].day_count is DayCount.ACT360
    assert b[Benchmark.SARON].day_count is DayCount.ACT360
    assert b[Benchmark.SONIA].day_count is DayCount.ACT365F
    assert b[Benchmark.TONA].day_count is DayCount.ACT365F


def test_tick_value():
    """E-mini S&P 500: tick 0.25 x multiplier 50 = USD 12.50."""
    assert config.contracts().contracts["ES"].tick_value == pytest.approx(12.5)


def test_every_market_benchmark_matches_currency():
    cfg = config.conventions()
    for m in cfg.markets.values():
        assert cfg.benchmarks[m.benchmark].ccy is m.ccy


def test_regulation_has_t1_dates():
    rules = {r.id: r for r in config.regulation().rules}
    dates = {str(k.date) for k in rules["t_plus_1"].key_dates}
    assert "2027-10-11" in dates
    assert rules["sec_10c_1a"].verify is True


def test_sbl_split_sums_to_one():
    s = config.desk().sbl
    assert s.lender_share + s.agent_share == pytest.approx(1.0)

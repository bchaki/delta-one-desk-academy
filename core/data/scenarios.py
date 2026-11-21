"""Scenario definitions for stress tests (thin wrapper over ``config/scenarios.yaml``)."""

from __future__ import annotations

from core import config
from core.config import Scenario


def scenario_ids() -> list[str]:
    return list(config.scenarios().scenarios)


def get_scenario(scenario_id: str) -> Scenario:
    return config.scenarios().scenarios[scenario_id]


def custom_scenario(
    name: str,
    equity_pct: float = 0.0,
    vol_pts: float = 0.0,
    rates_bps: float = 0.0,
    fx_pct: float = 0.0,
    div_pct: float = 0.0,
    borrow_bps: float = 0.0,
    single_name_pct: float = 0.0,
) -> Scenario:
    """Parallel shock across all regions/curves/pairs, for the Stress sandbox."""
    regions = ("US", "EU", "UK", "JP")
    return Scenario(
        name=name,
        kind="custom",
        equity_pct=dict.fromkeys(regions, equity_pct),
        vol_pts=vol_pts,
        rates_bps=dict.fromkeys(("SOFR", "ESTR", "SONIA", "TONA"), rates_bps),
        fx_pct=dict.fromkeys(("EURUSD", "GBPUSD", "USDJPY"), fx_pct),
        div_pct=dict.fromkeys(regions, div_pct),
        borrow_bps=dict.fromkeys(("GC", "warm", "special", "hard_to_borrow"), borrow_bps),
        single_name_pct=single_name_pct,
    )

"""Balance sheet, capital and client profitability (simplified standardised teaching approach).

Not a regulatory calculation: SA-CCR is reduced to RC + a flat supervisory add-on, and risk weights
come from ``config/desk.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass

from core import config


def sa_ccr_ead(
    mtm: float,
    collateral: float,
    notional: float,
    supervisory_factor: float,
    alpha: float | None = None,
) -> float:
    """Exposure at default, SA-CCR-lite: EAD = alpha x (RC + PFE add-on).

    RC = max(MTM - collateral, 0); add-on = supervisory factor x notional (multiplier 1).
    alpha defaults to config (1.4). Simplified: one trade, no netting set or maturity factor.
    """
    a = config.desk().balance_sheet.sa_ccr_alpha if alpha is None else alpha
    return a * (max(mtm - collateral, 0.0) + supervisory_factor * notional)


def leverage_exposure_swap_with_hedge(ead: float, hedge_market_value: float) -> float:
    """Leverage exposure of a swap plus its physical hedge: derivative EAD + hedge stock on balance sheet."""
    return ead + hedge_market_value


def leverage_exposure_margin_loan(loan_amount: float) -> float:
    """A margin loan sits on balance sheet at its funded amount."""
    return loan_amount


def rwa(ead: float, risk_weight: float) -> float:
    """Risk-weighted assets = EAD x risk weight."""
    return ead * risk_weight


def swap_rwa(
    ead: float, counterparty_rw: float, hedge_market_value: float, hedge_rw: float
) -> float:
    """RWA of a hedged swap = EAD x counterparty risk weight + hedge stock x hedge risk weight.

    Simplified: the hedge risk weight is a single flat input (config default 1.0; a lower figure is
    reasonable for hedged inventory). The full version adds market-risk and CVA capital.
    """
    return rwa(ead, counterparty_rw) + rwa(hedge_market_value, hedge_rw)


def capital_required(
    leverage_exposure: float, rwa_total: float, leverage_ratio: float, cet1_ratio: float
) -> float:
    """Capital held = max(leverage ratio x exposure, CET1 ratio x RWA): the binding constraint."""
    return max(leverage_ratio * leverage_exposure, cet1_ratio * rwa_total)


def balance_sheet_charge_bps(
    leverage_exposure: float, notional: float, cost_bps_per_exposure: float
) -> float:
    """Balance sheet charge in bps of notional per year = (exposure / notional) x cost bps."""
    return leverage_exposure / notional * cost_bps_per_exposure


def capital_charge_bps(capital: float, notional: float, cost_of_equity: float) -> float:
    """Capital charge in bps of notional per year = capital x cost of equity / notional x 10,000."""
    return capital * cost_of_equity / notional * 10_000.0


@dataclass(frozen=True)
class Profitability:
    net_contribution: float
    return_on_capital: float
    economic_profit: float


def client_profitability(
    revenue: float,
    funding_cost: float,
    balance_sheet_cost: float,
    capital: float,
    cost_of_equity: float,
) -> Profitability:
    """Net contribution = revenue - funding - balance sheet cost; RoC = net / capital;
    economic profit = net - capital x cost of equity. Annual figures in one currency."""
    net = revenue - funding_cost - balance_sheet_cost
    return Profitability(net, net / capital if capital else 0.0, net - capital * cost_of_equity)

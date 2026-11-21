"""Strategy: client flow and inventory management."""

from __future__ import annotations

import streamlit as st

from core.strategies import flow as fl
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "sfl_"


def sandbox() -> None:
    w = get_world()
    st.markdown(
        "**Thesis.** Clients trade with the desk; the desk quotes a spread, nets opposing flow so it never has to hedge it (internalisation), hedges only what breaches its inventory limit and keeps the spread. Taking risk earns more than agency but adds variance."
    )
    legs_diagram(
        [
            ("Clients", "buy and sell at desk's spread", "in"),
            ("Market", "hedge inventory above the limit", "out"),
            ("Axes (clients)", "advertise inventory the desk wants to move", "out"),
        ]
    )
    c.formula_box(
        r"PnL = \text{spread} - \text{hedge cost} + \text{inventory}\times r",
        {"spread": "bps on gross client notional", "r": "price return while holding inventory"},
    )
    a, b, cc = st.columns(3)
    spread = a.slider("Spread earned (bps of notional)", 1.0, 25.0, 8.0, 0.5, key=P + "sp")
    hedge = b.slider("Hedge cost (bps)", 0.0, 15.0, 3.0, 0.5, key=P + "hc")
    lim = cc.number_input("Inventory limit (USD)", 1e5, 1e9, 5e6, 1e6, key=P + "lim", format="%.0f")
    tpd = a.slider("Client trades a day", 1, 20, 6, key=P + "tpd")
    size = b.number_input("Mean trade size (USD)", 1e5, 1e8, 2e6, 5e5, key=P + "sz", format="%.0f")
    bias = cc.slider(
        "Flow imbalance (buy probability minus 50%)", 0.0, 0.4, 0.0, 0.05, key=P + "bias"
    )
    vol = a.slider("Daily volatility (%)", 0.5, 4.0, 1.5, 0.25, key=P + "vol") / 100
    seed = int(b.number_input("Scenario seed", 0, 9999, w.market.seed, key=P + "seed"))
    r = fl.simulate(seed, 250, size, tpd, spread, hedge, vol, lim, bias)
    d = r.daily
    c.metric_row(
        [
            ("Total PnL, 250 days", f"{r.total:,.0f}", f"spread {r.total_spread:,.0f}"),
            (
                "Internalisation",
                f"{fl.internalisation_rate(d):.0%}",
                "share of gross notional not hedged",
            ),
            ("Worst day", f"{(d.spread - d.hedge_cost + d.price_pnl).min():,.0f}", None),
            ("Peak inventory", f"{d.inventory.abs().max():,.0f}", f"limit {lim:,.0f}"),
        ]
    )
    st.plotly_chart(
        charts.lines(
            (d.spread - d.hedge_cost + d.price_pnl).cumsum().to_frame("Cumulative PnL"),
            "Cumulative PnL",
            "Day",
            "USD",
        ),
        use_container_width=True,
    )
    decomposition(
        {
            "Spread on client flow": r.total_spread,
            "Hedging cost": -r.total_hedge_cost,
            "Inventory price PnL": r.total_price_pnl,
        },
        "PnL decomposition (USD)",
        "USD",
    )
    st.plotly_chart(
        charts.lines(
            d[["inventory"]].rename(columns={"inventory": "Inventory (USD)"}),
            "Inventory through time",
            "Day",
            "USD, negative = desk short",
        ),
        use_container_width=True,
    )
    st.markdown("**Risk against agency on one trade**")
    n = st.number_input("Trade size (USD)", 1e5, 1e9, 10e6, 1e6, key=P + "tn", format="%.0f")
    hold = st.slider("Days to unwind", 0.5, 10.0, 3.0, 0.5, key=P + "hold")
    rt = fl.risk_trade_ev(n, spread, hedge, vol, hold)
    c.metric_row(
        [
            ("Agency PnL (1 bp commission)", f"{fl.agency_pnl(n, 1.0):,.0f}", None),
            (
                "Risk trade expected PnL",
                f"{rt['expected']:,.0f}",
                f"one-sigma risk {rt['one_sigma_risk']:,.0f}",
            ),
            ("Expected / one sigma", f"{rt['ratio']:.3f}", None),
        ]
    )
    st.caption(
        "Seeded simulation: one name, normal trade sizes, inventory hedged when it breaches the limit. A teaching model of the economics, not a forecast."
    )

    def one_way() -> dict[str, str]:
        r2 = fl.simulate(seed, 250, size, tpd, spread, hedge, vol, lim, 0.4)
        return {
            "Internalisation, balanced": f"{fl.internalisation_rate(d):.0%}",
            "Internalisation, one-way flow": f"{fl.internalisation_rate(r2.daily):.0%}",
            "Hedging cost": f"{r.total_hedge_cost:,.0f} → {r2.total_hedge_cost:,.0f}",
        }

    def vol_up() -> dict[str, str]:
        r2 = fl.simulate(seed, 250, size, tpd, spread, hedge, vol * 2, lim, bias)
        return {
            "Worst day now": f"{(d.spread - d.hedge_cost + d.price_pnl).min():,.0f}",
            "Worst day with volatility doubled": f"{(r2.daily.spread - r2.daily.hedge_cost + r2.daily.price_pnl).min():,.0f}",
        }

    def limit_off() -> dict[str, str]:
        r2 = fl.simulate(seed, 250, size, tpd, spread, hedge, vol, lim * 20, bias)
        return {
            "Peak inventory with a limit": f"{d.inventory.abs().max():,.0f}",
            "Peak inventory with the limit ignored": f"{r2.daily.inventory.abs().max():,.0f}",
            "Lesson": "Limits convert flow risk into hedging cost, by design.",
        }

    risk_buttons(
        P,
        [
            Risk("One-way flow", "Clients all on the same side.", one_way),
            Risk("Volatility doubles", "Inventory is worth more or less, fast.", vol_up),
            Risk("Ignore the limit", "No hedging of inventory.", limit_off),
        ],
    )
    c.reset_button(P)


render_module("s_flow", sandbox)

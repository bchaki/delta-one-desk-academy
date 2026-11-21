"""Cash Equities & Program Trading."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from core import config
from core.pricing import program_trading as pt
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings

P = "cp_"


def sandbox() -> None:
    s = get_settings()
    t1, t2 = st.tabs(["Impact and risk charge", "Basket risk bid"])
    with t1:

        def comp(v):
            q = v["adv_pct"] / 100 * v["adv"]
            imp = pt.sqrt_impact_bps(v["k"], v["vol"] / 100, q, v["adv"])
            risk = pt.risk_charge_bps(v["vol"] / 100, v["h"], v["ra"])
            xs = np.linspace(1, 50, 50)
            ys = [
                pt.sqrt_impact_bps(v["k"], v["vol"] / 100, x / 100 * v["adv"], v["adv"]) for x in xs
            ]
            fig = charts.lines(
                pd.DataFrame({"Impact (bps)": ys}, index=xs),
                "Square-root impact grows slower than size",
                "Order size (% of ADV)",
                "Impact (bps)",
            )
            return Out(
                metrics=[
                    ("Order size", f"{q:,.0f} shares", f"{v['adv_pct']:.0f}% of ADV"),
                    ("Impact", f"{imp:.1f} bps", None),
                    ("Risk charge", f"{risk:.1f} bps", f"{v['h']:.0f}-day horizon"),
                    ("Total cost to client", f"{imp + risk + v['hs']:.1f} bps", "with half spread"),
                ],
                figures=[fig],
                formula=(
                    r"impact = k\,\sigma_{d}\sqrt{Q/ADV}\times 10^4",
                    {
                        "k": "impact coefficient",
                        "sigma_d": "daily volatility",
                        "Q": "order",
                        "ADV": "avg daily volume",
                    },
                    [
                        rf"{v['k']:.2f}\times{v['vol'] / 100:.3f}\times\sqrt{{{v['adv_pct'] / 100:.2f}}}\times10^4 = {imp:.1f}"
                    ],
                ),
            )

        calculator(
            P + "im_",
            [
                Num(
                    "k",
                    "Impact coefficient k",
                    float(config.desk().trading_costs.impact_k),
                    0.1,
                    2.0,
                    0.05,
                ),
                Num("vol", "Daily volatility (%)", 2.0, 0.2, 10.0, 0.1),
                Num("adv", "ADV (shares)", 1_000_000.0, 1_000.0, None, 100_000.0, "%.0f"),
                Num("adv_pct", "Order (% of ADV)", 10.0, 1.0, 100.0, 1.0, "%.0f"),
                Num("h", "Horizon (days)", 2.0, 0.5, 20.0, 0.5, "%.1f"),
                Num("ra", "Risk aversion", 0.5, 0.0, 3.0, 0.1),
                Num("hs", "Half spread (bps)", 2.0, 0.0, 50.0, 0.5, advanced=True),
            ],
            comp,
            [
                "Quadruple the order: impact doubles, not quadruples.",
                "Lengthen the horizon to 8 days and watch the risk charge.",
            ],
            advanced=s.advanced,
        )
    with t2:
        n = st.slider("Legs", 2, 6, 3, key=P + "n")
        rho = st.slider("Pairwise correlation", 0.0, 1.0, 0.5, 0.05, key=P + "rho")
        h = st.slider("Horizon (days)", 1.0, 10.0, 2.0, 0.5, key=P + "bh")
        ra = st.slider("Risk aversion", 0.1, 2.0, 0.5, 0.1, key=P + "bra")
        legs = [
            pt.BasketLeg(50_000.0 * (i + 1), 40.0 + 15 * i, 600_000.0 * (i + 1), 0.012 + 0.003 * i)
            for i in range(n)
        ]
        bid = pt.principal_risk_bid(legs, 2.0, 0.7, rho, h, ra)
        mean, std = pt.win_pnl_moments(bid)
        c.metric_row(
            [
                ("Notional", f"{bid.notional:,.0f}", "currency units"),
                ("Bid", f"{bid.total_bps:.1f} bps", f"{bid.total_amount:,.0f} charged"),
                ("Expected PnL if won", f"{mean:+,.0f}", "= risk charge"),
                ("PnL std dev", f"{std:,.0f}", None),
            ]
        )
        sims = pt.simulate_win_pnl(bid, 5000, seed=1)
        st.plotly_chart(
            charts.bars(
                ["Half spread", "Impact", "Risk charge"],
                [bid.half_spread_bps, bid.impact_bps, bid.risk_charge_bps],
                "Principal risk bid components (bps)",
                "bps",
            ),
            use_container_width=True,
        )
        st.caption(
            f"Simulated win PnL (5,000 normal market moves): 5th percentile {np.percentile(sims, 5):,.0f}, "
            f"95th {np.percentile(sims, 95):,.0f}. Legs are synthetic and long-only; amounts in currency units."
        )
        c.what_to_try(
            [
                "Raise correlation to 1.0: the diversification benefit disappears.",
                "Add legs: basket vol falls but impact is unchanged.",
            ]
        )
        c.reset_button(P)


render_module("cash_program", sandbox)

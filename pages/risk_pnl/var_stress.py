"""VaR, ES & Stress."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core.data.scenarios import scenario_ids
from core.risk import basic as rb
from core.risk import var as vr
from core.risk.sensitivities import snapshot, usd_exposure_vector
from core.risk.stress import all_scenarios, apply_scenario
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "vs_"


def _exposure(w):
    snap = snapshot(w.book, w.market, w.as_of)
    exp = usd_exposure_vector(snap)
    return exp[exp.abs() > 1.0]


def book_var() -> None:
    s = get_settings()
    w = get_world()
    conf = st.select_slider("Confidence", [0.95, 0.975, 0.99], 0.99, key=P + "conf")
    look = st.slider("Lookback (trading days)", 60, 500, 250, 10, key=P + "look")
    exp = _exposure(w)
    rets = vr.usd_returns(w.market, list(exp.index), w.as_of, look)
    pnl = vr.hist_pnl(exp, rets)
    h, es = vr.var_from_pnl(pnl, conf), vr.es_from_pnl(pnl, 0.975)
    p = vr.parametric_var(exp, rets, conf)
    mc, mc_es = vr.mc_var(exp, rets, conf)
    c.metric_row(
        [
            (f"Historical VaR {conf:.1%}", f"{h:,.0f} USD", "1 day"),
            ("Parametric VaR", f"{p:,.0f} USD", "normal, sample covariance"),
            ("Monte Carlo VaR", f"{mc:,.0f} USD", "seeded"),
            ("Expected shortfall 97.5%", f"{es:,.0f} USD", f"MC {mc_es:,.0f}"),
        ]
    )
    fig = go.Figure(go.Histogram(x=pnl, nbinsx=40, name="Historical PnL"))
    fig.add_vline(x=-h, line_dash="dash", annotation_text="-VaR")
    st.plotly_chart(
        charts.style(
            fig, "One-day PnL of today's exposures under past returns (USD)", "PnL (USD)", "Days"
        ),
        use_container_width=True,
    )
    comp = vr.component_var(exp, rets, conf).sort_values(key=abs, ascending=False).head(10)
    st.plotly_chart(
        charts.bars(
            list(comp.index),
            list(comp.values),
            "Component VaR: top contributors (USD); negative = reduces risk",
            "USD",
        ),
        use_container_width=True,
    )
    ex = vr.backtest_exceptions(pnl, np.full(len(pnl), p))
    st.markdown(
        f"**In-sample check.** Today's exposures against their own last {len(pnl)} days exceeded the parametric VaR on **{ex}** days "
        f"(expected about {len(pnl) * (1 - conf):.1f}). Zone for 250 days at 99%: **{vr.traffic_light(ex)}**. "
        "A genuine backtest uses each day's own forecast and positions; this is a teaching illustration."
    )
    if s.advanced:
        c.blotter(comp.round(0).to_frame("component_var_usd"), "component_var", key=P + "dl")
    st.caption(
        "USD, desk side. Delta-only, USD returns of local price times FX; historical window of equal-weighted days."
    )


def two_asset() -> None:
    def comp(v):
        a = rb.parametric_var_1d(v["e1"], v["s1"] / 100, v["conf"] / 100)
        b = rb.parametric_var_1d(v["e2"], v["s2"] / 100, v["conf"] / 100)
        both = rb.two_asset_var(
            v["e1"], v["e2"], v["s1"] / 100, v["s2"] / 100, v["rho"], v["conf"] / 100
        )
        return Out(
            metrics=[
                ("Position 1 alone", f"{a:,.0f}", None),
                ("Position 2 alone", f"{b:,.0f}", None),
                ("Combined", f"{both:,.0f}", f"diversification benefit {a + b - both:,.0f}"),
                (
                    f"{v['days']:.0f}-day combined",
                    f"{rb.scale_var(both, v['days']):,.0f}",
                    "square-root-of-time",
                ),
                (
                    "Expected shortfall 97.5%, position 1",
                    f"{rb.es_normal(v['e1'], v['s1'] / 100):,.0f}",
                    None,
                ),
            ],
            formula=(
                r"VaR = z\sqrt{(e_1\sigma_1)^2+(e_2\sigma_2)^2+2\rho e_1e_2\sigma_1\sigma_2}",
                {"z": "normal quantile", "e": "signed exposure", "sigma": "daily volatility"},
                [],
            ),
        )

    calculator(
        P + "ta_",
        [
            Num("e1", "Exposure 1 (signed)", 10_000_000.0, None, None, 1_000_000.0, "%.0f"),
            Num("e2", "Exposure 2 (signed)", -9_000_000.0, None, None, 1_000_000.0, "%.0f"),
            Num("s1", "Daily vol 1 (%)", 1.5, 0.05, 20.0, 0.1),
            Num("s2", "Daily vol 2 (%)", 1.4, 0.05, 20.0, 0.1),
            Num("rho", "Correlation", 0.9, -1.0, 1.0, 0.05),
            Num("conf", "Confidence (%)", 99.0, 90.0, 99.9, 0.5),
            Num("days", "Horizon (days)", 10.0, 1.0, 250.0, 1.0, "%.0f"),
        ],
        comp,
        [
            "Set correlation to 1 and the exposures equal and opposite: VaR vanishes.",
            "Set correlation to 0 and watch the hedge stop working.",
        ],
    )
    c.reset_button(P)


def stress_tab() -> None:
    w = get_world()
    table = all_scenarios(w.book, w.market, w.as_of)
    st.markdown("**All scenarios, by factor (USD, desk side)**")
    c.blotter(table.round(0), "stress_table", key=P + "dl_st")
    pick = st.selectbox("Scenario", scenario_ids(), key=P + "sc")
    r = apply_scenario(w.book, w.market, w.as_of, pick)
    c.metric_row(
        [
            (r.scenario, f"{r.total:,.0f} USD", "illustrative scenario"),
            ("Hedges", f"{r.by_leg['hedges']:,.0f}", None),
            ("Client swaps", f"{r.by_leg['client_swaps']:,.0f}", None),
        ]
    )
    st.plotly_chart(
        charts.waterfall(r.by_factor, f"{r.scenario}: loss by factor (USD)", "USD", "Total"),
        use_container_width=True,
    )
    st.caption(
        "Scenarios are stylised teaching approximations in the spirit of each episode, labelled illustrative and to be verified."
    )


render_module(
    "var_stress", book_var, extra_tabs={"Two-asset calculator": two_asset, "Stress": stress_tab}
)

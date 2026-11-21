"""Cost of Exposure: futures versus swap versus ETF versus cash stocks."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.pricing import exposure as ex
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_settings

P = "ce_"


def sandbox() -> None:
    s = get_settings()
    n = st.number_input("Notional", 1e5, 1e10, 50e6, 1e6, key=P + "n", format="%.0f")
    days = st.slider("Holding period (days)", 5, 1080, 90, key=P + "d")
    rolls = st.slider(
        "Futures rolls during the hold",
        0,
        12,
        max(days // 90 - 1, 0) if False else 1,
        key=P + "rolls",
    )
    st.caption(
        "ACT/360. Costs in bps over the benchmark; inputs illustrative. Edit any assumption below."
    )
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.markdown("**Futures**")
        f_fin = st.number_input("Financing spread (bps pa)", 0.0, 200.0, 12.0, 1.0, key=P + "ff")
        f_tr = st.number_input("One-way trading (bps)", 0.0, 50.0, 1.5, 0.5, key=P + "ft")
    with a2:
        st.markdown("**Swap**")
        s_fin = st.number_input("Spread (bps pa)", 0.0, 500.0, 40.0, 1.0, key=P + "sf")
        s_lk = st.number_input("Dividend leakage (bps pa)", 0.0, 200.0, 15.0, 1.0, key=P + "sl")
        s_tr = st.number_input("One-way trading (bps)", 0.0, 50.0, 2.0, 0.5, key=P + "st")
    with a3:
        st.markdown("**ETF**")
        e_fin = st.number_input(
            "Investor funding spread (bps pa)", 0.0, 500.0, 50.0, 1.0, key=P + "ef"
        )
        e_fee = st.number_input("TER (bps pa)", 0.0, 200.0, 9.0, 1.0, key=P + "ee")
        e_tr = st.number_input("One-way trading (bps)", 0.0, 50.0, 2.0, 0.5, key=P + "et")
        e_one = st.number_input("One-off (bps)", 0.0, 100.0, 1.0, 0.5, key=P + "eo")
    with a4:
        st.markdown("**Cash stocks**")
        c_fin = st.number_input(
            "Investor funding spread (bps pa)", 0.0, 500.0, 50.0, 1.0, key=P + "cf"
        )
        c_tr = st.number_input("One-way trading (bps)", 0.0, 50.0, 3.0, 0.5, key=P + "ct")
        c_one = st.number_input(
            "Stamp duty / tax on entry (bps)", 0.0, 100.0, 10.0, 0.5, key=P + "co"
        )

    def all_costs(d: int):
        return [
            ex.exposure_cost("Futures", n, d, 360, f_fin, 0, 0, f_tr, 1.0 + rolls),
            ex.exposure_cost("Swap", n, d, 360, s_fin, 0, s_lk, s_tr, 1.0),
            ex.exposure_cost("ETF", n, d, 360, e_fin, e_fee, 0, e_tr, 1.0, e_one),
            ex.exposure_cost("Cash stocks", n, d, 360, c_fin, 0, 0, c_tr, 1.0, c_one),
        ]

    now = all_costs(days)
    best = min(now, key=lambda x: x.total)
    c.metric_row(
        [
            (
                x.name,
                f"{x.total:,.0f}",
                f"{x.total_bps_pa:.1f} bps pa" + (" (cheapest)" if x is best else ""),
            )
            for x in now
        ]
    )
    st.plotly_chart(
        charts.bars(
            [x.name for x in now],
            [x.total for x in now],
            f"Total cost of {n:,.0f} exposure over {days} days",
            "Currency units, investor cost",
        ),
        use_container_width=True,
    )
    grid = list(range(5, 1081, 15))
    curves = pd.DataFrame(
        {x.name: [all_costs(d)[i].total_bps_pa for d in grid] for i, x in enumerate(now)},
        index=grid,
    )
    st.plotly_chart(
        charts.lines(
            curves,
            "Annualised cost by holding period: trading costs fade, running costs stay",
            "Holding period (days)",
            "bps a year",
        ),
        use_container_width=True,
    )
    fut_fixed, fut_pa = f_tr * 2 * (1 + rolls), f_fin
    swp_fixed, swp_pa = s_tr * 2, s_fin + s_lk
    be = ex.breakeven_days(fut_fixed, fut_pa, swp_fixed, swp_pa)
    st.markdown(
        "**Futures versus swap:** "
        + (
            f"the future is cheaper beyond about **{be:.0f} days**."
            if be and fut_fixed > swp_fixed
            else "one wrapper is cheaper at every horizon."
            if be is None
            else f"the swap is cheaper beyond about **{be:.0f} days**."
        )
    )
    if s.advanced:
        c.blotter(
            pd.DataFrame([x.__dict__ for x in now]).set_index("name").round(2),
            "cost_of_exposure",
            key=P + "dl",
        )
    st.caption(
        "Omits market impact, tax by investor type, margin funding, tracking error and optionality. Futures rolls add a round trip each."
    )
    c.what_to_try(
        [
            "Hold for 5 days, then 1,000: the ranking changes.",
            "Set rolls to 12 and watch the futures trading cost.",
        ]
    )
    c.reset_button(P)


render_module("cost_of_exposure", sandbox)

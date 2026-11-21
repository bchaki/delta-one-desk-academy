"""Equity Indices."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from core import indices as ix
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "ix_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    m = w.market
    t1, t2, t3, t4 = st.tabs(
        ["Level and divisor", "Capping", "Inclusion demand", "The synthetic indices"]
    )
    with t1:

        def comp(v):
            pr, sh, ff, cf = (
                [v["p1"], v["p2"], v["p3"]],
                [v["s1"], v["s2"], v["s3"]],
                [1.0, v["f2"] / 100, 1.0],
                [1.0, 1.0, 1.0],
            )
            val = ix.index_value(pr, sh, ff, cf)
            level = val / v["d"]
            new_val = val + v["add"]
            d2 = ix.adjust_divisor(v["d"], val, new_val)
            return Out(
                metrics=[
                    ("Adjusted market value", f"{val:,.0f}", None),
                    ("Index level", f"{level:,.2f}", None),
                    (
                        "Divisor after adding value",
                        f"{d2:,.4f}",
                        f"level stays {new_val / d2:,.2f}",
                    ),
                ],
                formula=(
                    r"D' = D\,\frac{V_{after}}{V_{before}}",
                    {"D": "divisor", "V": "adjusted market value at the same prices"},
                    [rf"D' = {v['d']:,.2f}\times\frac{{{new_val:,.0f}}}{{{val:,.0f}}} = {d2:,.4f}"],
                ),
            )

        calculator(
            P + "lv_",
            [
                Num("p1", "Price 1", 100.0, 0.01),
                Num("p2", "Price 2", 50.0, 0.01),
                Num("p3", "Price 3", 20.0, 0.01),
                Num("s1", "Shares 1", 1000.0, 1.0, None, 100.0, "%.0f"),
                Num("s2", "Shares 2", 2000.0, 1.0, None, 100.0, "%.0f"),
                Num("s3", "Shares 3", 5000.0, 1.0, None, 100.0, "%.0f"),
                Num("f2", "Free float of stock 2 (%)", 50.0, 1.0, 100.0, 5.0),
                Num("d", "Divisor", 100.0, 0.01, None, 1.0),
                Num(
                    "add",
                    "Market value added by a new constituent",
                    50_000.0,
                    0.0,
                    None,
                    5000.0,
                    "%.0f",
                ),
            ],
            comp,
            [
                "Halve the free float of stock 2: the level falls.",
                "Add market value: the divisor rises but the level does not move.",
            ],
        )
    with t2:
        cap = st.slider("Cap per name (%)", 10, 60, 40, key=P + "cap") / 100
        raw = [
            st.number_input(
                f"Uncapped weight {i + 1} (%)",
                value=v,
                key=f"{P}w{i}",
                min_value=0.0,
                max_value=100.0,
            )
            for i, v in enumerate([50.0, 30.0, 12.0, 8.0])
        ]
        arr = np.array(raw) / sum(raw)
        try:
            capped = ix.apply_cap(arr, cap)
            cf = ix.capping_factors(arr, capped)
            df = pd.DataFrame(
                {"uncapped %": arr * 100, "capped %": capped * 100, "capping factor": cf}
            ).round(4)
            st.plotly_chart(
                charts.lines(
                    df[["uncapped %", "capped %"]],
                    "Capping clips the largest weights and spreads the excess pro rata",
                    "Constituent",
                    "Weight (%)",
                ),
                use_container_width=True,
            )
            c.blotter(df, "capping", key=P + "dl_cap", height=180)
        except ValueError as e:
            st.warning(f"{e}. With four names the cap must be at least 25%.")
    with t3:

        def comp3(v):
            d = ix.inclusion_demand(
                v["aum"] * 1e9, v["w"] / 100, v["px"], v["adv"] * 1e6, v["k"], v["vol"] / 100
            )
            return Out(
                metrics=[
                    ("Shares to buy", f"{d.shares:,.0f}", None),
                    ("Notional", f"{d.notional:,.0f}", None),
                    ("Days of ADV", f"{d.days_of_adv:.2f}", None),
                    ("Square-root impact", f"{d.impact_bps:.1f} bps", None),
                ]
            )

        calculator(
            P + "inc_",
            [
                Num("aum", "Assets tracking the index (bn)", 200.0, 0.1, None, 10.0),
                Num("w", "New weight (%)", 0.2, 0.001, 10.0, 0.05, "%.3f"),
                Num("px", "Price", 50.0, 0.01),
                Num("adv", "ADV (million shares)", 4.0, 0.01, None, 0.5),
                Num("k", "Impact coefficient k", 0.7, 0.0, 3.0, 0.05, advanced=True),
                Num("vol", "Daily volatility (%)", 2.0, 0.1, 20.0, 0.1, advanced=True),
            ],
            comp3,
            [
                "Halve ADV: days of ADV double and impact rises by sqrt(2).",
                "Raise the weight to 1%: when does it become a multi-day trade?",
            ],
            advanced=s.advanced,
        )
    with t4:
        name = st.selectbox("Index", list(m.index_level), key=P + "name")
        lvl = pd.DataFrame({"Price level": m.index_level[name], "Total return": m.index_tr[name]})
        st.plotly_chart(
            charts.lines(
                lvl,
                "The total return index outpaces the price index by the dividends paid",
                "Date",
                "Index level (base 1000)",
            ),
            use_container_width=True,
        )
        div = pd.DataFrame(m.index_divisor[name], columns=["date", "divisor"]).set_index("date")
        st.plotly_chart(
            charts.lines(
                div, "The divisor steps at each rebalance or membership change", "Date", "Divisor"
            ),
            use_container_width=True,
        )
        mem = dict(m.index_members[name])
        cur = [d for d in mem if d <= w.as_of][-1]
        members = list(mem[cur])
        px = {t: float(m.prices[t].ffill().at[pd.Timestamp(w.as_of)]) for t in members}
        shares = {
            t: m.shares0[t] * float(m.cumqf[t].ffill().at[pd.Timestamp(w.as_of)]) for t in members
        }
        ff = {t: m.universe.stocks[t].free_float for t in members}
        wt = ix.weights_float_cap(
            [px[t] * m.fx_usd_per(m.universe.stocks[t].ccy, w.as_of) for t in members],
            [shares[t] for t in members],
            [ff[t] for t in members],
        )
        tbl = (
            pd.DataFrame(
                {
                    "weight % (float-cap, before capping)": wt * 100,
                    "free float": [ff[t] for t in members],
                    "cap factor": [m.cap_factors[name].get(t, np.nan) for t in members],
                },
                index=members,
            )
            .sort_values("weight % (float-cap, before capping)", ascending=False)
            .round(3)
        )
        st.caption(
            f"{len(members)} constituents at {w.as_of}. Cap factors shown are the latest in the history."
        )
        c.blotter(tbl, "index_constituents", key=P + "dl_members")


render_module("indices", sandbox)

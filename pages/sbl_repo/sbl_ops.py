"""SBL Operations & Risk."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.financing import sbl
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "so_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    t1, t2 = st.tabs(["Collateral marks on the synthetic path", "Recall options"])
    with t1:
        m = w.market
        names = [t for t in m.universe.stocks if m.universe.stocks[t].listed_from is None]
        tk = st.selectbox("Stock", names, key=P + "tk")
        margin = st.slider("Margin", 1.00, 1.10, 1.02, 0.01, key=P + "mg")
        mta = st.number_input(
            "Minimum transfer amount", 0.0, 1e7, 50_000.0, 10_000.0, key=P + "mta"
        )
        shares = st.number_input(
            "Shares on loan", 1.0, 1e7, 100_000.0, 10_000.0, key=P + "sh", format="%.0f"
        )
        days = [d for d in m.days if d <= w.as_of][-60:]
        px = [m.price(tk, d) for d in days]
        moves = sbl.collateral_path(shares, px, margin, mta)
        df = pd.DataFrame(
            {
                "price": px[1:],
                "required": [x.required for x in moves],
                "collateral": [x.collateral_after for x in moves],
                "transfer": [x.transfer for x in moves],
            },
            index=days[1:],
        )
        c.metric_row(
            [
                (
                    "Top-ups",
                    f"{(df.transfer > 0).sum()}",
                    f"{df.transfer.clip(lower=0).sum():,.0f} posted",
                ),
                (
                    "Returns",
                    f"{(df.transfer < 0).sum()}",
                    f"{-df.transfer.clip(upper=0).sum():,.0f} returned",
                ),
                ("Min cover", f"{(df.collateral / df.required).min():.4f}", "never below 1.0000"),
            ]
        )
        st.plotly_chart(
            charts.lines(
                df[["required", "collateral"]],
                f"{tk}: collateral against requirement (local currency)",
                "Date",
                "Currency units",
            ),
            use_container_width=True,
        )
        if s.advanced:
            c.blotter(df.round(2), "collateral_marks", key=P + "dl")
        c.what_to_try(
            [
                "Raise the minimum transfer amount: returns become rarer.",
                "Raise the margin to 1.05.",
            ]
        )
    with t2:

        def comp(v):
            r = sbl.recall_options(
                v["sh"],
                v["px"],
                v["old"] / 1e4,
                v["new"] / 1e4,
                int(v["days"]),
                360,
                v["prem"] / 100,
                v["imp"] / 100,
                v["int"] / 1e4,
            )
            best = min(r, key=r.get)
            return Out(
                metrics=[
                    (k.replace("_", " ").title(), f"{val:,.0f}", "cheapest" if k == best else None)
                    for k, val in r.items()
                ],
                figures=[
                    charts.bars(
                        [k.replace("_", " ") for k in r],
                        list(r.values()),
                        "Cost of each recall response",
                        "Currency units",
                    )
                ],
            )

        calculator(
            P + "rc_",
            [
                Num("sh", "Shares recalled", 100_000.0, 1.0, None, 10_000.0, "%.0f"),
                Num("px", "Price", 50.0, 0.01, None, 1.0),
                Num("old", "Old fee (bps)", 100.0, 0.0, 10_000.0, 10.0, "%.0f"),
                Num("new", "New fee (bps)", 400.0, 0.0, 10_000.0, 10.0, "%.0f"),
                Num("days", "Horizon (days)", 30.0, 1.0, 360.0, 1.0, "%.0f"),
                Num("prem", "Buy-in premium (%)", 2.0, 0.0, 20.0, 0.5, advanced=True),
                Num("imp", "Market impact (%)", 1.0, 0.0, 20.0, 0.5, advanced=True),
                Num("int", "Internal cost (bps)", 50.0, 0.0, 1000.0, 5.0, "%.0f", advanced=True),
            ],
            comp,
            [
                "Raise the new fee to 3,000 bps: re-borrowing becomes the worst option.",
                "Lengthen the horizon.",
            ],
            advanced=s.advanced,
        )
    c.reset_button(P)


render_module("sbl_ops", sandbox)

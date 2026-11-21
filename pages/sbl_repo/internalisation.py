"""Internalisation & Financing Book."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.financing import internalisation as it
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "in_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    t1, t2 = st.tabs(["One name", "Book of special names"])
    with t1:

        def comp(v):
            n = it.NameInput("X", v["px"], v["short"], v["long"], v["inv"], v["street"])
            r = it.internalise_name(n, v["rh"] / 100, v["ic"], int(v["days"]), 360)
            return Out(
                metrics=[
                    ("Internal supply", f"{r.internal_supply:,.0f} sh", None),
                    (
                        "Internal cover",
                        f"{r.internal_cover:,.0f} sh",
                        f"{r.internal_cover / max(r.short_demand, 1):.0%} of demand",
                    ),
                    ("Street borrow", f"{r.street_borrow:,.0f} sh", None),
                    (
                        "Saving",
                        f"{r.savings:,.0f}",
                        f"{r.savings_bps:.1f} bps of short notional, annualised",
                    ),
                ],
                figures=[
                    charts.bars(
                        ["Internal cover", "Street borrow"],
                        [r.internal_cover, r.street_borrow],
                        "Where the short is covered from (shares)",
                        "Shares",
                    )
                ],
            )

        calculator(
            P + "nm_",
            [
                Num("px", "Price", 50.0, 0.01, None, 1.0),
                Num("short", "Client short shares", 200_000.0, 0.0, None, 10_000.0, "%.0f"),
                Num("long", "Client long shares", 150_000.0, 0.0, None, 10_000.0, "%.0f"),
                Num("inv", "Desk inventory", 20_000.0, 0.0, None, 5_000.0, "%.0f"),
                Num("rh", "Rehypothecable share (%)", 50.0, 0.0, 100.0, 5.0, "%.0f"),
                Num("street", "Street fee (bps)", 300.0, 0.0, 10_000.0, 10.0, "%.0f"),
                Num("ic", "Internal cost (bps)", 50.0, 0.0, 1000.0, 5.0, "%.0f"),
                Num("days", "Days", 30.0, 1.0, 360.0, 1.0, "%.0f"),
            ],
            comp,
            [
                "Halve the rehypothecable share and watch the street borrow.",
                "Set the street fee to 30 bps (GC): the saving almost vanishes.",
            ],
            advanced=s.advanced,
        )
    with t2:
        m = w.market
        fees = m.borrow_fee_bps.loc[pd.Timestamp(w.as_of)]
        top = fees.sort_values(ascending=False).head(8)
        rh = st.slider("Rehypothecable share of client longs (%)", 0, 100, 50, 5, key=P + "rh2")
        ic = st.number_input("Internal cost (bps)", 0.0, 500.0, 50.0, 5.0, key=P + "ic2")
        names = []
        for tk, fee in top.items():
            st_ = m.universe.stocks[tk]
            px = m.price(tk, w.as_of)
            names.append(
                it.NameInput(tk, px, 0.04 * st_.adv, 0.08 * st_.adv, 0.01 * st_.adv, float(fee))
            )
        rows, total, cov = it.internalise_book(names, rh / 100, ic, 30, 360)
        df = pd.DataFrame(
            [
                {
                    "ticker": r.ticker,
                    "fee_bps": n.street_fee_bps,
                    "demand": r.short_demand,
                    "cover": r.internal_cover,
                    "saving": r.savings,
                }
                for r, n in zip(rows, names, strict=True)
            ]
        ).set_index("ticker")
        c.metric_row(
            [
                ("Total saving (30 days)", f"{total:,.0f}", "local-currency units"),
                ("Coverage ratio", f"{cov:.0%}", None),
            ]
        )
        st.plotly_chart(
            charts.bars(
                list(df.index),
                list(df.saving),
                "Saving by name, ranked by street fee",
                "Currency units",
            ),
            use_container_width=True,
        )
        c.blotter(df.round(1), "internalisation_book", key=P + "dl")
        st.caption(
            "Synthetic: shorts are 4% of ADV, client longs 8% and desk inventory 1% in each of the eight highest-fee names at the as-of date."
        )
        c.reset_button(P)


render_module("internalisation", sandbox)

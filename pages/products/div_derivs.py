"""Dividend Derivatives & Delta One Notes."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.pricing import dividend_derivs as dd
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "dd_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    t1, t2, t3 = st.tabs(
        ["Swap payoff and cancellations", "Tracker note", "Synthetic dividend futures"]
    )
    with t1:

        def comp(v):
            fc = v["fc"]
            pnl = dd.dividend_swap_pnl(v["u"], v["k"], v["real"])
            pv = dd.dividend_swap_pv(v["u"], v["k"], v["exp"], v["df"])
            xs = [i * 5 for i in range(0, 21)]
            ys = [dd.cancellation_pnl(v["u"], v["k"], fc, x / 100) for x in xs]
            return Out(
                metrics=[
                    ("PnL at settlement (long)", f"{pnl:+,.0f}", "units x (realised - strike)"),
                    ("PV before settlement", f"{pv:+,.0f}", f"DF {v['df']:.3f}"),
                    (
                        "Implied vs forecast",
                        f"{dd.implied_vs_forecast(v['k'], fc)[0]:+.1f} pts",
                        f"{dd.implied_vs_forecast(v['k'], fc)[1]:+.1%}",
                    ),
                ],
                figures=[
                    charts.lines(
                        pd.DataFrame({"Long PnL": ys}, index=xs),
                        "Long dividend swap PnL by share of forecast dividends cancelled",
                        "Dividends cancelled (%)",
                        "PnL (currency units)",
                    )
                ],
                formula=(
                    r"PnL = units\,(realised - strike)",
                    {"realised": "sum of index dividend points over the period"},
                    [rf"{v['u']:,.0f}\times({v['real']:.1f} - {v['k']:.1f}) = {pnl:,.0f}"],
                ),
            )

        calculator(
            P + "sw_",
            [
                Num("u", "Units", 1000.0, 1.0, None, 100.0, "%.0f"),
                Num("k", "Strike (index points)", 90.0, 1.0, None, 1.0, "%.1f"),
                Num("real", "Realised dividends", 95.0, 0.0, None, 1.0, "%.1f"),
                Num("exp", "Expected dividends", 95.0, 0.0, None, 1.0, "%.1f"),
                Num("fc", "Analyst forecast", 95.0, 1.0, None, 1.0, "%.1f"),
                Num("df", "Discount factor", 0.97, 0.5, 1.0, 0.01, "%.3f"),
            ],
            comp,
            [
                "Move the realised level below the strike: the long loses.",
                "Read the chart at 60% cancelled.",
            ],
            advanced=s.advanced,
        )
    with t2:

        def comp2(v):
            val = dd.tracker_note_value(v["n"], v["r"] / 100, v["fee"] / 100, v["y"])
            return Out(
                metrics=[
                    ("Note value", f"{val:,.0f}", "before issuer credit"),
                    ("Fee drag", f"{v['n'] * (1 + v['r'] / 100) - val:,.0f}", None),
                ],
                formula=(
                    r"V = N(1+R)(1-f)^{T}",
                    {"R": "index total return", "f": "annual fee", "T": "years"},
                    [
                        rf"{v['n']:,.0f}\times{1 + v['r'] / 100:.3f}\times{1 - v['fee'] / 100:.4f}^{{{v['y']:.1f}}} = {val:,.0f}"
                    ],
                ),
            )

        calculator(
            P + "nt_",
            [
                Num("n", "Notional", 1_000_000.0, 1.0, None, 100_000.0, "%.0f"),
                Num("r", "Index total return (%)", 8.0, -90.0, 500.0, 1.0, "%.1f"),
                Num("fee", "Annual fee (%)", 1.0, 0.0, 10.0, 0.1, "%.2f"),
                Num("y", "Years", 2.0, 0.1, 10.0, 0.5, "%.1f"),
            ],
            comp2,
            ["Raise the fee to 3% and compare the drag."],
            advanced=s.advanced,
        )
    with t3:
        m = w.market
        years = sorted(m.div_futures)
        pick = st.multiselect(
            "Contract years",
            years,
            default=[y for y in years if y in (2025, 2026, 2027)],
            key=P + "yrs",
        )
        ts = [pd.Timestamp(d) for d in m.days if d <= w.as_of]
        df = pd.DataFrame({f"Dec-{y}": m.div_futures[y].reindex(ts) for y in pick}).dropna(
            how="all"
        )
        if df.empty:
            st.info("Select at least one contract year with data before the as-of date.")
        else:
            st.plotly_chart(
                charts.lines(
                    df, "Synthetic index dividend futures (index points)", "Date", "Index points"
                ),
                use_container_width=True,
            )
        st.caption(
            "Synthetic data. The dip in spring 2025 is the seeded EU dividend-cancellation episode."
        )
        c.reset_button(P)


render_module("div_derivs", sandbox)

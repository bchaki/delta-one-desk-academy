"""Dividends."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from core import config
from core.dividends import (
    dividend_leakage,
    implied_dividend_yield,
    implied_pv_dividends_from_forward,
    net_dividend,
    withholding_rate_pct,
)
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "dv_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    m = w.market
    t1, t2, t3, t4 = st.tabs(
        [
            "Leakage and pass-through",
            "Implied dividends",
            "Ex-date calendar",
            "Index dividend points",
        ]
    )
    with t1:
        mk = st.selectbox(
            "Market of the underlying", list(config.withholding().rates), key=P + "mkt"
        )
        treaty = st.toggle(
            "Treaty rate",
            key=P + "treaty",
            help="Use the reduced treaty rate instead of the statutory rate.",
        )
        wht = withholding_rate_pct(mk, treaty)
        st.caption(f"Withholding rate used: {wht:.2f}% ({'treaty' if treaty else 'statutory'}).")

        def comp(v):
            lk = dividend_leakage(v["g"], v["n"], wht, v["pt"] / 100)
            recv = v["n"] * net_dividend(v["g"], wht)
            paid = v["n"] * v["g"] * v["pt"] / 100
            return Out(
                metrics=[
                    ("Desk receives (net, on hedge)", f"{recv:,.0f}", None),
                    ("Desk pays client", f"{paid:,.0f}", None),
                    ("Desk gain (+) / loss (-)", f"{lk:+,.0f}", None),
                ],
                figures=[
                    charts.bars(
                        ["Receives on hedge", "Pays on swap", "Leakage"],
                        [recv, -paid, lk],
                        "Dividend cash flows for the desk on a long swap",
                        "Currency units",
                    )
                ],
                formula=(
                    r"leakage = N\,[g(1-w) - p\,g]",
                    {
                        "N": "shares",
                        "g": "gross dividend per share",
                        "w": "withholding rate",
                        "p": "pass-through",
                    },
                    [
                        rf"{v['n']:,.0f}\,[{v['g']:.2f}\,(1-{wht / 100:.4f}) - {v['pt'] / 100:.2f}\times{v['g']:.2f}] = {lk:,.0f}"
                    ],
                ),
            )

        calculator(
            P + "lk_",
            [
                Num("n", "Shares", 100_000.0, 0.0, None, 10_000.0, "%.0f"),
                Num("g", "Gross dividend per share", 2.0, 0.0, None, 0.1),
                Num("pt", "Pass-through (%)", 100.0, 1.0, 100.0, 5.0, "%.0f"),
            ],
            comp,
            [
                "Set pass-through to 85%: with a 15% rate the leakage vanishes.",
                "Switch market to CH and toggle treaty: the statutory rate is much higher.",
            ],
        )
        c.illustrative_note(config.withholding())
    with t2:

        def comp2(v):
            df = math.exp(-v["r"] / 100 * v["t"])
            pvd = implied_pv_dividends_from_forward(v["s"], v["f"], df)
            q = implied_dividend_yield(v["s"], v["f"], v["r"] / 100, v["t"])
            return Out(
                metrics=[
                    ("Implied PV of dividends", f"{pvd:.3f}", None),
                    ("Implied continuous yield", f"{q:.3%}", None),
                    (
                        "vs forecast PV",
                        f"{pvd - v['fc']:+.3f}",
                        "market prices a cut" if pvd < v["fc"] else "market prices more",
                    ),
                ],
                formula=(
                    r"PVD = S - F\,DF(T)",
                    {"S": "spot", "F": "forward", "DF": "discount factor to expiry"},
                    [rf"{v['s']:.2f} - {v['f']:.2f}\times{df:.5f} = {pvd:.3f}"],
                ),
            )

        calculator(
            P + "im_",
            [
                Num("s", "Spot", 100.0, 1.0, None, 1.0),
                Num("f", "Forward", 100.6, 1.0, None, 0.05),
                Num("r", "Rate (% cc)", 4.0, 0.0, 20.0, 0.1),
                Num("t", "Years to expiry", 0.5, 0.01, 5.0, 0.05),
                Num("fc", "Analyst forecast PV of dividends", 1.5, 0.0, None, 0.05),
            ],
            comp2,
            [
                "Raise the forward by 0.5: implied dividends fall by about 0.5.",
                "Set the forecast above the implied PV to see the 'market prices a cut' signal.",
            ],
        )
    with t3:
        days = st.slider("Window around the as-of date (days)", 7, 90, 30, key=P + "win")
        rows = [
            {
                "ex_date": e.ex_date,
                "ticker": e.ticker,
                "kind": e.kind,
                "amount": round(e.amount, 4),
                "forecast": round(e.forecast, 4),
                "ccy": m.universe.stocks[e.ticker].ccy.value,
                "yield %": round(100 * e.amount / m.price(e.ticker, m.clamp(e.ex_date)), 2),
            }
            for e in m.dividends
            if abs((e.ex_date - w.as_of).days) <= days
        ]
        df = (
            pd.DataFrame(rows).sort_values("ex_date") if rows else pd.DataFrame(columns=["ex_date"])
        )
        st.write(
            f"{len(df)} ex-dates within {days} days of {w.as_of}. Cancelled dividends show amount 0 against the forecast."
        )
        c.blotter(df, "ex_date_calendar", key=P + "dl_cal")
    with t4:
        name = st.selectbox("Index", list(m.index_div_events), key=P + "idx")
        evs = [(e.ex_date, e.amount) for e in m.index_div_events[name] if e.ex_date <= m.days[-1]]
        df = pd.DataFrame(evs, columns=["ex_date", "points"])
        df["year"] = [d.year for d in df.ex_date]
        by_year = df.groupby("year").points.sum()
        st.plotly_chart(
            charts.bars(
                [str(y) for y in by_year.index],
                list(by_year.values),
                "Annual dividend points paid by the index (the series dividend futures settle to)",
                "Index points",
            ),
            use_container_width=True,
        )
        c.blotter(
            by_year.round(2).to_frame("points"),
            "index_dividend_points",
            key=P + "dl_pts",
            height=200,
        )
        if s.advanced:
            st.caption(
                "Points = sum of dividend x index shares (after free float and capping) / divisor, recorded on each ex-date."
            )


render_module("dividends", sandbox)

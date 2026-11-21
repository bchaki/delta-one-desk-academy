"""Market Data, Marks & EOD."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.booking import marks as mk
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "me_"

EOD = [
    "Load prices, fixings and FX; compare with the expected sources",
    "Run stale, large-move and source-comparison checks",
    "Resolve flags: confirm with market data, override with approval and evidence",
    "Apply today's corporate actions and dividends",
    "Run accruals and resets",
    "Reconcile positions and cash",
    "Run PnL explain and risk",
    "Review unexplained PnL and open breaks",
    "Sign off with product control and release reports",
]


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    m = w.market
    t1, t2, t3 = st.tabs(["Flag scanner", "Impact of a wrong mark", "EOD checklist"])
    with t1:
        sb = next(b for b in w.book.breaks if b.kind == "stale_price")
        names = [t for t in m.universe.stocks if m.universe.stocks[t].listed_from is None]
        tk = st.selectbox("Stock", names, index=names.index(sb.ticker), key=P + "tk")
        thr = st.slider("Large-move threshold (%)", 2.0, 15.0, 8.0, 0.5, key=P + "thr") / 100
        tol = st.slider("Source tolerance (bps)", 1, 100, 25, key=P + "tol")
        apply_stale = st.toggle(
            "Apply the seeded stale mark (as booked)",
            value=True,
            key=P + "stale",
            help="Replaces the break date's price with the previous close, as the booked mark was.",
        )
        days = [d for d in m.days if d <= w.as_of][-120:]
        ts = [pd.Timestamp(d) for d in days]
        px = m.prices[tk].loc[ts].copy()
        if apply_stale and tk == sb.ticker and sb.date in days:
            i = days.index(sb.date)
            px.iloc[i] = px.iloc[i - 1]
        stale = mk.stale_flags(px.tolist())
        moves = mk.move_flags(px.tolist(), thr)
        secondary = (
            m.prices[tk].loc[ts] * (1 + 0.0004 * pd.Series(range(len(ts)), index=ts).mod(5))
        ).tolist()
        brk = mk.source_breaks(px.tolist(), secondary, tol)
        flags = sorted({i for i in stale} | set(moves) | {i for i, _ in brk})
        st.plotly_chart(
            charts.lines(
                pd.DataFrame({"Mark": px}),
                f"{tk}: marks over the last 120 trading days",
                "Date",
                "Price",
            ),
            use_container_width=True,
        )
        rows = [
            {
                "date": days[i],
                "mark": round(float(px.iloc[i]), 4),
                "stale": i in stale,
                "large move": i in moves,
                "source break": i in dict(brk),
            }
            for i in flags
        ]
        c.metric_row(
            [
                ("Stale flags", f"{len(stale)}", None),
                ("Large moves", f"{len(moves)}", f"> {thr:.1%}"),
                ("Source breaks", f"{len(brk)}", f"> {tol} bps"),
            ]
        )
        if rows:
            c.blotter(pd.DataFrame(rows), "mark_flags", key=P + "dl")
        else:
            st.success("No flags on this series.")
        st.caption(
            "The secondary source is synthetic: the primary plus a small deterministic difference that breaks tight tolerances. Fictional data."
        )
        c.what_to_try(
            [
                f"Select {sb.ticker} and toggle the stale mark on and off.",
                "Tighten the source tolerance to 5 bps and watch breaks appear.",
            ]
        )
    with t2:

        def comp(v):
            imp = mk.mark_impact(v["sh"], v["wrong"], v["right"], v["fx"])
            return Out(
                metrics=[
                    ("PnL error", f"{imp:+,.0f}", "positive = booked PnL overstated"),
                    (
                        "Error in bps of position",
                        f"{(v['wrong'] / v['right'] - 1) * 1e4:+.0f} bps",
                        None,
                    ),
                ],
                note="A stale mark usually reverses when the price corrects, so the error lasts a day, but it can breach a limit or mislead a trader meanwhile.",
            )

        calculator(
            P + "im_",
            [
                Num("sh", "Shares held (long)", 50_000.0, 1.0, None, 5_000.0, "%.0f"),
                Num("wrong", "Booked mark", 11.13, 0.0001, None, 0.05, "%.4f"),
                Num("right", "Right mark", 11.35, 0.0001, None, 0.05, "%.4f"),
                Num(
                    "fx", "FX to reporting currency", 1.0, 0.0001, None, 0.01, "%.4f", advanced=True
                ),
            ],
            comp,
            ["Swap the two marks: the sign flips.", "Set a 1,000,000 share position."],
            advanced=s.advanced,
        )
    with t3:
        done = sum(st.checkbox(f"{i + 1}. {x}", key=f"{P}eod{i}") for i, x in enumerate(EOD))
        st.progress(done / len(EOD), text=f"{done} of {len(EOD)} steps complete")
    c.reset_button(P)


render_module("marks_eod", sandbox)

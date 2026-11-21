"""Strategy: dividend trading."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.strategies import dividend as dv
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "sdv_"


def sandbox() -> None:
    w = get_world()
    m = w.market
    st.markdown(
        "**Thesis.** A dividend future settles on dividends actually paid. If the market price embeds more than you expect to be paid, sell it; if less, buy it. The desk also holds dividend exposure on its own books (structured notes, swaps) and uses futures to hedge it."
    )
    legs_diagram(
        [
            ("Exchange / dealer", "buy or sell dividend future", "out"),
            ("Index", "pays realised dividend points", "in"),
        ]
    )
    c.formula_box(
        r"PnL = U\,(D_{settle} - D_{entry})",
        {"U": "units (value per index point)", "D": "dividend index points"},
    )
    years = [y for y in sorted(m.div_futures) if y <= w.as_of.year]
    a, b, cc = st.columns(3)
    year = a.selectbox("Contract year", years, index=min(1, len(years) - 1), key=P + "y")
    off = b.slider("Enter this many trading days after listing", 0, 400, 0, key=P + "off")
    units = cc.number_input(
        "Units (value per point)", 100.0, 1e7, 10_000.0, 1000.0, key=P + "u", format="%.0f"
    )
    bt = dv.year_backtest(m, year, off)
    pnl = dv.future_pnl(units, bt["entry"], bt["settlement"])
    c.metric_row(
        [
            ("Entry", f"{bt['entry']:.2f} pts", None),
            ("Settlement", f"{bt['settlement']:.2f} pts", None),
            ("PnL, long", f"{pnl:,.0f}", f"worst mark {bt['worst_mtm'] * units:,.0f}"),
        ]
    )
    s = m.div_futures[year].loc[: pd.Timestamp(year=year, month=12, day=31)].dropna()
    st.plotly_chart(
        charts.lines(
            s.to_frame(f"Dec-{year} dividend future"),
            "Dividend future through its life",
            "Date",
            "Index dividend points",
        ),
        use_container_width=True,
    )
    decomposition(
        {"Mark-to-market from entry to settlement": pnl}, f"Long Dec-{year} dividend future", "USD"
    )
    st.markdown("**Cancellation stress for a long dividend swap**")
    strike = st.number_input("Strike (points)", 1.0, 100.0, 20.0, key=P + "k")
    forecast = st.number_input("Forecast (points)", 1.0, 100.0, 20.0, key=P + "fc")
    cs = dv.cancellation_stress(units, strike, forecast, [0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0])
    st.plotly_chart(
        charts.bars(
            [f"{int(i * 100)}%" for i in cs.index],
            list(cs.pnl),
            "Long swap PnL as dividends are cancelled",
            "USD",
        ),
        use_container_width=True,
    )
    st.caption(
        "Synthetic data. The synthetic dividend futures do not converge to a fixed fundamental value, so history shows large mark-to-market swings: that is the point, not a signal. No discounting between entry and settlement."
    )

    def cancel_half() -> dict[str, str]:
        return {
            "PnL of long swap, 50% cancelled": f"{cs.pnl.loc[0.5]:,.0f}",
            "PnL of the hedging short": f"{-cs.pnl.loc[0.5]:,.0f}",
        }

    def note_exposure() -> dict[str, str]:
        e = dv.hedge_note_exposure(units, forecast, 2.0, 0.25)
        return {
            "Desk exposure on notes paying dividends (2y, 25% cut)": f"{e:,.0f}",
            "Lesson": "The desk hedged by buying dividends; a cut makes the hedge worth less.",
        }

    def worst() -> dict[str, str]:
        return {
            "Worst mark during the year": f"{bt['worst_mtm'] * units:,.0f}",
            "Final PnL": f"{pnl:,.0f}",
            "Lesson": "The path can be worse than the end result: margin and limits care about the path.",
        }

    risk_buttons(
        P,
        [
            Risk("Half the dividends cancelled", "A 2020-style episode.", cancel_half),
            Risk(
                "Structured-note exposure",
                "The desk's own books are long dividends.",
                note_exposure,
            ),
            Risk("Path risk", "The mark-to-market before settlement.", worst),
        ],
    )
    c.reset_button(P)


render_module("s_dividend", sandbox)

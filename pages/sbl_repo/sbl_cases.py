"""SBL Case Studies: squeeze, recall wave, cum-ex as a compliance case."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.financing import sbl
from ui import charts
from ui import components as c
from ui.content import data_file
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_world

P = "sc_"


def sandbox() -> None:
    w = get_world()
    m = w.market
    t1, t2, t3 = st.tabs(["Squeeze replay", "Squeeze calculator", "Red-flag review"])
    with t1:
        tk = m.squeeze_ticker
        days = [d for d in m.days if d <= w.as_of]
        ts = [pd.Timestamp(d) for d in days]
        px = m.prices[tk].loc[ts]
        fee = m.borrow_fee_bps[tk].loc[ts]
        util = m.utilisation[tk].loc[ts]
        st.markdown(f"Synthetic squeeze name: **{tk}**.")
        st.plotly_chart(
            charts.lines(pd.DataFrame({"Price": px}), f"{tk}: price", "Date", "Price"),
            use_container_width=True,
        )
        st.plotly_chart(
            charts.lines(
                pd.DataFrame({"Borrow fee (bps)": fee}), f"{tk}: borrow fee", "Date", "bps"
            ),
            use_container_width=True,
        )
        st.plotly_chart(
            charts.lines(
                pd.DataFrame({"Utilisation": util}),
                f"{tk}: utilisation",
                "Date",
                "Share of lendable supply",
            ),
            use_container_width=True,
        )
        rec = [r for r in m.recalls if r.ticker == tk]
        if rec:
            c.blotter(
                pd.DataFrame(
                    [{"date": r.date, "ticker": r.ticker, "recalled_pct": r.pct} for r in rec]
                ),
                "squeeze_recalls",
                key=P + "dl",
            )
        st.caption(
            "Synthetic data. Read the three charts together: utilisation and fee move before and with the price."
        )
    with t2:

        def comp(v):
            u = sbl.squeeze_utilisation(v["sup"], v["dem"], v["rec"] / 100, v["mult"])
            fee = sbl.fee_from_utilisation(u, v["gc"], v["k"])
            carry = sbl.loan_fee(v["notional"], fee / 1e4, 30, 360)
            return Out(
                metrics=[
                    ("Utilisation", f"{u:.0%}", "capped at 99%"),
                    ("Borrow fee", f"{fee:,.0f} bps", None),
                    (
                        "30-day carry on the short",
                        f"{carry:,.0f}",
                        f"{v['notional']:,.0f} notional",
                    ),
                ],
            )

        calculator(
            P + "cl_",
            [
                Num("sup", "Lendable supply (shares)", 1_000_000.0, 1.0, None, 100_000.0, "%.0f"),
                Num("dem", "Demand (shares)", 600_000.0, 0.0, None, 50_000.0, "%.0f"),
                Num("rec", "Recalled share of supply (%)", 20.0, 0.0, 90.0, 5.0, "%.0f"),
                Num("mult", "Demand multiplier", 1.5, 0.5, 5.0, 0.1),
                Num("gc", "GC fee (bps)", 30.0, 1.0, 500.0, 5.0, "%.0f"),
                Num("k", "Fee steepness", 2.0, 0.1, 10.0, 0.1),
                Num("notional", "Short notional", 12_000_000.0, 1.0, None, 1_000_000.0, "%.0f"),
            ],
            comp,
            ["Set recalls to 0%: utilisation drops below the cap.", "Raise the demand multiplier."],
        )
    with t3:
        st.markdown(
            "Tick the red flags you can see in a hypothetical dividend-date trade proposal. This is a recognition exercise for compliance, not a method."
        )
        n = sum(
            st.checkbox(f, key=f"{P}rf{i}")
            for i, f in enumerate(data_file("case_studies")["sbl_red_flags"])
        )
        if n == 0:
            st.info("No flags ticked: proceed through the normal checks.")
        elif n < 3:
            st.warning(
                f"{n} flag(s): ask the sales or structuring owner for the commercial purpose and note the answer."
            )
        else:
            st.error(
                f"{n} flags: escalate to compliance, preserve records and do not process until reviewed."
            )
    c.reset_button(P)


render_module("sbl_cases", sandbox)

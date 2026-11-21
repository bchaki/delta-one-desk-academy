"""Inside a Delta One Desk."""

from __future__ import annotations

import numpy as np
import streamlit as st

from core.pnl.ledger import COMPONENTS
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world

P = "di_"

ROLES = {
    "Sales": "Owns the client relationship, quotes spreads, brings flow.",
    "Trader": "Hedges the exposure, runs the risk book, decides inventory.",
    "Structurer": "Builds bespoke baskets, notes and structures.",
    "TDA": "Books trades, runs the daily process, reconciles, chases breaks.",
    "Middle office": "Independently validates trades and PnL.",
    "Operations": "Settles cash and securities, handles confirmations and corporate actions.",
    "Product control": "Owns official PnL, valuation and balance-sheet numbers.",
    "Risk": "Sets and monitors limits, VaR and stress.",
    "Funding / treasury": "Prices internal funding and balance-sheet cost.",
    "Legal & documentation": "ISDAs, CSAs, confirmations and entities.",
    "Tax": "Withholding, 871(m), stamp duty and financial transaction taxes.",
    "Compliance": "Conduct, information barriers, surveillance.",
    "Technology": "Systems, data, automation and controls.",
}


def sandbox() -> None:
    w = get_world()
    t1, t2, t3 = st.tabs(["Stakeholders", "Where the PnL comes from", "Trade lifecycle swimlane"])
    with t1:
        dot = (
            "digraph G { rankdir=LR; node [shape=box, style=rounded]; "
            'Client -> Sales -> "Trader" -> Hedge; Sales -> TDA; Trader -> TDA; '
            'TDA -> "Middle office" -> "Product control"; TDA -> Operations; '
            'Risk -> Trader [style=dashed]; "Funding / treasury" -> Sales [style=dashed]; '
            "Legal -> TDA [style=dashed]; Tax -> TDA [style=dashed]; Compliance -> Trader [style=dashed]; }"
        )
        st.graphviz_chart(dot)
        who = st.selectbox("Role", list(ROLES), index=3, key=P + "role")
        c.term_sheet({"Owns": ROLES[who]}, who)
        st.caption(
            "Solid arrows: flow of trades and information. Dashed arrows: oversight and inputs."
        )
    with t2:
        days = [d for d in w.booked.days if d <= w.as_of]
        n = st.slider("Window (trading days)", 20, 250, 90, key=P + "win")
        window = set(days[-n:])
        mask = np.array([d in window for d in w.booked.days])
        tot = {k: 0.0 for k in COMPONENTS}
        for (_, comp), arr in w.clean.by_book.items():
            tot[comp] += float(arr[mask].sum())
        st.plotly_chart(
            charts.bars(
                list(tot),
                list(tot.values()),
                f"Desk PnL by component, last {n} trading days (USD)",
                "USD, gain to the desk",
            ),
            use_container_width=True,
        )
        st.caption(
            "Synthetic book, clean model, USD, positive = gain to the desk. Price and FX are mostly hedged away "
            "in the full book; the persistent lines are funding, SBL and repo, fees and dividends."
        )
    with t3:
        steps = [
            ("Sales", "Quote and agree the spread"),
            ("Trader", "Approve and hedge"),
            ("TDA", "Book swap, link hedge, check paper"),
            ("Middle office", "Validate trade and price"),
            ("Operations", "Confirm, settle, collect margin"),
            ("TDA", "Resets, dividends, corporate actions"),
            ("Product control", "Sign off PnL and marks"),
            ("TDA", "Unwind and final settlement"),
        ]
        st.markdown("\n".join(f"{i + 1}. **{who}**: {what}" for i, (who, what) in enumerate(steps)))
        dot = (
            "digraph G { rankdir=LR; node [shape=box, style=rounded]; "
            + " -> ".join(f'"{i + 1}. {who}"' for i, (who, _) in enumerate(steps))
            + "; }"
        )
        st.graphviz_chart(dot)
    c.what_to_try(
        [
            "Pick each role and note what they need from the TDA.",
            "Widen the PnL window to 250 days and see which lines persist.",
        ]
    )
    c.reset_button(P)


render_module("desk_inside", sandbox)

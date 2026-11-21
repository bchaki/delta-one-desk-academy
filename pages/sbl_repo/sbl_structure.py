"""SBL Market Structure."""

from __future__ import annotations

import streamlit as st

from core import config
from core.financing import sbl
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Choice, Num, Out, calculator

P = "ss_"


def sandbox() -> None:
    t1, t2 = st.tabs(["Loan, collateral and revenue split", "The lending chain"])
    with t1:

        def comp(v):
            margin = sbl.default_margin(v["xb"] == "Cross-border")
            lv = v["sh"] * v["px"]
            coll = sbl.collateral_required(lv, margin)
            fee = sbl.loan_fee(lv, v["fee"] / 1e4, v["days"], int(v["basis"]))
            owner, agent = sbl.revenue_split(fee, v["share"] / 100)
            div = sbl.manufactured_dividend(v["sh"], v["dps"])
            return Out(
                metrics=[
                    ("Loan value", f"{lv:,.0f}", "currency units"),
                    ("Collateral required", f"{coll:,.0f}", f"margin {margin:.0%}"),
                    ("Fee revenue", f"{fee:,.2f}", f"{v['days']:.0f} days, {v['fee']:.0f} bps"),
                    (
                        "Owner / agent",
                        f"{owner:,.0f} / {agent:,.0f}",
                        f"{v['share']:.0f}% to owner",
                    ),
                    ("Manufactured dividend", f"{div:,.0f}", "borrower pays lender"),
                ],
                formula=(
                    r"collateral = loan \times margin,\quad fee = loan \times f \times d/B",
                    {"f": "annual fee", "d": "days", "B": "day-count basis"},
                    [rf"{lv:,.0f}\times{margin:.2f} = {coll:,.0f}"],
                ),
            )

        calculator(
            P + "ln_",
            [
                Num("sh", "Shares on loan", 100_000.0, 1.0, None, 10_000.0, "%.0f"),
                Num("px", "Price", 50.0, 0.01, None, 1.0),
                Choice("xb", "Loan type", ["Domestic", "Cross-border"]),
                Num("fee", "Fee (bps a year)", 150.0, 0.0, 10_000.0, 10.0, "%.0f"),
                Num("days", "Days", 30.0, 1.0, 720.0, 1.0, "%.0f"),
                Choice("basis", "Day-count basis", [360, 365]),
                Num(
                    "share",
                    "Owner share of revenue (%)",
                    config.desk().sbl.lender_share * 100,
                    0.0,
                    100.0,
                    5.0,
                    "%.0f",
                ),
                Num("dps", "Dividend per share in the period", 1.2, 0.0, None, 0.1),
            ],
            comp,
            [
                "Switch to cross-border and watch collateral rise to 105%.",
                "Set a 3,000 bps fee (hard to borrow) and compare revenue.",
            ],
        )
        c.illustrative_note(config.desk())
    with t2:
        st.graphviz_chart(
            'digraph G { rankdir=LR; node [shape=box, style=rounded]; "Beneficial owner" -> "Lending agent" '
            '-> "Desk (intermediary)" -> "Hedge fund (end borrower)"; "Hedge fund (end borrower)" -> "Desk (intermediary)" '
            '[label="collateral"]; "Desk (intermediary)" -> "Lending agent" [label="collateral"]; }'
        )
        c.term_sheet(
            {
                "Beneficial owner": "Holds long term; lends for yield.",
                "Lending agent": "Custodian running the program; keeps a share.",
                "Desk": "Borrows upstream, lends downstream, earns the spread.",
                "End borrower": "Shorts, hedges or covers fails; pays the fee.",
            },
            "Roles",
        )
        c.reset_button(P)


render_module("sbl_structure", sandbox)

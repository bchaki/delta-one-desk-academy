"""Loan Economics."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.financing import sbl
from ui import charts
from ui.module_page import render_module
from ui.sandbox_kit import Choice, Num, Out, calculator
from ui.state import get_settings

P = "le_"


def sandbox() -> None:
    s = get_settings()
    t1, t2, t3 = st.tabs(["Fee and rebate", "Utilisation to fee", "Cost of a short"])
    with t1:

        def comp(v):
            lv = v["sh"] * v["px"]
            basis = int(v["basis"])
            fee = sbl.loan_fee(lv, v["fee"] / 1e4, v["days"], basis)
            coll = sbl.collateral_required(lv, v["margin"])
            rr = sbl.rebate_rate(v["reinv"] / 100, v["fee"] / 1e4)
            rebate = sbl.cash_rebate(coll, rr, v["days"], basis)
            return Out(
                metrics=[
                    ("Non-cash: fee paid by borrower", f"{fee:,.2f}", None),
                    (
                        "Rebate rate (cash)",
                        f"{rr:.2%}",
                        "negative: borrower pays" if rr < 0 else None,
                    ),
                    (
                        "Cash: rebate received by borrower",
                        f"{rebate:,.2f}",
                        f"on {coll:,.0f} collateral",
                    ),
                ],
                formula=(
                    r"rebate\ rate = reinvestment - fee",
                    {"reinvestment": "return the lender earns on cash", "fee": "annual borrow fee"},
                    [rf"{v['reinv'] / 100:.4f} - {v['fee'] / 1e4:.4f} = {rr:.4f}"],
                ),
            )

        calculator(
            P + "fr_",
            [
                Num("sh", "Shares", 100_000.0, 1.0, None, 10_000.0, "%.0f"),
                Num("px", "Price", 50.0, 0.01, None, 1.0),
                Num("fee", "Fee (bps a year)", 150.0, 0.0, 10_000.0, 10.0, "%.0f"),
                Num("reinv", "Reinvestment rate (%)", 4.25, 0.0, 20.0, 0.05),
                Num("days", "Days", 30.0, 1.0, 720.0, 1.0, "%.0f"),
                Choice("basis", "Day-count basis", [360, 365]),
                Num("margin", "Margin", 1.02, 1.0, 1.2, 0.01, advanced=True),
            ],
            comp,
            [
                "Raise the fee above 425 bps: the rebate rate turns negative.",
                "Compare 360 and 365 bases.",
            ],
            advanced=s.advanced,
        )
    with t2:

        def comp2(v):
            xs = [i / 100 for i in range(5, 99)]
            ys = [sbl.fee_from_utilisation(u, v["gc"], v["k"]) for u in xs]
            now = sbl.fee_from_utilisation(v["u"] / 100, v["gc"], v["k"])
            return Out(
                metrics=[("Fee at this utilisation", f"{now:,.0f} bps", f"GC {v['gc']:.0f} bps")],
                figures=[
                    charts.lines(
                        pd.DataFrame({"Fee (bps)": ys}, index=[x * 100 for x in xs]),
                        "Borrow fee against utilisation (illustrative curve)",
                        "Utilisation (%)",
                        "Fee (bps a year)",
                    )
                ],
                note="Illustrative curve, not market data.",
            )

        calculator(
            P + "cv_",
            [
                Num("gc", "GC fee (bps)", 30.0, 1.0, 500.0, 5.0, "%.0f"),
                Num("k", "Steepness", 2.0, 0.1, 10.0, 0.1),
                Num("u", "Utilisation (%)", 80.0, 1.0, 99.0, 1.0, "%.0f"),
            ],
            comp2,
            ["Move utilisation from 80% to 95%.", "Double the steepness."],
        )
    with t3:

        def comp3(v):
            sc = sbl.short_cost_drag(
                v["sh"], v["px"], v["fee"] / 1e4, int(v["days"]), 360, v["dps"]
            )
            lv = v["sh"] * v["px"]
            return Out(
                metrics=[
                    ("Borrow fee", f"{sc.fee:,.0f}", None),
                    ("Manufactured dividends", f"{sc.dividends:,.0f}", None),
                    ("Total carry drag", f"{sc.total:,.0f}", f"{sc.total / lv:.2%} of the loan"),
                ],
                figures=[
                    charts.bars(
                        ["Fee", "Dividends"],
                        [sc.fee, sc.dividends],
                        "Short carry drag",
                        "Currency units",
                    )
                ],
            )

        calculator(
            P + "sc_",
            [
                Num("sh", "Shares short", 100_000.0, 1.0, None, 10_000.0, "%.0f"),
                Num("px", "Price", 50.0, 0.01, None, 1.0),
                Num("fee", "Fee (bps)", 300.0, 0.0, 10_000.0, 10.0, "%.0f"),
                Num("days", "Days (ACT/360)", 90.0, 1.0, 360.0, 1.0, "%.0f"),
                Num("dps", "Dividends per share", 1.0, 0.0, None, 0.1),
            ],
            comp3,
            ["Add a dividend: carry can double.", "Shorten the horizon to 10 days."],
        )


render_module("loan_economics", sandbox)

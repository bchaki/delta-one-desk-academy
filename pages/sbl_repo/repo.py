"""Repo & Equity Financing."""

from __future__ import annotations

import streamlit as st

from core import config
from core.financing import repo as rp
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Choice, Num, Out, calculator
from ui.state import get_settings

P = "rp_"


def sandbox() -> None:
    s = get_settings()
    t1, t2 = st.tabs(["Repo calculator", "Funding comparison"])
    with t1:
        qual = list(config.desk().repo.haircut_by_quality)

        def comp(v):
            hc = rp.default_haircut(v["q"]) if v["use"] else v["hc"] / 100
            cash = rp.repo_cash(v["mv"], hc)
            gc = rp.gc_rate(v["bm"] / 100)
            sp = rp.special_rate(v["bm"] / 100, v["fee"])
            rate = sp if v["fee"] > 0 else gc
            interest = rp.repo_interest(cash, rate, int(v["days"]), 360)
            call = rp.repo_margin_call(v["mv"] * (1 + v["move"] / 100), cash, hc)
            return Out(
                metrics=[
                    ("Haircut", f"{hc:.0%}", None),
                    ("Cash lent", f"{cash:,.0f}", None),
                    ("GC / special rate", f"{gc:.2%} / {sp:.2%}", None),
                    ("Interest (ACT/360)", f"{interest:,.0f}", f"at {rate:.2%}"),
                    ("Margin call after move", f"{call:,.0f}", "negative = excess returned"),
                ],
            )

        calculator(
            P + "rc_",
            [
                Num("mv", "Collateral market value", 10_000_000.0, 1.0, None, 1_000_000.0, "%.0f"),
                Choice("q", "Collateral quality", qual, 1),
                Num("bm", "Benchmark (%)", 4.0, -1.0, 20.0, 0.05),
                Num("fee", "Borrow fee if special (bps)", 0.0, 0.0, 5000.0, 25.0, "%.0f"),
                Num("days", "Days", 7.0, 1.0, 360.0, 1.0, "%.0f"),
                Num("move", "Collateral price move (%)", -5.0, -50.0, 50.0, 1.0, "%.1f"),
                Num("hc", "Manual haircut (%)", 8.0, 0.0, 90.0, 1.0, "%.1f", advanced=True),
                Choice("use", "Use table haircut", [True, False], advanced=True),
            ],
            comp,
            [
                "Set a 300 bps fee: the repo rate drops below GC.",
                "Choose small_cap and see the haircut and cash change.",
            ],
            advanced=s.advanced,
        )
        c.illustrative_note(config.desk())
    with t2:

        def comp2(v):
            r = rp.funding_cost_comparison(
                v["n"],
                v["bm"] / 100,
                int(v["days"]),
                360,
                v["ftp"],
                v["hc"] / 100,
                v["rs"],
                v["ss"],
            )
            best = min(r, key=r.get)
            return Out(
                metrics=[
                    (k.title(), f"{val:,.0f}", "cheapest" if k == best else None)
                    for k, val in r.items()
                ],
                figures=[
                    charts.bars(
                        list(r),
                        list(r.values()),
                        "Cost of funding the book three ways",
                        "Currency units",
                    )
                ],
            )

        calculator(
            P + "fc_",
            [
                Num("n", "Notional", 100_000_000.0, 1.0, None, 10_000_000.0, "%.0f"),
                Num("bm", "Benchmark (%)", 4.0, 0.0, 20.0, 0.05),
                Num("days", "Days", 30.0, 1.0, 360.0, 1.0, "%.0f"),
                Num("ftp", "FTP spread (bps)", 50.0, 0.0, 500.0, 5.0, "%.0f"),
                Num("hc", "Haircut (%)", 8.0, 0.0, 90.0, 1.0, "%.1f"),
                Num("rs", "Repo spread (bps)", 15.0, -200.0, 500.0, 5.0, "%.0f"),
                Num("ss", "Swap spread (bps)", 35.0, 0.0, 500.0, 5.0, "%.0f"),
            ],
            comp2,
            [
                "Raise the haircut to 40%: repo loses its edge.",
                "Cut the swap spread below the repo spread.",
            ],
        )
    c.reset_button(P)


render_module("repo", sandbox)

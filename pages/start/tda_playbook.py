"""The TDA Playbook."""

from __future__ import annotations

import streamlit as st

from ui import components as c
from ui.module_page import render_module

P = "tp_"

# (London hour, task)
DAY = [
    (7, "Overnight news, ex-dividends and corporate actions for the day"),
    (7.5, "Load positions and prices; clear yesterday's open breaks"),
    (8, "Europe open: book trades, monitor limits, prepare resets due"),
    (11, "Margin calls to clients due; send and diary follow-up"),
    (13, "Mid-day PnL check; flag unexplained moves"),
    (14.5, "US open: repeat the loop for US names"),
    (16.5, "Europe close: validate marks and fixings"),
    (18, "Run PnL explain; chase breaks until explained or escalated"),
    (20, "Send reports; update handover checklist"),
]

CHECKLISTS = {
    "Start of day": [
        "Positions loaded and compared with last night's close",
        "Prices and FX loaded; stale prices flagged",
        "Ex-dividends and corporate actions for today listed",
        "Resets and margin calls due today listed",
        "Open breaks from yesterday reviewed",
    ],
    "Reset day": [
        "Fixings compared with the confirmation, equal",
        "Reset price source checked and not stale",
        "Notional, shares and spread agree with the booked terms",
        "Dividends in the period agree with the schedule and pass-through",
        "Cash flows released and client statement sent",
    ],
    "Dividend day": [
        "Gross dividend agrees with the issuer announcement",
        "Pass-through and withholding applied per trade terms",
        "Hedge dividend received or accrued and reconciled",
        "Special dividends and currency options identified",
    ],
    "Month end": [
        "All trades booked and confirmed",
        "Marks agreed with product control",
        "Accruals for funding, borrow and fees checked",
        "Unexplained PnL explained or escalated",
        "Reconciliations signed off",
    ],
    "Handover": [
        "Open items listed with owner and deadline",
        "Unusual trades, clients or markets noted",
        "Pending margin calls and settlements noted",
        "Contacts for each open item recorded",
    ],
}

PLAN = {
    "First 30 days: learn the book": [
        "Shadow the full daily process",
        "Learn every system and cut-off",
        "Book simple trades under review",
        "Start a personal glossary",
    ],
    "Days 31 to 60: own a process": [
        "Run the start of day independently",
        "Start the break log",
        "Explain PnL for one sub-book",
    ],
    "Days 61 to 90: improve and extend": [
        "Automate one recurring check",
        "Present a PnL explain to the trader",
        "Cover a colleague on holiday",
    ],
}


def _fmt(h: float) -> str:
    return f"{int(h):02d}:{int(round((h % 1) * 60)):02d}"


def sandbox() -> None:
    t1, t2, t3 = st.tabs(["A day in the life", "Checklists", "30/60/90 plan"])
    with t1:
        region = st.radio("Time zone", ["London", "New York"], horizontal=True, key=P + "tz")
        shift = 0.0 if region == "London" else -5.0
        for h, task in DAY:
            st.markdown(f"**{_fmt((h + shift) % 24)}** {task}")
        st.caption(
            "New York view is London minus five hours; daylight saving shifts differ for a few weeks a year."
        )
    with t2:
        name = st.selectbox("Checklist", list(CHECKLISTS), key=P + "cl")
        items = CHECKLISTS[name]
        done = sum(st.checkbox(it, key=f"{P}cl_{name}_{i}") for i, it in enumerate(items))
        st.progress(done / len(items), text=f"{done} of {len(items)} complete")
    with t3:
        total = done_all = 0
        for stage, items in PLAN.items():
            st.markdown(f"**{stage}**")
            for i, it in enumerate(items):
                total += 1
                done_all += st.checkbox(it, key=f"{P}plan_{stage}_{i}")
        st.progress(done_all / total, text=f"Plan: {done_all} of {total} complete")
    c.what_to_try(
        [
            "Switch to New York time and see when the first task lands.",
            "Tick through the reset-day checklist.",
        ]
    )
    c.reset_button(P)


render_module("tda_playbook", sandbox)

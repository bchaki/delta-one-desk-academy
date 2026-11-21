"""Trade Booking & Lifecycle: the ticket validator, event replay and cash flows."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.booking import lifecycle as lc
from core.booking.cashflows import swap_cashflows
from core.booking.validation import parse_swap_ticket
from core.types import Benchmark, Currency, Direction
from ui import components as c
from ui.module_page import render_module
from ui.state import get_settings, get_world

P = "bl_"


def ticket() -> None:
    w = get_world()
    book = w.book
    base = book.swaps()[0]
    cids = list(book.clients)
    st.markdown(
        "Fill in a swap ticket and run the validator. Defaults come from a synthetic trade; change fields to provoke errors."
    )
    a, b, d = st.columns(3)
    cid = a.selectbox(
        "Counterparty",
        cids,
        index=cids.index(base.counterparty_id),
        format_func=lambda x: f"{x} {book.clients[x].name}",
        key=P + "cid",
    )
    cl = book.clients[cid]
    entity = b.text_input("Legal entity", cl.legal_entity, key=P + "ent")
    isda = d.text_input("ISDA reference", f"ISDA-{cid}-2024", key=P + "isda")
    und = a.text_input("Underlying", "stock:ALDG", key=P + "und", help="stock:TICKER or index:NAME")
    direction = b.selectbox("Client direction", [x.value for x in Direction], key=P + "dir")
    ccy = d.selectbox("Currency", [x.value for x in Currency], index=0, key=P + "ccy")
    bench = a.selectbox("Benchmark", [x.value for x in Benchmark], key=P + "bm")
    shares = b.number_input("Shares", 0.0, 1e8, 10_000.0, 1_000.0, key=P + "sh", format="%.0f")
    px = d.number_input("Initial price", 0.0, 1e6, 100.0, 1.0, key=P + "px")
    spread = a.number_input("Spread (bps)", -50.0, 1000.0, 40.0, 1.0, key=P + "sp")
    reset = b.selectbox("Reset (months)", [1, 2, 3, 6, 12], key=P + "rs")
    pt = d.slider("Dividend pass-through", 0.0, 1.0, 1.0, 0.05, key=P + "pt")
    td = a.date_input("Trade date", date(2026, 3, 2), key=P + "td")
    ed = b.date_input("Effective date", date(2026, 3, 2), key=P + "ed")
    flag = d.toggle("871(m) flag", key=P + "871")
    borrow = a.number_input("Borrow cost (bps, shorts)", 0.0, 3000.0, 0.0, 10.0, key=P + "bw")
    data = dict(
        trade_id="NEW1",
        trade_date=td,
        effective_date=ed,
        book="Equity Swaps",
        counterparty_id=cid,
        legal_entity=entity,
        underlying=und,
        direction=direction,
        shares=shares,
        initial_price=px,
        spread_bps=spread,
        benchmark=bench,
        reset_months=reset,
        pass_through=pt,
        flag_871m=flag,
        isda_ref=isda,
        ccy=ccy,
        borrow_bps=borrow,
    )
    trade, issues = parse_swap_ticket(data, cl)
    errs = [i for i in issues if i.severity == "error"]
    for i in issues:
        (st.error if i.severity == "error" else st.warning)(f"**{i.field}**: {i.message}")
    if trade is None or errs:
        st.info("The ticket is blocked: fix the errors to book.")
    else:
        st.success("The ticket validates." + (" Warnings need a second look." if issues else ""))
        c.trade_ticket(
            {
                "Client": cl.name,
                "Underlying": und,
                "Direction": direction,
                "Shares": f"{shares:,.0f}",
                "Spread": f"{spread:.1f} bps over {bench}",
                "Reset": f"every {reset} month(s)",
                "Pass-through": f"{pt:.0%}",
            },
            "Validated ticket",
        )
    c.what_to_try(
        [
            "Change the legal entity to something else.",
            "Use a US-dollar stock with a non-US client and untick the 871(m) flag.",
            "Set the effective date to a Sunday.",
        ]
    )


def replay() -> None:
    s = get_settings()
    w = get_world()
    book, m = w.book, w.market
    swaps = book.swaps()
    ids = [t.trade_id for t in swaps if book.events_for(t.trade_id)]
    tid = st.selectbox("Swap", ids, key=P + "tid")
    t = book.trade(tid)
    evs = sorted(book.events_for(tid), key=lambda e: e.date)
    state = lc.process_events(t, evs)
    c.metric_row(
        [
            ("Shares at trade", f"{t.shares:,.0f}", None),
            ("Shares now", f"{state.shares:,.0f}", None),
            ("Spread now", f"{state.spread_bps:.1f} bps", f"booked at {t.spread_bps:.1f}"),
            ("Status", state.status, None),
        ]
    )
    ev_df = pd.DataFrame(
        [
            {
                "date": e.date,
                "event": e.kind,
                **{
                    k: v for k, v in e.model_dump().items() if k not in ("kind", "date", "trade_id")
                },
            }
            for e in evs
        ]
    )
    st.markdown("**Lifecycle events** (client trade, replayed in date order)")
    c.blotter(ev_df, "lifecycle_events", key=P + "dl_ev", height=220)
    flows = swap_cashflows(t, m, w.as_of, evs)
    cf = pd.DataFrame([f.model_dump() for f in flows])
    if cf.empty:
        st.info("No cash flows yet.")
        return
    st.markdown("**Cash flows** (amount positive = received by the desk, trade currency)")
    show = cf if s.advanced else cf.drop(columns=["status", "payer"], errors="ignore")
    c.blotter(show.round(2), "swap_cashflows", key=P + "dl_cf", height=260)
    st.caption(
        "Each component is rounded to cents with half-even rounding before the net is formed."
    )


render_module("booking_lifecycle", ticket, extra_tabs={"Lifecycle replay": replay})

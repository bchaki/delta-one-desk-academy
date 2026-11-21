"""PnL Explain & Attribution, with a break detective."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.data.world import build_world
from core.pnl import attribution as at
from core.pnl import diagnose as dg
from core.pnl.explain import explain_series, pnl_explain
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_settings, get_world

P = "pe_"


@st.cache_data(show_spinner=False)
def _series(seed: int) -> pd.DataFrame:
    w = build_world(seed)
    return explain_series(w.booked, w.clean)


def explain_tab() -> None:
    w = get_world()
    days = [d for d in w.booked.days if d <= w.as_of]
    n = st.slider("Window (trading days ending at the as-of date)", 5, 250, 20, key=P + "win")
    end, start = days[-1], days[-n - 1]
    books = ["All books", *sorted({b for b, _ in w.booked.by_book})]
    book = st.selectbox("Book", books, key=P + "book")
    ex = pnl_explain(w.booked, w.clean, start, end, None if book == "All books" else book)
    c.metric_row(
        [
            ("Total (booked)", f"{ex.total:,.2f} USD", f"{start} to {end}"),
            ("Explained", f"{ex.explained:,.2f} USD", None),
            (
                "Unexplained",
                f"{ex.unexplained:,.2f} USD",
                "reconciles to the cent" if ex.reconciles() else "does not reconcile",
            ),
        ]
    )
    comps = {**ex.components, "unexplained": ex.unexplained}
    st.plotly_chart(
        charts.waterfall(
            comps, "PnL explain: components plus unexplained equal the total (USD)", "USD", "Total"
        ),
        use_container_width=True,
    )
    st.caption(
        "USD, positive = gain to the desk. Components come from the clean model, the total from the booked ledger; unexplained is the residual of the cents-rounded components."
    )


def attribution_tab() -> None:
    w = get_world()
    days = [d for d in w.booked.days if d <= w.as_of]
    n = st.slider("Window (trading days)", 5, 250, 60, key=P + "awin")
    end, start = days[-1], days[-n - 1]
    st.markdown("**By book and component (USD)**")
    c.blotter(at.by_book(w.booked, start, end).round(0), "pnl_by_book", key=P + "dl_book")
    cl = at.by_client(w.booked, w.book, start, end)
    st.plotly_chart(
        charts.bars(
            list(cl.index),
            list(cl.values),
            "PnL by client, swaps and their hedges (USD)",
            "USD, desk side",
        ),
        use_container_width=True,
    )
    best, worst = at.top_movers(w.booked, start, end)
    a, b = st.columns(2)
    a.markdown("**Best tickers**")
    a.dataframe(best.round(0).to_frame("USD"), use_container_width=True)
    b.markdown("**Worst tickers**")
    b.dataframe(worst.round(0).to_frame("USD"), use_container_width=True)


def detective() -> None:
    s = get_settings()
    w = get_world()
    ser = _series(w.seed)
    ser = ser[ser.index <= w.as_of]
    st.markdown(
        "Unexplained PnL by day. Large days are where to start. Size each suspect, then see which matches."
    )
    st.plotly_chart(
        charts.lines(ser[["unexplained"]], "Daily unexplained PnL (USD)", "Date", "USD"),
        use_container_width=True,
    )
    top = ser.unexplained.abs().sort_values(ascending=False).head(8)
    pick = st.selectbox(
        "Day to investigate",
        list(top.index),
        format_func=lambda d: f"{d}: {ser.unexplained[d]:,.2f} USD",
        key=P + "day",
    )
    amount = float(ser.unexplained[pick])
    st.metric("Unexplained on that day", f"{amount:,.2f} USD")
    st.markdown(
        "**Size the suspects** (change the inputs to match what you can see in the trade or market data)"
    )
    a, b, d = st.columns(3)
    shares = a.number_input(
        "Shares affected", 0.0, 1e8, 50_000.0, 1_000.0, key=P + "sh", format="%.0f"
    )
    div = b.number_input("Dividend per share", 0.0, 100.0, 1.20, 0.05, key=P + "dv")
    stale = d.number_input(
        "Stale mark minus right mark (price)", -50.0, 50.0, -0.22, 0.01, key=P + "st"
    )
    notional = a.number_input("Swap notional", 0.0, 1e10, 25e6, 1e6, key=P + "no", format="%.0f")
    bps = b.number_input(
        "Spread error (booked minus correct, bps)", -200.0, 200.0, -10.0, 1.0, key=P + "bp"
    )
    days = d.number_input("Days", 1.0, 360.0, 30.0, 1.0, key=P + "dy")
    cands = {
        "missed_dividend": dg.missed_dividend_impact(shares, div),
        "stale_price": dg.stale_mark_impact(shares, stale, 0.0),
        "wrong_spread": dg.spread_error_impact(notional, bps, 0.0, int(days)),
    }
    tol = st.slider("Match tolerance (USD)", 1.0, 5000.0, 500.0, 1.0, key=P + "tol")
    st.dataframe(
        pd.Series(cands).round(2).to_frame("Expected impact (USD)"), use_container_width=True
    )
    hit = dg.classify(amount, cands, tol)
    if hit:
        st.success(
            f"The unexplained amount is within {tol:,.0f} of **{hit}**. Confirm in the trade or market data before fixing."
        )
    else:
        st.info(
            "No suspect matches yet. Check the timing: a break that reverses next day, a steady drift and a one-day jump point to different causes."
        )
    if st.toggle("Reveal the seeded breaks", key=P + "reveal"):
        rows = [
            {
                "kind": bk.kind,
                "date": bk.date,
                "trade": bk.trade_id,
                "ticker": bk.ticker,
                "impact_usd": round(bk.pnl_impact, 2),
                "clue": bk.clue,
            }
            for bk in w.book.breaks
        ]
        c.blotter(pd.DataFrame(rows), "seeded_breaks", key=P + "dl_br")
    if s.advanced:
        c.blotter(ser.round(2), "daily_explain", key=P + "dl_ser")
    c.what_to_try(
        [
            "Pick the largest day and match it with the right suspect.",
            "Reveal the breaks to check your answer.",
        ]
    )


render_module(
    "pnl_explain",
    explain_tab,
    extra_tabs={"Attribution": attribution_tab, "Break detective": detective},
)

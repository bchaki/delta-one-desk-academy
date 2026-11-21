"""Equity Swaps, TRS & CFDs: the centrepiece sandbox is the swap lifecycle simulator."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.booking.cashflows import terms_of  # noqa: F401  (documented link to the booking engine)
from core.booking.lifecycle import reset_dates
from core.conventions import CalendarName
from core.data.accessors import underlying_ccy, underlying_dividends, underlying_price
from core.data.market import BASIS_BY_BENCH, BENCH_BY_CCY, CAL_BY_BENCH
from core.dividends import withholding_rate_pct
from core.pricing import swaps as sw
from core.types import Direction
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_settings, get_world

P = "es_"


def simulator() -> None:
    s = get_settings()
    w = get_world()
    m = w.market
    u = m.universe
    names = [
        t for t, st_ in u.stocks.items() if t not in u.ca_plan.involved and st_.listed_from is None
    ]
    c1, c2, c3 = st.columns(3)
    und = c1.selectbox(
        "Underlying",
        [f"stock:{t}" for t in names] + [f"index:{n}" for n in u.indices],
        key=P + "und",
        index=names.index("HLVN") if "HLVN" in names else 0,
    )
    direction = Direction(c2.selectbox("Client direction", ["LONG", "SHORT"], key=P + "dir"))
    notional_usd = c3.number_input(
        "Notional (USD)",
        value=10_000_000.0,
        step=1_000_000.0,
        min_value=100_000.0,
        key=P + "notional",
        format="%.0f",
    )
    c4, c5, c6 = st.columns(3)
    spread = c4.number_input(
        "Spread (bps)",
        value=40.0,
        step=1.0,
        key=P + "spread",
        help="Over the benchmark. Short: the client receives benchmark minus this spread.",
    )
    months = c5.selectbox("Reset frequency (months)", [1, 3, 6], key=P + "freq")
    pt = c6.slider("Dividend pass-through (%)", 50, 100, 100, 5, key=P + "pt") / 100
    reset_flag = st.toggle("Notional resets to the current value", value=True, key=P + "nreset")
    days = [d for d in m.days if d <= w.as_of]
    if len(days) < 30:
        st.warning("Choose a later as-of date.")
        return
    cand = days[:-10]
    start = st.select_slider(
        "Trade date", options=cand, value=cand[max(len(cand) - 130, 0)], key=P + "start"
    )
    wht = (
        st.number_input(
            "Withholding on the desk's hedge dividends (%)",
            value=0.0,
            min_value=0.0,
            max_value=40.0,
            key=P + "wht",
            help=f"Statutory rates by market are on the Dividends page. e.g. US {withholding_rate_pct('US'):.0f}%.",
        )
        if s.advanced
        else 0.0
    )

    kind, _, name = und.partition(":")
    ccy = underlying_ccy(m, und)
    bench = BENCH_BY_CCY[ccy]
    cal: CalendarName = CAL_BY_BENCH[bench]
    px0 = underlying_price(m, und, start)
    fx0 = m.fx_usd_per(ccy, start)
    shares = max(round(notional_usd / (px0 * fx0)), 1)
    terms = sw.SwapTerms(
        direction, float(shares), px0, spread, BASIS_BY_BENCH[bench], pt, reset_flag, cal
    )
    fixings = m.fixings_dict(bench)
    divs = underlying_dividends(m, und)
    ftp = sw.ftp_component_bps(ccy)
    borrow = (
        float(m.borrow_fee_bps.at[pd.Timestamp(start), name])
        if kind == "stock" and direction is Direction.SHORT
        else 0.0
    )
    dates = [start, *reset_dates(start, w.as_of, months)]
    prices = {d: underlying_price(m, und, d) for d in dates}
    if len(dates) >= 2:
        sched = sw.build_schedule(terms, dates, prices, fixings, divs)
        rows = sched.to_records()
    else:
        rows = []
    last = dates[-1]
    price_now = underlying_price(m, und, w.as_of)
    terms.initial_price if last == start else prices[last]
    mtm = sw.mark_to_market(terms, dates, w.as_of, price_now, prices, fixings, divs)
    # desk economics per period (swap + hedge)
    pieces = []
    bounds = list(zip(dates[:-1], dates[1:], strict=True)) + (
        [(last, w.as_of)] if last < w.as_of else []
    )
    for a, b in bounds:
        p0 = terms.initial_price if a == start else prices[a]
        p1 = prices.get(b, price_now)
        e = sw.desk_economics(terms, a, b, p0, p1, fixings, divs, ftp, borrow, wht)
        pieces.append((a, b, e))

    def total(f):
        return sum(f(e) for _, _, e in pieces)

    comp = {
        "Swap: equity leg": total(lambda e: -e.client.price_cf),
        "Swap: dividends": total(lambda e: -e.client.dividend_cf),
        "Swap: funding": total(lambda e: -e.client.funding_cf),
        "Hedge: stock": total(lambda e: e.hedge.stock),
        "Hedge: dividends": total(lambda e: e.hedge.dividends),
        "Hedge: financing": total(lambda e: e.hedge.financing),
    }
    desk_total = sum(comp.values())
    client_settled = sum(r["net_cf"] for r in rows)
    sym = ccy.value
    c.metric_row(
        [
            ("Shares", f"{shares:,.0f}", f"{terms.initial_notional:,.0f} {sym} notional"),
            ("Client: settled cash", f"{client_settled:+,.0f} {sym}", None),
            ("Client: accrued MTM since last reset", f"{mtm:+,.0f} {sym}", None),
            (
                "Desk PnL, swap + hedge",
                f"{desk_total:+,.0f} {sym}",
                f"{total(lambda e: e.spread_edge):+,.0f} spread edge",
            ),
        ]
    )
    st.caption(
        f"Benchmark {bench.value} ({BASIS_BY_BENCH[bench]}-day basis), FTP {ftp:.0f} bps"
        + (f", borrow fee {borrow:.0f} bps at trade date" if borrow else "")
        + f". Client perspective: positive = client receives. Desk perspective: positive = gain to the desk. Amounts in {sym}."
    )
    st.plotly_chart(
        charts.waterfall(
            comp,
            "Desk PnL by source: the equity move cancels between swap and hedge",
            sym,
            "Desk PnL",
        ),
        use_container_width=True,
    )
    if rows:
        df = pd.DataFrame(rows).set_index("end").drop(columns=["start"])
        cum = pd.DataFrame(
            {
                "Client cumulative net cash": df.net_cf.cumsum(),
                "Desk cumulative (swap + hedge)": pd.Series(
                    {b: sum(e.total for aa, bb, e in pieces if bb <= b) for _, b, e in pieces}
                ),
            }
        )
        st.plotly_chart(
            charts.lines(
                cum,
                "Client PnL and desk PnL along the synthetic price path",
                "Reset date",
                f"Cumulative ({sym})",
            ),
            use_container_width=True,
        )
        st.markdown("**Cash-flow schedule (client perspective)**")
        c.blotter(df.round(2), "swap_schedule", key=P + "dl_sched")
    else:
        st.info(
            "No reset has occurred yet: only accruals. Choose an earlier trade date or a shorter reset frequency."
        )
    if s.advanced:
        st.caption(
            "Spread edge = funding notional x (spread - FTP or borrow) x period. Differences from desk PnL come from dividend pass-through below 100%, withholding, fixed notional and cent rounding."
        )
    c.what_to_try(
        [
            "Set pass-through to 70% on a high-yield stock and watch 'Swap: dividends' versus 'Hedge: dividends'.",
            "Choose SHORT on a hard-to-borrow name: the borrow fee at the trade date can exceed the spread.",
            "Turn off notional reset and compare 'Swap: funding' with 'Hedge: financing'.",
        ]
    )
    c.reset_button(P)


def lifecycle() -> None:
    dot = """digraph G { rankdir=LR; node [shape=box, style=rounded];
    Trade -> Reset -> Dividend -> "Corporate action" -> "Partial unwind" -> Termination;
    Reset -> Reset [label="each period"]; Dividend -> Reset; "Partial unwind" -> Reset; "Corporate action" -> Reset;}"""
    st.graphviz_chart(dot)
    info = {
        "Trade": (
            "Booking, hedge, confirmation",
            "No cash. Initial price and notional fixed; hedge bought or borrowed and sold; sales credit paid.",
            "Sales, trader, middle office",
        ),
        "Reset": (
            "Compound benchmark, fix price, settle",
            "Equity leg (price change) and funding leg (notional x (R +/- spread) x days/basis) settle; notional updates.",
            "TDA, operations",
        ),
        "Dividend": (
            "Ex-date entry",
            "Dividend equivalent x pass-through paid to long (or by short); hedge receives or pays the underlying dividend.",
            "TDA, operations, tax",
        ),
        "Corporate action": (
            "Adjust terms",
            "Quantity and price factors, any cash or new line; hedge adjusted in step.",
            "TDA, calculation agent",
        ),
        "Partial unwind": (
            "Reduce shares",
            "Realises equity PnL on the unwound shares; hedge sold the same day.",
            "Trader, middle office",
        ),
        "Termination": (
            "Final settlement",
            "Final period settles at the termination price; hedge closed; accruals paid.",
            "Trader, operations",
        ),
    }
    st_sel = st.selectbox("Select a state", list(info), key=P + "state")
    booking, flows, owner = info[st_sel]
    c.term_sheet({"Booking event": booking, "Cash flows": flows, "Owner": owner}, st_sel)


render_module("equity_swaps", simulator, extra_tabs={"Lifecycle": lifecycle})

"""Strategy: index rebalance and event trading."""

from __future__ import annotations

import streamlit as st

from core import config, indices
from core.strategies import index_events as ie
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "sre_"


def sandbox() -> None:
    w = get_world()
    m = w.market
    st.markdown(
        "**Thesis.** Index funds must buy additions and sell deletions at the effective close. If you can forecast the change and the size of the demand, you can pre-position, or you can guarantee the closing price to the funds and hedge during the day."
    )
    legs_diagram(
        [
            ("Index funds", "guarantee closing price (MOC)", "in"),
            ("Market", "hedge through the day / pre-position", "out"),
        ]
    )
    c.formula_box(
        r"\text{demand (shares)} = \frac{AUM\times w}{P},\qquad \text{impact} = k\,\sigma\sqrt{\tfrac{q}{ADV}}",
        {
            "AUM": "assets tracking the index",
            "w": "weight of the new member",
            "q": "shares",
            "ADV": "average daily volume",
        },
    )
    index = st.selectbox("Index", ["D1 US 30", "D1 Europe 20"], key=P + "ix")
    ch = ie.membership_changes(m, index)
    es = ie.event_study(
        m, index, st.slider("Pre-position this many days ahead", 1, 15, 5, key=P + "lead"), 5
    )
    if es.empty:
        st.info("No membership change with enough price history around it in this index.")
    else:
        st.markdown("**Event study on the synthetic membership history**")
        c.blotter(
            es.apply(lambda s: s.round(1) if s.dtype.kind == "f" else s),
            "index_events",
            key=P + "dl",
            height=160,
        )
        adds = es[es.kind == "add"].pre_bps
        c.metric_row(
            [
                ("Events", f"{len(es)}", f"{len(ch)} membership changes"),
                (
                    "Average pre-event move, adds",
                    f"{adds.mean():+.0f} bps" if len(adds) else "n/a",
                    None,
                ),
                (
                    "Average move after the effective date",
                    f"{es.post_bps.mean():+.0f} bps",
                    "reversal if negative for adds",
                ),
            ]
        )
    st.markdown("**Inclusion demand and facilitation**")
    a, b, cc = st.columns(3)
    names = [t for t in m.universe.stocks if m.universe.stocks[t].listed_from is None]
    tk = a.selectbox("Candidate stock", names, key=P + "tk")
    aum = b.number_input(
        "AUM tracking the index (USD)", 1e8, 1e13, 5e10, 1e9, key=P + "aum", format="%.0f"
    )
    wgt = cc.slider("Weight in the index (%)", 0.1, 10.0, 1.5, 0.1, key=P + "w") / 100
    pre = a.slider("Pre-positioning move (bps)", 0, 300, 80, key=P + "pm")
    crowd = b.slider("Crowding multiplier on exit impact", 1.0, 6.0, 1.0, 0.5, key=P + "cr")
    fee = cc.slider("Facilitation fee (bps)", 0.0, 20.0, 6.0, 0.5, key=P + "fee")
    st_ = m.universe.stocks[tk]
    px = m.price(tk, w.as_of)
    adv = m.stock_adv(tk, w.as_of)
    k = float(config.desk().trading_costs.impact_k)
    dem = indices.inclusion_demand(aum, wgt, px, adv, k, st_.daily_vol)
    notional = min(dem.notional * 0.05, 50e6)
    entry_impact = dem.impact_bps * 0.25
    exit_impact = ie.crowded_unwind_bps(notional / px, adv, st_.daily_vol, k, crowd)
    pre_pnl = ie.preposition_pnl(notional, pre, entry_impact, 2.0) - notional * exit_impact / 1e4
    moc = ie.moc_facilitation_pnl(
        dem.shares * 0.1,
        px,
        fee,
        st.slider("Hedge slippage versus the close (bps)", 0.0, 20.0, 3.0, 0.5, key=P + "sl"),
    )
    c.metric_row(
        [
            (
                "Index fund demand",
                f"{dem.shares:,.0f} shares",
                f"{dem.days_of_adv:.1f} days of ADV",
            ),
            ("Expected impact", f"{dem.impact_bps:.0f} bps", f"{st_.ccy.value} price {px:,.2f}"),
            ("Pre-position PnL (5% of demand)", f"{pre_pnl:,.0f}", f"notional {notional:,.0f}"),
            ("Facilitation PnL (10% of demand)", f"{moc:,.0f}", None),
        ]
    )
    decomposition(
        {
            "Pre-positioning move": notional * pre / 1e4,
            "Entry impact and costs": -(entry_impact + 2.0) * notional / 1e4,
            "Exit impact (crowding)": -exit_impact * notional / 1e4,
        },
        "Pre-position PnL decomposition (price currency)",
        "Currency units",
    )
    st.plotly_chart(
        charts.bars(
            ["Pre-position", "Facilitation"],
            [pre_pnl, moc],
            "Two ways to trade the same event",
            "Currency units",
        ),
        use_container_width=True,
    )
    st.caption(
        "Synthetic data and a stylised demand model: inclusion demand = AUM x weight / price; square-root impact with the desk's illustrative k. The 5% and 10% shares of demand are assumptions of this page."
    )

    def crowded() -> dict[str, str]:
        e6 = ie.crowded_unwind_bps(notional / px, adv, st_.daily_vol, k, 6.0)
        return {
            "Exit impact as set": f"{exit_impact:.0f} bps",
            "Exit impact if six times as crowded": f"{e6:.0f} bps",
            "PnL": f"{ie.preposition_pnl(notional, pre, entry_impact, 2.0) - notional * e6 / 1e4:,.0f}",
        }

    def no_move() -> dict[str, str]:
        return {
            "Pre-position PnL if the stock does not move": f"{ie.preposition_pnl(notional, 0, entry_impact, 2.0) - notional * exit_impact / 1e4:,.0f}",
            "Lesson": "Costs are certain; the move is not.",
        }

    def wrong() -> dict[str, str]:
        return {
            "Loss if the forecast add is not announced and the stock falls 100 bps": f"{ie.preposition_pnl(notional, -100, entry_impact, 2.0) - notional * exit_impact / 1e4:,.0f}",
            "Lesson": "Forecasting adds is a guess until the announcement.",
        }

    risk_buttons(
        P,
        [
            Risk("Crowded exit", "Many hold the same pre-position.", crowded),
            Risk("No move", "The pre-positioning gain does not arrive.", no_move),
            Risk("Wrong forecast", "The stock is not added.", wrong),
        ],
    )
    c.reset_button(P)


render_module("s_rebalance", sandbox)

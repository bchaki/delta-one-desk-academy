"""Strategy: ETF arbitrage and create/redeem."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.strategies import etf_arb as ea
from core.strategies import meanrev as mr
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "sea_"


def sandbox() -> None:
    w = get_world()
    m = w.market
    st.markdown(
        "**Thesis.** An ETF can be created or redeemed against its basket, so its price cannot stray far from NAV. When the premium or discount exceeds the cost of the round trip, the arbitrageur sells the rich side and buys the cheap one and delivers or redeems through the authorised participant."
    )
    legs_diagram(
        [
            ("Exchange", "sell ETF if rich / buy if cheap", "out"),
            ("Cash market", "buy basket / sell basket", "out"),
            ("Authorised participant", "create or redeem units, creation fee", "out"),
        ]
    )
    c.formula_box(
        r"\text{threshold} = \frac{fee}{CU\ value} + c_{basket} + c_{ETF}",
        {"fee": "creation fee per unit", "c": "costs in bps"},
    )
    a, b, cc = st.columns(3)
    tk = a.selectbox("ETF", list(m.universe.etfs), key=P + "t")
    edge = b.slider("Extra edge demanded over break-even (bps)", 0, 30, 3, key=P + "e")
    basket = cc.slider("Basket execution cost (bps)", 0.0, 20.0, 5.0, 0.5, key=P + "bc")
    hs = a.slider("ETF half-spread (bps)", 0.0, 10.0, 2.0, 0.5, key=P + "hs")
    stress = b.slider("Stress multiplier on market costs", 1.0, 5.0, 1.0, 0.5, key=P + "st")
    notional = cc.number_input(
        "Notional per trade (USD)", 1e5, 1e9, 1e6, 1e5, key=P + "n", format="%.0f"
    )
    e = m.universe.etfs[tk]
    nav0 = float(m.index_tr[e.index].iloc[-1] * e.scale)
    thr = ea.threshold_bps(e.creation_fee, nav0 * e.cu_size, basket, hs, stress)
    t = ea.backtest(m, tk, edge, basket, hs, stress, notional)
    prem = ea.premium_series_bps(m, tk)
    tot = float(t.pnl.sum()) if len(t) else 0.0
    c.metric_row(
        [
            (
                "Break-even premium",
                f"{thr:.1f} bps",
                f"creation fee {e.creation_fee:,.0f} per unit of {e.cu_size:,}",
            ),
            ("Trades", f"{len(t)}", None),
            ("Net PnL", f"{tot:,.0f}", f"hit rate {(t.pnl > 0).mean() if len(t) else 0:.0%}"),
        ]
    )
    band = pd.DataFrame(
        {"Premium (bps)": prem, "+ threshold": thr + edge, "- threshold": -(thr + edge)}
    )
    st.plotly_chart(
        charts.lines(band, f"{tk}: premium to NAV and the trading threshold", "Date", "bps of NAV"),
        use_container_width=True,
    )
    decomposition(
        {
            "Gross convergence": float((t.pnl_signal + thr).sum() * notional / 1e4)
            if len(t)
            else 0.0,
            "Round-trip costs (fee, basket, ETF)": -thr * len(t) * notional / 1e4,
        },
        "PnL decomposition",
        "USD",
    )
    sw = mr.sweep_entry(prem, [thr + x for x in (0, 5, 10, 20, 40)], thr / 2, thr, notional)
    st.plotly_chart(
        charts.bars(
            [f"+{x:g}" for x in (0, 5, 10, 20, 40)],
            list(sw.total_pnl),
            "Net PnL against the edge demanded (bps over break-even)",
            "USD",
        ),
        use_container_width=True,
    )
    st.caption(
        f"Synthetic data. NAV = index total return x scale {e.scale:g}. Closing prices, no intraday iNAV drift."
    )

    def stressed() -> dict[str, str]:
        t2 = ea.backtest(m, tk, edge, basket, hs, 4.0, notional)
        return {
            "Break-even at 1x costs": f"{ea.threshold_bps(e.creation_fee, nav0 * e.cu_size, basket, hs, 1.0):.1f} bps",
            "Break-even at 4x costs": f"{ea.threshold_bps(e.creation_fee, nav0 * e.cu_size, basket, hs, 4.0):.1f} bps",
            "Trades at 4x": f"{len(t2)}",
        }

    def fee_up() -> dict[str, str]:
        return {
            "Break-even if the creation fee doubles": f"{ea.threshold_bps(2 * e.creation_fee, nav0 * e.cu_size, basket, hs, stress):.1f} bps",
            "Lesson": "Fees matter more for small units.",
        }

    def nav_stale() -> dict[str, str]:
        return {
            "Largest premium in history": f"{prem.abs().max():.1f} bps",
            "Meaning": "Part of a large premium can be a stale or mis-marked NAV, not an opportunity; check the basket prices first.",
        }

    risk_buttons(
        P,
        [
            Risk("Liquidity stress", "Underlying spreads widen four times.", stressed),
            Risk("Creation fee doubles", "Unit economics worsen.", fee_up),
            Risk("Stale NAV", "Apparent mispricing is a data problem.", nav_stale),
        ],
    )
    c.reset_button(P)


render_module("s_etf_arb", sandbox)

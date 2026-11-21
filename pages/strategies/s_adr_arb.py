"""Strategy: ADR and cross-listing arbitrage."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.strategies import adr_arb as aa
from core.strategies import meanrev as mr
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "saa_"


def sandbox() -> None:
    w = get_world()
    m = w.market
    st.markdown(
        "**Thesis.** An ADR is a claim on local shares at a fixed ratio, so ADR = local price x ratio x FX. If it strays by more than the conversion fee and trading costs, sell the rich side, buy the cheap one and convert through the depositary."
    )
    legs_diagram(
        [
            ("US market", "sell ADR if rich / buy if cheap", "out"),
            ("Local market", "buy local shares / sell local shares", "out"),
            ("FX market", "convert proceeds", "out"),
            ("Depositary", "issue or cancel, conversion fee", "out"),
        ]
    )
    c.formula_box(
        r"FV = P_{local}\times ratio\times FX,\qquad band = \frac{fee}{FV} + c",
        {
            "ratio": "local shares per ADR",
            "FX": "USD per unit of local currency",
            "c": "trading and FX costs, bps",
        },
    )
    a, b, cc = st.columns(3)
    tk = a.selectbox("ADR", list(m.universe.adrs), key=P + "t")
    cost = b.slider("Trading and FX cost (bps of fair value)", 0.0, 40.0, 10.0, 1.0, key=P + "c")
    edge = cc.slider("Extra edge demanded (bps)", 0.0, 30.0, 2.0, 1.0, key=P + "e")
    notional = a.number_input(
        "Notional per trade (USD)", 1e5, 1e9, 1e6, 1e5, key=P + "n", format="%.0f"
    )
    adr = m.universe.adrs[tk]
    fair = float(m.adr_prices[tk].iloc[-1])
    band = aa.band_bps(adr.depositary_fee, fair, cost)
    dev = aa.deviation_series_bps(m, tk)
    t = aa.backtest(m, tk, cost, edge, notional)
    tot = float(t.pnl.sum()) if len(t) else 0.0
    c.metric_row(
        [
            ("Band half-width", f"{band:.1f} bps", f"fee {adr.depositary_fee:.3f} USD per ADR"),
            ("Trades", f"{len(t)}", None),
            ("Net PnL", f"{tot:,.0f}", f"hit rate {(t.pnl > 0).mean() if len(t) else 0:.0%}"),
        ]
    )
    df = pd.DataFrame(
        {"Deviation from parity (bps)": dev, "+ band": band + edge, "- band": -(band + edge)}
    )
    st.plotly_chart(
        charts.lines(df, f"{tk}: ADR against parity", "Date", "bps of fair value"),
        use_container_width=True,
    )
    decomposition(
        {
            "Gross convergence": float((t.pnl_signal + band).sum() * notional / 1e4)
            if len(t)
            else 0.0,
            "Round-trip band (fee and costs)": -band * len(t) * notional / 1e4,
        },
        "PnL decomposition",
        "USD",
    )
    sw = mr.sweep_entry(dev, [band + x for x in (0, 3, 6, 12, 24)], band / 2, band, notional)
    st.plotly_chart(
        charts.bars(
            [f"+{x}" for x in (0, 3, 6, 12, 24)],
            list(sw.total_pnl),
            "Net PnL against the edge demanded",
            "USD",
        ),
        use_container_width=True,
    )
    st.caption(
        "Synthetic data. Closing prices on both legs, no settlement mismatch, no borrow on the local leg and no conversion cut-off. Parity uses the synthetic FX closes."
    )

    def fx_jump() -> dict[str, str]:
        loss = notional * 0.005
        return {
            "Loss from a 50 bps FX move between the legs on one trade": f"{-loss:,.0f}",
            "Lesson": "Hedge FX at the same moment as the share legs.",
        }

    def fee_up() -> dict[str, str]:
        b2 = aa.band_bps(adr.depositary_fee * 3, fair, cost)
        return {
            "Band now": f"{band:.1f} bps",
            "Band if the conversion fee triples": f"{b2:.1f} bps",
        }

    def closed() -> dict[str, str]:
        return {
            "Largest deviation in history": f"{dev.abs().max():.0f} bps",
            "Lesson": "Large gaps often coincide with a closed local market or a halt; you cannot hedge what you cannot trade.",
        }

    risk_buttons(
        P,
        [
            Risk("FX gap", "FX moves between the legs.", fx_jump),
            Risk("Conversion fee triples", "Depositary changes its fee.", fee_up),
            Risk("Local market closed", "One leg cannot trade.", closed),
        ],
    )
    c.reset_button(P)


render_module("s_adr_arb", sandbox)

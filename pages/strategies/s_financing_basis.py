"""Strategy: financing and basis trades."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.strategies import basis as bs
from core.strategies import common as cm
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "sfb_"


@st.cache_data(show_spinner=False)
def _implied(index: str, seed: int, as_of: str) -> pd.Series:
    dev = cm.futures_deviation_series(get_world().market, index)
    return bs.implied_financing_spread_series(dev)


def sandbox() -> None:
    w = get_world()
    st.markdown(
        "**Thesis.** A client pays benchmark plus a spread on a swap. The desk hedges and funds the hedge at its own cost. What is left is the financing carry, and it depends on which hedge is cheapest: stock on the balance sheet, or futures with margin."
    )
    legs_diagram(
        [
            ("Client", "pays benchmark + spread", "in"),
            ("Treasury", "funds stock at benchmark + FTP", "out"),
            ("Cash market", "buys hedge stock", "out"),
            ("Exchange", "alternative: futures hedge", "out"),
        ]
    )
    c.formula_box(
        r"\text{carry} = N\,(s - \mathrm{FTP} - b)\,\frac{d}{360},\qquad \text{futures hedge: } s - i - m\cdot \mathrm{FTP}",
        {
            "s": "client spread, bps over benchmark",
            "FTP": "funding transfer price spread, bps",
            "b": "balance sheet charge, bps",
            "i": "financing spread implied by the future, bps",
            "m": "initial margin as share of notional",
        },
    )
    a, b, cc = st.columns(3)
    n = a.number_input("Notional (USD)", 1e6, 1e10, 50e6, 5e6, key=P + "n", format="%.0f")
    spread = b.slider("Client spread (bps over benchmark, ACT/360)", 0, 200, 60, key=P + "s")
    ftp = cc.slider("FTP spread (bps)", 0, 150, 35, key=P + "f")
    bsc = a.slider("Balance sheet charge (bps)", 0, 60, 12, key=P + "b")
    marg = b.slider("Futures initial margin (% of notional)", 1, 15, 5, key=P + "m") / 100
    index = cc.selectbox("Index for the futures hedge", ["D1 US 30", "D1 Europe 20"], key=P + "ix")
    imp = _implied(index, w.market.seed, str(w.as_of))
    imp_now = float(imp.iloc[-1])
    pnl_stock = bs.swap_financing_pnl(n, spread, ftp, bsc, 360)
    hc = bs.hedge_choice(spread, ftp, bsc, imp_now, marg)
    pnl_fut = n * hc["futures"] / 1e4
    c.metric_row(
        [
            ("Stock hedge, net spread", f"{hc['stock']:.1f} bps", f"PnL {pnl_stock:,.0f} a year"),
            ("Futures hedge, net spread", f"{hc['futures']:.1f} bps", f"PnL {pnl_fut:,.0f} a year"),
            (
                "Implied financing in the future now",
                f"{imp_now:.1f} bps over benchmark",
                f"{index}, ACT/365 annualised",
            ),
            ("Cheaper hedge", "Futures" if hc["best_is_futures"] else "Stock", None),
        ]
    )
    decomposition(
        {
            "Client spread": n * spread / 1e4,
            "Funding (FTP)": -n * ftp / 1e4,
            "Balance sheet": -n * bsc / 1e4,
        },
        "Annual carry on the stock hedge (USD)",
        "USD",
    )
    ftps = list(range(0, 121, 10))
    st.plotly_chart(
        charts.lines(
            bs.sensitivity_table(n, spread, bsc, [float(x) for x in ftps]).rename(
                columns={"pnl": "Annual PnL"}
            ),
            "Sensitivity to the funding spread",
            "FTP spread (bps)",
            "USD a year",
        ),
        use_container_width=True,
    )
    st.plotly_chart(
        charts.lines(
            imp.rolling(5).mean().dropna().to_frame("Implied financing spread (5-day average)"),
            "Financing implied by the front future",
            "Date",
            "bps over benchmark",
        ),
        use_container_width=True,
    )
    st.caption(
        "Synthetic data. Flat rates, one balance sheet charge. The full version adds margin funding timing, tax and multi-currency funding."
    )

    def funding_up() -> dict[str, str]:
        p2 = bs.swap_financing_pnl(n, spread, ftp + 25, bsc, 360)
        return {
            "Annual PnL now": f"{pnl_stock:,.0f}",
            "With FTP +25 bps": f"{p2:,.0f}",
            "Change": f"{p2 - pnl_stock:+,.0f}",
        }

    def bs_up() -> dict[str, str]:
        p2 = bs.swap_financing_pnl(n, spread, ftp, bsc + 15, 360)
        return {
            "Annual PnL now": f"{pnl_stock:,.0f}",
            "With balance sheet +15 bps": f"{p2:,.0f}",
            "Lesson": "Quarter-end and rule changes move this line.",
        }

    def margin_up() -> dict[str, str]:
        h2 = bs.hedge_choice(spread, ftp, bsc, imp_now, marg * 2)
        return {
            "Futures net now": f"{hc['futures']:.1f} bps",
            "With margin doubled": f"{h2['futures']:.1f} bps",
            "Lesson": "Margin is funded; a volatility spike raises it.",
        }

    risk_buttons(
        P,
        [
            Risk("Funding spread +25 bps", "Treasury reprices FTP.", funding_up),
            Risk("Balance sheet +15 bps", "Capital or leverage constraint tightens.", bs_up),
            Risk("Margin doubles", "Volatility raises futures margin.", margin_up),
        ],
    )
    c.reset_button(P)


render_module("s_financing_basis", sandbox)

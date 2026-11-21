"""Strategy: index arbitrage (cash-and-carry and reverse)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.strategies import cash_carry as cc
from core.strategies import common as cm
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "sia_"
MULT = {"D1 US 30": 50.0, "D1 Europe 20": 10.0}


@st.cache_data(show_spinner=False)
def _dev(index: str, funding_spread_bps: float, seed: int, as_of: str) -> pd.DataFrame:
    return cm.futures_deviation_series(get_world().market, index, funding_spread_bps / 1e4)


def sandbox() -> None:
    w = get_world()
    st.markdown(
        "**Thesis.** When the future trades outside its no-arbitrage band, sell it and buy the basket (cash-and-carry) or buy it and short the basket (reverse). The deviation converges at expiry, and the desk keeps what is left after costs."
    )
    legs_diagram(
        [
            ("Futures exchange", "sell future if rich / buy if cheap", "out"),
            ("Cash market", "buy basket if rich / short if cheap", "out"),
            ("Funding / borrow", "financing and borrow cost", "out"),
        ]
    )
    c.formula_box(
        r"PnL = N\,M\,[\,\mathrm{sign}(d_0)\,(d_0 - d_T) - c\,]",
        {
            "d": "future minus fair value, index points",
            "N": "contracts",
            "M": "multiplier",
            "c": "costs and slippage, index points",
        },
    )
    a, b, cc_ = st.columns(3)
    index = a.selectbox("Index", list(MULT), key=P + "ix")
    entry = b.slider("Entry threshold (bps of spot)", 2, 60, 12, key=P + "en")
    exit_ = cc_.slider("Exit threshold (bps)", 0, 20, 3, key=P + "ex")
    cost = a.slider("Round-trip cost (bps of spot)", 0.0, 10.0, 2.0, 0.5, key=P + "co")
    slip = b.slider("Slippage per side (bps)", 0.0, 5.0, 0.5, 0.25, key=P + "sl")
    fs = cc_.slider("Funding spread used in fair value (bps)", 0, 40, 10, key=P + "fs")
    n = a.number_input("Contracts", 1, 1000, 10, key=P + "n")
    dev = _dev(index, float(fs), w.market.seed, str(w.as_of))
    r = cc.arb_backtest(dev, entry, exit_, cost, slip, float(n), MULT[index])
    t = r.trades
    stats = (
        cm.trade_stats(t.gross - t.costs - t.slippage)
        if len(t)
        else cm.trade_stats(pd.Series(dtype=float))
    )
    c.metric_row(
        [
            ("Trades", f"{int(stats['trades'])}", None),
            ("Net PnL (local currency)", f"{r.net:,.0f}", f"gross {r.gross:,.0f}"),
            ("Hit rate", f"{stats['hit_rate']:.0%}", None),
            ("Worst trade", f"{stats['worst']:,.0f}", None),
        ]
    )
    band = pd.DataFrame(
        {"deviation (bps of spot)": dev.dev_bps, "+ entry": float(entry), "- entry": -float(entry)}
    )
    st.plotly_chart(
        charts.lines(band, "Future minus fair value (front contract)", "Date", "bps of spot"),
        use_container_width=True,
    )
    decomposition(
        {"Gross convergence": r.gross, "Round-trip costs": -r.costs, "Slippage": -r.slippage},
        "PnL decomposition (local currency)",
        "Currency units",
    )
    widths = [4, 8, 12, 20, 30, 45]
    sweep = pd.Series(
        {
            f"{x} bps": cc.arb_backtest(dev, x, exit_, cost, slip, float(n), MULT[index]).net
            for x in widths
        }
    )
    st.plotly_chart(
        charts.bars(
            list(sweep.index),
            list(sweep.values),
            "Net PnL against entry band width",
            "Currency units",
        ),
        use_container_width=True,
    )
    if len(t):
        c.blotter(
            t.apply(lambda s: s.round(2) if s.dtype.kind == "f" else s),
            "index_arb_trades",
            key=P + "dl",
            height=240,
        )
    st.caption(
        "Synthetic data. Closing-price entries and exits, a single round-trip cost, no intraday path. Units are the contract currency. Dividends are known in this model; a dividend cut moves fair value (see the risk buttons)."
    )

    def dividend_cut() -> dict[str, str]:
        last = dev.index[-1]
        divs = w.market.index_dividends_between(index, last.date(), dev.expiry.iloc[-1])
        pts = sum(x.amount for x in divs)
        hit = 0.2 * pts
        return {
            "Dividend points still to come on the front contract": f"{pts:.2f}",
            "Fair value rises by about (20% cut)": f"{hit:.2f} pts",
            "PnL on a short future position": f"{-hit * MULT[index] * n:,.0f}",
        }

    def double_slip() -> dict[str, str]:
        r2 = cc.arb_backtest(dev, entry, exit_, cost, slip * 2, float(n), MULT[index])
        return {
            "Net PnL as now": f"{r.net:,.0f}",
            "Net PnL with slippage doubled": f"{r2.net:,.0f}",
            "Change": f"{r2.net - r.net:+,.0f}",
        }

    def funding_up() -> dict[str, str]:
        d2 = _dev(index, float(fs + 50), w.market.seed, str(w.as_of))
        r2 = cc.arb_backtest(d2, entry, exit_, cost, slip, float(n), MULT[index])
        return {
            "Net PnL as now": f"{r.net:,.0f}",
            "Net PnL if the true funding spread is +50 bps above the model": f"{r2.net:,.0f}",
            "Lesson": "A wrong funding input looks like an arbitrage that is not there.",
        }

    def tight_band() -> dict[str, str]:
        r2 = cc.arb_backtest(dev, 3, exit_, cost, slip, float(n), MULT[index])
        return {
            "Trades at a 3 bps entry": f"{len(r2.trades)}",
            "Net PnL at a 3 bps entry": f"{r2.net:,.0f}",
            "Lesson": "A band tighter than your costs trades a lot and loses.",
        }

    risk_buttons(
        P,
        [
            Risk(
                "Dividend cut",
                "Fair value assumes forecast dividends; a cut moves it.",
                dividend_cut,
            ),
            Risk("Slippage doubles", "Basket execution is worse than assumed.", double_slip),
            Risk(
                "Funding input wrong",
                "The funding spread in fair value is 50 bps too low.",
                funding_up,
            ),
            Risk(
                "Band tighter than costs",
                "Entry threshold below the cost of the round trip.",
                tight_band,
            ),
        ],
    )
    c.reset_button(P)


render_module("s_index_arb", sandbox)

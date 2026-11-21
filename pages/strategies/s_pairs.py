"""Strategy: pairs and statistical arbitrage."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.strategies import pairs as pr
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "spr_"


@st.cache_data(show_spinner=False)
def _screen(sector: str, seed: int, as_of: str) -> pd.DataFrame:
    m = get_world().market
    names = [
        t for t, s in m.universe.stocks.items() if s.sector == sector and s.listed_from is None
    ][:10]
    return pr.screen_pairs(m.prices, names, 6)


def sandbox() -> None:
    w = get_world()
    m = w.market
    st.markdown(
        "**Thesis.** Two related stocks drift together. When their spread is unusually wide, short the rich leg and buy the cheap one, in the hedge ratio, and wait for it to revert. A flow desk does not run this as a main business, but clients do and you will hear the vocabulary."
    )
    legs_diagram(
        [
            ("Stock A", "buy if spread cheap / sell if rich", "out"),
            ("Stock B", "opposite, scaled by hedge ratio", "out"),
            ("Borrow desk", "short leg borrow fee", "out"),
        ]
    )
    c.formula_box(
        r"s_t = \ln A_t - \beta \ln B_t - \alpha,\qquad z_t = \frac{s_t-\bar s}{\sigma_s}",
        {"beta": "OLS hedge ratio", "z": "rolling z-score"},
    )
    sectors = sorted({s.sector for s in m.universe.stocks.values()})
    sec = st.selectbox("Sector to screen", sectors, key=P + "sec")
    sc = _screen(sec, m.seed, str(w.as_of))
    st.markdown(
        "**Cointegration screen (Engle-Granger style, ADF critical value about -3.34 at 5%)**"
    )
    st.dataframe(sc.round(3), use_container_width=True)
    st.caption(
        "Screen enough pairs and some will look cointegrated by chance. That multiple-testing problem is why a pair that passes in-sample often fails out of sample."
    )
    if sc.empty:
        return
    labels = [f"{r.a} / {r.b}" for r in sc.itertuples()]
    pick = st.selectbox("Pair to trade", labels, key=P + "pair")
    a_, b_ = pick.split(" / ")
    ps = pr.pair_stats(m.prices, a_, b_)
    x, y, z = st.columns(3)
    ez = x.slider("Entry z-score", 1.0, 3.5, 2.0, 0.25, key=P + "ez")
    xz = y.slider("Exit z-score", 0.0, 1.5, 0.5, 0.25, key=P + "xz")
    win = z.slider("Rolling window (days)", 20, 120, 60, 10, key=P + "w")
    cost = x.slider("Round-trip cost (z units)", 0.0, 0.5, 0.1, 0.05, key=P + "c")
    t = pr.backtest(m.prices, a_, b_, ez, xz, cost, win)
    c.metric_row(
        [
            ("Hedge ratio beta", f"{ps.beta:.2f}", None),
            (
                "ADF statistic",
                f"{ps.adf:.2f}",
                "cointegrated at 5%" if ps.cointegrated else "not cointegrated at 5%",
            ),
            (
                "Half-life",
                f"{ps.half_life:.0f} days" if ps.half_life != float("inf") else "none",
                None,
            ),
            ("Backtest PnL", f"{float(t.pnl.sum()):,.0f}" if len(t) else "0", f"{len(t)} trades"),
        ]
    )
    zs = pr.zscores(pr.spread(m.prices[a_], m.prices[b_]), win)
    st.plotly_chart(
        charts.lines(
            pd.DataFrame({"z-score": zs, "+ entry": ez, "- entry": -ez}),
            "Spread z-score",
            "Date",
            "z",
        ),
        use_container_width=True,
    )
    if len(t):
        gross = float(
            (t.pnl_signal + cost).sum() * float(pr.spread(m.prices[a_], m.prices[b_]).std()) * 1e6
        )
        decomposition(
            {
                "Gross reversion": gross,
                "Costs": -cost * len(t) * float(pr.spread(m.prices[a_], m.prices[b_]).std()) * 1e6,
            },
            "PnL decomposition on 1,000,000 per leg",
            "USD",
        )
        c.blotter(
            t.apply(lambda s: s.round(3) if s.dtype.kind == "f" else s),
            "pairs_trades",
            key=P + "dl",
            height=200,
        )
    st.caption(
        "Synthetic prices. Hedge ratio fitted over the whole sample (look-ahead): a live version must refit through time. Costs are in z units and borrow on the short leg is not charged."
    )

    def break_down() -> dict[str, str]:
        return {
            "Spread standard deviation": f"{float(pr.spread(m.prices[a_], m.prices[b_]).std()):.3f}",
            "Meaning": "If the relationship breaks (merger, scandal), the spread does not revert and the position loses without limit; use a stop on z.",
        }

    def slow() -> dict[str, str]:
        return {
            "Half-life": f"{ps.half_life:.0f} days",
            "Lesson": "A long half-life means capital tied up and borrow paid for months.",
        }

    def multi() -> dict[str, str]:
        return {
            "Pairs screened": f"{len(sc)} shown from all pairs in the sector",
            "Lesson": "Report the number of pairs tested, not just the winner.",
        }

    risk_buttons(
        P,
        [
            Risk("Relationship breaks", "The spread never reverts.", break_down),
            Risk("Slow reversion", "Half-life too long.", slow),
            Risk("Data mining", "Multiple testing.", multi),
        ],
    )
    c.reset_button(P)


render_module("s_pairs", sandbox)

"""Strategy: futures roll and calendar spreads."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.strategies import roll as rl
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "sro_"
MULT = {"D1 US 30": 50.0, "D1 Europe 20": 10.0}


@st.cache_data(show_spinner=False)
def _events(
    index: str, days_before: int, funding_bps: float, seed: int, as_of: str
) -> pd.DataFrame:
    return rl.roll_events(get_world().market, index, days_before, funding_bps / 1e4)


def sandbox() -> None:
    w = get_world()
    st.markdown(
        "**Thesis.** Everyone long index futures must roll before expiry. The spread between the contracts embeds the financing and dividends; when it is rich against its fair carry the desk sells the roll, and when it is cheap it buys it."
    )
    legs_diagram(
        [
            ("Exchange", "sell near, buy far (long rolls)", "out"),
            ("Financing", "carry = rate - dividend yield", "in"),
        ]
    )
    c.formula_box(
        r"\text{roll cost} = F_{far} - F_{near},\qquad \text{richness} = (F_{far}-F_{near}) - \text{fair spread}",
        {"F": "futures prices, index points", "fair spread": "carry between the two expiries"},
    )
    a, b, cc = st.columns(3)
    index = a.selectbox("Index", list(MULT), key=P + "ix")
    days_before = b.slider("Roll this many trading days before expiry", 1, 15, 5, key=P + "db")
    fund = cc.slider("Funding spread in fair value (bps)", 0, 40, 10, key=P + "fs")
    n = a.number_input("Contracts (long)", 1, 1000, 100, key=P + "n")
    ev = _events(index, days_before, float(fund), w.market.seed, str(w.as_of))
    if ev.empty:
        st.info("No roll events in the history for this setting.")
        return
    cost = (ev.spread * MULT[index] * n).rename("Roll cost (currency units, paid by a long)")
    rich = (ev.richness * MULT[index] * n).rename("Richness vs fair (currency units)")
    c.metric_row(
        [
            ("Rolls in history", f"{len(ev)}", None),
            ("Average gross roll cost", f"{ev.cost_bps_pa.mean():.0f} bps a year", None),
            (
                "Average richness",
                f"{ev.richness_bps_pa.mean():+.0f} bps a year",
                "above fair = rich",
            ),
            ("Total richness captured by selling every roll", f"{rich.sum():,.0f}", None),
        ]
    )
    st.plotly_chart(
        charts.lines(
            ev[["cost_bps_pa", "richness_bps_pa"]].rename(
                columns={"cost_bps_pa": "Gross roll cost", "richness_bps_pa": "Richness vs fair"}
            ),
            "Roll cost and richness (bps a year, ACT/365)",
            "Roll date",
            "bps a year",
        ),
        use_container_width=True,
    )
    decomposition(
        {
            "Gross roll cost to a long": -float(cost.sum()),
            "Fair carry (the part that is not a mispricing)": float(
                (ev.fair_spread * MULT[index] * n).sum()
            ),
            "Richness (the trade)": float(rich.sum()),
        },
        "Roll PnL decomposition for a long that rolls every quarter",
        "Currency units",
    )
    tbl = ev[["near", "far", "f_near", "f_far", "spread", "fair_spread", "richness"]].round(2)
    c.blotter(tbl, "roll_events", key=P + "dl", height=240)
    st.caption(
        "Synthetic data. One flat rate per roll date, no open-interest data (not modelled) and no roll-week liquidity effects."
    )

    def late_roll() -> dict[str, str]:
        e2 = _events(index, 1, float(fund), w.market.seed, str(w.as_of))
        return {
            "Average richness 5 days out": f"{ev.richness_bps_pa.mean():+.0f} bps",
            "Average richness 1 day out": f"{e2.richness_bps_pa.mean():+.0f} bps",
            "Lesson": "Rolling on the last day removes optionality and pays the roll-week crowd.",
        }

    def spread_widen() -> dict[str, str]:
        big = ev.spread.abs().max()
        return {
            "Largest absolute spread in history": f"{big:.2f} pts",
            "PnL of a calendar spread position of the same size": f"{big * MULT[index] * n:,.0f}",
            "Lesson": "A spread position has far less risk than an outright, but not none.",
        }

    def funding_model() -> dict[str, str]:
        e2 = _events(index, days_before, float(fund + 25), w.market.seed, str(w.as_of))
        return {
            "Average richness as now": f"{ev.richness_bps_pa.mean():+.0f} bps",
            "Average richness with funding +25 bps": f"{e2.richness_bps_pa.mean():+.0f} bps",
            "Lesson": "Richness depends on the carry model: change the funding input and the trade changes sign.",
        }

    risk_buttons(
        P,
        [
            Risk("Roll on the last day", "No time to find a good price.", late_roll),
            Risk("Spread dislocation", "The spread moves against a spread position.", spread_widen),
            Risk("Carry model wrong", "The funding spread is 25 bps different.", funding_model),
        ],
    )
    c.reset_button(P)


render_module("s_roll", sandbox)

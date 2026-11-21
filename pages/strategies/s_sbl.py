"""Strategy: securities lending."""

from __future__ import annotations

import streamlit as st

from core import config
from core.financing import sbl
from core.strategies import sbl_strats as ss
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, legs_diagram, risk_buttons

P = "ssb_"


def sandbox() -> None:
    w = get_world()
    m = w.market
    st.markdown(
        "**Thesis.** Borrow demand is uneven. Hard-to-borrow names earn large fees, general collateral earns little. A lending desk finds the specials, prices them as utilisation rises, manages recalls and upgrades collateral for a fee."
    )
    legs_diagram(
        [
            ("Beneficial owner", "lends shares, receives fee share", "in"),
            ("Borrower", "pays fee or rebate", "in"),
            ("Treasury", "reinvests cash collateral", "out"),
        ]
    )
    c.formula_box(
        r"Revenue = V\,u\,f\,\frac{d}{360}",
        {"V": "lendable value", "u": "utilisation", "f": "fee, bps a year", "d": "days"},
    )
    st.markdown("**Specials screen at the as-of date**")
    sp = ss.specials_screen(m, w.as_of, 10)
    st.dataframe(sp.round(3), use_container_width=True)
    a, b, cc = st.columns(3)
    val = a.number_input("Lendable value (USD)", 1e6, 1e11, 100e6, 10e6, key=P + "v", format="%.0f")
    gc = b.slider("General collateral fee (bps)", 5, 100, 30, key=P + "gc")
    steep = cc.slider("Fee-curve steepness", 0.5, 8.0, 2.0, 0.5, key=P + "st")
    split = (
        a.slider(
            "Lender share of fee revenue (%)",
            50,
            95,
            int(config.desk().sbl.lender_share * 100),
            key=P + "sp",
        )
        / 100
    )
    curve = ss.utilisation_revenue_curve(val, gc, steep)
    st.plotly_chart(
        charts.lines(
            curve[["revenue"]].rename(columns={"revenue": "Annual revenue (USD)"}),
            "Revenue against utilisation: the fee curve is convex",
            "Utilisation",
            "USD a year",
        ),
        use_container_width=True,
    )
    u = st.slider("Utilisation (%)", 5, 99, 40, key=P + "u") / 100
    fee = sbl.fee_from_utilisation(u, gc, steep)
    r = ss.lending_revenue(val, u, fee, 360, split)
    c.metric_row(
        [
            ("Fee at this utilisation", f"{fee:.0f} bps", f"general collateral {gc} bps"),
            ("Gross revenue, year", f"{r['gross']:,.0f}", None),
            ("Our share", f"{r['agent']:,.0f}", f"lender {r['lender']:,.0f}"),
        ]
    )
    decomposition(
        {"Lender share": -r["lender"], "Gross fee revenue": r["gross"]},
        "Fee revenue split (USD a year, desk view)",
        "USD",
    )
    st.markdown("**Collateral upgrade**")
    up = ss.collateral_upgrade_revenue(
        st.number_input(
            "Notional upgraded (USD)", 1e6, 1e10, 20e6, 1e6, key=P + "up", format="%.0f"
        ),
        st.slider("Upgrade fee (bps)", 1, 60, 12, key=P + "uf"),
        90,
    )
    st.metric("Revenue over 90 days (ACT/360)", f"{up:,.0f}")
    st.caption(
        "Synthetic profiles and an illustrative fee curve. Fee held flat over the period; recall risk is not netted from revenue."
    )

    def recall() -> dict[str, str]:
        rk = ss.recall_cost_ranking(100_000, 50.0, 0.01, 0.05, 30, 0.02, 0.01, 0.005)
        return {f"{i + 1}. {n}": f"{v:,.0f}" for i, (n, v) in enumerate(rk)}

    def squeeze() -> dict[str, str]:
        f2 = sbl.fee_from_utilisation(0.97, gc, steep)
        return {
            "Fee at 97% utilisation": f"{f2:.0f} bps",
            "Revenue gain": f"{ss.lending_revenue(val, 0.97, f2, 360, split)['agent'] - r['agent']:+,.0f}",
            "Lesson": "The same event that earns fees can bring recalls, buy-ins and reputational risk.",
        }

    def cash_loss() -> dict[str, str]:
        return {
            "Loss on 100m cash collateral if reinvestment loses 0.5%": f"{-0.005 * 100e6:,.0f}",
            "Lesson": "Reinvestment risk can wipe out a year of fees.",
        }

    risk_buttons(
        P,
        [
            Risk("Recall", "A lender recalls 100,000 shares: compare responses.", recall),
            Risk("Squeeze", "Utilisation hits 97%.", squeeze),
            Risk("Reinvestment loss", "Cash collateral reinvested badly.", cash_loss),
        ],
    )
    c.reset_button(P)


render_module("s_sbl", sandbox)

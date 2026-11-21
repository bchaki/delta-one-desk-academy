"""ETFs: NAV, premium and the create/redeem arbitrage."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.pricing import etf as et
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "et_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    t1, t2 = st.tabs(["Create / redeem calculator", "Synthetic ETF premium history"])
    with t1:

        def comp(v):
            r = et.etf_arbitrage(v["px"], v["inav"], v["cu"], v["fee"], v["bc"], v["hs"])
            cu_value = v["inav"] * v["cu"]
            prem = et.premium_discount(v["px"], v["inav"]) * 1e4
            xs = [x / 2 for x in range(-120, 121)]
            thr = r.threshold_bps
            ys = [max(abs(x) - thr, 0.0) / 1e4 * cu_value for x in xs]
            fig = charts.lines(
                pd.DataFrame({"Arbitrage PnL per creation unit": ys}, index=xs),
                "Arbitrage PnL by premium: zero inside the threshold",
                "Premium (bps)",
                "PnL per creation unit (fund currency)",
            )
            return Out(
                metrics=[
                    ("Premium / discount", f"{prem:+.1f} bps", None),
                    ("Break-even threshold", f"{thr:.1f} bps", None),
                    (
                        "Action",
                        {"create": "Create", "redeem": "Redeem", "none": "No arbitrage"}[
                            r.action.value
                        ],
                        None,
                    ),
                    (
                        "PnL per creation unit",
                        f"{r.pnl_per_creation_unit:,.0f}",
                        f"CU value {cu_value:,.0f}",
                    ),
                ],
                figures=[fig],
                formula=(
                    r"threshold = \frac{fee}{CU\ value}10^4 + basket\ bps + ETF\ half\ spread",
                    {"CU value": "iNAV x creation unit size"},
                    [
                        rf"{v['fee']:.0f}/{cu_value:,.0f}\times10^4 + {v['bc']:.1f} + {v['hs']:.1f} = {thr:.2f}"
                    ],
                ),
            )

        calculator(
            P + "arb_",
            [
                Num("inav", "iNAV", 110.0, 1.0, None, 0.1),
                Num("px", "ETF price", 110.8, 1.0, None, 0.05),
                Num("cu", "Creation unit (shares)", 50_000.0, 1_000.0, None, 5_000.0, "%.0f"),
                Num("fee", "Creation fee", 500.0, 0.0, None, 50.0, "%.0f"),
                Num("bc", "Basket cost (bps)", 4.0, 0.0, 100.0, 0.5, "%.1f"),
                Num("hs", "ETF half spread (bps)", 2.0, 0.0, 100.0, 0.5, "%.1f"),
            ],
            comp,
            [
                "Set the ETF price below iNAV to see a redemption.",
                "Raise basket cost to 40 bps (stress): the arbitrage disappears.",
            ],
            advanced=s.advanced,
        )
    with t2:
        m = w.market
        etfs = m.universe.etfs
        pick = st.selectbox("ETF", list(etfs), key=P + "pick")
        e = etfs[pick]
        ts = [pd.Timestamp(d) for d in m.days if d <= w.as_of]
        px = m.etf_prices[pick].loc[ts]
        nav = m.index_tr[e.index].loc[ts] * e.scale
        prem = (px / nav - 1) * 1e4
        st.plotly_chart(
            charts.lines(
                pd.DataFrame({"Premium (bps)": prem}),
                f"{pick}: premium to NAV in the synthetic market",
                "Date",
                "bps",
            ),
            use_container_width=True,
        )
        st.caption(
            "Synthetic data. NAV is the index total return times the fund's scale. Premium = ETF close / NAV - 1, in bps."
        )
        c.reset_button(P)


render_module("etfs", sandbox)

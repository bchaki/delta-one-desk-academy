"""ADRs & Cross-listings."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.data.market import _usd_per_array  # noqa: F401
from core.pricing import adr as ad
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "ad_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    t1, t2 = st.tabs(["Parity and band", "Synthetic ADR vs local"])
    with t1:

        def comp(v):
            band = ad.adr_band(v["lp"], v["ratio"], v["fx"], v["fee"], v["cost"])
            action, edge = ad.adr_arbitrage(v["adr"], band)
            text = {
                "sell_adr_buy_local_issue": "ADR rich: sell ADR, buy local, issue",
                "buy_adr_cancel_sell_local": "ADR cheap: buy ADR, cancel, sell local",
                "none": "Inside the band: no arbitrage",
            }[action.value]
            fig = charts.bars(
                ["Lower bound", "Fair value", "Upper bound", "ADR price"],
                [band.lower, band.fair_value, band.upper, v["adr"]],
                "ADR price against the arbitrage band (USD)",
                "USD per ADR",
            )
            return Out(
                metrics=[
                    ("Fair value (parity)", f"{band.fair_value:.3f} USD", None),
                    ("Band", f"{band.lower:.3f} to {band.upper:.3f}", None),
                    ("Signal", text, None),
                    (
                        "Edge per ADR",
                        f"{edge:.4f} USD",
                        f"{edge * v['n']:,.0f} on {v['n']:,.0f} ADRs",
                    ),
                ],
                figures=[fig],
                formula=(
                    r"FV = P_{local}\times ratio\times FX",
                    {
                        "ratio": "local shares per ADR",
                        "FX": "USD per unit of local currency (JPY: 1/USDJPY)",
                    },
                    [
                        rf"{v['lp']:.2f}\times{v['ratio']:.2f}\times{v['fx']:.4f} = {band.fair_value:.3f}"
                    ],
                ),
            )

        calculator(
            P + "pb_",
            [
                Num("lp", "Local price", 40.0, 0.01, None, 0.5),
                Num("ratio", "Ratio (local per ADR)", 0.5, 0.01, 50.0, 0.1),
                Num("fx", "FX (USD per local)", 1.10, 0.0001, None, 0.01, "%.4f"),
                Num("adr", "ADR price (USD)", 22.10, 0.01, None, 0.05),
                Num("fee", "Conversion fee per ADR (USD)", 0.02, 0.0, None, 0.01, "%.3f"),
                Num("cost", "Other costs (bps)", 10.0, 0.0, 200.0, 1.0, "%.1f"),
                Num("n", "ADRs", 100_000.0, 1.0, None, 10_000.0, "%.0f", advanced=True),
            ],
            comp,
            [
                "Set the ADR at 21.95: the signal flips to cancel.",
                "For a yen stock set FX to 1/150 = 0.0067.",
            ],
            advanced=s.advanced,
        )
    with t2:
        m = w.market
        adrs = m.universe.adrs
        pick = st.selectbox("ADR", list(adrs), key=P + "pick")
        a = adrs[pick]
        st_ = m.universe.stocks[a.underlying]
        ts = [pd.Timestamp(d) for d in m.days if d <= w.as_of]
        days = [d for d in m.days if d <= w.as_of]
        fx = pd.Series([m.fx_usd_per(st_.ccy, d) for d in days], index=ts)
        fair = m.prices[a.underlying].loc[ts] * a.ratio * fx
        dev = (m.adr_prices[pick].loc[ts] / fair - 1) * 1e4
        st.plotly_chart(
            charts.lines(
                pd.DataFrame({"ADR deviation from parity (bps)": dev}),
                f"{pick} vs {a.underlying}: deviation from parity",
                "Date",
                "bps",
            ),
            use_container_width=True,
        )
        st.caption(
            f"Synthetic data. Ratio {a.ratio:g} local per ADR, depositary fee {a.depositary_fee:.3f} USD per ADR."
        )
        c.reset_button(P)


render_module("adrs", sandbox)

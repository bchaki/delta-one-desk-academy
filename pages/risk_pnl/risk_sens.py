"""Risk Sensitivities."""

from __future__ import annotations

import streamlit as st

from core.risk import basic as rb
from core.risk.liquidity import concentration, liquidity_table
from core.risk.sensitivities import sensitivities, snapshot
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "rs_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    m, book, d = w.market, w.book, w.as_of
    t1, t2, t3, t4 = st.tabs(
        ["Book snapshot", "Sensitivities", "Liquidity and concentration", "Calculator"]
    )
    snap = snapshot(book, m, d)
    with t1:
        net = float(snap.delta_usd.sum())
        gross = float((snap.cash_usd.abs() + snap.fut_usd.abs()).sum())
        c.metric_row(
            [
                ("Net delta", f"{net:,.0f} USD", "desk side, + = long to the desk"),
                ("Gross (hedges and futures)", f"{gross:,.0f} USD", None),
                ("Beta-adjusted delta", f"{float(snap.beta_delta_usd.sum()):,.0f} USD", None),
            ]
        )
        top = snap.reindex(snap.delta_usd.abs().sort_values(ascending=False).index).head(12)
        st.plotly_chart(
            charts.bars(
                list(top.key),
                list(top.delta_usd),
                "Largest net exposures by underlying (USD)",
                "USD, desk side",
            ),
            use_container_width=True,
        )
        cols = ["key", "kind", "region", "ccy", "cash_usd", "swap_usd", "fut_usd", "delta_usd"]
        st.markdown(
            "**Exposure by source.** A swap and its hedge sit in different columns of the same row and net out."
        )
        c.blotter(snap[cols].round(0), "risk_snapshot", key=P + "dl_snap")
        st.caption(
            f"Synthetic book at {d}. USD, desk side: cash = hedge inventory, swap = the desk's side of client swaps, fut = index futures."
        )
    with t2:
        sens = sensitivities(book, m, d)
        fx = sens["fx_delta"]
        c.metric_row(
            [
                ("Funding +1 bp (annual)", f"{sens['ftp_plus_1bp_annual']:,.0f} USD", None),
                ("Dividends -10% (12 months)", f"{sens['dividend_minus10pct']:,.0f} USD", None),
                ("Borrow +100 bps (annual)", f"{sens['borrow_plus_100bp_annual']:,.0f} USD", None),
                ("Dividend futures per point", f"{sens['divfut_per_point']:,.0f} USD", None),
            ]
        )
        st.plotly_chart(
            charts.bars(
                list(fx),
                list(fx.values()),
                "FX delta: PnL for a +1% move of each currency (USD)",
                "USD",
            ),
            use_container_width=True,
        )
        st.caption(
            "Units differ: funding is per basis point a year, dividends per 10% of forecast, borrow per 100 bps a year, FX per 1% move."
        )
    with t3:
        part = st.slider("Participation of ADV (%)", 5, 50, 20, 5, key=P + "part") / 100
        liq = liquidity_table(snap, m, d, part)
        conc = concentration(snap)
        c.metric_row(
            [
                (
                    "Max days to liquidate",
                    f"{liq.days_to_liquidate.max():.2f}" if len(liq) else "n/a",
                    f"at {part:.0%} of ADV",
                ),
                ("Top-5 share of gross inventory", f"{conc['top5']:.0%}", None),
                ("Herfindahl index", f"{conc['hhi']:.3f}", "1/n even; 1 = one name"),
            ]
        )
        if len(liq):
            worst = (
                liq.sort_values("days_to_liquidate", ascending=False).head(10).set_index("ticker")
            )
            st.plotly_chart(
                charts.bars(
                    list(worst.index),
                    list(worst.days_to_liquidate),
                    "Slowest positions to liquidate (days)",
                    "Days",
                ),
                use_container_width=True,
            )
            c.blotter(worst.round(3), "liquidity", key=P + "dl_liq")
    with t4:

        def comp(v):
            dl = rb.delta_exposure(v["sh"], v["px"], v["fx"])
            return Out(
                metrics=[
                    ("Delta", f"{dl:,.0f}", "reporting currency"),
                    (
                        "Beta-adjusted",
                        f"{rb.beta_adjusted(dl, v['beta']):,.0f}",
                        f"beta {v['beta']:.2f}",
                    ),
                    (
                        "FX effect of the move",
                        f"{rb.fx_translation_pnl(dl, v['fxm']):+,.0f}",
                        f"{v['fxm']:+.1f}% currency move",
                    ),
                    (
                        "Dividend effect",
                        f"{rb.dividend_exposure_pnl(dl, v['yld'] / 100, v['dpc']):+,.0f}",
                        f"{v['dpc']:+.0f}% forecast change",
                    ),
                    (
                        "Days to liquidate",
                        f"{rb.days_to_liquidate(v['sh'], v['adv'], v['part'] / 100):.2f}",
                        f"{v['part']:.0f}% participation",
                    ),
                ],
                formula=(
                    r"\Delta = N\times P\times FX",
                    {"N": "shares", "P": "price", "FX": "reporting per local"},
                    [rf"{v['sh']:,.0f}\times{v['px']:.2f}\times{v['fx']:.2f} = {dl:,.0f}"],
                ),
            )

        calculator(
            P + "ca_",
            [
                Num("sh", "Shares (long +)", 10_000.0, None, None, 1_000.0, "%.0f"),
                Num("px", "Price", 50.0, 0.01, None, 1.0),
                Num("fx", "FX (reporting per local)", 1.10, 0.0001, None, 0.01, "%.4f"),
                Num("beta", "Beta", 1.2, -1.0, 4.0, 0.05),
                Num("fxm", "Currency move (%)", -2.0, -50.0, 50.0, 0.5),
                Num("yld", "Dividend yield (%)", 3.0, 0.0, 30.0, 0.1),
                Num("dpc", "Forecast dividend change (%)", -10.0, -100.0, 100.0, 5.0, "%.0f"),
                Num("adv", "ADV (shares)", 1_000_000.0, 1.0, None, 100_000.0, "%.0f"),
                Num("part", "Participation (%)", 20.0, 1.0, 100.0, 5.0, "%.0f"),
            ],
            comp,
            [
                "Make shares negative: every sensitivity flips sign.",
                "Raise participation to 50% and watch days to liquidate.",
            ],
            advanced=s.advanced,
        )
    c.reset_button(P)


render_module("risk_sens", sandbox)

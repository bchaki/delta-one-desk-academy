"""Pricing Lab: forwards, implied financing, swap quote sheet, TRF conversion and a bump table."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from core.pricing import forwards as fw
from core.pricing import futures as fu
from core.pricing import swaps as sw
from core.pricing import trf
from core.types import Direction
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings

P = "pl_"


def sandbox() -> None:
    s = get_settings()
    t1, t2, t3, t4 = st.tabs(
        ["Forward and implied repo", "Swap quote sheet", "Price future to TRF", "Bump table"]
    )
    with t1:

        def comp(v):
            t = v["days"] / 365.0
            divs = [(v["dt"] / 365.0, v["div"])] if v["div"] else []
            fc = fw.forward_continuous(v["s"], v["r"] / 100, v["q"] / 100, t)
            fd = fu.model_forward(v["s"], v["r"] / 100, divs, t)
            fv = sum(d * math.exp(v["r"] / 100 * (t - ti)) for ti, d in divs if ti <= t)
            ir = fu.implied_repo_simple(v["s"], v["f"], fv, int(v["days"]), 365)
            return Out(
                metrics=[
                    ("Forward, continuous yield", f"{fc:.4f}", f"yield {v['q']:.2f}% cc"),
                    (
                        "Forward, discrete dividend",
                        f"{fd:.4f}",
                        f"{v['div']:.2f} at day {v['dt']:.0f}",
                    ),
                    ("Implied simple repo (ACT/365)", f"{ir:.2%}", f"from market {v['f']:.2f}"),
                    (
                        "Market vs discrete fair value",
                        f"{v['f'] - fd:+.3f}",
                        "rich" if v["f"] > fd else "cheap",
                    ),
                ],
                formula=(
                    r"F = S e^{rT} - \sum_i D_i e^{r(T - t_i)}",
                    {
                        "S": "spot",
                        "r": "financing rate, continuous, ACT/365",
                        "D": "dividend",
                        "t": "ex-date, years",
                    },
                    [rf"{v['s']:.2f}e^{{{v['r'] / 100:.4f}\times{t:.4f}}} - {fv:.4f} = {fd:.4f}"],
                ),
            )

        calculator(
            P + "fw_",
            [
                Num("s", "Spot", 100.0, 0.01, None, 1.0),
                Num("r", "Financing rate (% cc, ACT/365)", 4.0, -2.0, 20.0, 0.05),
                Num("q", "Dividend yield (% cc)", 2.0, 0.0, 20.0, 0.1),
                Num("div", "Discrete dividend", 1.0, 0.0, None, 0.1),
                Num("dt", "Dividend ex-date (days from now)", 90.0, 1.0, 730.0, 1.0, "%.0f"),
                Num("days", "Days to expiry", 180.0, 1.0, 730.0, 1.0, "%.0f"),
                Num("f", "Market futures price", 101.2, 0.01, None, 0.05),
            ],
            comp,
            [
                "Move the dividend after expiry: it drops out of the forward.",
                "Compare the yield and discrete forwards.",
            ],
            advanced=s.advanced,
        )
    with t2:
        dirn = Direction(
            st.radio("Client direction", ["LONG", "SHORT"], horizontal=True, key=P + "dir")
        )
        label = "Funding (FTP)" if dirn is Direction.LONG else "Borrow fee"
        cols = st.columns(3)
        base = cols[0].number_input(f"{label} (bps)", 0.0, 3000.0, 35.0, 1.0, key=P + "ftp")
        parts = {
            "bs": cols[1].number_input("Balance sheet (bps)", 0.0, 500.0, 4.0, 0.5, key=P + "bs"),
            "cap": cols[2].number_input("Capital (bps)", 0.0, 500.0, 3.0, 0.5, key=P + "cap"),
            "xva": cols[0].number_input(
                "Credit and funding valuation adjustments (bps)",
                0.0,
                500.0,
                2.0,
                0.5,
                key=P + "xva",
            ),
            "hc": cols[1].number_input("Hedging cost (bps)", 0.0, 500.0, 1.0, 0.5, key=P + "hc"),
            "mg": cols[2].number_input("Target margin (bps)", 0.0, 500.0, 5.0, 0.5, key=P + "mg"),
        }
        sb = sw.spread_build_up(
            dirn,
            base if dirn is Direction.LONG else 0.0,
            base if dirn is Direction.SHORT else 0.0,
            parts["bs"],
            parts["cap"],
            parts["xva"],
            parts["hc"],
            parts["mg"],
        )
        st.plotly_chart(
            charts.waterfall(
                {
                    label: base,
                    **{
                        k: v
                        for k, v in zip(
                            ["Balance sheet", "Capital", "XVA", "Hedging cost", "Margin"],
                            parts.values(),
                            strict=True,
                        )
                    },
                },
                "Client spread build-up (bps over benchmark)",
                "bps",
                "Spread",
            ),
            use_container_width=True,
        )
        c.metric_row(
            [
                ("Quoted client spread", f"{sb.total_bps:.1f} bps", "over the local benchmark"),
                ("Negotiable part", f"{parts['mg']:.1f} bps", "target margin only"),
            ]
        )
        st.caption(
            "A short's spread is quoted as benchmark minus this figure on the proceeds. Illustrative components."
        )
    with t3:

        def comp3(v):
            tau = v["days"] / 360.0
            basis = trf.trf_spread_to_price_basis(v["s"], v["spr"], v["bm"] / 100, tau, v["fvd"])
            back = trf.price_basis_to_trf_spread_bps(
                v["s"], v["s"] + basis, v["bm"] / 100, tau, v["fvd"]
            )
            sp2 = trf.price_basis_to_trf_spread_bps(v["s"], v["f"], v["bm"] / 100, tau, v["fvd"])
            return Out(
                metrics=[
                    ("TRF spread to price basis", f"{basis:.2f} pts", f"at {v['spr']:.1f} bps"),
                    ("Round trip check", f"{back:.2f} bps", "equals the input"),
                    ("Price future to TRF spread", f"{sp2:.2f} bps", f"future {v['f']:,.1f}"),
                ],
                formula=(
                    r"F - S = S(b + \text{spread})\tau - FV(D)",
                    {
                        "b": "benchmark",
                        "tau": "period in years, ACT/360",
                        "FV(D)": "dividends at expiry, index points",
                    },
                    [
                        rf"{v['s']:,.0f}\times{v['bm'] / 100 + v['spr'] / 1e4:.4f}\times{tau:.3f} - {v['fvd']:.1f} = {basis:.2f}"
                    ],
                ),
            )

        calculator(
            P + "tr_",
            [
                Num("s", "Index spot", 5000.0, 1.0, None, 10.0, "%.1f"),
                Num("bm", "Benchmark (% simple, ACT/360)", 4.0, 0.0, 20.0, 0.05),
                Num("spr", "TRF spread (bps)", 16.0, -100.0, 500.0, 1.0, "%.1f"),
                Num("days", "Days", 90.0, 1.0, 720.0, 1.0, "%.0f"),
                Num("fvd", "Dividends at expiry (index points)", 12.0, 0.0, None, 0.5, "%.1f"),
                Num("f", "Price future", 5040.0, 1.0, None, 1.0, "%.1f"),
            ],
            comp3,
            [
                "Raise dividends: the price basis falls for the same TRF spread.",
                "Set the price future at spot plus basis and see the spread return.",
            ],
        )
    with t4:
        st.markdown(
            "Bump each input and reprice the discrete forward: this is how risk systems compute sensitivities."
        )
        sp, r, d, tt = 100.0, 0.04, 1.0, 0.5
        base_f = fu.model_forward(sp, r, [(0.25, d)], tt)
        rows = [
            ("Spot +1%", fu.model_forward(sp * 1.01, r, [(0.25, d)], tt) - base_f),
            ("Rate +1 bp", fu.model_forward(sp, r + 1e-4, [(0.25, d)], tt) - base_f),
            ("Dividend +0.10", fu.model_forward(sp, r, [(0.25, d + 0.1)], tt) - base_f),
            ("Expiry +1 month", fu.model_forward(sp, r, [(0.25, d)], tt + 1 / 12) - base_f),
        ]
        df = pd.DataFrame(rows, columns=["Bump", "Change in forward"]).set_index("Bump")
        st.dataframe(df.style.format("{:+.4f}"), use_container_width=True)
        st.caption("Base: spot 100, r 4% cc, one dividend of 1.00 at 0.25 years, expiry 0.5 years.")
    c.reset_button(P)


render_module("pricing_lab", sandbox)

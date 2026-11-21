"""Rates, Funding & Financing."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import config
from core.data.market import BASIS_BY_BENCH, CAL_BY_BENCH
from core.rates import (
    compound_overnight,
    convert_basis,
    funding_rate,
    simple_average_overnight,
    simple_interest,
)
from core.types import Benchmark, Currency
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "rf_"


def sandbox() -> None:
    s = get_settings()
    w = get_world()
    m = w.market
    t1, t2, t3 = st.tabs(
        ["Day counts and interest", "Compounding in arrears", "Funding rate and carry"]
    )
    with t1:

        def comp(v):
            on360 = simple_interest(v["n"], v["r"] / 100, int(v["d"]), 360)
            on365 = simple_interest(v["n"], v["r"] / 100, int(v["d"]), 365)
            return Out(
                metrics=[
                    ("Interest ACT/360", f"{on360:,.2f}", None),
                    ("Interest ACT/365F", f"{on365:,.2f}", f"{on365 - on360:+,.2f}"),
                    (
                        "Same cash, ACT/365F rate",
                        f"{convert_basis(v['r'] / 100, 360, 365):.4%}",
                        None,
                    ),
                ],
                formula=(
                    r"I = N \times r \times \frac{d}{basis}",
                    {
                        "N": "principal (currency units)",
                        "r": "annual rate (decimal)",
                        "d": "actual days",
                        "basis": "360 or 365",
                    },
                    [
                        rf"I_{{360}} = {v['n']:,.0f} \times {v['r'] / 100:.4f} \times {v['d']:.0f}/360 = {on360:,.2f}"
                    ],
                ),
            )

        calculator(
            P + "dc_",
            [
                Num("n", "Principal", 10_000_000.0, 0.0, None, 100_000.0, "%.0f"),
                Num("r", "Rate (% a year)", 4.30, 0.0, 30.0, 0.05),
                Num("d", "Days", 91.0, 1.0, 3650.0, 1.0, "%.0f"),
            ],
            comp,
            [
                "Switch to 182 days: the gap between bases grows with the period.",
                "Try a 1% rate: the basis effect shrinks with the rate level.",
            ],
        )
    with t2:
        bench = st.selectbox(
            "Benchmark", list(Benchmark), key=P + "bench", format_func=lambda b: b.value
        )
        cal, basis = CAL_BY_BENCH[bench], BASIS_BY_BENCH[bench]
        fix = m.fixings_dict(bench)
        days = [d for d in m.days if d <= w.as_of][-80:]
        start = st.selectbox("Period start", days[:-25], index=len(days[:-25]) - 1, key=P + "start")
        length = st.slider("Period length (business days)", 5, 40, 21, key=P + "len")
        end_candidates = [d for d in m.days if d > start]
        end = end_candidates[min(length, len(end_candidates)) - 1]
        look = st.slider("Lookback (business days)", 0, 5, 0, key=P + "look") if s.advanced else 0
        shift = st.toggle("Observation shift", key=P + "shift") if s.advanced else False
        try:
            comp_r = compound_overnight(
                fix, start, end, cal, basis, lookback=look, observation_shift=shift
            )
            avg_r = simple_average_overnight(fix, start, end, cal)
        except KeyError as e:
            st.warning(f"Missing fixing: {e}. Pick a later start date or lower the lookback.")
            return
        notional = 25_000_000
        dd = (end - start).days
        c.metric_row(
            [
                ("Compounded in arrears", f"{comp_r:.5%}", None),
                ("Simple average", f"{avg_r:.5%}", f"{(comp_r - avg_r) * 1e4:+.2f} bps"),
                (
                    f"Interest on {notional / 1e6:.0f}m",
                    f"{notional * comp_r * dd / basis:,.0f}",
                    f"{notional * (comp_r - avg_r) * dd / basis:+,.0f} vs simple",
                ),
            ]
        )
        st.caption(
            f"{bench.value}: {cal.value} calendar, basis {basis}, {dd} calendar days from {start} to {end}. Lookback {look}, shift {'on' if shift else 'off'}."
        )
        ser = pd.Series({d: fix[d] * 100 for d in days if d in fix}, name=f"{bench.value} (%)")
        st.plotly_chart(
            charts.lines(
                ser.to_frame(),
                f"{bench.value} fixings over the last 80 trading days",
                "Date",
                "% a year",
            ),
            use_container_width=True,
        )
    with t3:
        ccy = st.selectbox(
            "Currency",
            [Currency.USD, Currency.EUR, Currency.GBP, Currency.JPY, Currency.CHF],
            key=P + "ccy",
            format_func=lambda x: x.value,
        )
        bench = {
            Currency.USD: Benchmark.SOFR,
            Currency.EUR: Benchmark.ESTR,
            Currency.GBP: Benchmark.SONIA,
            Currency.JPY: Benchmark.TONA,
            Currency.CHF: Benchmark.SARON,
        }[ccy]
        on = m.fixing(bench, w.as_of)

        def comp3(v):
            fund = funding_rate(on, ccy)
            carry = v["n"] * (v["sp"] - config.desk().ftp_spread_bps[ccy]) / 1e4
            return Out(
                metrics=[
                    (f"{bench.value} on {w.as_of}", f"{on:.3%}", None),
                    (
                        "Desk funding rate",
                        f"{fund:.3%}",
                        f"+{config.desk().ftp_spread_bps[ccy]:.0f} bps FTP",
                    ),
                    (
                        "Annual carry on a long swap",
                        f"{carry:+,.0f} {ccy.value}",
                        f"{v['sp'] - config.desk().ftp_spread_bps[ccy]:+.0f} bps net",
                    ),
                ]
            )

        calculator(
            P + "fc_",
            [
                Num("n", f"Notional ({ccy.value})", 25_000_000.0, 0.0, None, 1_000_000.0, "%.0f"),
                Num("sp", "Client swap spread (bps)", 30.0, -50.0, 300.0, 1.0),
            ],
            comp3,
            [
                "Set the spread below the FTP spread to see a negative carry.",
                "Switch currency: FTP spreads differ.",
            ],
        )
        c.illustrative_note(config.desk())


render_module("rates_funding", sandbox)

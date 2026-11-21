"""Counterparty Risk & XVA."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import config
from core.financing import xva_lite as xv
from core.types import Direction
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_settings

P = "xv_"


@st.cache_data(show_spinner=False)
def _profile(notional, vol, maturity, steps, reset_every, direction, paths, mpor, threshold):
    d = Direction(direction)
    return xv.simulate_exposure(
        notional, vol, maturity, steps, reset_every, d, paths, 0, mpor, threshold
    )


def sandbox() -> None:
    s = get_settings()
    x = config.desk().xva
    b = config.desk().balance_sheet
    a, bcol, ccol = st.columns(3)
    n = a.number_input("Notional", 1e5, 1e10, 10e6, 1e6, key=P + "n", format="%.0f")
    vol = bcol.slider("Annual volatility (%)", 10, 80, 25, key=P + "vol") / 100
    mat = ccol.slider("Maturity (years)", 0.25, 5.0, 1.0, 0.25, key=P + "mat")
    steps = int(round(mat * 52))
    reset_weeks = a.selectbox("Reset every (weeks)", [4, 13, 26, 52], index=1, key=P + "rs")
    direction = bcol.selectbox("Client direction", ["LONG", "SHORT"], key=P + "dir")
    cpty = ccol.selectbox(
        "Client type", [k for k in x.cds_spread_bps if x.cds_spread_bps[k] > 0], key=P + "cp"
    )
    csa_on = a.toggle("CSA in force", value=True, key=P + "csa")
    mpor = bcol.slider("Margin period of risk (weeks)", 0, 6, 2, key=P + "mpor") if csa_on else None
    th = (
        ccol.number_input("CSA threshold", 0.0, 1e9, 0.0, 100_000.0, key=P + "th", format="%.0f")
        if csa_on
        else 0.0
    )
    paths = 3000 if not s.advanced else 5000
    prof = _profile(n, vol, mat, steps, reset_weeks, direction, paths, mpor, th)
    nocsa = _profile(n, vol, mat, steps, reset_weeks, direction, paths, None, 0.0)
    spread = x.cds_spread_bps[cpty]
    cv = xv.cva(prof.ee, prof.times, spread, x.lgd)
    fv = xv.fva(prof.ee, prof.times, x.funding_spread_bps)
    kv = xv.kva(prof.ee, prof.times, b.counterparty_rw[cpty], b.cet1_ratio, x.kva_hurdle)
    mv = xv.mva(0.0 if not csa_on else 0.05 * n, mat, x.mva_funding_bps)
    tot = cv + fv + kv + mv
    c.metric_row(
        [
            ("Peak PFE (95%)", f"{prof.peak_pfe:,.0f}", f"no CSA: {nocsa.peak_pfe:,.0f}"),
            ("Average expected exposure", f"{prof.epe:,.0f}", f"no CSA: {nocsa.epe:,.0f}"),
            ("CVA", f"{cv:,.0f}", f"credit spread {spread:.0f} bps, LGD {x.lgd:.0%}"),
            (
                "FVA + KVA + MVA",
                f"{fv + kv + mv:,.0f}",
                f"FVA {fv:,.0f}, KVA {kv:,.0f}, MVA {mv:,.0f}",
            ),
            ("XVA as a spread", f"{xv.xva_charge_bps(tot, n, mat):.1f} bps a year", None),
        ]
    )
    df = pd.DataFrame(
        {"Expected exposure": prof.ee, "PFE 95%": prof.pfe, "EE without CSA": nocsa.ee},
        index=prof.times,
    )
    st.plotly_chart(
        charts.lines(
            df,
            "Exposure profile of the swap: a saw-tooth that resets to zero",
            "Years",
            "Currency units, desk's exposure to the client",
        ),
        use_container_width=True,
    )
    st.caption(
        f"Seeded simulation ({paths:,} paths, weekly steps), lognormal underlying, flat hazard and rates, no netting or wrong-way risk. "
        "Credit spreads, funding spread, LGD and hurdle are illustrative (config/desk.yaml). The initial margin for MVA is assumed to be 5% of notional when a CSA is in force."
    )
    c.what_to_try(
        [
            "Switch the CSA off: exposure and CVA jump.",
            "Lengthen the reset period to 52 weeks and watch the peak PFE grow.",
            "Change the client type to pension: CVA falls.",
        ]
    )
    c.illustrative_note(config.desk())
    c.reset_button(P)


render_module("xva", sandbox)

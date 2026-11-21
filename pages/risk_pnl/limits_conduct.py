"""Limits, Controls & Conduct."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import config
from core.risk import var as vr
from core.risk.limits import check_limits
from core.risk.liquidity import concentration, liquidity_table
from core.risk.sensitivities import snapshot, usd_exposure_vector
from ui import charts
from ui import components as c
from ui.content import data_file
from ui.module_page import render_module
from ui.state import get_settings, get_world

P = "lc_"

ICON = {"ok": "OK", "soft": "SOFT: escalate", "hard": "HARD: breach"}


def _metrics(w) -> dict[str, float]:
    snap = snapshot(w.book, w.market, w.as_of)
    exp = usd_exposure_vector(snap)
    exp = exp[exp.abs() > 1.0]
    rets = vr.usd_returns(w.market, list(exp.index), w.as_of, 250)
    liq = liquidity_table(snap, w.market, w.as_of)
    conc = concentration(snap)
    return {
        "net_delta_usd": float(snap.delta_usd.sum()),
        "gross_notional_usd": float((snap.cash_usd.abs() + snap.fut_usd.abs()).sum()),
        "var_99_1d_usd": vr.var_from_pnl(vr.hist_pnl(exp, rets), 0.99),
        "single_name_pct_adv": float(liq.pct_adv.max()) if len(liq) else 0.0,
        "days_to_liquidate": float(liq.days_to_liquidate.max()) if len(liq) else 0.0,
        "top5_concentration": conc["top5"],
    }


def monitor() -> None:
    w = get_world()
    base = _metrics(w)
    scale = st.slider(
        "What-if: scale every metric by",
        0.25,
        3.0,
        1.0,
        0.05,
        key=P + "scale",
        help="Shows how statuses change as risk grows.",
    )
    rows = check_limits({k: v * scale for k, v in base.items()})
    df = pd.DataFrame(
        [
            {
                "limit": r.name,
                "value": r.value,
                "soft": r.soft,
                "hard": r.hard,
                "utilisation": r.utilisation,
                "status": ICON[r.status],
            }
            for r in rows
        ]
    ).set_index("limit")
    worst = max((r.status for r in rows), key=["ok", "soft", "hard"].index)
    c.metric_row(
        [
            ("Worst status", ICON[worst], None),
            ("Highest utilisation", f"{max(r.utilisation for r in rows):.0%}", "of the hard limit"),
            ("Limits checked", f"{len(rows)}", None),
        ]
    )
    st.plotly_chart(
        charts.bars(
            list(df.index),
            list(df.utilisation * 100),
            "Utilisation of the hard limit (%)",
            "% of hard limit",
        ),
        use_container_width=True,
    )
    c.blotter(df.round(3), "limit_report", key=P + "dl")
    st.caption(
        "Limits are illustrative (config/desk.yaml). Soft = escalate and explain. Hard = reduce or obtain an approved exception. Status is shown in words, not colour alone."
    )
    c.illustrative_note(config.desk())
    st.markdown(
        "**Breach process:** detect, notify risk and the desk head, explain the cause, decide (reduce, hedge or approved excess), record, follow up on the limit itself."
    )


def cases() -> None:
    items = data_file("case_studies")["conduct"]
    st.markdown(
        "These are compliance cases to **recognise and refuse**, never techniques. Pick one to see its red flags and what to do."
    )
    title = st.selectbox("Case", [i["title"] for i in items], key=P + "case")
    it = next(i for i in items if i["title"] == title)
    st.markdown(f"**What it is.** {it['what']}")
    a, b = st.columns(2)
    a.markdown("**Red flags**\n\n" + "\n".join(f"- {x}" for x in it["red_flags"]))
    b.markdown("**What to do**\n\n" + "\n".join(f"- {x}" for x in it["do"]))
    st.info(
        "If you suspect misconduct: stop, do not tip off, record what you saw and escalate to compliance or the whistleblowing channel. Do not investigate alone."
    )


def controls() -> None:
    s = get_settings()
    st.markdown("**Where each control sits**")
    df = pd.DataFrame(
        [
            (
                "Pre-trade",
                "Limit check, locate check, restricted list, ticket validation",
                "Desk and risk",
            ),
            ("Real time", "Intraday limit monitor, price and order-size alerts", "Desk and risk"),
            (
                "End of day",
                "Price checks, PnL explain, reconciliations",
                "Desk, middle office, product control",
            ),
            (
                "Periodic",
                "Independent price verification, access and documentation reviews",
                "Second and third line",
            ),
        ],
        columns=["Stage", "Controls", "Owner"],
    ).set_index("Stage")
    st.dataframe(df, use_container_width=True)
    if s.advanced:
        st.caption(
            "Three lines of defence: the desk owns risk and controls, risk and compliance oversee them, internal audit tests them independently."
        )


render_module("limits_conduct", monitor, extra_tabs={"Conduct cases": cases, "Controls": controls})

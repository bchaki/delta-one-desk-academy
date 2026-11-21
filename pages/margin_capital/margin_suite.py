"""Margin Calculator Suite: six methods in six tabs."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from core import config
from core.margin import csa, regt
from core.margin import exchange as xc
from core.margin import pb_house as pb
from core.margin import portfolio_margin as pm
from core.margin import simm_lite as sm
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_settings, get_world

P = "mg_"


def _result_metrics(r, label: str = "Net margin") -> list[tuple[str, str, str | None]]:
    return [
        ("Gross", f"{r.gross:,.0f}", None),
        ("Credits / offsets", f"{r.credits:,.0f}", None),
        (label, f"{r.net:,.0f}", None),
    ]


def exchange_tab() -> None:
    w = get_world()
    specs = config.contracts().contracts
    prods = list(config.margin().exchange.scan_range_pct)
    st.markdown(
        "Up to three futures positions. Quantity is signed (+ long). Expiry labels are 'near' and 'far' for calendar matching."
    )
    rows = []
    cols = st.columns(3)
    defaults = [("ES", "near", 10), ("D1US30", "near", -10), ("ES", "far", 0)]
    for i, (dp, de, dq) in enumerate(defaults):
        with cols[i]:
            prod = st.selectbox(f"Product {i + 1}", prods, index=prods.index(dp), key=f"{P}x_p{i}")
            exp = st.selectbox(
                f"Expiry {i + 1}",
                ["near", "far"],
                index=["near", "far"].index(de),
                key=f"{P}x_e{i}",
            )
            qty = st.number_input(
                f"Contracts {i + 1}", value=float(dq), step=1.0, key=f"{P}x_q{i}", format="%.0f"
            )
            spec = specs.get(prod, None)
            mult = spec.multiplier if spec else 50.0
            lvl = 5000.0
            if spec and spec.index_key and spec.index_key in w.market.index_level.columns:
                lvl = float(w.market.index_level[spec.index_key].ffill().iloc[-1])
            if qty:
                rows.append(xc.FuturePos(prod, exp, qty, lvl, mult))
    if not rows:
        st.info("Enter at least one non-zero position.")
        return
    r = xc.span_like_margin(rows)
    c.metric_row(_result_metrics(r))
    det = pd.Series(r.detail).to_frame("USD or local currency")
    st.dataframe(det.round(0), use_container_width=True)
    st.caption(
        "SPAN-like teaching model. Prices are the synthetic index levels at the as-of date; multipliers and scan ranges come from config (illustrative)."
    )
    c.illustrative_note(config.margin())


def otc_tab() -> None:
    s = get_settings()

    def comp(v):
        r = sm.schedule_im(v["gross"], v["net"])
        return Out(
            metrics=_result_metrics(r, "Net schedule IM")
            + [("Net-to-gross ratio", f"{r.detail['ngr']:.2f}", None)],
            formula=(
                r"IM_{net} = IM_{gross}\,(w + (1-w)\,NGR)",
                {"w": "gross weight 0.40", "NGR": "net / gross notional"},
                [
                    rf"{r.gross:,.0f}\times({0.4:.2f} + {0.6:.2f}\times{r.detail['ngr']:.2f}) = {r.net:,.0f}"
                ],
            ),
        )

    st.markdown("**Schedule-based IM**")
    calculator(
        P + "sch_",
        [
            Num("gross", "Gross notional", 100e6, 1.0, None, 10e6, "%.0f"),
            Num("net", "Net notional", 20e6, None, None, 5e6, "%.0f"),
        ],
        comp,
        [
            "Set net equal to gross: no netting benefit.",
            "Set net to zero: IM falls to the gross weight share.",
        ],
        advanced=s.advanced,
    )
    st.markdown("**SIMM-lite equity delta** (sensitivities per 1% move; invented weights)")
    a, b = st.columns(2)
    b1 = a.selectbox("Bucket A", list(range(1, 12)), index=0, key=P + "ba")
    b2 = b.selectbox("Bucket B", list(range(1, 12)), index=1, key=P + "bb")
    s1 = a.text_input("Sensitivities in bucket A (comma-separated)", "100000, -50000", key=P + "sa")
    s2 = b.text_input("Sensitivities in bucket B", "80000", key=P + "sb")
    try:
        sens = {b1: [float(x) for x in s1.split(",") if x.strip()]}
        if b2 != b1:
            sens[b2] = [float(x) for x in s2.split(",") if x.strip()]
        r = sm.equity_delta_margin(sens)
        c.metric_row(_result_metrics(r, "SIMM-lite margin"))
        st.dataframe(pd.Series(r.detail).round(0).to_frame("value"), use_container_width=True)
    except ValueError:
        st.warning("Enter numbers separated by commas.")
    c.illustrative_note(config.simm())


def broker_tab() -> None:
    c1, c2 = st.columns(2)
    lm = c1.number_input(
        "Long market value", 0.0, 1e10, 1_000_000.0, 100_000.0, key=P + "lm", format="%.0f"
    )
    sm_ = c1.number_input(
        "Short market value (absolute)",
        0.0,
        1e10,
        500_000.0,
        100_000.0,
        key=P + "sm",
        format="%.0f",
    )
    ri, rm = regt.regt_requirements(lm, sm_)
    lev = regt.gross_leverage_allowed(lm, sm_)
    with c2:
        c.metric_row(
            [
                ("Reg T initial", f"{ri.net:,.0f}", None),
                ("Maintenance", f"{rm.net:,.0f}", None),
                (
                    "Gross leverage",
                    f"{lev:.1f}x" if lev else "n/a",
                    "gross exposure per unit of initial margin",
                ),
            ]
        )
    st.markdown(
        "**Portfolio margin** for the same book, with the long in a single name and the short in a broad index"
    )
    pr = pm.portfolio_margin([pm.PMPosition("NAME", lm), pm.PMPosition("INDEX", -sm_, True)])
    c.metric_row(
        _result_metrics(pr, "Portfolio margin")
        + [("Worst scenario", f"{pr.detail['worst_scenario']:+.2f}", "grid point, -1 to +1")]
    )
    st.plotly_chart(
        charts.bars(
            ["Reg T initial", "Portfolio margin"],
            [ri.net, pr.net],
            "Same book, two methods",
            "Margin",
        ),
        use_container_width=True,
    )
    st.caption(
        "Reg T parameters and the grid are illustrative. Portfolio margin recognises offsets, but a single-name long against an index short only partly offsets."
    )
    c.reset_button(P + "br")


def house_tab() -> None:
    eq = st.number_input(
        "Client equity", 1e5, 1e10, 10_000_000.0, 1_000_000.0, key=P + "eq", format="%.0f"
    )
    df = pd.DataFrame(
        [
            {
                "ticker": "X",
                "market_value": 5_000_000.0,
                "price": 50.0,
                "adv_shares": 100_000.0,
                "daily_vol": 0.02,
                "short_interest": 0.05,
            },
            {
                "ticker": "Y",
                "market_value": -2_000_000.0,
                "price": 20.0,
                "adv_shares": 500_000.0,
                "daily_vol": 0.03,
                "short_interest": 0.25,
            },
        ]
    )
    ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=P + "pbed")
    pos = [
        pb.PBPosition(
            str(r.ticker),
            float(r.market_value),
            float(r.price),
            float(r.adv_shares),
            float(r.daily_vol),
            float(r.short_interest),
        )
        for r in ed.itertuples()
        if r.price and r.adv_shares and r.market_value
    ]
    if not pos:
        st.info("Add at least one position with a price and ADV.")
        return
    r = pb.pb_house_margin(pos, eq)
    c.metric_row(
        [
            ("Base", f"{r.base:,.0f}", None),
            ("Add-ons", f"{r.addons:,.0f}", None),
            ("Total house margin", f"{r.total:,.0f}", f"{r.total / eq:.0%} of equity"),
        ]
    )
    st.plotly_chart(
        charts.bars(
            ["Base", "Concentration", "Liquidity", "Directionality", "Squeeze"],
            [r.base, r.concentration, r.liquidity, r.directionality, r.squeeze],
            "House margin by component",
            "Currency units",
        ),
        use_container_width=True,
    )
    st.caption(
        "Add-ons reflect what simple margin misses: a concentrated, one-way or illiquid book. Parameters are illustrative."
    )


def csa_tab() -> None:
    w = get_world()
    m = w.market
    names = [t for t in m.universe.stocks if m.universe.stocks[t].listed_from is None]
    c1, c2, c3 = st.columns(3)
    tk = c1.selectbox("Underlying", names, key=P + "ctk")
    direction = c2.selectbox("Client direction", ["LONG", "SHORT"], key=P + "cdir")
    notional = c3.number_input("Notional", 1e5, 1e10, 10e6, 1e6, key=P + "cn", format="%.0f")
    th = c1.number_input(
        "Threshold (counterparty)", 0.0, 1e9, 0.0, 100_000.0, key=P + "cth", format="%.0f"
    )
    mta = c2.number_input(
        "Minimum transfer amount", 0.0, 1e8, 250_000.0, 50_000.0, key=P + "cm", format="%.0f"
    )
    rnd = c3.number_input("Rounding", 0.0, 1e7, 100_000.0, 50_000.0, key=P + "cr", format="%.0f")
    days = [d for d in m.days if d <= w.as_of][-40:]
    px = np.array([m.price(tk, d) for d in days])
    client_mtm = (1 if direction == "LONG" else -1) * notional * (px / px[0] - 1)
    exposure = -client_mtm  # desk is owed when the client's MTM is negative
    path = csa.call_path(list(exposure), csa.CsaTerms(threshold_cpty=th, mta=mta, rounding=rnd))
    df = pd.DataFrame(
        {
            "exposure": [p.exposure for p in path],
            "required": [p.required for p in path],
            "call": [p.amount for p in path],
        },
        index=days,
    ).round(0)
    held = np.cumsum(df.call.to_numpy())
    st.plotly_chart(
        charts.lines(
            pd.DataFrame({"Desk exposure": df.exposure, "Collateral held": held}, index=days),
            "Exposure and collateral held (client perspective of the swap)",
            "Date",
            "Currency units",
        ),
        use_container_width=True,
    )
    c.metric_row(
        [
            (
                "Calls (+) and returns (-)",
                f"{(df.call != 0).sum()} transfers",
                f"net {df.call.sum():,.0f}",
            ),
            ("Largest call", f"{df.call.max():,.0f}", None),
        ]
    )
    c.blotter(df, "csa_calls", key=P + "dl_csa", height=240)
    st.caption(
        "Positive exposure = the client owes the desk. A positive call means the client posts; negative means the desk returns collateral. Amounts below the MTA are not moved."
    )
    st.markdown("**Dispute:** pay the undisputed amount, then resolve the rest.")
    a, b = st.columns(2)
    own = a.number_input(
        "Our call", value=1_200_000.0, step=100_000.0, key=P + "own", format="%.0f"
    )
    cpt = b.number_input(
        "Counterparty's call", value=900_000.0, step=100_000.0, key=P + "cpt", format="%.0f"
    )
    d = csa.dispute(own, cpt)
    st.write(f"Undisputed {d.undisputed:,.0f}; disputed {d.disputed:,.0f}.")


render_module(
    "margin_suite",
    exchange_tab,
    extra_tabs={
        "OTC initial margin": otc_tab,
        "Reg T and portfolio": broker_tab,
        "PB house margin": house_tab,
        "CSA calls": csa_tab,
    },
)

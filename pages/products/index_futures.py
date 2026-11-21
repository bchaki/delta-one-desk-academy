"""Index Futures & Total Return Futures: the reference module for the page template."""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from core import config
from core.margin.exchange import (
    FuturePos,
    span_like_margin,
    variation_margin_flows,
    vm_funding_cost,
)
from core.pricing import futures as fut
from core.pricing import trf
from core.types import Benchmark
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_settings, get_world

MODULE = "index_futures"
P = "if_"  # session-key prefix for the reset button
INDEXES = {"D1 US 30": ("D1US30", Benchmark.SOFR), "D1 Europe 20": ("D1EU20", Benchmark.ESTR)}


def _selection(m, d: date) -> tuple[str, list[date], date | None]:
    """Selected index and expiry, repaired when the as-of date change makes the stored expiry invalid."""
    index = st.session_state.get(f"{P}index", "D1 US 30")
    exps = m.front_expiries(index, d, 4)
    if st.session_state.get(f"{P}expiry") not in exps:
        st.session_state.pop(f"{P}expiry", None)
    return index, exps, (st.session_state.get(f"{P}expiry") or (exps[0] if exps else None))


def _divs(m, index: str, d: date, expiry: date, scale: float) -> list[tuple[float, float]]:
    return [
        ((e.ex_date - d).days / 365.0, e.amount * scale)
        for e in m.index_dividends_between(index, d, expiry)
    ]


def sandbox() -> None:
    s = get_settings()
    tabs = st.tabs(
        ["Fair value", "Basis convergence", "Implied repo", "Roll cost", "TRF vs price", "Margin"]
    )
    w = get_world()
    m, d = w.market, w.as_of
    index, exps, expiry = _selection(m, d)
    if not exps:
        st.warning(
            "No contract is listed after this as-of date. Pick an earlier date in the sidebar."
        )
        return

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        index = c1.selectbox("Index", list(INDEXES), key=f"{P}index")
        exps = m.front_expiries(index, d, 4)
        if st.session_state.get(f"{P}expiry") not in exps:
            st.session_state.pop(f"{P}expiry", None)
        expiry = c2.selectbox(
            "Expiry", exps, key=f"{P}expiry", format_func=lambda e: e.strftime("%d %b %Y")
        )
        scale = (
            1
            + c3.slider(
                "Dividend forecast change (%)",
                -50,
                20,
                0,
                key=f"{P}divchg",
                help="Scale the dividends forecast to expiry. Try -20% to mimic a cancellation episode.",
            )
            / 100
        )
        spec = config.contracts().contracts[INDEXES[index][0]]
        bench = INDEXES[index][1]
        spot = float(m.index_level.at[pd.Timestamp(d), index])
        on = m.fixing(bench, d)
        r_default = (math.log(1 + on) + 0.0010) * 100
        r = (
            st.number_input(
                "Financing rate, continuously compounded (% a year)",
                value=round(r_default, 3),
                step=0.05,
                format="%.3f",
                key=f"{P}rate",
                help=f"Default = ln(1 + {bench.value}) + 10 bps funding spread on {d}.",
            )
            / 100
        )
        t = (expiry - d).days / 365.0
        divs = _divs(m, index, d, expiry, scale)
        fair = fut.model_forward(spot, r, divs, t)
        market = m.futures_price(index, expiry, d)
        basis = market - spot
        fv_divs = sum(a * math.exp(r * (t - ti)) for ti, a in divs)
        c.metric_row(
            [
                ("Spot (index points)", f"{spot:,.2f}", None),
                ("Fair value", f"{fair:,.2f}", f"{fair - spot:+.2f} basis"),
                ("Market future", f"{market:,.2f}", f"{market - fair:+.2f} vs fair"),
                (
                    "Market basis",
                    f"{basis:+,.2f}",
                    f"{(market - fair) / spot * 1e4:+.1f} bps of spot",
                ),
            ]
        )
        verdict = "rich" if market > fair else "cheap"
        st.write(
            f"The market future is **{abs(market - fair):.2f} points {verdict}** against fair value at this rate. "
            f"Dividends to expiry: {sum(a for _, a in divs):,.2f} points (valued at expiry: {fv_divs:,.2f}). "
            f"One contract = {spec.multiplier:g} {spec.ccy.value} per point, so a point of richness is worth "
            f"{spec.multiplier:g} {spec.ccy.value} per contract."
        )
        c.formula_box(
            r"F = S\,e^{rT} - \sum_i D_i\,e^{r\,(T-t_i)}",
            {
                "S": "spot index level (index points)",
                "r": "financing rate, continuously compounded, per year",
                "T": "years to expiry (ACT/365)",
                "D_i": "dividend in index points",
                "t_i": "years until ex-date",
            },
            steps=[
                rf"S\,e^{{rT}} = {spot:,.2f} \times e^{{{r:.4f} \times {t:.4f}}} = {spot * math.exp(r * t):,.2f}",
                rf"\sum D_i e^{{r(T-t_i)}} = {fv_divs:,.2f}",
                rf"F = {spot * math.exp(r * t):,.2f} - {fv_divs:,.2f} = {fair:,.2f}",
            ],
        )
        c.what_to_try(
            [
                "Cut the dividend forecast by 20%. Fair value rises by roughly the dividends removed, "
                "and a long future gains if the market had priced the old dividends.",
                "Raise the rate by 50 bps and see how much of the basis is financing.",
            ]
        )
        c.reset_button(P)

    with tabs[1]:
        index, exps, expiry = _selection(m, d)
        ser = m.futures[(index, expiry)]
        lvl = m.index_level[index]
        window = 90
        idx = [x for x in ser.index if x <= pd.Timestamp(d)][-window:]
        df = pd.DataFrame({"Futures": ser.loc[idx], "Index": lvl.loc[idx]})
        st.plotly_chart(
            charts.lines(
                df,
                "The gap between the future and the index closes to zero at expiry",
                "Date",
                "Index points",
            ),
            use_container_width=True,
        )
        bas = (df["Futures"] - df["Index"]).rename("Basis (points)")
        st.plotly_chart(
            charts.lines(
                bas.to_frame(), "Basis (future minus index) decays towards zero", "Date", "Points"
            ),
            use_container_width=True,
        )
        c.blotter(df.round(2), "basis_convergence", key=f"{P}dl_basis", height=200)

    with tabs[2]:
        index, exps, expiry = _selection(m, d)
        spot = float(m.index_level.at[pd.Timestamp(d), index])
        market = m.futures_price(index, expiry, d)
        t = (expiry - d).days / 365.0
        days = (expiry - d).days
        divs = _divs(m, index, d, expiry, 1.0)
        px = st.number_input(
            "Futures price (index points)", value=round(market, 2), step=0.5, key=f"{P}ir_px"
        )
        bench = INDEXES[index][1]
        on = m.fixing(bench, d)
        long_fund = on + config.desk().ftp_spread_bps[m.universe.indices[index].ccy] / 1e4
        rebate = on - 0.0015
        fv = sum(a * math.exp(on * (t - ti)) for ti, a in divs)
        if t <= 0:
            st.warning("Expiry is today: implied repo is undefined.")
        else:
            simple = fut.implied_repo_simple(spot, px, fv, max(days, 1), 360)
            try:
                exact = fut.implied_repo(spot, px, divs, t)
            except ValueError:
                exact = float("nan")
            c.metric_row(
                [
                    ("Implied repo (simple, ACT/360)", f"{simple:.3%}", None),
                    ("Implied repo (exact, cc ACT/365)", f"{exact:.3%}", None),
                    (
                        f"Long funding ({bench.value} + FTP)",
                        f"{long_fund:.3%}",
                        f"{(simple - long_fund) * 1e4:+.0f} bps",
                    ),
                    (
                        f"Short rebate ({bench.value} - 15 bps)",
                        f"{rebate:.3%}",
                        f"{(simple - rebate) * 1e4:+.0f} bps",
                    ),
                ]
            )
            costs = config.desk().trading_costs
            band = fut.no_arbitrage_band(
                spot,
                divs,
                t,
                math.log(1 + long_fund),
                math.log(1 + rebate),
                fut.round_trip_cost_bps(costs),
            )
            sig, edge = fut.arb_signal(px, band)
            label = {
                "cash_and_carry": "Rich: cash and carry open (sell future, buy basket)",
                "reverse_cash_and_carry": "Cheap: reverse cash and carry open (buy future, short basket)",
                "none": "Inside the no-arbitrage band: nothing to do",
            }[sig.value]
            st.write(
                f"**{label}.** Band {band.lower:,.2f} to {band.upper:,.2f}; edge {edge:,.2f} points."
            )
            grid = np.linspace(band.lower - 15, band.upper + 15, 60)
            ir = [fut.implied_repo_simple(spot, g, fv, max(days, 1), 360) * 100 for g in grid]
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_scatter(x=grid, y=ir, name="Implied repo (%)")
            fig.add_hline(y=long_fund * 100, line_dash="dash", annotation_text="long funding")
            fig.add_hline(y=rebate * 100, line_dash="dot", annotation_text="short rebate")
            st.plotly_chart(
                charts.style(
                    fig,
                    "Implied repo rises one-for-one with the futures price",
                    "Futures price (index points)",
                    "Implied repo (% a year, ACT/360)",
                ),
                use_container_width=True,
            )
            if s.advanced:
                st.caption(
                    f"Round-trip cost used: {fut.round_trip_cost_bps(costs):.2f} bps of spot "
                    "(stock in and out, futures in). Costs are illustrative config values."
                )
                c.illustrative_note(config.desk())

    with tabs[3]:
        index, exps, expiry = _selection(m, d)
        if len(exps) < 2:
            st.info("Need two listed expiries after the as-of date.")
        else:
            near = st.selectbox(
                "Near", exps[:-1], key=f"{P}rl_near", format_func=lambda e: e.strftime("%d %b %Y")
            )
            far_opts = [e for e in exps if e > near]
            far = st.selectbox(
                "Far", far_opts, key=f"{P}rl_far", format_func=lambda e: e.strftime("%d %b %Y")
            )
            fn, ff = m.futures_price(index, near, d), m.futures_price(index, far, d)
            dt = (far - near).days / 365.0
            spot = float(m.index_level.at[pd.Timestamp(d), index])
            bench = INDEXES[index][1]
            rr = math.log(1 + m.fixing(bench, d)) + 0.001
            tn, tf = (near - d).days / 365.0, (far - d).days / 365.0
            fair_sp = fut.calendar_spread_fair(spot, _divs(m, index, d, far, 1.0), tn, tf, rr)
            qty = st.number_input("Contracts to roll (long)", value=100, step=10, key=f"{P}rl_qty")
            spec = config.contracts().contracts[INDEXES[index][0]]
            cost_bps = fut.roll_cost_bps_per_year(fn, ff, dt)
            rich = fut.roll_richness_bps_per_year(fn, ff, fair_sp, dt)
            c.metric_row(
                [
                    ("Calendar spread (far - near)", f"{ff - fn:+,.2f}", f"fair {fair_sp:+,.2f}"),
                    ("Gross roll cost", f"{cost_bps:,.0f} bps a year", None),
                    (
                        "Richness vs fair",
                        f"{rich:+,.0f} bps a year",
                        "expensive" if rich > 0 else "cheap",
                    ),
                    (
                        "Cash cost of roll",
                        f"{(ff - fn) * qty * spec.multiplier:,.0f} {spec.ccy.value}",
                        None,
                    ),
                ]
            )
            st.caption(
                "Cash cost = (far - near) x contracts x multiplier, in contract currency, paid by a long rolling forward."
            )

    with tabs[4]:
        index, exps, expiry = _selection(m, d)
        bench = INDEXES[index][1]
        on = m.fixing(bench, d)
        spot = float(m.index_level.at[pd.Timestamp(d), index])
        t = max((expiry - d).days, 1) / 365.0
        tau = max((expiry - d).days, 1) / 360.0
        divs = _divs(m, index, d, expiry, 1.0)
        fvd = sum(a * math.exp(on * (t - ti)) for ti, a in divs)
        market = m.futures_price(index, expiry, d)
        spread = st.slider("TRF spread (bps over benchmark)", -20, 120, 40, key=f"{P}trf_spread")
        prem = st.slider(
            "Swap premium over TRF (bps)",
            -10,
            40,
            12,
            key=f"{P}trf_prem",
            help="Balance sheet, credit and bilateral margin the cleared contract does not carry.",
        )
        basis_pts = trf.trf_spread_to_price_basis(spot, spread, on, tau, fvd)
        implied = trf.price_basis_to_trf_spread_bps(spot, market, on, tau, fvd)
        swap = trf.swap_equivalent_spread_bps(spread, prem)
        c.metric_row(
            [
                ("TRF spread -> price basis", f"{basis_pts:+,.2f} points", None),
                (
                    "Market price future implies",
                    f"{implied:+,.1f} bps TRF spread",
                    f"{implied - spread:+.1f} vs input",
                ),
                ("Equivalent swap spread", f"{swap:,.1f} bps", None),
                (
                    f"Funding on 25m ({(expiry - d).days}d, ACT/360)",
                    f"{trf.trf_funding_amount(25e6, on, spread, max((expiry - d).days, 1), 360):,.0f}",
                    None,
                ),
            ]
        )
        st.caption(
            f"Benchmark {bench.value} = {on:.3%} (ACT/360 simple); dividends valued at expiry = {fvd:,.2f} points."
        )

    with tabs[5]:
        index, exps, expiry = _selection(m, d)
        spec = config.contracts().contracts[INDEXES[index][0]]
        qty = st.number_input("Position (contracts, + long)", value=100, step=10, key=f"{P}mg_qty")
        px = m.futures_price(index, expiry, d)
        res = span_like_margin(
            [FuturePos(INDEXES[index][0], expiry.isoformat(), qty, px, spec.multiplier)]
        )
        c.metric_row(
            [
                ("Initial margin (SPAN-like)", f"{res.net:,.0f} {spec.ccy.value}", None),
                ("Notional", f"{abs(qty) * px * spec.multiplier:,.0f} {spec.ccy.value}", None),
                (
                    "Margin / notional",
                    f"{res.net / max(abs(qty) * px * spec.multiplier, 1):.2%}",
                    None,
                ),
            ]
        )
        c.illustrative_note(config.margin())
        ser = m.futures[(index, expiry)]
        hist = ser.loc[: pd.Timestamp(d)].iloc[-11:]
        flows = variation_margin_flows(qty, spec.multiplier, hist.to_numpy())
        bench = INDEXES[index][1]
        cost = vm_funding_cost(flows, m.fixing(bench, d), 360, symmetric=False)
        dfv = pd.DataFrame(
            {
                "date": hist.index[1:],
                "points": np.diff(hist.to_numpy()),
                f"VM ({spec.ccy.value})": flows,
                "cumulative": np.cumsum(flows),
            }
        ).set_index("date")
        st.plotly_chart(
            charts.bars(
                [x.strftime("%d %b") for x in dfv.index],
                list(dfv.iloc[:, 1]),
                "Variation margin: gains are paid in (+), losses paid out (-)",
                f"{spec.ccy.value} per day",
            ),
            use_container_width=True,
        )
        st.caption(
            f"Funding cost of negative balances over the window (asymmetric, ACT/360): {cost:,.0f} {spec.ccy.value}. "
            "Positive = cost to the holder."
        )
        c.blotter(dfv.round(2), "variation_margin", key=f"{P}dl_vm", height=220)


def contract_specs() -> None:
    cfg = config.contracts()
    rows = [
        {
            "Contract": k,
            "Name": v.name,
            "Exchange": v.exchange,
            "Currency": v.ccy.value,
            "Multiplier": v.multiplier,
            "Tick (points)": v.tick,
            "Tick value": v.tick_value,
            "Cycle (months)": ",".join(map(str, v.cycle_months)),
            "Last trading day": v.last_trading_day,
            "Final settlement": v.settlement,
            "Hours": v.hours,
        }
        for k, v in cfg.contracts.items()
    ]
    c.illustrative_note(cfg)
    c.blotter(
        pd.DataFrame(rows).set_index("Contract"), "contract_specs", key=f"{P}dl_specs", height=300
    )
    st.caption(
        "D1US30 and D1EU20 are the fictional synthetic-index contracts used throughout the app."
    )


render_module(MODULE, sandbox, extra_tabs={"Contract specs": contract_specs})

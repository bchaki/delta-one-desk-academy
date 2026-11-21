"""Funding, Balance Sheet & Capital."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import config
from core.financing import balance_sheet as bs
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Choice, Num, Out, calculator
from ui.state import get_settings

P = "fc_"


def sandbox() -> None:
    s = get_settings()
    cfg = config.desk()
    b = cfg.balance_sheet
    t1, t2 = st.tabs(["Capital stack and profitability", "FTP and levers"])
    with t1:

        def comp(v):
            rw = b.counterparty_rw[v["cpty"]]
            sf = (
                b.sa_ccr_index_supervisory_factor
                if v["idx"] == "Index"
                else b.sa_ccr_equity_supervisory_factor
            )
            ead = bs.sa_ccr_ead(v["mtm"], v["coll"], v["n"], sf)
            lev = bs.leverage_exposure_swap_with_hedge(ead, v["n"] * v["hedge"])
            rwa = bs.swap_rwa(ead, rw, v["n"] * v["hedge"], v["hrw"])
            cap = bs.capital_required(lev, rwa, v["lr"] / 100, b.cet1_ratio)
            lev_cap, rwa_cap = v["lr"] / 100 * lev, b.cet1_ratio * rwa
            binding = "leverage ratio" if lev_cap >= rwa_cap else "CET1 on RWA"
            bsc = bs.balance_sheet_charge_bps(lev, v["n"], b.cost_bps_per_year_on_exposure)
            kc = bs.capital_charge_bps(cap, v["n"], b.cost_of_equity)
            revenue = v["n"] * v["spr"] / 1e4
            fund = v["n"] * v["ftp"] / 1e4
            pf = bs.client_profitability(
                revenue, fund, lev * b.cost_bps_per_year_on_exposure / 1e4, cap, b.cost_of_equity
            )
            be = (
                (fund + lev * b.cost_bps_per_year_on_exposure / 1e4 + cap * b.cost_of_equity)
                / v["n"]
                * 1e4
            )
            return Out(
                metrics=[
                    ("EAD", f"{ead:,.0f}", f"supervisory factor {sf:.2f}"),
                    ("Leverage exposure", f"{lev:,.0f}", None),
                    ("RWA", f"{rwa:,.0f}", f"counterparty weight {rw:.2f}"),
                    ("Capital held", f"{cap:,.0f}", f"binding: {binding}"),
                    (
                        "Balance sheet + capital charge",
                        f"{bsc:.1f} + {kc:.1f} bps",
                        "per year on notional",
                    ),
                    (
                        "Return on capital",
                        f"{pf.return_on_capital:.1%}",
                        f"economic profit {pf.economic_profit:+,.0f}",
                    ),
                    (
                        "Spread to cover funding, balance sheet and cost of equity",
                        f"{be:.1f} bps",
                        None,
                    ),
                ],
                figures=[
                    charts.bars(
                        ["Leverage-ratio capital", "CET1 capital on RWA"],
                        [lev_cap, rwa_cap],
                        "The larger capital requirement binds",
                        "Currency units",
                    )
                ],
                formula=(
                    r"EAD = \alpha\,(RC + SF\times N),\quad K = \max(\lambda\,L,\; c\,RWA)",
                    {
                        "alpha": "1.4",
                        "RC": "replacement cost",
                        "SF": "supervisory factor",
                        "lambda": "leverage ratio",
                        "c": "CET1 ratio",
                    },
                    [],
                ),
            )

        calculator(
            P + "cs_",
            [
                Num("n", "Notional", 50e6, 1e5, None, 5e6, "%.0f"),
                Choice("cpty", "Counterparty type", list(b.counterparty_rw), 3),
                Choice("idx", "Underlying", ["Single name", "Index"]),
                Num("mtm", "MTM owed by the client", 1e6, 0.0, None, 100_000.0, "%.0f"),
                Num("coll", "Collateral held", 0.0, 0.0, None, 100_000.0, "%.0f"),
                Num("hedge", "Hedge as a share of notional", 1.0, 0.0, 1.5, 0.1),
                Num("hrw", "Hedge stock risk weight", 0.25, 0.0, 1.0, 0.05),
                Num(
                    "lr", "Leverage ratio target (%)", b.leverage_ratio_target * 100, 0.5, 10.0, 0.5
                ),
                Num("spr", "Client spread (bps over benchmark)", 100.0, 0.0, 500.0, 5.0, "%.0f"),
                Num("ftp", "Funding cost, FTP (bps)", 35.0, 0.0, 200.0, 5.0, "%.0f"),
            ],
            comp,
            [
                "Switch the counterparty to hedge_fund: RWA binds and capital jumps.",
                "Reduce the hedge share to 0.5 to see netting at work.",
            ],
            columns=3,
            advanced=s.advanced,
        )
        c.illustrative_note(cfg)
    with t2:
        df = pd.DataFrame({"FTP spread (bps)": cfg.ftp_spread_bps}).rename_axis("Currency")
        df.index = [str(i) for i in df.index]
        st.markdown("**Funding spreads by currency (illustrative)**")
        st.dataframe(df, use_container_width=True)
        st.markdown("**Levers that cut the cost of a trade**")
        st.markdown(
            "- Netting opposite client trades reduces hedge inventory and leverage exposure.\n"
            "- Internalising shorts avoids external borrow and balance sheet.\n"
            "- Client collateral lowers replacement cost.\n"
            "- Futures hedges use margin rather than balance sheet.\n"
            "- A lower risk-weight counterparty needs less capital under RWA.\n"
            "- A shorter tenor uses capital for less time."
        )
        c.reset_button(P)


render_module("funding_capital", sandbox)

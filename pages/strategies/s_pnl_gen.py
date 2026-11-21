"""Capstone: PnL generation, a year of desk revenue by source, tier and sub-book."""

from __future__ import annotations

import streamlit as st

from core import config
from core.pnl.explain import ledgers
from core.strategies import pnl_gen as pg
from ui import charts
from ui import components as c
from ui.module_page import render_module
from ui.state import get_world
from ui.strategy_kit import Risk, decomposition, risk_buttons

P = "spg_"


@st.cache_data(show_spinner=False)
def _clean(seed: int, as_of: str):
    w = get_world()
    return ledgers(w.book, w.market)[1]


def sandbox() -> None:
    w = get_world()
    m = w.market
    clean = _clean(m.seed, str(w.as_of))
    end = w.as_of
    start = m.days[max(0, m.days.index(end) - 250)]
    st.markdown(
        "**Thesis.** A desk earns from many small sources. Each has a cost: funding, balance sheet and capital. Net contribution after those costs, not gross revenue, tells you whether the business earns its place."
    )
    src = pg.revenue_by_source(clean, start, end)
    sub = pg.revenue_by_subbook(clean, start, end)
    tier = pg.revenue_by_tier(clean, w.book, start, end)
    rev = float(src.sum())
    st.markdown("**Revenue by source (ledger components grouped; USD, last 250 trading days)**")
    st.plotly_chart(
        charts.bars(list(src.index), list(src.values), "Revenue by source", "USD"),
        use_container_width=True,
    )
    a, b = st.columns(2)
    with a:
        st.plotly_chart(
            charts.bars(list(sub.index), list(sub.values), "Revenue by sub-book", "USD"),
            use_container_width=True,
        )
    with b:
        st.plotly_chart(
            charts.bars(
                [f"Tier {t}" for t in tier.index],
                list(tier.values),
                "Revenue by client tier (swap clients)",
                "USD",
            ),
            use_container_width=True,
        )
    st.caption(
        "Sub-books net to the same total: swap and hedge books offset, which is why a single book on its own can look loss-making. The ledger is the clean model; no seeded breaks."
    )
    x, y, z = st.columns(3)
    notional = pg.swap_notional_usd(w.book, m, end)
    lev = x.slider("Balance sheet use (x swap notional)", 0.5, 3.0, 1.5, 0.1, key=P + "lev")
    ftp = y.slider(
        "Funding on hedge stock (FTP, bps)",
        0,
        100,
        int(config.desk().ftp_spread_bps.get("USD", 35)),
        key=P + "ftp",
    )
    budget_scale = z.slider("Budget as % of actual revenue", 50, 150, 100, 5, key=P + "bud")
    d = config.desk().balance_sheet
    nc = pg.net_contribution(
        rev,
        notional,
        float(ftp),
        lev,
        d.cost_bps_per_year_on_exposure,
        d.leverage_ratio_target,
        d.cost_of_equity,
    )
    c.metric_row(
        [
            ("Gross revenue", f"{rev:,.0f}", None),
            (
                "Net contribution",
                f"{nc['net_contribution']:,.0f}",
                f"after funding {nc['funding']:,.0f} and balance sheet {nc['balance_sheet']:,.0f}",
            ),
            (
                "Return on capital",
                f"{nc['return_on_capital']:.1%}",
                f"capital {nc['capital']:,.0f}",
            ),
            ("Economic profit", f"{nc['economic_profit']:,.0f}", None),
        ]
    )
    decomposition(
        {
            "Gross revenue": rev,
            "Funding": -nc["funding"],
            "Balance sheet": -nc["balance_sheet"],
            "Cost of capital": -nc["capital"] * d.cost_of_equity,
        },
        "From revenue to economic profit (USD)",
        "USD",
    )
    budget = src * budget_scale / 100
    bva = pg.budget_vs_actual(src, budget.sample(frac=1, random_state=m.seed))
    st.markdown(
        "**Budget against actual** (budget values shuffled across sources for illustration of a variance table)"
    )
    st.dataframe(bva.round(2), use_container_width=True)
    st.markdown(
        "**Client revenue and risk revenue.** Financing spread, bid/offer, fees and lending are *client revenue*: earned by serving flow. Price and basis moves on inventory are *risk revenue*: earned by holding positions, and the less repeatable of the two. A good desk watches the ratio."
    )
    client_rev = float(
        src.drop(labels=[i for i in src.index if "Basis" in i], errors="ignore").sum()
    )
    c.metric_row(
        [
            ("Client revenue", f"{client_rev:,.0f}", None),
            ("Risk revenue", f"{rev - client_rev:,.0f}", None),
        ]
    )
    st.caption(
        "Synthetic ledger; swap notional is the gross USD value of live swaps at the as-of date. Balance sheet, FTP and capital parameters are illustrative (config/desk.yaml)."
    )

    def funding_up() -> dict[str, str]:
        n2 = pg.net_contribution(
            rev,
            notional,
            float(ftp + 25),
            lev,
            d.cost_bps_per_year_on_exposure,
            d.leverage_ratio_target,
            d.cost_of_equity,
        )
        return {
            "Net contribution now": f"{nc['net_contribution']:,.0f}",
            "With FTP +25 bps": f"{n2['net_contribution']:,.0f}",
        }

    def lose_client() -> dict[str, str]:
        t1 = float(tier.get(1, 0.0))
        return {
            "Revenue of the largest-tier clients": f"{t1:,.0f}",
            "Net contribution without them (costs unchanged)": f"{nc['net_contribution'] - t1:,.0f}",
        }

    def bs_double() -> dict[str, str]:
        n2 = pg.net_contribution(
            rev,
            notional,
            float(ftp),
            lev * 2,
            d.cost_bps_per_year_on_exposure,
            d.leverage_ratio_target,
            d.cost_of_equity,
        )
        return {
            "Net contribution now": f"{nc['net_contribution']:,.0f}",
            "Balance sheet use doubled": f"{n2['net_contribution']:,.0f}",
            "Economic profit": f"{n2['economic_profit']:,.0f}",
        }

    risk_buttons(
        P,
        [
            Risk("Funding +25 bps", "Treasury reprices.", funding_up),
            Risk("Lose the top tier", "The best clients leave.", lose_client),
            Risk("Balance sheet doubles", "Leverage use rises.", bs_double),
        ],
    )
    c.reset_button(P)


render_module("s_pnl_gen", sandbox)

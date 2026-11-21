"""Data Explorer: browse the synthetic universe, market history, book and trades, with filters and downloads."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.pnl.explain import explain_series, ledgers
from ui import charts
from ui import components as c
from ui.module_page import page_setup
from ui.state import get_world

page_setup()
st.title("Data Explorer")
st.markdown(
    "Everything in the academy is generated from one seeded synthetic world: fictional stocks, prices and clients. Browse it here and download any table to run your own analysis."
)
w = get_world()
m = w.market
st.caption(
    f"Seed {m.seed}, as-of {w.as_of.isoformat()}, {len(m.days)} trading days from {m.days[0]}. All names and numbers are fictional."
)
tabs = st.tabs(
    [
        "Universe",
        "Prices",
        "Rates and FX",
        "Futures and dividends",
        "Borrow",
        "Book and trades",
        "Daily PnL explain",
    ]
)

with tabs[0]:
    df = pd.DataFrame(
        [
            {
                "ticker": s.ticker,
                "name": s.name,
                "country": s.country,
                "ccy": s.ccy.value,
                "sector": s.sector,
                "price0": s.price0,
                "free float": s.free_float,
                "ADV": s.adv,
                "beta": s.beta,
                "div yield": s.dividend.annual_yield,
                "borrow tier": s.borrow.tier,
                "borrow fee (bps)": round(s.borrow.fee_bps, 1),
            }
            for s in m.universe.stocks.values()
        ]
    )
    f1, f2 = st.columns(2)
    country = f1.multiselect("Country", sorted(df.country.unique()), key="de_c")
    sector = f2.multiselect("Sector", sorted(df.sector.unique()), key="de_s")
    if country:
        df = df[df.country.isin(country)]
    if sector:
        df = df[df.sector.isin(sector)]
    st.dataframe(df, use_container_width=True, hide_index=True)
    c.download_df(df, "universe", key="de_dl_u")
    st.caption(
        f"{len(m.universe.adrs)} ADRs, {len(m.universe.etfs)} ETFs and 2 indices also exist; see the Prices tab."
    )

with tabs[1]:
    names = (
        list(m.prices.columns)
        + list(m.adr_prices.columns)
        + list(m.etf_prices.columns)
        + list(m.index_level.columns)
    )
    pick = st.multiselect("Series", names, default=names[:2], key="de_px")
    lo, hi = st.select_slider(
        "Date range",
        options=list(m.prices.index),
        value=(m.prices.index[0], m.prices.index[-1]),
        format_func=lambda d: d.strftime("%Y-%m-%d"),
        key="de_rng",
    )
    frames = {
        n: next(
            f[n] for f in (m.prices, m.adr_prices, m.etf_prices, m.index_level) if n in f.columns
        )
        for n in pick
    }
    df = pd.DataFrame(frames).loc[lo:hi]
    if len(df.columns):
        st.plotly_chart(
            charts.lines(df, "Selected series (local currency)", "Date", "Price or level"),
            use_container_width=True,
        )
        c.download_df(df, "prices", key="de_dl_p")

with tabs[2]:
    fx = m.fx
    st.plotly_chart(
        charts.lines(fx / fx.iloc[0], "FX rebased to 1 at the start", "Date", "Rebased"),
        use_container_width=True,
    )
    fixings = pd.DataFrame({b.value: s for b, s in m.fixings.items()})
    st.plotly_chart(
        charts.lines(fixings * 100, "Overnight benchmark fixings (% a year)", "Date", "% a year"),
        use_container_width=True,
    )
    c.download_df(fx.join(fixings.add_prefix("fix_"), how="outer"), "rates_fx", key="de_dl_r")

with tabs[3]:
    idx = st.selectbox("Index", list(m.index_level.columns), key="de_ix")
    exps = sorted(e for (i, e) in m.futures if i == idx)
    ex = st.selectbox("Expiry", exps, key="de_ex")
    s = m.futures[(idx, ex)]
    st.plotly_chart(
        charts.lines(s.to_frame(f"{idx} {ex}"), "Futures price", "Date", "Index points"),
        use_container_width=True,
    )
    c.download_df(s.to_frame("price"), "future", key="de_dl_f")
    st.markdown("**Dividend futures by year**")
    st.plotly_chart(
        charts.lines(
            pd.DataFrame({f"Dec-{y}": v for y, v in m.div_futures.items()}),
            "Dividend futures",
            "Date",
            "Index dividend points",
        ),
        use_container_width=True,
    )

with tabs[4]:
    tk = st.multiselect(
        "Stocks",
        list(m.borrow_fee_bps.columns),
        default=list(m.borrow_fee_bps.columns)[:3],
        key="de_bt",
    )
    if tk:
        st.plotly_chart(
            charts.lines(m.borrow_fee_bps[tk], "Borrow fee (bps a year)", "Date", "bps"),
            use_container_width=True,
        )
        st.plotly_chart(
            charts.lines(m.utilisation[tk], "Utilisation", "Date", "Share lent"),
            use_container_width=True,
        )
    st.markdown("**Recalls**")
    rc = pd.DataFrame(
        [{"date": r.date, "ticker": r.ticker, "share recalled": r.pct} for r in m.recalls]
    )
    st.dataframe(rc, use_container_width=True, hide_index=True)

with tabs[5]:
    b = w.book
    rows = [
        {
            "trade_id": t.trade_id,
            "product": t.product,
            "book": t.book,
            "counterparty": t.counterparty_id,
            "trade_date": t.trade_date,
            "status": t.status,
            "underlying": getattr(t, "underlying", ""),
            "direction": getattr(t, "direction", ""),
        }
        for t in b.trades
    ]
    df = pd.DataFrame(rows)
    f1, f2 = st.columns(2)
    prod = f1.multiselect("Product", sorted(df["product"].unique()), key="de_pr")
    cp = f2.multiselect("Counterparty", sorted(df.counterparty.dropna().unique()), key="de_cp")
    if prod:
        df = df[df["product"].isin(prod)]
    if cp:
        df = df[df.counterparty.isin(cp)]
    st.dataframe(df, use_container_width=True, hide_index=True)
    c.download_df(df, "trades", key="de_dl_t")
    st.markdown("**Clients**")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "id": x.id,
                    "name": x.name,
                    "type": x.type,
                    "tier": x.tier,
                    "margin method": x.margin_method,
                }
                for x in b.clients.values()
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

with tabs[6]:
    booked, clean = ledgers(w.book, m)
    ex = explain_series(booked, clean)
    n = st.slider("Last N trading days", 20, 250, 60, key="de_n")
    view = ex.tail(n)
    st.plotly_chart(
        charts.lines(
            view[["total", "unexplained"]], "Booked PnL and unexplained (USD)", "Date", "USD"
        ),
        use_container_width=True,
    )
    st.dataframe(view.round(0), use_container_width=True)
    c.download_df(view, "pnl_explain", key="de_dl_x")
    st.caption(
        "Total is the booked ledger; components are the clean model; unexplained is the residual and contains the seeded breaks."
    )

"""Market conventions and regulation reference, straight from config with as-of dates and verify flags."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import config
from ui import components as c
from ui.module_page import page_setup

page_setup()
st.title("Market Conventions & Regulation")
st.markdown(
    "Reference tables for the markets in the academy. Everything comes from `config/*.yaml`, with an as-of date and a verify flag. **Illustrative: verify against the official source before relying on any figure.**"
)
t1, t2, t3, t4 = st.tabs(
    ["Markets", "Benchmarks and day counts", "Withholding tax", "Regulation tracker"]
)
conv = config.conventions()
with t1:
    rows = [
        {
            "Market": m.name,
            "Currency": m.ccy.value,
            "Benchmark": m.benchmark.value,
            "Settlement": f"T+{m.settlement_days}",
            "Settlement note": m.settlement_note,
            "Hours": m.hours,
            "Opening auction": m.open_auction,
            "Closing auction": m.close_auction,
            "Tick regime": m.tick_regime,
            "Transaction tax (bps)": m.transaction_tax_bps,
            "Tax note": m.transaction_tax_note,
        }
        for m in conv.markets.values()
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    c.download_df(df, "market_conventions", key="cr_dl_mkt")
    c.illustrative_note(conv)
with t2:
    df = pd.DataFrame(
        [
            {
                "Benchmark": b.value,
                "Currency": v.ccy.value,
                "Name": v.name,
                "Day count": v.day_count.value,
            }
            for b, v in conv.benchmarks.items()
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown(
        "Quote every rate with its day count and compounding. USD and EUR overnight benchmarks accrue on ACT/360; sterling and yen on ACT/365F; the Swiss benchmark on ACT/360. LIBOR is discontinued and appears only as history."
    )
    c.illustrative_note(conv)
with t3:
    wh = config.withholding()
    df = pd.DataFrame(
        [
            {
                "Market": k,
                "Statutory (%)": v.statutory_pct,
                "Treaty (%)": v.treaty_pct,
                "Note": v.note,
            }
            for k, v in wh.rates.items()
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    c.illustrative_note(wh)
with t4:
    reg = config.regulation()
    q = st.text_input("Filter rules", key="cr_q").strip().lower()
    for r in reg.rules:
        if q and q not in (r.name + r.summary + r.d1_impact + r.region).lower():
            continue
        with st.expander(f"{r.name}  ·  {r.region}" + ("  ·  verify" if r.verify else "")):
            st.markdown(f"**What it is.** {r.summary}")
            st.markdown(f"**What it means for a Delta One desk.** {r.d1_impact}")
            if r.key_dates:
                st.markdown("**Key dates**")
                st.table(
                    pd.DataFrame(
                        [{"Date": k.date.isoformat(), "Event": k.event} for k in r.key_dates]
                    )
                )
            st.caption(
                f"Source: {r.source}. {'Verify current status.' if r.verify else 'Source-checked at the as-of date.'}"
            )
    c.illustrative_note(reg)

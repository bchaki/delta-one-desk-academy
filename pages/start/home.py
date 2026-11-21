"""Home: what the app is, the 4-week path, progress dashboard and the desk at a glance."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.risk.sensitivities import sensitivities, snapshot
from ui import charts
from ui import components as c
from ui.content import registry
from ui.module_page import page_setup
from ui.state import (
    export_progress,
    fmt_money,
    get_settings,
    get_world,
    import_progress,
    is_complete,
    progress,
)

page_setup()
reg = registry()
s = get_settings()

st.title("Delta One Desk Academy")
st.markdown(
    "A 90-day learning platform for a new **trading desk assistant (AVP)** on an equity Delta One desk. "
    "Every number comes from tested Python over a **seeded synthetic market**: fictional stocks, "
    "fictional clients, the same world every time you use the same seed."
)

with st.container(border=True):
    st.subheader("What is Delta One in 30 seconds?")
    st.markdown(
        "A Delta One product moves **one-for-one with its underlying**: delta is about 1 and there is no "
        "optionality. Futures, swaps, ETFs and cash equities all qualify. The desk therefore does not sell a "
        "view. It sells **access** (exposure without owning the shares), **financing** (leverage and shorts, "
        "priced as a spread over a benchmark) and **liquidity** (taking the other side of client flow). It "
        "earns the spread, the carry on its inventory, borrow fees, and the occasional dislocation it can "
        "arbitrage. Your job is to make sure the numbers are right: PnL, risk, bookings, resets and dividends."
    )

st.subheader("Your 4-week path")
WEEKS = {
    1: "Week 1: foundations and products",
    2: "Week 2: borrow, financing, pricing and booking",
    3: "Week 3: risk, PnL and margin",
    4: "Week 4: strategies, the simulator and interview prep",
}
cols = st.columns(4)
for col, (wk, title) in zip(cols, WEEKS.items(), strict=True):
    with col:
        st.markdown(f"**{title}**")
        for m in [m for m in reg.modules if m.week == wk]:
            mark = "✓ " if is_complete(m.id) else ""
            c.module_link(m.id, prefix=mark)

st.subheader("Progress dashboard")
learn = [m for m in reg.modules if m.built and not m.reference]
done = [m for m in learn if is_complete(m.id)]
prog = progress()
scores = {k: v["best"] for k, v in prog["quiz"].items()}
avg = sum(scores.values()) / len(scores) if scores else 0.0
c.metric_row(
    [
        ("Modules complete", f"{len(done)} of {len(learn)}", None),
        ("Quizzes attempted", str(len(scores)), None),
        ("Average best quiz score", f"{avg:.0%}" if scores else "none yet", None),
        (
            "Best simulator score",
            str(prog["sim_best"]) if prog["sim_best"] is not None else "not played",
            None,
        ),
    ]
)
if scores:
    by_sec: dict[str, list[float]] = {}
    for mid, sc in scores.items():
        by_sec.setdefault(reg.get(mid).section, []).append(sc)
    names = {x.id: x.title for x in reg.sections}
    st.plotly_chart(
        charts.bars(
            [names[k] for k in by_sec],
            [100 * sum(v) / len(v) for v in by_sec.values()],
            "Quiz average by section (best attempts)",
            "% correct",
        ),
        use_container_width=True,
    )
    weakest = sorted(scores.items(), key=lambda kv: kv[1])[:3]
    st.markdown(
        "**Weakest topics:** " + ", ".join(f"{reg.get(k).title} ({v:.0%})" for k, v in weakest)
    )
else:
    st.caption("Take a quiz in any module's **Check yourself** tab and the dashboard fills in.")
with st.expander("Export or import progress"):
    st.download_button(
        "Download progress (JSON)",
        export_progress(),
        file_name="d1_academy_progress.json",
        mime="application/json",
    )
    up = st.file_uploader("Import progress", type="json", key="progress_upload")
    if up is not None and st.button("Load file"):
        if import_progress(up.read().decode()):
            st.success("Progress loaded.")
            st.rerun()
        else:
            st.error("That file is not a valid progress export.")

st.subheader("The desk at a glance")
w = get_world()
m = w.market


@st.cache_data(show_spinner=False)
def glance(seed: int, as_of) -> dict:
    wd = get_world()
    snap = snapshot(wd.book, wd.market, wd.as_of)
    sens = sensitivities(wd.book, wd.market, wd.as_of)
    i = wd.market.days.index(wd.as_of)
    top = snap.assign(gross=snap.swap_usd.abs()).sort_values("gross", ascending=False).head(5)
    return {
        "pnl_day": float(wd.booked.total()[i]),
        "pnl_mtd": float(
            sum(
                wd.booked.total()[j]
                for j, d in enumerate(wd.market.days)
                if d.year == wd.as_of.year and d.month == wd.as_of.month and d <= wd.as_of
            )
        ),
        "net_delta": sens["net_delta"],
        "gross": sens["gross"],
        "funded": float(snap.cash_usd.clip(lower=0).sum()),
        "top": top[["key", "swap_usd", "delta_usd"]].round(0).to_dict("records"),
    }


g = glance(s.seed, s.as_of)
c.metric_row(
    [
        (f"Desk PnL, {s.as_of:%d %b %Y}", fmt_money(w, g["pnl_day"]), None),
        ("Desk PnL, month to date", fmt_money(w, g["pnl_mtd"]), None),
        ("Net delta (all products)", fmt_money(w, g["net_delta"]), None),
        ("Financing balance (long inventory funded)", fmt_money(w, g["funded"]).lstrip("+"), None),
    ]
)
top = pd.DataFrame(g["top"]).rename(
    columns={
        "key": "underlying",
        "swap_usd": "client swap exposure (desk side)",
        "delta_usd": "net delta after hedges",
    }
)
if not top.empty:
    for col in top.columns[1:]:
        top[col] = top[col].map(lambda v: fmt_money(w, float(v)))
    st.markdown(
        "**Top 5 underlyings by client swap exposure** (the desk is short what the client is long; "
        "hedges bring net delta close to zero):"
    )
    c.blotter(top.set_index("underlying"), "top_exposures", key="home_top", height=215)
st.caption(
    f"Reporting currency {s.ccy}; amounts are USD converted at the {s.as_of} fixing. "
    "Positive PnL is a gain to the desk."
)

st.divider()
st.markdown(f'<div class="disc">{c.DISCLAIMER}</div>', unsafe_allow_html=True)

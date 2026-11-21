"""Formula sheet and calculator hub: every formula grouped and rendered with st.latex, plus links and quick calculators."""

from __future__ import annotations

import math
from collections import defaultdict

import streamlit as st

from core import rates
from core.pricing import futures as fu
from ui import components as c
from ui.content import data_file, registry
from ui.module_page import page_setup

page_setup()
st.title("Formula Sheet & Calculator Hub")
reg = registry()
F = data_file("formulas")["formulas"]
t1, t2, t3 = st.tabs(["Formula sheet", "Quick calculators", "Calculator hub"])
with t1:
    q = st.text_input("Filter", key="fs_q").strip().lower()
    groups: dict[str, list[dict]] = defaultdict(list)
    for f in F:
        if q and q not in (f["name"] + f["group"] + f["vars"]).lower():
            continue
        groups[f["group"]].append(f)
    md = ["# Delta One Desk Academy: formula sheet", ""]
    for gname, items in groups.items():
        st.subheader(gname)
        md += [f"## {gname}", ""]
        for f in items:
            a, b = st.columns([1, 2])
            a.markdown(f"**{f['name']}**")
            if f["vars"]:
                a.caption(f["vars"])
            with b:
                st.latex(f["latex"])
                if f["module"] in {m.id for m in reg.modules if m.built}:
                    c.module_link(f["module"])
            md += [
                f"- **{f['name']}**: `{f['latex']}`" + (f" ({f['vars']})" if f["vars"] else ""),
                "",
            ]
    st.download_button(
        "Download as Markdown",
        "\n".join(md),
        file_name="formula_sheet.md",
        mime="text/markdown",
        key="fs_dl",
    )
    st.caption("PDF export is not built; print this page from the browser if you need one.")
with t2:
    st.markdown("**Forward price** F = S e^(rT) - dividends grown to expiry")
    a, b, cc, d = st.columns(4)
    S = a.number_input("Spot", 1.0, 1e6, 5000.0, key="fs_s")
    r = b.number_input("Rate, continuous (% a year)", -5.0, 30.0, 4.5, 0.05, key="fs_r") / 100
    T = cc.number_input("T (years, ACT/365)", 0.01, 5.0, 0.25, 0.01, key="fs_t")
    D = d.number_input("Dividend, one payment 0.1 years ahead", 0.0, 1e4, 15.0, key="fs_d")
    st.metric(
        "Fair value", f"{fu.model_forward(S, r, [(0.1, D)] if D and T > 0.1 else [], T):,.2f}"
    )
    st.markdown("**Simple interest accrual**")
    a, b, cc, d = st.columns(4)
    P = a.number_input("Principal", 1.0, 1e12, 10e6, key="fs_p", format="%.0f")
    rr = b.number_input("Rate (% a year)", 0.0, 30.0, 5.0, 0.05, key="fs_rr") / 100
    days = cc.number_input("Days", 1, 3650, 30, key="fs_days")
    basis = d.selectbox("Basis", [360, 365], key="fs_basis")
    st.metric("Interest", f"{rates.simple_interest(P, rr, int(days), int(basis)):,.2f}")
    st.markdown("**Continuous from simple**")
    x = st.number_input("Simple annual rate (%)", 0.0, 50.0, 5.0, 0.05, key="fs_x") / 100
    st.metric("Continuously compounded", f"{math.log(1 + x) * 100:.4f} %")
with t3:
    st.markdown("Every module's sandbox in one place.")
    for sec in reg.sections:
        mods = [m for m in reg.in_section(sec.id) if m.built and not m.reference]
        if not mods:
            continue
        st.markdown(f"**{sec.title}**")
        cols = st.columns(3)
        for i, m in enumerate(mods):
            with cols[i % 3]:
                c.module_link(m.id)

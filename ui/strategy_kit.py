"""Shared pieces of the Strategy Lab sandbox: legs diagram, PnL driver formula, risk scenario buttons."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import streamlit as st

from ui import components as c


@dataclass(frozen=True)
class Risk:
    """A failure mode with a button that runs its scenario and returns label/value pairs to display."""

    name: str
    blurb: str
    run: Callable[[], dict[str, str]]


def legs_diagram(legs: Sequence[tuple[str, str, str]], center: str = "Desk") -> None:
    """Trade legs as a diagram: ``(counterparty, edge label, direction)`` with direction 'out' or 'in'.

    'out' draws an arrow from the desk to the counterparty (the desk pays or sells); 'in' draws it back.
    Colour is never the only cue: each edge carries a text label.
    """
    lines = [
        "digraph G { rankdir=LR; bgcolor=transparent;",
        'node [shape=box, style="rounded", fontname=Helvetica]; edge [fontname=Helvetica, fontsize=10];',
        f'"{center}" [style="rounded,bold"];',
    ]
    for who, label, direction in legs:
        a, b = (center, who) if direction == "out" else (who, center)
        lines.append(f'"{a}" -> "{b}" [label="{label}"];')
    lines.append("}")
    st.graphviz_chart("\n".join(lines))


def risk_buttons(prefix: str, risks: Sequence[Risk]) -> None:
    """One button per failure mode; the result of the last click is kept in session state and shown below."""
    st.markdown("**Risks and failure modes: press a button to trigger the scenario**")
    cols = st.columns(len(risks))
    key = f"{prefix}risk_sel"
    for i, (col, r) in enumerate(zip(cols, risks, strict=True)):
        if col.button(r.name, key=f"{prefix}risk_{i}", use_container_width=True, help=r.blurb):
            st.session_state[key] = i
    sel = st.session_state.get(key)
    if sel is None or sel >= len(risks):
        st.caption("Pick a risk to see its effect on this strategy's numbers.")
        return
    r = risks[sel]
    st.markdown(f"**{r.name}.** {r.blurb}")
    res = r.run()
    c.metric_row([(k, v, None) for k, v in res.items()])


def decomposition(components: dict[str, float], title: str, ytitle: str) -> None:
    """PnL decomposition waterfall: gains in one colour, losses in another, each labelled with its sign."""
    c.pnl_waterfall(components, title, ytitle)

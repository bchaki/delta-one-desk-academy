"""Small helpers that keep sandboxes short: typed inputs, a metric row, optional chart and table."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from ui import components as c


@dataclass(frozen=True)
class Num:
    key: str
    label: str
    default: float
    min: float | None = None
    max: float | None = None
    step: float | None = None
    fmt: str = "%.2f"
    help: str | None = None
    advanced: bool = False  # shown only when the Advanced switch is on (default used otherwise)


@dataclass(frozen=True)
class Choice:
    key: str
    label: str
    options: Sequence[Any]
    index: int = 0
    help: str | None = None
    advanced: bool = False


@dataclass
class Out:
    """What a compute function returns: any of metrics, figure(s), table and a note."""

    metrics: Sequence[tuple[str, str, str | None]] = ()
    figures: Sequence[Any] = ()
    table: pd.DataFrame | None = None
    table_name: str = "table"
    note: str = ""
    formula: tuple[str, dict[str, str], Sequence[str]] | None = None


def read_inputs(
    prefix: str, specs: Sequence[Num | Choice], columns: int = 3, advanced: bool = False
) -> dict[str, Any]:
    vals: dict[str, Any] = {}
    shown = [s for s in specs if advanced or not s.advanced]
    cols = st.columns(min(columns, max(len(shown), 1)))
    i = 0
    for s in specs:
        if s.advanced and not advanced:
            vals[s.key] = s.default if isinstance(s, Num) else s.options[s.index]
            continue
        col = cols[i % len(cols)]
        i += 1
        k = f"{prefix}{s.key}"
        if isinstance(s, Num):
            kw = {
                k_: v
                for k_, v in (("min_value", s.min), ("max_value", s.max), ("step", s.step))
                if v is not None
            }
            vals[s.key] = col.number_input(
                s.label, value=float(s.default), format=s.fmt, key=k, help=s.help, **kw
            )
        else:
            vals[s.key] = col.selectbox(s.label, list(s.options), index=s.index, key=k, help=s.help)
    return vals


def calculator(
    prefix: str,
    specs: Sequence[Num | Choice],
    compute: Callable[[dict[str, Any]], Out],
    what_to_try: Sequence[str] = (),
    columns: int = 3,
    advanced: bool = False,
    defaults_note: str = "",
) -> dict[str, Any]:
    """Render inputs, call ``compute`` and draw its outputs. Returns the input values."""
    vals = read_inputs(prefix, specs, columns, advanced)
    try:
        out = compute(vals)
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        st.warning(f"These inputs can't be evaluated: {e}")
        return vals
    if out.metrics:
        c.metric_row(list(out.metrics))
    if out.note:
        st.markdown(out.note)
    for fig in out.figures:
        st.plotly_chart(fig, use_container_width=True)
    if out.table is not None:
        c.blotter(out.table, out.table_name, key=f"{prefix}dl_{out.table_name}", height=240)
    if out.formula:
        c.formula_box(*out.formula)
    if defaults_note:
        st.caption(defaults_note)
    if what_to_try:
        c.what_to_try(what_to_try)
    c.reset_button(prefix)
    return vals

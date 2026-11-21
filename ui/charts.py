"""Plotly chart helpers. Titles state the takeaway; axes carry units; gains carry a + sign."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ui.theme import GAIN, LOSS, PALETTE


def style(fig: go.Figure, title: str, xtitle: str = "", ytitle: str = "") -> go.Figure:
    fig.update_layout(title={"text": title, "x": 0.0, "font": {"size": 15}}, height=380)
    fig.update_xaxes(title=xtitle)
    fig.update_yaxes(title=ytitle)
    return fig


def lines(
    df: pd.DataFrame, title: str, xtitle: str, ytitle: str, dash: dict[str, str] | None = None
) -> go.Figure:
    """One line per column of ``df`` (index on x). Distinct colours plus optional dash styles."""
    fig = go.Figure()
    for i, c in enumerate(df.columns):
        fig.add_scatter(
            x=df.index,
            y=df[c],
            name=str(c),
            mode="lines",
            line={"color": PALETTE[i % len(PALETTE)], "dash": (dash or {}).get(c, "solid")},
        )
    return style(fig, title, xtitle, ytitle)


def waterfall(
    components: dict[str, float], title: str, ytitle: str = "USD", total_label: str = "Total"
) -> go.Figure:
    """Waterfall with +/- text labels (blue for gains, orange for losses, never colour alone)."""
    names = list(components) + [total_label]
    vals = list(components.values())
    fig = go.Figure(
        go.Waterfall(
            x=names,
            y=[*vals, 0.0],
            measure=["relative"] * len(vals) + ["total"],
            text=[f"{v:+,.0f}" for v in vals] + [f"{sum(vals):+,.0f}"],
            textposition="outside",
            increasing={"marker": {"color": GAIN}},
            decreasing={"marker": {"color": LOSS}},
            totals={"marker": {"color": PALETTE[7]}},
            connector={"line": {"color": "#888"}},
        )
    )
    return style(fig, title, "", ytitle)


def bars(labels: list[str], values: list[float], title: str, ytitle: str) -> go.Figure:
    colors = [GAIN if v >= 0 else LOSS for v in values]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker={"color": colors},
            text=[f"{v:+,.0f}" for v in values],
            textposition="outside",
        )
    )
    return style(fig, title, "", ytitle)

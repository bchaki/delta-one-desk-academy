"""Theme: CSS layer, colour-blind-safe palette and the Plotly template."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Okabe-Ito: distinguishable under the common forms of colour blindness.
PALETTE = ["#56B4E9", "#E69F00", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#999999"]
GAIN = "#56B4E9"  # blue = gain (always paired with a + sign)
LOSS = "#E69F00"  # orange = loss (always paired with a - sign)
ACCENT = "#4F9DFF"

_CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
code, .mono, [data-testid="stMetricValue"] {font-family: ui-monospace, SFMono-Regular, Menlo, monospace;}
.card {border: 1px solid rgba(128,128,128,.35); border-radius: 10px; padding: .9rem 1.1rem; margin: .4rem 0 .8rem 0;}
.card h4 {margin: 0 0 .35rem 0;}
.pill {display:inline-block; padding: 1px 9px; border-radius: 999px; border: 1px solid rgba(128,128,128,.5); font-size: .78rem; margin-right: .35rem;}
abbr.g {text-decoration: underline dotted; cursor: help;}
.kv {display:grid; grid-template-columns: 40% 60%; gap: .25rem .8rem; font-size: .93rem;}
.kv div:nth-child(odd) {opacity: .75;}
.disc {font-size: .78rem; opacity: .7;}
</style>
"""


def _template() -> go.layout.Template:
    return go.layout.Template(
        layout=go.Layout(
            colorway=PALETTE,
            font={"family": "ui-monospace, Menlo, monospace", "size": 12},
            margin={"l": 60, "r": 20, "t": 60, "b": 50},
            hovermode="x unified",
            legend={"orientation": "h", "y": -0.2},
        )
    )


def apply_theme() -> None:
    """Inject CSS and register the Plotly template (idempotent)."""
    pio.templates["d1"] = _template()
    pio.templates.default = "plotly_dark+d1"
    st.markdown(_CSS, unsafe_allow_html=True)

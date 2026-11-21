"""Automation Corner: ten short, runnable snippets that use the app's core library on the synthetic data."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import streamlit as st

from ui import components as c
from ui.content import CONTENT
from ui.module_page import page_setup
from ui.state import get_world

SNIPPETS = sorted((CONTENT / "snippets").glob("*.py"))

page_setup()
st.title("Automation Corner")
st.markdown(
    "TDAs automate the daily checks. These ten snippets use the same `core` library and the same synthetic world as the app. "
    "Run one here, download it, then adapt it. From a terminal, run any of them from the repo root: "
    "`uv run python content/snippets/<name>.py`."
)


def load(path: Path):
    spec = importlib.util.spec_from_file_location(f"snippet_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


names = [p.stem.replace("_", " ").capitalize() for p in SNIPPETS]
pick = st.selectbox("Snippet", range(len(SNIPPETS)), format_func=lambda i: names[i], key="au_pick")
path = SNIPPETS[pick]
src = path.read_text()
doc = (src.split('"""')[1] if '"""' in src else "").strip()
st.markdown(f"**{names[pick]}**")
st.markdown(doc.replace("\n", "  \n"))
st.code(src, language="python")
a, b = st.columns(2)
a.download_button(
    "Download snippet", src, file_name=path.name, mime="text/x-python", key=f"au_dl_{path.stem}"
)
if b.button("Run on the synthetic world", key=f"au_run_{path.stem}", type="primary"):
    df = load(path).run(get_world())
    st.dataframe(df, use_container_width=True)
    c.download_df(df, path.stem, key=f"au_dlr_{path.stem}")
st.caption(
    "Fictional data. The snippets are teaching examples: check any logic against your desk's own definitions before relying on it."
)

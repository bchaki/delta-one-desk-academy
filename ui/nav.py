"""Navigation built from the module registry: only ``built: true`` pages appear."""

from __future__ import annotations

import streamlit as st

from ui.content import registry


def build_pages() -> dict[str, list[st.Page]]:
    reg = registry()
    out: dict[str, list[st.Page]] = {}
    for sec in reg.sections:
        pages = [
            st.Page(
                m.page_path, title=m.title, icon=m.icon, url_path=m.id, default=(m.id == "home")
            )
            for m in reg.in_section(sec.id)
            if m.built
        ]
        if pages:
            out[sec.title] = pages
    return out


def run() -> None:
    st.navigation(build_pages()).run()

"""Glossary: searchable, filterable by category, with formulas, one-line examples and module links."""

from __future__ import annotations

import streamlit as st

from ui import components as c
from ui.content import registry
from ui.glossary import load_glossary
from ui.module_page import page_setup

page_setup()
st.title("Glossary")
st.markdown(
    "Search a term or filter by category. Every entry has a definition; formulas and one-line examples are shown where they exist, with links to the modules that use the term."
)

terms = sorted({t.term: t for t in load_glossary().values()}.values(), key=lambda t: t.term.lower())
cats = sorted({t.category for t in terms})
a, b = st.columns([2, 1])
q = (
    a.text_input("Search", key="gl_q", placeholder="for example: rebate, SIMM, ex-date")
    .strip()
    .lower()
)
chosen = b.multiselect("Category", cats, key="gl_cat")
only_ex = st.toggle("Only terms with a worked example", key="gl_ex")
hits = [
    t
    for t in terms
    if (
        not q
        or q in t.term.lower()
        or q in t.definition.lower()
        or any(q in al.lower() for al in t.aliases)
    )
    and (not chosen or t.category in chosen)
    and (not only_ex or t.example)
]
st.caption(f"{len(hits)} of {len(terms)} terms")
reg = registry()
for t in hits:
    with st.expander(f"{t.term}  ·  {t.category}"):
        st.markdown(t.definition)
        if t.aliases:
            st.caption("Also: " + ", ".join(t.aliases))
        if t.formula:
            st.code(t.formula, language=None)
        if t.example:
            st.markdown(f"**Example.** {t.example}")
        mods = [m for m in t.modules if any(x.id == m for x in reg.modules)]
        if mods:
            cols = st.columns(min(len(mods), 4))
            for i, m in enumerate(mods):
                with cols[i % len(cols)]:
                    c.module_link(m)

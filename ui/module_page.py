"""The page template: header, five tabs, footer. Every module page calls ``render_module``."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from ui import components as c
from ui.content import check_example, examples, lesson_sections, registry, run_example
from ui.state import get_settings, init_state, sidebar_controls
from ui.theme import apply_theme


def page_setup() -> None:
    """Theme, state defaults and global sidebar. Call at the top of every page."""
    init_state()
    apply_theme()
    sidebar_controls()


def header(module_id: str) -> None:
    m = registry().get(module_id)
    reg = registry()
    st.title(m.title)
    st.markdown(m.purpose)
    st.markdown(
        f"<span class='pill'>~{m.minutes} min</span><span class='pill'>difficulty {c.stars(m.difficulty or 1)}</span>",
        unsafe_allow_html=True,
    )
    if m.prereqs:
        parts = []
        for p in m.prereqs:
            pm = reg.get(p)
            parts.append(pm.title)
        st.caption("Prerequisites: " + " · ".join(parts))
    with st.expander("Learning objectives", expanded=False):
        st.markdown("\n".join(f"- {o}" for o in m.objectives))


def worked_example_tab(module_id: str) -> None:
    c.lesson(module_id, "Worked example")
    exs = examples(module_id)
    if not exs:
        return
    rows = []
    for k, ex in exs.items():
        ok = check_example(ex)
        res = run_example(ex)
        rows.append(
            {
                "example": k,
                "function": ex["fn"].replace("core.", ""),
                "result": _fmt(res),
                "stored expectation": _fmt(ex["expected"]),
                "matches core": "yes" if ok else "NO",
            }
        )
    st.markdown(
        "**Every number above is recomputed live from `core` and compared with the stored value.**"
    )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _fmt(x) -> str:
    if isinstance(x, dict):
        return ", ".join(f"{k}={_fmt(v)}" for k, v in x.items())
    if isinstance(x, list | tuple):
        return "(" + ", ".join(_fmt(v) for v in x) + ")"
    if isinstance(x, float):
        return f"{x:,.6g}"
    if hasattr(x, "__dataclass_fields__"):
        return ", ".join(f"{k}={_fmt(getattr(x, k))}" for k in x.__dataclass_fields__)
    return str(x)


def render_module(
    module_id: str,
    sandbox: Callable[[], None],
    extra_tabs: dict[str, Callable[[], None]] | None = None,
) -> None:
    """Render a module page. ``sandbox`` draws the Sandbox tab; ``extra_tabs`` adds more after it."""
    page_setup()
    header(module_id)
    names = [
        "Learn",
        "Worked example",
        "Sandbox",
        *(extra_tabs or {}),
        "Desk reality",
        "Check yourself",
    ]
    tabs = st.tabs(names)
    tab = dict(zip(names, tabs, strict=True))
    with tab["Learn"]:
        c.lesson(module_id, "Learn")
    with tab["Worked example"]:
        worked_example_tab(module_id)
    with tab["Sandbox"]:
        _run_fragment(sandbox)
    for name, fn in (extra_tabs or {}).items():
        with tab[name]:
            _run_fragment(fn)
    with tab["Desk reality"]:
        c.lesson(module_id, "Desk reality")
    with tab["Check yourself"]:
        c.quiz_block(module_id)
    c.mark_complete(module_id)
    c.footer(module_id)


def _run_fragment(fn: Callable[[], None]) -> None:
    @st.fragment
    def frag() -> None:
        fn()

    frag()


__all__ = ["render_module", "page_setup", "get_settings", "lesson_sections"]

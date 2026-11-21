"""Reusable building blocks for every module page."""

from __future__ import annotations

import html
from collections.abc import Sequence
from datetime import date

import pandas as pd
import streamlit as st

from core.booking.models import Cashflow
from ui import charts
from ui.content import registry, render_lesson_md
from ui.glossary import lookup, render_terms
from ui.quiz import grade, load_quiz, summarise
from ui.state import get_settings, is_complete, record_quiz, set_complete

DISCLAIMER = (
    "Educational use only. All stocks, prices and clients are fictional and the market is simulated. "
    "Illustrative parameters are for teaching and must be verified against the official source. "
    "Nothing here is investment, legal, tax or regulatory advice."
)


def module_link(module_id: str, label: str | None = None, prefix: str = "") -> None:
    """Page link for a built module. Falls back to plain text when the page is run outside
    ``st.navigation`` (for example in a single-page test)."""
    from streamlit.errors import StreamlitPageNotFoundError

    m = registry().get(module_id)
    text = f"{prefix}{label or m.title}"
    if not m.built:
        st.caption(f"{text} (not built yet)")
        return
    try:
        st.page_link(m.page_path, label=text, icon=m.icon)
    except StreamlitPageNotFoundError:
        st.markdown(f"{m.icon} {text}")


def concept_card(title: str, body: str) -> None:
    st.markdown(
        f'<div class="card"><h4>{html.escape(title)}</h4>{render_terms(body)}</div>',
        unsafe_allow_html=True,
    )


def formula_box(latex: str, variables: dict[str, str], steps: Sequence[str] | None = None) -> None:
    """Formula with a variable legend (name -> meaning and units). With "Show the math" on, the
    numeric substitution steps (LaTeX strings) are shown line by line."""
    st.latex(latex)
    with st.expander("Variables and units", expanded=False):
        st.markdown("\n".join(f"- `{k}`: {v}" for k, v in variables.items()))
    if steps and get_settings().show_math:
        st.markdown("**Step by step with your numbers**")
        for s in steps:
            st.latex(s)


def desk_reality(text: str) -> None:
    st.info(render_terms(text), icon=":material/domain:")


def pitfall(text: str) -> None:
    st.warning(render_terms(text), icon=":material/error:")


def rule_of_thumb(text: str) -> None:
    st.success(render_terms(text), icon=":material/lightbulb:")


def regulatory_note(text: str, verify: bool = True) -> None:
    suffix = " *Illustrative, verify against the official source.*" if verify else ""
    st.error(render_terms(text) + suffix, icon=":material/gavel:")


def illustrative_note(cfg) -> None:
    """Label for config-driven parameters: as-of date, source and verify flag."""
    flag = "Illustrative, verify against the official source" if cfg.verify else "Source-checked"
    st.caption(f"{flag}. As of {cfg.as_of}. Source: {cfg.source}")


def metric_row(items: Sequence[tuple[str, str, str | None]]) -> None:
    """KPI tiles: (label, value, delta or None)."""
    cols = st.columns(len(items))
    for c, (label, value, delta) in zip(cols, items, strict=True):
        c.metric(label, value, delta)


def term_sheet(rows: dict[str, str], title: str | None = None) -> None:
    """Two-column key/value card."""
    body = "".join(
        f"<div>{html.escape(k)}</div><div class='mono'>{html.escape(str(v))}</div>"
        for k, v in rows.items()
    )
    head = f"<h4>{html.escape(title)}</h4>" if title else ""
    st.markdown(
        f'<div class="card">{head}<div class="kv">{body}</div></div>', unsafe_allow_html=True
    )


def download_df(df: pd.DataFrame, name: str, key: str) -> None:
    st.download_button(
        "Download CSV", df.to_csv().encode(), file_name=f"{name}.csv", mime="text/csv", key=key
    )


def blotter(df: pd.DataFrame, name: str, key: str, height: int = 320) -> None:
    """A downloadable table."""
    st.dataframe(df, use_container_width=True, height=height)
    download_df(df, name, key)


def pnl_waterfall(components: dict[str, float], title: str, ytitle: str = "USD") -> None:
    st.plotly_chart(charts.waterfall(components, title, ytitle), use_container_width=True)


def cashflow_timeline(
    flows: Sequence[Cashflow], title: str = "Cash flows by date (positive = received by the desk)"
) -> None:
    if not flows:
        st.caption("No cash flows in the window.")
        return
    df = pd.DataFrame(
        [
            {
                "date": f.date,
                "type": f.type,
                "amount": f.amount,
                "ccy": f.ccy.value,
                "from": f.payer.value.lower(),
            }
            for f in flows
        ]
    )
    piv = df.pivot_table(index="date", columns="type", values="amount", aggfunc="sum").fillna(0.0)
    import plotly.graph_objects as go

    fig = go.Figure()
    for i, c in enumerate(piv.columns):
        fig.add_bar(x=piv.index, y=piv[c], name=c, marker={"color": charts.PALETTE[i % 8]})
    fig.update_layout(barmode="relative")
    st.plotly_chart(
        charts.style(fig, title, "Date", "Amount (contract currency)"), use_container_width=True
    )
    blotter(df, "cashflows", key=f"cf_{len(flows)}_{df.date.min()}", height=220)


def trade_ticket(fields: dict[str, object], title: str = "Trade ticket") -> None:
    term_sheet(
        {
            k: (f"{v:,.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))
            for k, v in fields.items()
        },
        title,
    )


def glossary_term(name: str) -> str:
    """Inline tooltip markup for use inside ``st.markdown(..., unsafe_allow_html=True)``."""
    return render_terms(f"[[{name}]]")


def what_to_try(items: Sequence[str]) -> None:
    with st.expander("What to try", expanded=False):
        st.markdown("\n".join(f"- {i}" for i in items))


def reset_button(prefix: str, key: str | None = None) -> None:
    """'Reset to defaults' for a sandbox: clears every session key that starts with ``prefix``."""

    def _clear() -> None:
        for k in [k for k in st.session_state if str(k).startswith(prefix)]:
            del st.session_state[k]

    st.button("Reset to defaults", on_click=_clear, key=key or f"{prefix}reset")


# ---------------------------------------------------------------------------- quiz and completion


def quiz_block(module_id: str) -> None:
    """Multiple-choice and numeric questions with explanations; records the score."""
    qs = load_quiz(module_id)
    st.caption(f"{len(qs)} questions. Answer, then press **Check answers**.")
    responses: dict[str, float | int | None] = {}
    with st.form(f"quiz_{module_id}"):
        for i, q in enumerate(qs, 1):
            st.markdown(
                f"**{i}. {render_terms(q.prompt)}**  \n<span class='pill'>level {q.difficulty}</span>",
                unsafe_allow_html=True,
            )
            key = f"q_{q.id}"
            if q.type == "numeric":
                v = st.number_input(
                    f"Answer{f' ({q.unit})' if q.unit else ''}",
                    value=None,
                    key=key,
                    format="%.4f",
                    label_visibility="visible",
                )
                if v is not None:
                    responses[q.id] = v
            else:
                idx = st.radio(
                    "Choose one",
                    range(len(q.options)),
                    format_func=lambda j, q=q: q.options[j],
                    index=None,
                    key=key,
                    label_visibility="collapsed",
                )
                if idx is not None:
                    responses[q.id] = idx
        submitted = st.form_submit_button("Check answers")
    if submitted:
        correct, missed = summarise(qs, responses)
        answered = len(responses)
        record_quiz(
            module_id, correct, len(qs), missed + [q.id for q in qs if q.id not in responses]
        )
        st.success(f"Score: {correct} of {len(qs)} ({answered} answered).")
        for q in qs:
            if q.id not in responses:
                continue
            ok = grade(q, responses[q.id])
            label = "Correct" if ok else "Not quite"
            ans = (
                f"{q.answer:,.4f}".rstrip("0").rstrip(".")
                if q.type == "numeric"
                else q.options[int(q.answer)]
            )
            st.markdown(
                f"- **{q.id}: {label}.** Answer: {ans}. {render_terms(q.explanation)}",
                unsafe_allow_html=True,
            )


def mark_complete(module_id: str) -> None:
    done = is_complete(module_id)
    label = "Mark as not complete" if done else "Mark module complete"
    if st.button(label, key=f"done_{module_id}", type="secondary" if done else "primary"):
        set_complete(module_id, not done)
        st.rerun()
    if done:
        st.caption("Completed")


def footer(module_id: str, lesson_text: str = "") -> None:
    reg = registry()
    m = reg.get(module_id)
    st.divider()
    rel = [reg.get(r) for r in m.related if any(x.id == r for x in reg.modules)]
    if rel:
        st.markdown("**Related modules**")
        cols = st.columns(min(len(rel), 4))
        for c, r in zip(cols, rel, strict=False):  # noqa: B007
            with c:
                module_link(r.id)
    if m.terms:
        with st.expander("Glossary terms used on this page"):
            for t in m.terms:
                g = lookup(t)
                if g:
                    st.markdown(f"**{g.term}**: {g.definition}")
    st.markdown(f'<div class="disc">{DISCLAIMER}</div>', unsafe_allow_html=True)


def lesson(module_id: str, section: str) -> None:
    from ui.content import lesson_sections

    st.markdown(
        render_lesson_md(module_id, lesson_sections(module_id)[section]), unsafe_allow_html=True
    )


def stars(n: int) -> str:
    return "●" * n + "○" * (3 - n)


def as_of_str(d: date) -> str:
    return d.strftime("%d %b %Y")

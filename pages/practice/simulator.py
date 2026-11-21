"""Desk Simulator: 'A day on the desk'. A session-state machine over nine timed events, scored."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.sim import desk_day as dd
from ui import charts
from ui import components as c
from ui.module_page import page_setup
from ui.state import get_world, progress

K = "sim"

page_setup()
st.title("Desk Simulator: a day on the desk")
st.markdown(
    "Nine timed events, from the 07:00 PnL explain to the 18:00 sign-off. Each run is seeded, so the same seed "
    "gives the same day and a different seed gives a different one. You are scored on **accuracy**, **PnL**, "
    "**risk discipline** and **escalation**, and finish with a debrief that shows what an experienced TDA would have done."
)
w = get_world()
state = st.session_state.get(K)


def start(seed: int) -> None:
    st.session_state[K] = {"seed": seed, "idx": 0, "results": [], "last": None}


if state is None:
    seed = st.number_input("Seed for this day", 0, 99_999, 1, key="sim_seed_in")
    a, b = st.columns(2)
    if a.button("Start the day", type="primary", key="sim_start"):
        start(int(seed))
        st.rerun()
    if b.button("Random seed", key="sim_rand"):
        import random

        start(random.randint(0, 99_999))
        st.rerun()
    best = progress().get("sim_best")
    if best:
        st.caption(f"Your best total score so far: {best['total']:.0f} (seed {best['seed']}).")
    st.stop()

sc = dd.build_scenario(w, state["seed"])
idx = state["idx"]
st.progress(
    min(idx, len(sc.steps)) / len(sc.steps),
    text=f"Seed {state['seed']} · step {min(idx + 1, len(sc.steps))} of {len(sc.steps)}",
)


def render_inputs(step: dd.Step):
    key = f"sim_{state['seed']}_{step.id}"
    if step.kind == "choice":
        i = st.radio(
            "Your decision",
            range(len(step.options)),
            format_func=lambda j: step.options[j],
            index=None,
            key=key,
        )
        return i
    if step.kind in ("multi", "text_multi"):
        return [j for j, o in enumerate(step.options) if st.checkbox(o, key=f"{key}_{j}")]
    if step.kind == "rfq":
        return st.number_input(
            "Your quote (bps a year over the benchmark, ACT/360)", 0.0, 500.0, 40.0, 0.5, key=key
        )
    est = st.number_input(
        "Estimated buying in days of ADV", 0.0, 1000.0, 1.0, 0.5, key=f"{key}_est"
    )
    act = st.radio(
        "Decision",
        range(len(step.options)),
        format_func=lambda j: step.options[j],
        index=None,
        key=f"{key}_act",
    )
    return None if act is None else (est, act)


if idx < len(sc.steps):
    step = sc.steps[idx]
    st.subheader(f"{step.time}  {step.title}")
    st.markdown(step.prompt)
    if step.facts:
        st.table(pd.Series(step.facts, name="Facts").to_frame())
    last = state["last"]
    if last is None:
        resp = render_inputs(step)
        ready = resp is not None
        if st.button("Submit", key=f"sim_submit_{idx}", disabled=not ready, type="primary"):
            res = dd.score_step(sc, step.id, resp)
            state["results"].append(res)
            state["last"] = res
            st.rerun()
    else:
        st.info(last.feedback)
        if last.pnl:
            st.metric("PnL from this decision (USD, gain to the desk)", f"{last.pnl:+,.0f}")
        if st.button(
            "Next event" if idx + 1 < len(sc.steps) else "Finish the day",
            key=f"sim_next_{idx}",
            type="primary",
        ):
            state["idx"] += 1
            state["last"] = None
            st.rerun()
    st.caption(
        "Parameters are illustrative; the scenario teaches the order of decisions, not market prediction."
    )
    if st.button("Abandon this day", key="sim_abandon"):
        del st.session_state[K]
        st.rerun()
    st.stop()

rep = dd.final_report(state["results"])
best = progress().get("sim_best")
if not best or rep.total > best["total"]:
    progress()["sim_best"] = {"total": rep.total, "seed": state["seed"]}
st.header("Debrief")
c.metric_row(
    [
        ("Total score", f"{rep.total:.0f} / 100", rep.grade),
        ("Day PnL (USD)", f"{rep.pnl:+,.0f}", None),
    ]
    + [(k.capitalize(), f"{v:.0f}", None) for k, v in rep.scores.items()]
)
st.plotly_chart(
    charts.bars(
        [k.capitalize() for k in rep.scores],
        [round(v) for v in rep.scores.values()],
        "Score by category (0 to 100)",
        "Score",
    ),
    use_container_width=True,
)
st.markdown("**What happened and what an experienced TDA would have done**")
for step, res in zip(sc.steps, state["results"], strict=True):
    with st.expander(f"{step.time}  {step.title}"):
        st.markdown(f"**Your result.** {res.feedback}")
        st.markdown(f"**What an experienced TDA does.** {res.ideal}")
        cols = st.columns(max(len(res.modules), 1))
        for col, m in zip(cols, res.modules, strict=False):
            with col:
                c.module_link(m)
ideal = dd.final_report(dd.perfect_run(sc))
st.caption(
    f"The model answers on this seed score {ideal.total:.0f}/100 with a day PnL of {ideal.pnl:+,.0f} USD."
)
if st.button("Start another day", key="sim_again"):
    del st.session_state[K]
    st.rerun()

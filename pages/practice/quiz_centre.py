"""Quiz Centre and interview prep: by module, mixed review, timed mock, spaced repetition, spot the error."""

from __future__ import annotations

import random
import time

import streamlit as st
import yaml

from ui import components as c
from ui.content import CONTENT, registry
from ui.glossary import render_terms
from ui.module_page import page_setup
from ui.quiz import Question, all_questions, grade, load_quiz, spot_questions
from ui.state import progress, record_quiz

page_setup()
st.title("Quiz Centre & Interview Prep")
reg = registry()
qs_all = all_questions()
by_id = {q.id: q for q in qs_all}
st.markdown(
    f"**{len(qs_all)}** questions across **{len({q.module for q in qs_all}) - 1}** modules plus a spot-the-error bank, and **{len(yaml.safe_load((CONTENT / 'interview_questions.yaml').open())['questions'])}** interview questions with model answers."
)


def run_set(
    questions: list[Question], key: str, on_done=None, limit_minutes: float | None = None
) -> None:
    """Render a form for ``questions``, grade on submit and show explanations."""
    t0_key = f"{key}_t0"
    if limit_minutes and t0_key not in st.session_state:
        st.session_state[t0_key] = time.time()
    with st.form(key):
        resp: dict[str, float | int] = {}
        for i, q in enumerate(questions, 1):
            st.markdown(
                f"**{i}. {render_terms(q.prompt)}**  \n<span class='pill'>{q.module} · level {q.difficulty}</span>",
                unsafe_allow_html=True,
            )
            if q.type == "numeric":
                v = st.number_input(
                    f"Answer{f' ({q.unit})' if q.unit else ''}",
                    value=None,
                    key=f"{key}_{q.id}",
                    format="%.4f",
                )
                if v is not None:
                    resp[q.id] = v
            else:
                j = st.radio(
                    "Choose one",
                    range(len(q.options)),
                    format_func=lambda k, q=q: q.options[k],
                    index=None,
                    key=f"{key}_{q.id}",
                    label_visibility="collapsed",
                )
                if j is not None:
                    resp[q.id] = j
        done = st.form_submit_button("Check answers")
    if not done:
        return
    elapsed = (
        (time.time() - st.session_state.get(t0_key, time.time())) / 60 if limit_minutes else None
    )
    right = [q.id for q in questions if q.id in resp and grade(q, resp[q.id])]
    wrong = [q.id for q in questions if q.id not in right]
    st.success(
        f"Score: {len(right)} of {len(questions)}."
        + (
            f" Time: {elapsed:.1f} of {limit_minutes:g} minutes."
            + (" Over time." if elapsed > limit_minutes else "")
            if elapsed is not None
            else ""
        )
    )
    if on_done:
        on_done(right, wrong)
    for q in questions:
        ok = q.id in right
        ans = (
            f"{q.answer:,.4f}".rstrip("0").rstrip(".")
            if q.type == "numeric"
            else q.options[int(q.answer)]
        )
        st.markdown(
            f"- **{q.id}: {'Correct' if ok else 'Not quite'}.** Answer: {ans}. {render_terms(q.explanation)}",
            unsafe_allow_html=True,
        )
    st.session_state.pop(t0_key, None)


def update_missed(right: list[str], wrong: list[str]) -> None:
    """Spaced repetition: correct answers leave the missed queue, wrong ones join it."""
    prog = progress()["quiz"]
    for qid in right + wrong:
        q = by_id[qid]
        if q.module == "spot":
            continue
        rec = prog.setdefault(q.module, {"best": 0.0, "last": 0.0, "attempts": 0, "missed": []})
        if qid in right and qid in rec["missed"]:
            rec["missed"].remove(qid)
        if qid in wrong and qid not in rec["missed"]:
            rec["missed"].append(qid)


tabs = st.tabs(
    [
        "By module",
        "Mixed review",
        "Timed mock test",
        "Spaced repetition",
        "Spot the error",
        "Interview prep",
    ]
)
with tabs[0]:
    mods = [m for m in reg.modules if m.built and (CONTENT / "quizzes" / f"{m.id}.yaml").exists()]
    pick = st.selectbox(
        "Module",
        mods,
        format_func=lambda m: f"{m.title} ({len(load_quiz(m.id))} questions)",
        key="qc_mod",
    )
    if pick:
        run_set(
            list(load_quiz(pick.id)),
            f"qc_m_{pick.id}",
            lambda r, w: (record_quiz(pick.id, len(r), len(r) + len(w), w), update_missed(r, w)),
        )
with tabs[1]:
    n = st.slider("Questions", 5, 30, 10, key="qc_n")
    seed = st.number_input("Shuffle seed", 0, 9999, 1, key="qc_seed")
    pool = [q for q in qs_all if q.module != "spot"]
    sel = random.Random(int(seed)).sample(pool, n)
    run_set(sel, f"qc_mix_{n}_{int(seed)}", update_missed)
with tabs[2]:
    st.markdown(
        "Twenty mixed questions in 30 minutes. The clock starts when this tab first renders a set; the result reports your time."
    )
    sel = random.Random(int(st.number_input("Mock test number", 0, 9999, 1, key="qc_mock"))).sample(
        [q for q in qs_all if q.module != "spot"], 20
    )
    run_set(sel, "qc_mock_form", update_missed, limit_minutes=30)
with tabs[3]:
    missed = [
        qid for rec in progress()["quiz"].values() for qid in rec.get("missed", []) if qid in by_id
    ]
    if not missed:
        st.info(
            "Nothing missed yet. Questions you get wrong in any mode are queued here until you get them right."
        )
    else:
        st.caption(f"{len(missed)} questions in your queue.")
        run_set([by_id[x] for x in missed[:10]], "qc_srs", update_missed)
with tabs[4]:
    st.markdown("Each item contains a mistake. Find it.")
    run_set(list(spot_questions()), "qc_spot")
with tabs[5]:
    IQ = yaml.safe_load((CONTENT / "interview_questions.yaml").open())["questions"]
    cats = sorted({x["category"] for x in IQ})
    cat = st.multiselect("Category", cats, default=cats, key="iq_cat")
    q = st.text_input("Search", key="iq_q").strip().lower()
    show = [
        x
        for x in IQ
        if x["category"] in cat and (not q or q in (x["question"] + x["answer"]).lower())
    ]
    st.caption(
        f"{len(show)} of {len(IQ)} questions. Try to answer aloud before you reveal the model answer."
    )
    for x in show:
        with st.expander(f"{x['id']}  ·  {x['category']}  ·  {x['question']}"):
            st.markdown(f"**Model answer.** {x['answer']}")
            if x["follow_ups"]:
                st.markdown("**Follow-ups:** " + "; ".join(x["follow_ups"]))
            if any(m.id == x["module"] and m.built for m in reg.modules):
                c.module_link(x["module"], "Review the module")

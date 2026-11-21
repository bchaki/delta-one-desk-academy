"""Phase 7 content: interview bank, spot-the-error bank, glossary size, formula sheet, quiz centre."""

import yaml
from streamlit.testing.v1 import AppTest

from ui.content import CONTENT, ROOT, registry
from ui.glossary import load_glossary
from ui.quiz import all_questions, grade, spot_questions

REG_IDS = {m.id for m in registry().modules}


def test_interview_bank():
    qs = yaml.safe_load((CONTENT / "interview_questions.yaml").read_text())["questions"]
    assert len(qs) >= 60
    assert len({q["id"] for q in qs}) == len(qs)
    assert {q["category"] for q in qs} == {"Technical", "Pricing brain-teaser", "Behavioural"}
    for q in qs:
        assert (
            q["question"] and len(q["answer"]) > 15 and q["follow_ups"] and q["module"] in REG_IDS
        )


def test_spot_the_error_bank():
    sq = spot_questions()
    assert len(sq) >= 10
    for q in sq:
        assert (
            q.type == "spot_error"
            and grade(q, q.answer)
            and not grade(q, (q.answer + 1) % len(q.options))
        )


def test_glossary_has_250_terms_with_unique_names():
    names = {t.term for t in load_glossary().values()}
    assert len(names) >= 250


def test_question_bank_size_and_unique_ids():
    qs = all_questions()
    assert len(qs) >= 600
    assert len({q.id for q in qs if q.module != "spot"}) == len(
        [q for q in qs if q.module != "spot"]
    )


def test_formula_sheet_data():
    fs = yaml.safe_load((CONTENT / "formulas.yaml").read_text())["formulas"]
    assert len(fs) >= 50
    for f in fs:
        assert f["name"] and f["latex"] and f["module"] in REG_IDS


def test_quiz_centre_grades_a_module_set(world):
    at = AppTest.from_file(str(ROOT / "pages/practice/quiz_centre.py"), default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    for r in at.radio[:3]:
        r.set_value(0)
    at.run()
    [b for b in at.get("form_submit_button")][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.success


def test_all_practice_pages_registered_and_built():
    pages = [m for m in registry().modules if m.section == "practice"]
    assert len(pages) == 7 and all(m.built for m in pages)

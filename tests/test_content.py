"""Content checks: built modules are complete, tokens and glossary links resolve, configs are labelled."""

import pytest
import yaml

from core import config
from ui.content import CONTENT, lesson_sections, registry, unresolved_tokens, word_count
from ui.glossary import load_glossary, terms_in
from ui.quiz import load_quiz

BUILT = [m for m in registry().modules if m.built and not m.reference]


def test_registry_shape():
    reg = registry()
    ids = [m.id for m in reg.modules]
    assert len(ids) == len(set(ids)) == 48
    assert {m.section for m in reg.modules} <= {s.id for s in reg.sections}
    for m in reg.modules:
        assert set(m.prereqs + m.related) <= set(ids), m.id


@pytest.mark.parametrize("m", BUILT, ids=lambda m: m.id)
def test_built_module_complete(m):
    secs = lesson_sections(m.id)
    assert {"Learn", "Worked example", "Desk reality"} <= set(secs)
    assert word_count(m.id) >= 1000
    assert len(load_quiz(m.id)) >= 15
    assert m.objectives and 3 <= len(m.objectives) <= 5 and m.minutes and m.difficulty and m.purpose
    assert unresolved_tokens(m.id) == []
    assert (m.id + ".py") in {p.name for p in (CONTENT.parent / "pages" / m.section).glob("*.py")}


@pytest.mark.parametrize("m", BUILT, ids=lambda m: m.id)
def test_glossary_links_resolve(m):
    gl = load_glossary()
    text = " ".join(lesson_sections(m.id).values())
    for q in load_quiz(m.id):
        text += f" {q.prompt} {q.explanation}"
    missing = [t for t in terms_in(text) + m.terms if t.lower() not in gl]
    assert not missing


def test_quiz_ids_unique():
    for m in BUILT:
        ids = [q.id for q in load_quiz(m.id)]
        assert len(ids) == len(set(ids))


def test_every_config_has_as_of_source_verify():
    for loader in config.ALL_LOADERS.values():
        cfg = loader()
        assert cfg.as_of and cfg.source and isinstance(cfg.verify, bool)


def test_glossary_entries_wellformed():
    raw = yaml.safe_load((CONTENT / "glossary.yaml").read_text())["terms"]
    names = [t["term"].lower() for t in raw]
    assert len(names) == len(set(names))
    assert all(t["definition"] for t in raw)

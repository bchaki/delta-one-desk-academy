"""Every built page renders without exceptions in Beginner and Advanced mode, within a time budget."""

import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ui.content import ROOT, registry

BUILT = [m for m in registry().modules if m.built]
FIRST_LOAD_BUDGET = 90.0
WARM_BUDGET = 8.0


@pytest.fixture(scope="session", autouse=True)
def _warm(world):
    return world


@pytest.mark.parametrize("module", BUILT, ids=lambda m: m.id)
@pytest.mark.parametrize("advanced", [False, True], ids=["beginner", "advanced"])
def test_page_renders(module, advanced):
    path = str(ROOT / module.page_path)
    assert Path(path).exists(), f"{module.id} is built but {module.page_path} is missing"
    at = AppTest.from_file(path, default_timeout=60)
    at.session_state["s_advanced"] = advanced
    t0 = time.time()
    at.run()
    elapsed = time.time() - t0
    assert not at.exception, [e.value for e in at.exception]
    assert elapsed < WARM_BUDGET, f"{module.id} took {elapsed:.1f}s"
    assert at.title, "page has no title"


def test_full_app_runs_through_navigation():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value == "Delta One Desk Academy"


def test_navigation_lists_only_built_pages(monkeypatch):
    import streamlit as st

    from ui import nav

    class Stub:
        def __init__(self, path, title, **kw):
            self.path, self.title = path, title

    monkeypatch.setattr(st, "Page", Stub)
    pages = nav.build_pages()
    assert {p.title for ps in pages.values() for p in ps} == {m.title for m in BUILT}
    assert all(Path(ROOT / p.path).exists() for ps in pages.values() for p in ps)

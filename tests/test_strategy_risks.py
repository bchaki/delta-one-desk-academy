"""Every risk button on every Strategy Lab page runs its scenario without error and shows results."""

import pytest
from streamlit.testing.v1 import AppTest

from ui.content import ROOT, registry

STRATEGIES = [m for m in registry().modules if m.section == "strategies" and m.built]


@pytest.fixture(scope="session", autouse=True)
def _warm(world):
    return world


def test_all_eleven_strategies_built():
    assert len(STRATEGIES) == 11


@pytest.mark.parametrize("module", STRATEGIES, ids=lambda m: m.id)
def test_risk_buttons(module):
    at = AppTest.from_file(str(ROOT / module.page_path), default_timeout=60)
    at.run()
    assert not at.exception
    buttons = [b for b in at.button if "risk_" in (b.key or "") and "reset" not in (b.key or "")]
    assert len(buttons) >= 3, f"{module.id} has fewer than three risk buttons"
    for i in range(len(buttons)):
        at = AppTest.from_file(str(ROOT / module.page_path), default_timeout=60)
        at.run()
        [b for b in at.button if "risk_" in (b.key or "") and "reset" not in (b.key or "")][
            i
        ].click().run()
        assert not at.exception, (module.id, i, [e.value for e in at.exception])

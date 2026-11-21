"""Play a whole day through the simulator page with AppTest."""

from streamlit.testing.v1 import AppTest

from ui.content import ROOT


def test_full_day_through_page(world):
    at = AppTest.from_file(str(ROOT / "pages/practice/simulator.py"), default_timeout=60)
    at.run()
    assert not at.exception
    [b for b in at.button if b.key == "sim_start"][0].click().run()
    for i in range(9):
        assert not at.exception, [e.value for e in at.exception]
        # answer whatever widgets are present with defaults, then submit
        for r in at.radio:
            r.set_value(0)
        at.run()
        sub = [b for b in at.button if b.key == f"sim_submit_{i}"][0]
        sub.click().run()
        assert not at.exception, [e.value for e in at.exception]
        nxt = [b for b in at.button if b.key == f"sim_next_{i}"][0]
        nxt.click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Debrief" in h.value for h in at.header)
    assert at.session_state["progress"]["sim_best"] is not None

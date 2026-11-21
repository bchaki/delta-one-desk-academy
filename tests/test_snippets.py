"""The ten automation snippets run on the synthetic world and return what they promise."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from ui.content import CONTENT

PATHS = sorted((CONTENT / "snippets").glob("*.py"))


def _load(p: Path):
    spec = importlib.util.spec_from_file_location(f"snip_{p.stem}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_there_are_ten_snippets_each_documented():
    assert len(PATHS) == 10
    for p in PATHS:
        assert '"""' in p.read_text() and "Run from the repo root" in p.read_text()


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_snippet_runs(path, world):
    df = _load(path).run(world)
    assert isinstance(df, pd.DataFrame)
    assert len(df.columns) >= 4


def test_snippet_results_are_sensible(world):
    pnl = _load(CONTENT / "snippets/daily_pnl_explain.py").run(world)
    assert len(pnl) == 5 and pnl["flag"].any()  # the stale-mark break (16 Nov) is flagged
    rec = _load(CONTENT / "snippets/position_reconciliation.py").run(world)
    assert set(rec["kind"]) == {"missing", "extra", "qty_break"}
    calls = _load(CONTENT / "snippets/margin_call_checker.py").run(world)
    assert (calls["call"] >= 0).all() and (calls["call"] % 1 == 0).all()
    lim = _load(CONTENT / "snippets/limit_utilisation.py").run(world)
    assert set(lim["status"]) <= {"ok", "soft", "hard"}
    rst = _load(CONTENT / "snippets/reset_schedule.py").run(world)
    assert (rst["days_until"] >= 1).all()
    div = _load(CONTENT / "snippets/dividend_ex_date_checker.py").run(world)
    assert set(div["status"]) <= {"went ex", "upcoming"}
    fv = _load(CONTENT / "snippets/futures_fair_value_monitor.py").run(world)
    assert set(fv["signal"]) <= {"rich", "cheap", "fair"}
    rc = _load(CONTENT / "snippets/sbl_recall_impact.py").run(world)
    assert (rc["cheapest"] == rc[["reborrow", "buy_in", "internalise"]].idxmin(axis=1)).all()


def test_reconcile_function_directly():
    mod = _load(CONTENT / "snippets/position_reconciliation.py")
    ours = pd.Series({"A": 100.0, "B": 50.0})
    theirs = pd.Series({"A": 100.0, "B": 49.0, "C": 5.0})
    r = mod.reconcile(ours, theirs)
    assert list(r["kind"]) == ["qty_break", "extra"]

"""Reconciliation of two position files: missing, extra and quantity breaks.

Run from the repo root:  uv run python content/snippets/position_reconciliation.py
The demo compares the book's net quantities with a counterparty file that has been altered on
purpose (one missing name, one quantity difference, one extra name) so that the breaks show up.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

import pandas as pd

from core.data.world import build_world
from core.risk.sensitivities import snapshot


def reconcile(ours: pd.Series, theirs: pd.Series, tol: float = 0.5) -> pd.DataFrame:
    """Breaks between two quantity series indexed by ticker. ``kind`` is missing, extra or qty_break."""
    rows = []
    for t in sorted(set(ours.index) | set(theirs.index)):
        a, b = float(ours.get(t, 0.0)), float(theirs.get(t, 0.0))
        if t not in theirs.index:
            rows.append({"ticker": t, "ours": a, "theirs": None, "diff": a, "kind": "missing"})
        elif t not in ours.index:
            rows.append({"ticker": t, "ours": None, "theirs": b, "diff": -b, "kind": "extra"})
        elif abs(a - b) > tol:
            rows.append({"ticker": t, "ours": a, "theirs": b, "diff": a - b, "kind": "qty_break"})
    return pd.DataFrame(rows, columns=["ticker", "ours", "theirs", "diff", "kind"])


def run(world=None) -> pd.DataFrame:
    world = world or build_world(7)
    snap = snapshot(world.book, world.market, world.as_of)
    snap = snap[snap["qty"] != 0]
    ours = pd.Series(snap["qty"].to_numpy(), index=list(snap["key"]))
    theirs = ours.copy()
    theirs = theirs.drop(theirs.index[0])
    theirs.iloc[1] += 500.0
    theirs["stock:ZZZZ"] = 1000.0
    return reconcile(ours, theirs)


if __name__ == "__main__":
    print(run().to_string())

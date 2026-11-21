"""Corporate action impact check: which held names are affected and what the position becomes.

Run from the repo root:  uv run python content/snippets/corporate_action_impact.py
Splits are adjusted automatically (quantity x ratio, price / ratio). Other event kinds are listed
for manual review, because the treatment depends on the terms.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

import pandas as pd

from core.corporate_actions import apply_to_position, split
from core.data.world import build_world
from core.risk.sensitivities import snapshot


def run(world=None) -> pd.DataFrame:
    """Every corporate action in the history, with the current quantity held and the adjusted quantity for splits."""
    world = world or build_world(7)
    m = world.market
    snap = snapshot(world.book, m, world.as_of)
    stocks = snap[snap["kind"] == "stock"]
    held = {k.split(":", 1)[1]: q for k, q in zip(stocks["key"], stocks["qty"], strict=True)}
    rows = []
    for ca in m.corporate_actions:
        q = held.get(ca.ticker, 0.0)
        row = {
            "date": ca.date,
            "ticker": ca.ticker,
            "kind": ca.kind,
            "qty_now": q,
            "held": bool(q),
            "qty_after": None,
            "treatment": "manual review",
        }
        if ca.kind == "split":
            nq, _, _, _ = apply_to_position(q, 1.0, split(float(ca.terms["ratio"])))
            row.update({"qty_after": nq, "treatment": "automatic: qty x ratio"})
        rows.append(row)
    return pd.DataFrame(
        rows, columns=["date", "ticker", "kind", "qty_now", "held", "qty_after", "treatment"]
    )


if __name__ == "__main__":
    print(run().to_string())

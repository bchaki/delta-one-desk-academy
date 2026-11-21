"""SBL recall impact: cost of each response to the most recent recalls on the desk's names.

Run from the repo root:  uv run python content/snippets/sbl_recall_impact.py
Responses: re-borrow at a higher fee, buy in, or internalise (cover from inventory). Assumes
a 20-day horizon, a 1% old fee, a 5% new fee and illustrative buy-in and internal costs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

import pandas as pd

from core.data.world import build_world
from core.financing import sbl


def run(world=None, n: int = 5, default_shares: float = 100_000.0) -> pd.DataFrame:
    """Cost of the three responses for the last ``n`` recalls, and the cheapest."""
    world = world or build_world(7)
    m = world.market
    rows = []
    for r in m.recalls[-n:]:
        px = m.price(r.ticker, r.date)
        shares = default_shares * r.pct
        opts = sbl.recall_options(shares, px, 0.01, 0.05, 20, 360, 0.02, 0.01, 0.005)
        rows.append(
            {
                "date": r.date,
                "ticker": r.ticker,
                "recalled_pct": r.pct,
                "shares": shares,
                **opts,
                "cheapest": min(opts, key=opts.get),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(run().round(0).to_string())

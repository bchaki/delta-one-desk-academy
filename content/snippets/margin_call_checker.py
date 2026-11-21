"""Margin call checker: required collateral per client from swap mark-to-market and CSA terms.

Run from the repo root:  uv run python content/snippets/margin_call_checker.py
Exposure = amount the client owes the desk on its swaps, in USD at the as-of date. Collateral held is
assumed to be zero in this demo, so the call is the full requirement (calls round up, MTA applies).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

import pandas as pd

from core.data.world import build_world
from core.margin.csa import CsaTerms, collateral_call


def run(world=None) -> pd.DataFrame:
    """One row per client with a positive exposure."""
    world = world or build_world(7)
    m, d, b = world.market, world.as_of, world.book
    exposure: dict[str, float] = {}
    for s in b.swaps():
        if s.status != "live" or not s.underlying.startswith("stock:"):
            continue
        tk = s.underlying.split(":", 1)[1]
        sign = 1.0 if s.direction.value == "LONG" else -1.0
        client_pnl = sign * s.shares * (m.price(tk, d) - s.initial_price) * m.fx_usd_per(s.ccy, d)
        exposure[s.counterparty_id] = exposure.get(s.counterparty_id, 0.0) - client_pnl
    rows = []
    for cid, e in exposure.items():
        c = b.clients[cid].csa
        terms = CsaTerms(threshold_cpty=c.threshold_cpty, mta=c.mta, rounding=c.rounding)
        res = collateral_call(max(e, 0.0), 0.0, terms)
        rows.append(
            {
                "client": cid,
                "exposure_usd": max(e, 0.0),
                "required": res.required,
                "call": res.amount,
                "mta": c.mta,
            }
        )
    return (
        pd.DataFrame(rows, columns=["client", "exposure_usd", "required", "call", "mta"])
        .sort_values("call", ascending=False)
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    print(run().round(0).to_string())

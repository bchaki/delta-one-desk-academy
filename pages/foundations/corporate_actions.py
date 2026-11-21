"""Corporate Actions."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import corporate_actions as ca
from ui import components as c
from ui.module_page import render_module
from ui.sandbox_kit import Num, Out, calculator
from ui.state import get_world

P = "ca_"
KINDS = ["Split", "Rights issue", "Spin-off", "Special dividend", "Cash merger", "Stock merger"]


def sandbox() -> None:
    w = get_world()
    m = w.market
    t1, t2 = st.tabs(["Adjustment calculator", "Events in the synthetic market"])
    with t1:
        kind = st.selectbox("Event", KINDS, key=P + "kind")
        specs = {
            "Split": [Num("r", "New shares per old", 2.0, 0.01, 50.0, 0.5)],
            "Rights issue": [
                Num("k", "Subscription price", 40.0, 0.01, None, 1.0),
                Num("r", "New shares per old", 0.25, 0.01, 5.0, 0.05),
            ],
            "Spin-off": [
                Num("v", "Spin-off value per parent share", 12.0, 0.0, None, 1.0),
                Num("r", "New shares per parent share", 0.5, 0.01, 10.0, 0.1),
            ],
            "Special dividend": [Num("a", "Special dividend per share", 5.0, 0.0, None, 0.5)],
            "Cash merger": [Num("o", "Offer price", 31.25, 0.0, None, 0.25)],
            "Stock merger": [
                Num("a", "Acquirer price", 50.0, 0.01, None, 1.0),
                Num("r", "Exchange ratio", 0.5, 0.0, 10.0, 0.05),
                Num("cash", "Cash per share", 5.0, 0.0, None, 0.5),
            ],
        }[kind]
        specs = [
            Num("p", "Price before event", 50.0 if kind != "Spin-off" else 100.0, 0.01, None, 1.0),
            Num("q", "Position (shares)", 10_000.0, 1.0, None, 1000.0, "%.0f"),
            *specs,
        ]

        def comp(v):
            p, q = v["p"], v["q"]
            if kind == "Split":
                adj = ca.split(v["r"])
            elif kind == "Rights issue":
                adj = ca.rights_issue(p, v["k"], v["r"])
            elif kind == "Spin-off":
                adj = ca.spin_off(p, v["v"], v["r"])
            elif kind == "Special dividend":
                adj = ca.special_dividend(p, v["a"])
            elif kind == "Cash merger":
                adj = ca.cash_merger(v["o"])
            else:
                adj = ca.stock_merger(p, v["a"], v["r"], v["cash"])
            nq, npx, cash, nnew = ca.apply_to_position(q, p, adj)
            val_after = nq * npx + cash + nnew * adj.new_asset_price
            before = q * p
            tbl = (
                pd.DataFrame(
                    {
                        "item": [
                            "Quantity",
                            "Price",
                            "Cash received",
                            "New-asset quantity",
                            "Total value",
                        ],
                        "before": [q, p, 0.0, 0.0, before],
                        "after": [nq, npx, cash, nnew, val_after],
                    }
                )
                .set_index("item")
                .round(4)
            )
            note = (
                "Value is preserved."
                if abs(val_after - before) < 1e-6 * max(before, 1)
                else f"Value changes by {val_after - before:+,.2f}: for mergers this is the merger-arb gap (target price vs deal value)."
            )
            return Out(
                metrics=[
                    ("Quantity factor", f"{adj.qty_factor:.4f}", None),
                    ("Price factor", f"{adj.price_factor:.4f}", None),
                    ("Value after - before", f"{val_after - before:+,.2f}", None),
                ],
                table=tbl,
                table_name="ca_adjustment",
                note=note,
            )

        calculator(
            P + kind.replace(" ", "_") + "_",
            specs,
            comp,
            [
                "Try each event and check the value line: only mergers away from deal value change it.",
                "Rights: lower the subscription price and watch TERP fall.",
            ],
        )
    with t2:
        rows = []
        for e in m.corporate_actions:
            before = after = None
            if e.ticker in m.prices.columns and e.date in m.days:
                i = m.days.index(e.date)
                before, after = m.prices[e.ticker].iloc[i - 1], m.prices[e.ticker].iloc[i]
            rows.append(
                {
                    "date": e.date,
                    "event": e.kind,
                    "ticker": e.ticker,
                    "price before": before,
                    "price on date": after,
                    "terms": {
                        k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.terms.items()
                    },
                }
            )
        df = pd.DataFrame(rows)
        st.write(
            "Every corporate action in the synthetic history. Check the price move on the effective date against the adjustment."
        )
        c.blotter(df.astype({"terms": str}), "synthetic_corporate_actions", key=P + "dl_events")
        affected = [
            s
            for s in w.book.swaps()
            if s.underlying.split(":")[-1] in {e.ticker for e in m.corporate_actions}
        ]
        st.caption(
            f"Swaps in the book on affected names: {len(affected)}. The generated book avoids these names so every swap reconciles without an event adjustment."
        )


render_module("corporate_actions", sandbox)

"""Reset schedule report: the next reset date for every live equity swap and days until it falls due.

Run from the repo root:  uv run python content/snippets/reset_schedule.py
Reset dates are the trade date plus k x reset months, rolled to the following trading day.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # run from the repo root

from datetime import timedelta

import pandas as pd

from core.conventions import CalendarName, RollRule, add_months, adjust
from core.data.world import build_world

CAL = {
    "USD": CalendarName.US,
    "EUR": CalendarName.TARGET,
    "GBP": CalendarName.UK,
    "JPY": CalendarName.JAPAN,
    "CHF": CalendarName.TARGET,
}


def run(world=None, horizon_days: int = 45) -> pd.DataFrame:
    """Swaps with a reset in the next ``horizon_days``, soonest first.

    The next reset is the trade date plus k x reset months (smallest k that falls after the as-of
    date), rolled to the following business day in the currency's calendar.
    """
    world = world or build_world(7)
    d = world.as_of
    rows = []
    for s in world.book.swaps():
        if s.status != "live" or not s.notional_reset:
            continue
        k = 1
        while add_months(s.trade_date, k * s.reset_months) <= d:
            k += 1
        nxt = adjust(
            add_months(s.trade_date, k * s.reset_months), RollRule.FOLLOWING, CAL[s.ccy.value]
        )
        if nxt <= d + timedelta(days=horizon_days):
            rows.append(
                {
                    "trade_id": s.trade_id,
                    "client": s.counterparty_id,
                    "underlying": s.underlying,
                    "next_reset": nxt,
                    "days_until": (nxt - d).days,
                    "reset_months": s.reset_months,
                }
            )
    cols = ["trade_id", "client", "underlying", "next_reset", "days_until", "reset_months"]
    return (
        pd.DataFrame(rows, columns=cols)
        .sort_values(["next_reset", "trade_id"])
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    print(run().to_string())

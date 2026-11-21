"""Desk Simulator: 'A day on the desk'. A pure, seeded scenario generator and scorer (no Streamlit).

``build_scenario(world, seed)`` returns nine timed steps. Facts shown to the user are derived from
the seed and the synthetic world; the correct answers and the hidden market level stay in the
scenario's private ``key``. ``score_step`` grades one response and returns points per scoring
category (earned, maximum), a PnL in USD (gain to the desk), feedback and what an experienced TDA
would have done. ``final_report`` turns the step results into 0-100 scores for accuracy, PnL, risk
discipline and escalation. Simplified: single stock per step, closing-style prices, illustrative
parameters from ``config/desk.yaml``; it teaches the sequence of decisions, not market prediction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from core import config
from core.data.world import World
from core.financing import balance_sheet as bs
from core.financing import sbl
from core.margin import csa
from core.pricing import futures as fu
from core.pricing import swaps as sw
from core.pricing.program_trading import sqrt_impact_bps
from core.types import Direction

CATEGORIES = ("accuracy", "pnl", "risk", "escalation")


@dataclass(frozen=True)
class Step:
    id: str
    time: str
    title: str
    kind: str  # choice | multi | numeric_choice | rfq | text_multi
    prompt: str
    facts: dict[str, Any] = field(default_factory=dict)
    options: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class StepResult:
    step_id: str
    points: dict[str, tuple[float, float]]
    pnl: float
    feedback: str
    ideal: str
    modules: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    seed: int
    steps: tuple[Step, ...]
    key: dict[str, Any]


@dataclass(frozen=True)
class Report:
    scores: dict[str, float]
    total: float
    pnl: float
    grade: str


def _pts(**kw: tuple[float, float]) -> dict[str, tuple[float, float]]:
    return dict(kw)


# ---------------------------------------------------------------------------- scenario


def build_scenario(world: World, seed: int) -> Scenario:
    """Nine timed steps for ``seed``; same seed and world give an identical scenario."""
    rng = np.random.default_rng(seed)
    m = world.market
    d = world.as_of
    key: dict[str, Any] = {}
    steps: list[Step] = []
    names = [
        t
        for t, s in m.universe.stocks.items()
        if s.listed_from is None and np.isfinite(m.price(t, d)) and np.isfinite(m.stock_adv(t, d))
    ]

    # 07:00 overnight explain with a seeded break
    br = [b for b in world.book.breaks if b.kind != "wrong_entity"]
    b = br[int(rng.integers(len(br)))]
    kinds = ("missed_dividend", "wrong_fixing", "wrong_spread", "stale_price")
    key["break"] = b.kind
    steps.append(
        Step(
            "pnl_break",
            "07:00",
            "Overnight PnL explain",
            "choice",
            "The explain shows an unexplained amount. Read the clue and pick the most likely cause.",
            {"Unexplained (USD)": f"{b.pnl_impact:+,.0f}", "Trade": b.trade_id, "Clue": b.clue},
            kinds,
            ("pnl_explain", "marks_eod"),
        )
    )

    # 08:00 corporate actions, dividends, resets
    pool = [
        ("Dividend on a swap underlying", 0),
        ("Swap reset due", 0),
        ("Stock split effective", 0),
        ("Dividend, ex-date yesterday (already processed)", -1),
        ("Swap reset due next week", 5),
        ("Rights issue, record date next month", 25),
    ]
    order = list(rng.permutation(len(pool)))
    items = [f"{pool[i][0]} ({names[int(rng.integers(len(names)))]})" for i in order]
    key["due"] = [i for i, k in enumerate(order) if pool[k][1] == 0]
    steps.append(
        Step(
            "ca_checks",
            "08:00",
            "Corporate actions, dividends and resets",
            "multi",
            "Tick the items that need action today. Wrong ticks cost points.",
            {"Date": d.isoformat()},
            tuple(items),
            ("corporate_actions", "booking_lifecycle", "dividends"),
        )
    )

    # 09:00 RFQ
    tk = names[int(rng.integers(len(names)))]
    stock = m.universe.stocks[tk]
    direction = Direction.LONG if rng.random() < 0.6 else Direction.SHORT
    notional = float(rng.choice([10e6, 25e6, 50e6]))
    tenor = float(rng.choice([0.5, 1.0, 2.0]))
    cfg = config.desk()
    ftp = sw.ftp_component_bps(stock.ccy)
    borrow = (
        sw.borrow_component_bps(float(m.borrow_fee_bps[tk].loc[pd.Timestamp(d)]))
        if direction is Direction.SHORT
        else 0.0
    )
    bsc = bs.balance_sheet_charge_bps(
        notional * 1.5, notional, cfg.balance_sheet.cost_bps_per_year_on_exposure
    )
    cap = bs.capital_charge_bps(
        notional * 1.5 * cfg.balance_sheet.leverage_ratio_target,
        notional,
        cfg.balance_sheet.cost_of_equity,
    )
    build = sw.spread_build_up(direction, ftp, borrow, bsc, cap, 3.0, 4.0 / tenor, 0.0)
    cost = build.total_bps
    competitor = cost + float(rng.uniform(2.0, 25.0))
    key["rfq"] = {"cost": cost, "market": competitor, "notional": notional, "tenor": tenor}
    steps.append(
        Step(
            "rfq",
            "09:00",
            "Client RFQ for a swap",
            "rfq",
            "Quote a spread in bps a year over the benchmark. You win if you are at or inside the hidden market level. Selling below cost wins the trade and loses money.",
            {
                "Client": "A tier 2 hedge fund",
                "Underlying": f"{tk} ({stock.ccy.value})",
                "Direction": f"Client {direction.value}",
                "Notional": f"{notional:,.0f}",
                "Tenor": f"{tenor:g} years",
                "Cost build-up (bps)": ", ".join(
                    f"{k} {v:.1f}" for k, v in build.components.items()
                )
                + f" (total {cost:.1f})",
            },
            (),
            ("pricing_lab", "equity_swaps"),
        )
    )

    # 11:00 index rebalance
    tk2 = names[int(rng.integers(len(names)))]
    s2 = m.universe.stocks[tk2]
    px2, adv2 = m.price(tk2, d), m.stock_adv(tk2, d)
    aum = float(rng.choice([2e10, 4e10, 8e10]))
    wgt = float(rng.choice([0.01, 0.015, 0.02]))
    shares = aum * wgt / px2
    days_adv = shares / adv2
    impact = sqrt_impact_bps(cfg.trading_costs.impact_k, s2.daily_vol, shares, adv2)
    crowd = float(rng.choice([1.0, 3.0]))
    realised = float(rng.normal(0.4 * impact, 0.5 * impact))
    key["rebalance"] = {
        "days_adv": days_adv,
        "impact": impact,
        "crowd": crowd,
        "realised": realised,
        "px": px2,
    }
    steps.append(
        Step(
            "rebalance",
            "11:00",
            "Index rebalance announcement",
            "numeric_choice",
            "Estimate the index funds' buying in days of ADV, then decide whether to pre-hedge 5 million.",
            {
                "Stock": tk2,
                "Tracking AUM": f"{aum:,.0f}",
                "New weight": f"{wgt:.2%}",
                "Price": f"{px2:,.2f}",
                "ADV (shares)": f"{adv2:,.0f}",
                "Crowding": "high" if crowd > 1 else "normal",
            },
            ("Pre-hedge 5 million", "Do not pre-hedge"),
            ("s_rebalance", "indices"),
        )
    )

    # 13:00 recall
    shares3 = float(rng.choice([50_000, 100_000, 200_000]))
    px3 = float(rng.choice([20.0, 50.0, 80.0]))
    have_inventory = bool(rng.random() < 0.6)
    newfee = float(rng.choice([0.04, 0.08]))
    opts = sbl.recall_options(shares3, px3, 0.01, newfee, 20, 360, 0.02, 0.01, 0.005)
    feasible = {k: v for k, v in opts.items() if k != "internalise" or have_inventory}
    best = min(feasible, key=feasible.get)
    key["recall"] = {"opts": opts, "best": best, "feasible": feasible}
    steps.append(
        Step(
            "recall",
            "13:00",
            "Recall on a hard-to-borrow name",
            "choice",
            "A lender recalls shares hedging a client short. Choose the response.",
            {
                "Shares": f"{shares3:,.0f}",
                "Price": f"{px3:,.2f}",
                "Old fee": "1.00%",
                "New borrow fee": f"{newfee:.0%}",
                "Horizon": "20 days",
                "Own inventory available": "yes" if have_inventory else "no",
            },
            ("Re-borrow", "Buy in", "Internalise from inventory"),
            ("sbl_ops", "internalisation"),
        )
    )

    # 15:00 margin call dispute
    terms = csa.CsaTerms(threshold_cpty=0.0, mta=250_000.0, rounding=100_000.0)
    exposure = float(rng.choice([3.1e6, 4.6e6, 5.2e6]))
    held = float(rng.choice([2.0e6, 3.0e6]))
    own = csa.collateral_call(exposure, held, terms).amount
    cp_extra = float(rng.choice([200_000.0, 300_000.0, 500_000.0]))
    cp = own + cp_extra
    dsp = csa.dispute(cp, own)
    key["margin"] = {"own": own, "cp": cp, "undisputed": dsp.undisputed, "disputed": dsp.disputed}
    steps.append(
        Step(
            "margin",
            "15:00",
            "Counterparty margin call, disputed amount",
            "choice",
            "The counterparty calls more than your own calculation. What do you do?",
            {
                "Exposure": f"{exposure:,.0f}",
                "Collateral held": f"{held:,.0f}",
                "Our calculation": f"{own:,.0f}",
                "Counterparty's call": f"{cp:,.0f}",
                "Difference": f"{cp - own:,.0f}",
            },
            (
                "Pay the full call",
                "Pay the undisputed amount and open a dispute for the rest, with evidence",
                "Reject the call entirely",
                "Ignore it until tomorrow",
            ),
            ("margin_suite", "pricing_lab"),
        )
    )

    # 16:30 futures rich into the close
    spot = float(rng.choice([4800.0, 5000.0, 5200.0]))
    t = 20 / 365.0
    divs = [(10 / 365.0, 6.0)]
    rf, rebate = 0.045, 0.040
    band = fu.no_arbitrage_band(spot, divs, t, rf, rebate, 3.0)
    outside = rng.random() < 0.6
    if outside:
        fut = (
            band.upper + float(rng.uniform(1.0, 6.0))
            if rng.random() < 0.7
            else band.lower - float(rng.uniform(1.0, 6.0))
        )
    else:
        fut = band.mid + float(rng.uniform(-0.3, 0.3)) * band.width / 2
    sig, edge = fu.arb_signal(fut, band)
    key["arb"] = {"signal": sig.value, "edge": edge, "mult": 50.0, "contracts": 20}
    steps.append(
        Step(
            "arb",
            "16:30",
            "Futures away from fair value into the close",
            "choice",
            "Decide on the arbitrage. 20 contracts, multiplier 50. The band includes 3 bps of costs.",
            {
                "Spot": f"{spot:,.2f}",
                "Future": f"{fut:,.2f}",
                "No-arbitrage band": f"{band.lower:,.2f} to {band.upper:,.2f}",
                "Dividend before expiry": "6.0 points in 10 days",
            },
            ("Sell the future, buy the basket", "Buy the future, short the basket", "No trade"),
            ("s_index_arb", "index_futures"),
        )
    )

    # 17:30 limit breach
    metric = str(rng.choice(["net_delta_usd", "single_name_pct_adv", "gross_notional_usd"]))
    spec = cfg.limits[metric]
    val = spec.hard * float(rng.uniform(1.02, 1.15))
    key["limit"] = metric
    steps.append(
        Step(
            "limit",
            "17:30",
            "Risk run shows a limit breach",
            "choice",
            "Choose how to escalate.",
            {
                "Metric": metric,
                "Value": f"{val:,.2f}",
                "Soft limit": f"{spec.soft:,.2f}",
                "Hard limit": f"{spec.hard:,.2f}",
            },
            (
                "Hedge quietly and say nothing",
                "Tell the head of desk and risk now with size, cause and a plan, and log it",
                "Wait until the end of day report",
                "Ask risk to raise the limit",
            ),
            ("limits_conduct",),
        )
    )

    # 18:00 sign-off commentary
    good = [
        f"Unexplained traced to {b.kind.replace('_', ' ')} on {b.trade_id}; booking fix requested.",
        "Open breaks and their size are stated; the PnL is not final until they are fixed.",
        "Margin dispute: undisputed amount paid; disputed amount escalated with evidence.",
        "Limit breach reported to the head of desk and risk with the hedge plan.",
    ]
    bad = [
        "PnL is clean; nothing to report.",
        "The break is probably small, so it is left out of the report.",
    ]
    allc = good + bad
    order2 = list(rng.permutation(len(allc)))
    key["commentary_good"] = [i for i, k in enumerate(order2) if k < len(good)]
    steps.append(
        Step(
            "signoff",
            "18:00",
            "PnL sign-off commentary",
            "text_multi",
            "Tick the statements that belong in the sign-off commentary. Wrong ticks cost points.",
            {},
            tuple(allc[i] for i in order2),
            ("pnl_explain", "s_pnl_gen"),
        )
    )
    return Scenario(seed, tuple(steps), key)


# ---------------------------------------------------------------------------- scoring


def score_step(sc: Scenario, step_id: str, response: Any) -> StepResult:
    """Grade one response. ``response`` is an option index, a list of indices, a spread or a tuple, by step."""
    k = sc.key
    step = next(s for s in sc.steps if s.id == step_id)
    mods = step.modules
    if step_id == "pnl_break":
        ok = step.options[int(response)] == k["break"]
        return StepResult(
            step_id,
            _pts(accuracy=(2.0 if ok else 0.0, 2.0), escalation=(1.0 if ok else 0.0, 1.0)),
            0.0,
            "Correct." if ok else f"The break was {k['break'].replace('_', ' ')}.",
            "Size each suspect from the clue and match it to the unexplained amount, then ask for a booking fix.",
            mods,
        )
    if step_id == "ca_checks":
        due = set(k["due"])
        chosen = set(response)
        raw = len(due & chosen) - len(chosen - due)
        earned = max(raw, 0)
        return StepResult(
            step_id,
            _pts(
                accuracy=(float(earned), float(len(due))), risk=(1.0 if due == chosen else 0.0, 1.0)
            ),
            0.0,
            f"{len(due & chosen)} of {len(due)} due items found, {len(chosen - due)} wrong.",
            "Work from the calendar: ex-dates today, resets due today and corporate actions effective today. Skip what is already processed or in the future.",
            mods,
        )
    if step_id == "rfq":
        r = k["rfq"]
        q = float(response)
        win = q <= r["market"]
        pnl = r["notional"] * (q - r["cost"]) / 1e4 * r["tenor"] if win else 0.0
        best = r["notional"] * (r["market"] - r["cost"]) / 1e4 * r["tenor"]
        pnl_pts = max(0.0, min(pnl / best, 1.0)) if best > 0 else 0.0
        below = q < r["cost"]
        return StepResult(
            step_id,
            _pts(pnl=(pnl_pts * 3.0, 3.0), risk=(0.0 if below else 1.0, 1.0)),
            pnl,
            (
                f"Won at {q:.1f} bps; market was {r['market']:.1f}; cost {r['cost']:.1f}."
                if win
                else f"Lost: the market was {r['market']:.1f} bps, you quoted {q:.1f}."
            )
            + (" You quoted below cost." if below else ""),
            f"Quote just inside the market level, never below cost ({r['cost']:.1f} bps). Best achievable PnL here was about {best:,.0f}.",
            mods,
        )
    if step_id == "rebalance":
        est, act = response
        r = k["rebalance"]
        err = abs(est - r["days_adv"]) / r["days_adv"]
        acc = 2.0 if err <= 0.10 else 1.0 if err <= 0.30 else 0.0
        notional = 5e6
        exit_imp = r["impact"] * r["crowd"] * 0.5
        pnl = (
            notional * (r["realised"] - 0.25 * r["impact"] - 2.0 - exit_imp) / 1e4
            if act == 0
            else 0.0
        )
        ev_pre = r["impact"] * 0.4 - 0.25 * r["impact"] - 2.0 - exit_imp
        right = (ev_pre > 0) == (act == 0)
        return StepResult(
            step_id,
            _pts(
                accuracy=(acc, 2.0),
                risk=(1.0 if right else 0.0, 1.0),
                pnl=(1.0 if pnl >= 0 else 0.0, 1.0),
            ),
            pnl,
            f"Demand was {r['days_adv']:.1f} days of ADV (you said {est:.1f}). Expected impact {r['impact']:.0f} bps; crowding x{r['crowd']:g}.",
            "Size the demand in days of ADV, compare the expected move with entry impact, costs and a crowded exit, and only then decide. If the edge is thin after a crowded exit, do not pre-hedge.",
            mods,
        )
    if step_id == "recall":
        r = k["recall"]
        names = ("reborrow", "buy_in", "internalise")
        pick = names[int(response)]
        cost = r["opts"][pick]
        feasible = pick in r["feasible"]
        pnl = -(cost if feasible else r["opts"]["buy_in"])
        extra = pnl + r["feasible"][r["best"]]
        ok = pick == r["best"]
        return StepResult(
            step_id,
            _pts(
                accuracy=(2.0 if ok else 0.0, 2.0),
                pnl=(1.0 if ok else 0.0, 1.0),
                risk=(1.0 if feasible else 0.0, 1.0),
            ),
            pnl,
            (
                "Cheapest feasible response."
                if ok
                else f"The cheapest feasible response was {r['best'].replace('_', '-')}; yours cost {-extra:,.0f} more."
            )
            + ("" if feasible else " You had no inventory to internalise from."),
            "Compare the three costs, check inventory first and act before the settlement deadline.",
            mods,
        )
    if step_id == "margin":
        r = k["margin"]
        ok = int(response) == 1
        pnl = -r["disputed"] * 0.0 if ok else 0.0
        return StepResult(
            step_id,
            _pts(
                accuracy=(2.0 if ok else 0.0, 2.0),
                escalation=(2.0 if ok else 0.0, 2.0),
                risk=(1.0 if int(response) in (0, 1) else 0.0, 1.0),
            ),
            pnl,
            (
                f"Correct: pay the undisputed {r['undisputed']:,.0f} and dispute {r['disputed']:,.0f} with evidence."
                if ok
                else f"Pay the undisputed {r['undisputed']:,.0f} and open a dispute for the {r['disputed']:,.0f} difference."
            ),
            "Recompute the call, pay the undisputed amount on time, raise the dispute in writing with your calculation and agree a resolution date.",
            mods,
        )
    if step_id == "arb":
        r = k["arb"]
        names = ("cash_and_carry", "reverse_cash_and_carry", "none")
        pick = names[int(response)]
        ok = pick == r["signal"]
        edge_money = r["edge"] * r["mult"] * r["contracts"]
        pnl = (
            edge_money
            if ok and pick != "none"
            else (-edge_money * 0.5 - 500.0 if not ok and pick != "none" else 0.0)
        )
        if not ok and pick != "none" and r["signal"] == "none":
            pnl = -2_000.0
        return StepResult(
            step_id,
            _pts(
                accuracy=(2.0 if ok else 0.0, 2.0),
                pnl=(1.0 if pnl >= 0 else 0.0, 1.0),
                risk=(1.0 if ok or pick == "none" else 0.0, 1.0),
            ),
            pnl,
            ("Correct." if ok else f"The signal was {r['signal'].replace('_', ' ')}.")
            + f" Edge {r['edge']:.2f} points.",
            "Compute fair value and the band with costs, trade only outside the band and check borrow and dividend risk for the reverse trade.",
            mods,
        )
    if step_id == "limit":
        ok = int(response) == 1
        return StepResult(
            step_id,
            _pts(escalation=(3.0 if ok else 0.0, 3.0), risk=(2.0 if ok else 0.0, 2.0)),
            0.0,
            "Correct."
            if ok
            else "Breaches are reported at once, not hidden or deferred, and limits are not raised to fit the position.",
            "Tell the head of desk and risk immediately: metric, size, cause, plan and time to fix. Then execute the plan and log it.",
            mods,
        )
    if step_id == "signoff":
        good = set(k["commentary_good"])
        chosen = set(response)
        raw = len(good & chosen) - len(chosen - good)
        return StepResult(
            step_id,
            _pts(
                accuracy=(float(max(raw, 0)), float(len(good))),
                escalation=(1.0 if good == chosen else 0.0, 1.0),
            ),
            0.0,
            f"{len(good & chosen)} of {len(good)} required statements chosen; {len(chosen - good)} wrong.",
            "State what the PnL is, what is unexplained and why, what is open, and what you escalated. Never present a number you cannot reconcile.",
            mods,
        )
    raise KeyError(step_id)


def final_report(results: list[StepResult]) -> Report:
    """Scores 0-100 per category (earned over maximum), the total (mean) and the day's PnL."""
    scores: dict[str, float] = {}
    for c in CATEGORIES:
        e = sum(r.points.get(c, (0.0, 0.0))[0] for r in results)
        mx = sum(r.points.get(c, (0.0, 0.0))[1] for r in results)
        scores[c] = 100.0 * e / mx if mx else 0.0
    total = sum(scores.values()) / len(CATEGORIES)
    grade = (
        "Strong"
        if total >= 85
        else "Solid"
        if total >= 70
        else "Needs work"
        if total >= 50
        else "Review the modules"
    )
    return Report(scores, total, sum(r.pnl for r in results), grade)


def ideal_answers(sc: Scenario) -> dict[str, str]:
    """The model answer text for each step, for the debrief."""
    out = {}
    for s in sc.steps:
        out[s.id] = score_step(sc, s.id, _ideal_response(sc, s)).ideal
    return out


def _ideal_response(sc: Scenario, s: Step) -> Any:
    k = sc.key
    if s.id == "pnl_break":
        return s.options.index(k["break"])
    if s.id == "ca_checks":
        return k["due"]
    if s.id == "rfq":
        r = k["rfq"]
        return r["market"] - min(0.05, (r["market"] - r["cost"]) / 2)
    if s.id == "rebalance":
        r = k["rebalance"]
        exit_imp = r["impact"] * r["crowd"] * 0.5
        return (
            r["days_adv"],
            0 if r["impact"] * 0.4 - 0.25 * r["impact"] - 2.0 - exit_imp > 0 else 1,
        )
    if s.id == "recall":
        return ("reborrow", "buy_in", "internalise").index(k["recall"]["best"])
    if s.id == "margin":
        return 1
    if s.id == "arb":
        return ("cash_and_carry", "reverse_cash_and_carry", "none").index(k["arb"]["signal"])
    if s.id == "limit":
        return 1
    return k["commentary_good"]


def perfect_run(sc: Scenario) -> list[StepResult]:
    """Results of the model answers: used by tests and for the 'ideal day' benchmark."""
    return [score_step(sc, s.id, _ideal_response(sc, s)) for s in sc.steps]


__all__ = [
    "CATEGORIES",
    "Report",
    "Scenario",
    "Step",
    "StepResult",
    "build_scenario",
    "final_report",
    "ideal_answers",
    "perfect_run",
    "score_step",
]

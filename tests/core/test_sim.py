"""Desk Simulator: deterministic scenarios, graded answers, scoring."""

import pytest

from core.sim import desk_day as dd


@pytest.fixture(scope="module")
def sc(world):
    return dd.build_scenario(world, 3)


def test_nine_timed_steps_in_order(sc):
    """The nine events of the spec run from 07:00 to 18:00."""
    assert [s.time for s in sc.steps] == [
        "07:00",
        "08:00",
        "09:00",
        "11:00",
        "13:00",
        "15:00",
        "16:30",
        "17:30",
        "18:00",
    ]


def test_same_seed_same_scenario_different_seed_differs(world):
    a, b, c = dd.build_scenario(world, 1), dd.build_scenario(world, 1), dd.build_scenario(world, 2)
    assert a.key == b.key and [s.facts for s in a.steps] == [s.facts for s in b.steps]
    assert a.key != c.key


@pytest.mark.parametrize("seed", range(8))
def test_perfect_play_scores_high(world, seed):
    """Model answers earn at least 90 in every category. PnL can be negative: a recall costs money even when handled best."""
    s = dd.build_scenario(world, seed)
    rep = dd.final_report(dd.perfect_run(s))
    assert all(v >= 90 for v in rep.scores.values()), rep.scores
    assert rep.grade == "Strong"
    assert rep.pnl >= -s.key["recall"]["opts"]["buy_in"]


def test_poor_play_scores_low(world):
    """Always picking option 0 for choices, ticking nothing and quoting far below cost scores poorly."""
    s = dd.build_scenario(world, 4)
    res = []
    for st in s.steps:
        if st.id in ("ca_checks", "signoff"):
            r = []
        elif st.id == "rfq":
            r = s.key["rfq"]["cost"] - 10
        elif st.id == "rebalance":
            r = (1.0, 0)
        elif st.id == "pnl_break":
            r = (s.steps[0].options.index(s.key["break"]) + 1) % 4
        elif st.id == "margin":
            r = 3
        elif st.id == "limit":
            r = 0
        elif st.id == "arb":
            r = 0 if s.key["arb"]["signal"] != "cash_and_carry" else 1
        else:
            r = 1 if s.key["recall"]["best"] == "reborrow" else 0
        res.append(dd.score_step(s, st.id, r))
    rep = dd.final_report(res)
    assert rep.total < 50 and rep.grade == "Review the modules"


def test_rfq_win_and_lose_hand_check(world):
    """Quote above the hidden market loses with zero PnL; quoting between cost and market wins (quote - cost) x notional x tenor."""
    s = dd.build_scenario(world, 5)
    r = s.key["rfq"]
    lose = dd.score_step(s, "rfq", r["market"] + 1)
    assert lose.pnl == 0 and "Lost" in lose.feedback
    q = (r["cost"] + r["market"]) / 2
    win = dd.score_step(s, "rfq", q)
    assert win.pnl == pytest.approx(r["notional"] * (q - r["cost"]) / 1e4 * r["tenor"])
    below = dd.score_step(s, "rfq", r["cost"] - 5)
    assert below.pnl < 0 and below.points["risk"][0] == 0


def test_ca_checks_partial_credit_and_penalty(world):
    s = dd.build_scenario(world, 6)
    due = s.key["due"]
    one = dd.score_step(s, "ca_checks", due[:1])
    assert one.points["accuracy"][0] == 1 and one.points["risk"][0] == 0
    wrong = dd.score_step(s, "ca_checks", [i for i in range(6) if i not in due])
    assert wrong.points["accuracy"][0] == 0


def test_rebalance_estimate_tolerance(world):
    s = dd.build_scenario(world, 7)
    d = s.key["rebalance"]["days_adv"]
    assert dd.score_step(s, "rebalance", (d * 1.05, 1)).points["accuracy"][0] == 2
    assert dd.score_step(s, "rebalance", (d * 1.25, 1)).points["accuracy"][0] == 1
    assert dd.score_step(s, "rebalance", (d * 2, 1)).points["accuracy"][0] == 0


def test_recall_infeasible_internalise_is_penalised(world):
    """Choosing internalisation without inventory is treated as a buy-in with no risk credit."""
    for seed in range(40):
        s = dd.build_scenario(world, seed)
        if "internalise" not in s.key["recall"]["feasible"]:
            r = dd.score_step(s, "recall", 2)
            assert r.points["risk"][0] == 0 and r.pnl == pytest.approx(
                -s.key["recall"]["opts"]["buy_in"]
            )
            return
    pytest.fail("no seed without inventory found")


def test_margin_dispute_and_limit_choices(world):
    s = dd.build_scenario(world, 8)
    m = s.key["margin"]
    assert m["cp"] - m["own"] == pytest.approx(m["disputed"] + (m["undisputed"] - m["own"]))
    assert dd.score_step(s, "margin", 1).points["escalation"] == (2.0, 2.0)
    assert dd.score_step(s, "margin", 0).points["escalation"][0] == 0
    assert dd.score_step(s, "limit", 1).points["escalation"] == (3.0, 3.0)
    assert dd.score_step(s, "limit", 3).points["risk"][0] == 0


def test_arb_both_signals_and_none(world):
    seen = set()
    for seed in range(60):
        s = dd.build_scenario(world, seed)
        seen.add(s.key["arb"]["signal"])
        wrong = dd.score_step(s, "arb", 2 if s.key["arb"]["signal"] != "none" else 0)
        right = dd.score_step(
            s,
            "arb",
            ("cash_and_carry", "reverse_cash_and_carry", "none").index(s.key["arb"]["signal"]),
        )
        assert right.points["accuracy"][0] == 2 and wrong.points["accuracy"][0] == 0
    assert seen == {"cash_and_carry", "reverse_cash_and_carry", "none"}


def test_ideal_answers_and_unknown_step(world):
    s = dd.build_scenario(world, 9)
    ia = dd.ideal_answers(s)
    assert set(ia) == {x.id for x in s.steps} and all(ia.values())
    with pytest.raises(StopIteration):
        dd.score_step(s, "nope", 0)


def test_signoff_penalises_wrong_statements(world):
    s = dd.build_scenario(world, 10)
    good = s.key["commentary_good"]
    allv = list(range(6))
    r = dd.score_step(s, "signoff", allv)
    assert r.points["accuracy"][0] == len(good) - 2 and r.points["escalation"][0] == 0


def test_final_report_empty_and_grades():
    rep = dd.final_report([])
    assert rep.total == 0 and rep.grade == "Review the modules"

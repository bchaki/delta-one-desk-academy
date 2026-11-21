"""Session state: global settings, progress tracking, formatting and the cached world.

Settings and progress live in ``st.session_state`` only (no database). Progress can be exported to
and imported from a JSON file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

import streamlit as st

from core.data.market import HISTORY_END, HISTORY_START
from core.data.world import DEFAULT_SEED, World, build_world
from core.types import Currency

CCYS = ("USD", "EUR", "GBP")
DEFAULT_AS_OF = date(2026, 11, 20)


@dataclass(frozen=True)
class Settings:
    as_of: date
    seed: int
    ccy: str
    show_math: bool
    advanced: bool


def init_state() -> None:
    """Create defaults on first run (safe to call on every page)."""
    ss = st.session_state
    ss.setdefault("s_as_of", DEFAULT_AS_OF)
    ss.setdefault("s_seed", DEFAULT_SEED)
    ss.setdefault("s_ccy", "USD")
    ss.setdefault("s_show_math", False)
    ss.setdefault("s_advanced", False)
    ss.setdefault("progress", new_progress())


def new_progress() -> dict[str, Any]:
    return {"completed": [], "quiz": {}, "sim_best": None, "checklists": {}}


def get_settings() -> Settings:
    init_state()
    ss = st.session_state
    return Settings(ss.s_as_of, int(ss.s_seed), ss.s_ccy, bool(ss.s_show_math), bool(ss.s_advanced))


@st.cache_resource(show_spinner="Building the synthetic world (first load per seed only)...")
def _warm_world(seed: int) -> int:
    build_world(seed)
    return seed


def get_world() -> World:
    """The synthetic world for the current seed and as-of date (cached)."""
    s = get_settings()
    _warm_world(s.seed)
    return build_world(s.seed, s.as_of)


def usd_to_reporting(world: World, usd: float) -> float:
    """Convert a USD amount to the reporting currency at the as-of fixing."""
    s = get_settings()
    if s.ccy == "USD":
        return usd
    return usd * world.market.fx_rate(Currency.USD, Currency(s.ccy), world.as_of)


def fmt_money(world: World, usd: float, decimals: int = 0) -> str:
    """Format a USD amount in the reporting currency with a sign for gains and losses."""
    s = get_settings()
    v = usd_to_reporting(world, usd)
    return f"{v:+,.{decimals}f} {s.ccy}"


# ---------------------------------------------------------------------------- progress


def progress() -> dict[str, Any]:
    init_state()
    return st.session_state.progress


def is_complete(module_id: str) -> bool:
    return module_id in progress()["completed"]


def set_complete(module_id: str, done: bool = True) -> None:
    comp = progress()["completed"]
    if done and module_id not in comp:
        comp.append(module_id)
    if not done and module_id in comp:
        comp.remove(module_id)


def record_quiz(module_id: str, correct: int, total: int, missed: list[str]) -> None:
    q = progress()["quiz"].setdefault(
        module_id, {"best": 0.0, "last": 0.0, "attempts": 0, "missed": []}
    )
    score = correct / total if total else 0.0
    q["last"] = score
    q["best"] = max(q["best"], score)
    q["attempts"] += 1
    q["missed"] = missed


def export_progress() -> str:
    return json.dumps(progress(), indent=2, sort_keys=True)


def import_progress(text: str) -> bool:
    """Load progress from JSON; returns False (and changes nothing) if the file is not valid."""
    try:
        data = json.loads(text)
        base = new_progress()
        if not isinstance(data, dict) or not set(data) <= set(base):
            return False
        base.update(data)
        if not isinstance(base["completed"], list) or not isinstance(base["quiz"], dict):
            return False
    except (ValueError, TypeError):
        return False
    st.session_state.progress = base
    return True


def sidebar_controls() -> None:
    """Global controls that persist across pages (shared widget keys)."""
    init_state()
    with st.sidebar:
        st.markdown("### Desk settings")
        st.date_input(
            "As-of date",
            min_value=HISTORY_START,
            max_value=HISTORY_END,
            key="s_as_of",
            help="Any day in the synthetic history (2023-11-21 to 2026-11-20). Non-trading days snap to the prior trading day.",
        )
        st.number_input(
            "Random seed",
            min_value=1,
            max_value=999,
            step=1,
            key="s_seed",
            help="Seed of the synthetic world. Same seed, same world. A new seed takes about 10 seconds to build.",
        )
        st.selectbox(
            "Reporting currency",
            CCYS,
            key="s_ccy",
            help="Desk-level amounts are shown in this currency.",
        )
        st.toggle(
            "Show the math",
            key="s_show_math",
            help="Repeat formulas with your numbers substituted, step by step.",
        )
        st.toggle(
            "Advanced",
            key="s_advanced",
            help="Reveal extra parameters and edge cases in sandboxes.",
        )
        from ui.content import registry

        mods = [m for m in registry().modules if m.built and not m.reference]
        done = sum(is_complete(m.id) for m in mods)
        st.progress(
            done / len(mods) if mods else 0.0, text=f"Progress: {done} of {len(mods)} modules"
        )

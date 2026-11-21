"""Limit monitoring against config/desk.yaml (illustrative soft and hard limits)."""

from __future__ import annotations

from dataclasses import dataclass

from core import config


@dataclass(frozen=True)
class LimitStatus:
    name: str
    value: float
    soft: float
    hard: float
    status: str  # ok / soft / hard
    utilisation: float  # value / hard


def check_limits(metrics: dict[str, float]) -> list[LimitStatus]:
    """Compare ``metrics`` (keys as in the config) to the limits: |value| > soft is an escalation, > hard a breach."""
    out = []
    for name, spec in config.desk().limits.items():
        if name not in metrics:
            continue
        v = abs(metrics[name])
        status = "hard" if v > spec.hard else "soft" if v > spec.soft else "ok"
        out.append(LimitStatus(name, metrics[name], spec.soft, spec.hard, status, v / spec.hard))
    return out

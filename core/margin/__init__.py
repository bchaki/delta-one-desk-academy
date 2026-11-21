"""Margin models. All results share :class:`MarginResult`."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarginResult:
    """Margin outcome: gross requirement, credits (offsets), net requirement (never negative)."""

    gross: float
    credits: float
    detail: dict[str, float] = field(default_factory=dict)

    @property
    def net(self) -> float:
        return max(self.gross - self.credits, 0.0)

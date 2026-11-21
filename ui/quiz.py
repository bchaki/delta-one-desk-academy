"""Quiz engine: YAML questions, grading and score recording."""

from __future__ import annotations

from functools import cache
from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

from ui.content import CONTENT


class Question(BaseModel):
    id: str
    module: str
    difficulty: int = 1
    type: Literal["mcq", "numeric", "spot_error"]
    prompt: str
    options: list[str] = []
    answer: float | int
    tolerance: float = 0.0
    unit: str = ""
    explanation: str

    @model_validator(mode="after")
    def _check(self) -> Question:
        if self.type in ("mcq", "spot_error"):
            if len(self.options) < 2 or not 0 <= int(self.answer) < len(self.options):
                raise ValueError(f"{self.id}: answer index outside options")
        elif self.options:
            raise ValueError(f"{self.id}: numeric question must not have options")
        return self


@cache
def load_quiz(module_id: str) -> tuple[Question, ...]:
    path = CONTENT / "quizzes" / f"{module_id}.yaml"
    with path.open() as f:
        raw = yaml.safe_load(f)["questions"]
    return tuple(Question(module=module_id, **q) for q in raw)


@cache
def spot_questions() -> tuple[Question, ...]:
    """Spot-the-error bank (``content/spot_the_error.yaml``), module id ``spot``."""
    with (CONTENT / "spot_the_error.yaml").open() as f:
        raw = yaml.safe_load(f)["questions"]
    return tuple(Question(module="spot", **q) for q in raw)


@cache
def all_questions() -> tuple[Question, ...]:
    """Every question of every built module that has a quiz, plus the spot-the-error bank."""
    from ui.content import registry

    out: list[Question] = []
    for m in registry().modules:
        if m.built and (CONTENT / "quizzes" / f"{m.id}.yaml").exists():
            out.extend(load_quiz(m.id))
    out.extend(spot_questions())
    return tuple(out)


def grade(q: Question, response: float | int | None) -> bool:
    """True when the response is right. Numeric answers pass within ``tolerance`` (absolute)."""
    if response is None:
        return False
    if q.type == "numeric":
        return abs(float(response) - float(q.answer)) <= q.tolerance
    return int(response) == int(q.answer)


def summarise(
    questions: tuple[Question, ...], responses: dict[str, float | int | None]
) -> tuple[int, list[str]]:
    """(correct count, ids missed) over the questions that were answered."""
    correct, missed = 0, []
    for q in questions:
        if q.id not in responses:
            continue
        if grade(q, responses[q.id]):
            correct += 1
        else:
            missed.append(q.id)
    return correct, missed

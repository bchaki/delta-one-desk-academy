"""Content loading: module registry, lesson Markdown with golden-example tokens and glossary tooltips."""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"


class Section(BaseModel):
    id: str
    title: str


class Module(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    section: str
    title: str
    icon: str
    help: str
    week: int = 0
    built: bool = False
    reference: bool = False
    minutes: int | None = None
    difficulty: int | None = None
    prereqs: list[str] = []
    purpose: str = ""
    objectives: list[str] = []
    related: list[str] = []
    terms: list[str] = []

    @property
    def page_path(self) -> str:
        return f"pages/{self.section}/{self.id}.py"


class Registry(BaseModel):
    sections: list[Section]
    modules: list[Module]

    def get(self, module_id: str) -> Module:
        return next(m for m in self.modules if m.id == module_id)

    def in_section(self, section_id: str) -> list[Module]:
        return [m for m in self.modules if m.section == section_id]


@cache
def registry() -> Registry:
    with (CONTENT / "modules.yaml").open() as f:
        return Registry(**yaml.safe_load(f))


# ---------------------------------------------------------------------------- lessons


@cache
def data_file(name: str) -> Any:
    """Load ``content/<name>.yaml`` (teaching data such as case studies, checklists and roles)."""
    with (CONTENT / f"{name}.yaml").open() as f:
        return yaml.safe_load(f)


@cache
def _lesson_text(module_id: str) -> str:
    return (CONTENT / "lessons" / f"{module_id}.md").read_text()


@cache
def lesson_sections(module_id: str) -> dict[str, str]:
    """Split a lesson file on ``## `` headings: ``{"Learn": md, "Worked example": md, ...}``."""
    parts = re.split(r"^## +(.+)$", _lesson_text(module_id), flags=re.MULTILINE)
    return {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def word_count(module_id: str) -> int:
    return len(re.findall(r"\w+", _lesson_text(module_id)))


# ---------------------------------------------------------------------------- golden examples


@cache
def examples(module_id: str) -> dict[str, dict[str, Any]]:
    path = CONTENT / "examples" / f"{module_id}.yaml"
    if not path.exists():
        return {}
    with path.open() as f:
        return yaml.safe_load(f)["examples"]


def _resolve(dotted: str):
    mod, _, name = dotted.rpartition(".")
    return getattr(importlib.import_module(mod), name)


def _build(node: Any) -> Any:
    """Resolve ``{"$": "pkg.Class", "args": [...], "kwargs": {...}}`` nodes into objects, recursively."""
    if isinstance(node, dict):
        if "$" in node:
            return _resolve(node["$"])(
                *_build(node.get("args", [])), **_build(node.get("kwargs", {}))
            )
        return {k: _build(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_build(v) for v in node]
    return node


def run_example(ex: dict[str, Any]) -> Any:
    """Call the core function named in a golden example with its stored arguments.

    Argument values may build objects with ``{"$": "module.Class", "args": [...], "kwargs": {...}}``.
    """
    return _resolve(ex["fn"])(**_build(ex["args"]))


def matches(result: Any, expected: Any, tol: float) -> bool:
    """Compare a result with the stored expectation (scalar, sequence or attribute dict)."""
    if isinstance(expected, dict):
        return all(
            matches(result[k] if isinstance(result, dict) else getattr(result, k), v, tol)
            for k, v in expected.items()
        )
    if isinstance(expected, list | tuple):
        return len(result) == len(expected) and all(
            matches(r, e, tol) for r, e in zip(result, expected, strict=True)
        )
    if isinstance(expected, str):
        return str(result) == expected
    return abs(float(result) - float(expected)) <= tol


def check_example(ex: dict[str, Any]) -> bool:
    return matches(run_example(ex), ex["expected"], float(ex.get("tolerance", 1e-6)))


_TOKEN = re.compile(r"\{\{\s*(abs\s+)?ex\.([a-z0-9_]+)\.([^}:\s]+)(?::([^}]+))?\s*\}\}")


def fill_tokens(module_id: str, text: str) -> str:
    """Replace ``{{ex.<id>.<path>[:fmt]}}`` with values from the module's golden examples."""
    exs = examples(module_id)

    def sub(m: re.Match) -> str:
        absval, ex_id, path, fmt = m.group(1), m.group(2), m.group(3), m.group(4)
        node: Any = exs[ex_id]
        for part in path.split("."):
            node = node[int(part)] if isinstance(node, list) else node[part]
        if absval:
            node = abs(node)
        return format(node, fmt) if fmt else str(node)

    return _TOKEN.sub(sub, text)


def render_lesson_md(module_id: str, text: str) -> str:
    """Tokens first, then glossary tooltips."""
    from ui.glossary import render_terms

    return render_terms(fill_tokens(module_id, text))


@dataclass(frozen=True)
class LessonCheck:
    unresolved_tokens: list[str]


def unresolved_tokens(module_id: str) -> list[str]:
    bad = []
    for name, text in lesson_sections(module_id).items():
        try:
            fill_tokens(module_id, text)
        except (KeyError, IndexError, ValueError) as e:
            bad.append(f"{name}: {e!r}")
    return bad

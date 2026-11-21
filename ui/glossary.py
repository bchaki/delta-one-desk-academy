"""Glossary loading and inline ``[[term]]`` tooltips."""

from __future__ import annotations

import html
import re
from functools import cache

import yaml
from pydantic import BaseModel

from ui.content import CONTENT


class GlossaryTerm(BaseModel):
    term: str
    category: str
    definition: str
    formula: str | None = None
    example: str | None = None
    modules: list[str] = []
    aliases: list[str] = []


@cache
def load_glossary() -> dict[str, GlossaryTerm]:
    """All terms keyed by lowercase name and aliases."""
    with (CONTENT / "glossary.yaml").open() as f:
        raw = yaml.safe_load(f)["terms"]
    out: dict[str, GlossaryTerm] = {}
    for item in raw:
        t = GlossaryTerm(**item)
        out[t.term.lower()] = t
        for a in t.aliases:
            out[a.lower()] = t
    return out


def lookup(name: str) -> GlossaryTerm | None:
    return load_glossary().get(name.lower())


_REF = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def terms_in(text: str) -> list[str]:
    """Names referenced with ``[[...]]`` in a text, in order, without duplicates."""
    seen: list[str] = []
    for m in _REF.finditer(text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def render_terms(text: str) -> str:
    """Replace ``[[term]]`` / ``[[term|shown text]]`` with a dotted-underline tooltip.

    Unknown terms render as plain text (a content test fails on them).
    """

    def sub(m: re.Match) -> str:
        name, shown = m.group(1), m.group(2) or m.group(1)
        t = lookup(name)
        if t is None:
            return shown
        return f'<abbr class="g" title="{html.escape(t.definition, quote=True)}">{shown}</abbr>'

    return _REF.sub(sub, text)

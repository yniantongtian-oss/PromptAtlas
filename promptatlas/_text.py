"""Comparison keys that normalize prose while preserving literal code."""

from __future__ import annotations

import re

from ._markdown import inline_code_spans, opening_fence
from .schema import Component

_SPACE = re.compile(r"\s+")


def prose_key(text: str, *, casefold: bool = False) -> str:
    """Collapse prose whitespace; code contents keep whitespace and case."""
    spans = inline_code_spans(text)
    if not spans:
        result = " ".join(text.split())
        return result.casefold() if casefold else result
    parts = []
    position = 0
    for start, end in [*spans, (len(text), len(text))]:
        prose = _SPACE.sub(" ", text[position:start])
        parts.extend((prose.casefold() if casefold else prose, text[start:end]))
        position = end
    return "".join(parts).strip()


def component_key(component: Component) -> tuple[str, str]:
    content = component.content
    if component.kind in {"tool", "few_shot"} or opening_fence(
        content.partition("\n")[0].partition("\r")[0]
    ):
        return component.kind, content
    return component.kind, prose_key(content)

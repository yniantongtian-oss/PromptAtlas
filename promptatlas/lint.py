"""Explainable structural checks; these do not predict model behavior."""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import asdict, dataclass

from ._markdown import closes_fence, opening_fence
from ._templates import has_unresolved_template, variable_names
from ._text import component_key, prose_key
from .parse import parse_prompt
from .schema import VALID_COMPONENT_KINDS, PromptSpec


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    line: int | None = None
    component_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def lint_spec(
    spec: PromptSpec,
    *,
    required_kinds: tuple[str, ...] = (),
    allowed_variables: tuple[str, ...] = (),
) -> list[Finding]:
    """Check empty prompts, missing sections, duplicates, and explicit conflicts.

    PA004 only recognizes opposite Always/Never directives with otherwise
    identical words. It is deliberately conservative, not a semantic judge.
    """
    if any(kind not in VALID_COMPONENT_KINDS for kind in required_kinds):
        raise ValueError("required_kinds contains an invalid component kind")
    allowed = frozenset(variable_names(allowed_variables))
    findings = []
    if not spec.raw.strip() and not spec.components:
        return [Finding("PA001", "error", "The prompt is empty.", 1)]
    if not spec.by_kind("role"):
        findings.append(Finding("PA002", "warning", "No explicit role or mission was found."))
    seen: dict[tuple[str, str], str] = {}
    directives: dict[str, tuple[str, str]] = {}
    line_starts, offset = [0], 0
    for source_line in spec.raw.splitlines(keepends=True):
        offset += len(source_line)
        line_starts.append(offset)
    for component in spec.components:
        line = bisect_right(line_starts, component.start) if component.start is not None else None
        key = component_key(component)
        if key in seen:
            findings.append(
                Finding(
                    "PA003", "warning", "A component repeats an earlier rule.", line, component.id
                )
            )
        seen[key] = component.id
        if component.kind in {"few_shot", "context", "tool"}:
            continue
        directive = re.match(r"^(Always|Never)\s+(.+?)[.!]?\s*$", component.content, re.I)
        if directive:
            polarity, body = directive[1].casefold(), prose_key(directive[2], casefold=True)
            previous = directives.get(body)
            if previous and previous[0] != polarity:
                findings.append(
                    Finding(
                        "PA004",
                        "error",
                        "Opposite Always/Never rules have identical wording; review the conflict.",
                        line,
                        component.id,
                    )
                )
            directives[body] = (polarity, component.id)
        if has_unresolved_template(component.content, allowed):
            findings.append(
                Finding(
                    "PA005",
                    "warning",
                    "An undeclared template variable, unsupported expression, or TODO remains.",
                    line,
                    component.id,
                )
            )
    active_fence = None
    for number, line_text in enumerate(spec.raw.splitlines(), 1):
        if active_fence is None:
            marker = opening_fence(line_text)
            if marker:
                active_fence = (marker, number)
        elif closes_fence(line_text, active_fence[0]):
            active_fence = None
    if active_fence:
        findings.append(
            Finding("PA006", "error", "A fenced code block is not closed.", active_fence[1])
        )
    for kind in dict.fromkeys(required_kinds):
        if not spec.by_kind(kind):
            findings.append(
                Finding("PA007", "error", f"Required component kind is missing: {kind}.")
            )
    return findings


def lint_prompt(
    raw: str,
    *,
    required_kinds: tuple[str, ...] = (),
    allowed_variables: tuple[str, ...] = (),
) -> list[Finding]:
    """Parse a prompt and return stable, explainable structural findings."""
    return lint_spec(
        parse_prompt(raw), required_kinds=required_kinds, allowed_variables=allowed_variables
    )

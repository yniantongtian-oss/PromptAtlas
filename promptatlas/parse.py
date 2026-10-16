"""Deterministic English-oriented parsing with source spans and opaque blocks.

Classification is a heuristic, not a safety verdict. Code, examples, and tool
schemas remain intact so their contents cannot become duplicate directives.
"""

from __future__ import annotations

import hashlib
import json
import re

from ._json import loads
from ._markdown import fence_end, mask_inline_code, opening_fence
from .schema import Component, PromptSpec

_NEGATION = re.compile(
    r"\b(never|do not|don't|must not|should not|avoid|refuse|cannot|can't)\b", re.I
)
_OUTPUT = re.compile(
    r"\b(output format|respond with|respond in|always (?:use|respond)|return (?:valid )?json|"
    r"json format|markdown|in (?:english|chinese|the user'?s language)|"
    r"concise|without (?:preamble|explanation))\b",
    re.I,
)
_STOP = re.compile(
    r"\b(stop|wait for|ask (?:the user|one clarifying)|hand off|escalate|"
    r"if you (?:are unsure|cannot)|do not proceed|check with)\b",
    re.I,
)
_CONTEXT = re.compile(
    r"^(?:environment|system info|working directory|current (?:date|time|dir)|platform|os[:=])",
    re.I,
)
_ROLE = re.compile(r"^(?:you are|your role is|act as)\b", re.I)
_DIRECTIVE = re.compile(
    r"^(?:always|only|use|when|before|after|first|then|if|for each|make sure|ensure|verify|keep)\b",
    re.I,
)
_EXAMPLE = re.compile(r"^\s*(?:#{1,6}\s*)?(?:example(?:\s+\d+)?|few[- ]shot)(?:\s*[:#]?\s*)$", re.I)
_DIALOGUE = re.compile(r"^\s*(?:User|Assistant|Human|System)\s*:", re.I)
_SECTIONS = {
    "role": "role",
    "persona": "role",
    "mission": "role",
    "instructions": "instruction",
    "instruction": "instruction",
    "behavior": "instruction",
    "tools": "tool",
    "tool definitions": "tool",
    "guardrails": "guardrail",
    "safety": "guardrail",
    "constraints": "guardrail",
    "output": "output_rule",
    "output rules": "output_rule",
    "response format": "output_rule",
    "stop conditions": "stop_condition",
    "handoff": "stop_condition",
    "context": "context",
    "environment": "context",
    "examples": "few_shot",
    "few shot examples": "few_shot",
}


def _heading(line: str) -> tuple[bool, str | None]:
    match = re.match(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$", line)
    if not match:
        return False, None
    key = re.sub(r"[^a-z0-9 ]", " ", match[1].casefold())
    return True, _SECTIONS.get(" ".join(key.split()))


def _is_tool(value: object) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, list):
            if not item:
                return False
            pending.extend(item)
        elif isinstance(item, dict):
            if item.get("type") == "function" or ("name" in item and "parameters" in item):
                continue
            tools = item.get("tools")
            if not isinstance(tools, list) or not tools:
                return False
            pending.extend(tools)
        else:
            return False
    return True


def _classify(text: str, section: str | None) -> str:
    if section and section != "instruction":
        return section
    if _ROLE.match(text):
        return "role"
    if _CONTEXT.match(text):
        return "context"
    if _STOP.search(text):
        return "stop_condition"
    if _NEGATION.search(text):
        return "guardrail"
    if _OUTPUT.search(text):
        return "output_rule"
    if section == "instruction" or _DIRECTIVE.match(text):
        return "instruction"
    return "context"


def parse_prompt(raw: str, product: str = "", version: str = "") -> PromptSpec:
    """Parse without network calls; equal inputs produce equal serialized specs.

    Offsets point into the unchanged input, including CRLF and Unicode. IDs
    include kind, content, and occurrence index, so repeated rules stay distinct.
    """
    spec = PromptSpec(raw=raw, product=product, version=version)
    lines = raw.splitlines(keepends=True)
    offsets = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)
    occurrences: dict[tuple[str, str], int] = {}

    def append(kind: str, start: int, end: int, confidence: float) -> None:
        chunk = raw[start:end]
        start += len(chunk) - len(chunk.lstrip())
        end -= len(chunk) - len(chunk.rstrip())
        if start >= end:
            return
        content = raw[start:end]
        key = (kind, content)
        occurrence = occurrences.get(key, 0)
        occurrences[key] = occurrence + 1
        identity = json.dumps([kind, content, occurrence], ensure_ascii=False)
        spec.components.append(
            Component(
                kind=kind,
                content=content,
                product=product,
                version=version,
                id=hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16],
                confidence=confidence,
                start=start,
                end=end,
            )
        )

    section = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        fence = opening_fence(line)
        if fence:
            j = body_end = fence_end(lines, i, fence)
            j = min(j + 1, len(lines))
            kind = "context"
            try:
                if _is_tool(loads("".join(lines[i + 1 : body_end]))):
                    kind = "tool"
            except (ValueError, TypeError):
                pass
            append(
                kind,
                offsets[i],
                offsets[j] if j < len(lines) else len(raw),
                0.95 if kind == "tool" else 0.7,
            )
            i = j
            continue
        # XML-style tool blocks are data, never evaluated or executed.
        tool_tag = re.match(r"^\s*<(tools?|tool_schema)(?:\s[^>]*)?>", line, re.I)
        if tool_tag:
            j = i
            closing_tag = re.compile(r"</" + tool_tag[1] + r"\s*>", re.I)
            while j < len(lines) and not closing_tag.search(lines[j]):
                j += 1
            j = min(j + 1, len(lines))
            append("tool", offsets[i], offsets[j] if j < len(lines) else len(raw), 0.9)
            i = j
            continue
        is_heading, heading_kind = _heading(line)
        if is_heading and not _EXAMPLE.match(line):
            section = heading_kind
            i += 1
            continue
        if _EXAMPLE.match(line) or _DIALOGUE.match(line) or (section == "few_shot"):
            j = i + 1
            while j < len(lines):
                example_fence = opening_fence(lines[j])
                if example_fence:
                    j = min(fence_end(lines, j, example_fence) + 1, len(lines))
                    continue
                if _heading(lines[j])[0] or _EXAMPLE.match(lines[j]):
                    break
                if not lines[j].strip():
                    k = j + 1
                    while k < len(lines) and not lines[k].strip():
                        k += 1
                    if k >= len(lines) or not _DIALOGUE.match(lines[k]):
                        break
                j += 1
            append("few_shot", offsets[i], offsets[j] if j < len(lines) else len(raw), 0.8)
            i = j
            continue
        prefix = re.match(r"\s*(?:(?:[-*+]|\d+[.)])\s+)?", line)
        start = offsets[i] + prefix.end()
        end = offsets[i] + len(line.rstrip())
        text = raw[start:end]
        prose = mask_inline_code(text)
        position = 0
        for boundary in list(re.finditer(r"(?<=[.!?])\s+(?=[A-Z])", prose)) + [None]:
            finish = boundary.start() if boundary else len(text)
            content = text[position:finish]
            if content.strip():
                kind = _classify(prose[position:finish], section)
                append(kind, start + position, start + finish, 0.9 if kind == "role" else 0.7)
            position = boundary.end() if boundary else len(text)
        i += 1
    return spec

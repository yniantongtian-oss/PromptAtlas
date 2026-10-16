"""Heuristic parser that structures a raw system prompt into Components.

The parser is deterministic and dependency-free. It recognises:
  - role           : leading "You are ..." statements / first paragraph
  - guardrail      : sentences containing negated imperatives
                     (never, do not, must not, refuse, don't)
  - output_rule    : sentences about response format / language / length
  - stop_condition : sentences about stopping, waiting, handing off, asking
  - tool           : JSON function schemas and <tool>-like blocks
  - few_shot       : example dialogue blocks (User:/Assistant: patterns)
  - context        : environment facts (paths, dates, runtime)
  - instruction    : everything else that is a directive
"""

from __future__ import annotations

import json
import re

from .schema import Component, PromptSpec

_NEGATION = re.compile(r"\b(never|do not|don't|must not|should not|avoid|refuse|"
                       r"do not|cannot|can't)\b", re.I)
_OUTPUT = re.compile(r"\b(output format|respond with|respond in|always (use|respond)|"
                     r"json format|markdown|in (english|chinese|the user'?s language)|"
                     r"concise|without (preamble|explanation))\b", re.I)
_STOP = re.compile(r"\b(stop|wait for|ask the user|hand off|escalate|"
                   r"if you (are unsure|cannot)|do not proceed|check with)\b", re.I)
_CONTEXT = re.compile(r"^\s*(environment|system info|working directory|"
                      r"current (date|time|dir)|platform|os[:=])", re.I | re.M)
_ROLE = re.compile(r"^\s*you are\b", re.I)
_TOOL_SCHEMA = re.compile(r'"type"\s*:\s*"function"')
_DIRECTIVE = re.compile(r"^(always|only|use|when|before|after|first|then|if|"
                        r"for each|make sure|ensure)\b", re.I)


def _sentences(text: str) -> list:
    parts = re.split(r"(?<=[.!?\n])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _classify_sentence(sent: str) -> str:
    if _NEGATION.search(sent):
        return "guardrail"
    if _STOP.search(sent):
        return "stop_condition"
    if _OUTPUT.search(sent):
        return "output_rule"
    if _DIRECTIVE.match(sent):
        return "instruction"
    return "context"


def parse_prompt(raw: str, product: str = "", version: str = "") -> PromptSpec:
    """Structure a raw system prompt into a PromptSpec."""
    spec = PromptSpec(raw=raw, product=product, version=version)
    text = raw.strip()
    components = []

    # 1. Extract tool JSON blocks first so they aren't mangled.
    tool_blocks = []
    for m in re.finditer(r"```(?:json)?\s*\n(.*?)```", text, re.S):
        block = m.group(1)
        if _TOOL_SCHEMA.search(block):
            try:
                json.loads(block)
                tool_blocks.append((m.start(), m.end(), block))
            except json.JSONDecodeError:
                pass
    for start, end, block in sorted(tool_blocks, reverse=True):
        components.append(Component(
            kind="tool", content=block, product=product, version=version,
            confidence=0.95))
        text = text[:start] + " " + text[end:]

    # 2. Extract few-shot example blocks.
    for m in re.finditer(r"(Example \d+|Few-shot)[: ]*\n(.*?)(?=\n\n|\Z)",
                         text, re.S | re.I):
        components.append(Component(
            kind="few_shot", content=m.group(2).strip(), product=product,
            version=version, confidence=0.8))

    # 3. Remaining text -> sentences, classified by heuristics.
    sents = _sentences(text)
    for i, sent in enumerate(sents):
        if not sent:
            continue
        if i == 0 and _ROLE.search(sent):
            kind = "role"
        elif _CONTEXT.search(sent):
            kind = "context"
        else:
            kind = _classify_sentence(sent)
        components.append(Component(kind=kind, content=sent,
                                    product=product, version=version,
                                    confidence=0.7 if kind != "role" else 0.9))

    spec.components = components
    return spec

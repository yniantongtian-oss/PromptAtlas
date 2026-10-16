"""Shared Markdown boundaries; this is not a complete Markdown parser."""

from __future__ import annotations

import re

_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
_CLOSE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")
_BACKTICKS = re.compile(r"`+")


def opening_fence(line: str) -> str | None:
    """Recognize a fence without mistaking a backtick code span for one.

    As in earlier releases, indentation is accepted without interpreting list
    containers. Backtick fence info strings cannot contain backticks.
    """
    match = _FENCE.match(line.rstrip("\r\n"))
    if match and not (match[1][0] == "`" and "`" in match[2]):
        return match[1]
    return None


def closes_fence(line: str, opening: str) -> bool:
    match = _CLOSE.match(line.rstrip("\r\n"))
    return bool(match and match[1][0] == opening[0] and len(match[1]) >= len(opening))


def fence_end(lines: list[str], start: int, opening: str) -> int:
    """Return the closing line index, or len(lines) for an unclosed fence."""
    end = start + 1
    while end < len(lines) and not closes_fence(lines[end], opening):
        end += 1
    return end


def inline_code_spans(text: str) -> list[tuple[int, int]]:
    """Find equal-length backtick delimiters in linear time.

    An escaped opening delimiter is literal. Backslashes within a code span do
    not escape its closing delimiter. Unmatched runs remain ordinary text.
    Callers control the block boundary; the prompt parser uses one source line.
    """
    runs = list(_BACKTICKS.finditer(text))
    following: dict[int, int] = {}
    partners: dict[int, int] = {}
    for index in range(len(runs) - 1, -1, -1):
        length = runs[index].end() - runs[index].start()
        if length in following:
            partners[index] = following[length]
        following[length] = index
    spans = []
    index = 0
    while index < len(runs):
        start = runs[index].start()
        cursor = start
        while cursor > 0 and text[cursor - 1] == "\\":
            cursor -= 1
        partner = partners.get(index)
        if (start - cursor) % 2 or partner is None:
            index += 1
            continue
        spans.append((start, runs[partner].end()))
        index = partner + 1
    return spans


def mask_inline_code(text: str) -> str:
    """Hide literal keywords and punctuation without changing source offsets."""
    parts = []
    position = 0
    for start, end in inline_code_spans(text):
        parts.extend((text[position:start], "\0" * (end - start)))
        position = end
    parts.append(text[position:])
    return "".join(parts)

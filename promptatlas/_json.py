"""Unambiguous JSON input with finite numbers and ordinary input errors."""

from __future__ import annotations

import json
import math

# CPython's decoder depth limit depends on the platform stack size, so a deeply
# nested input can decode on Linux/macOS but fail on Windows. Keep the boundary
# explicit and below the default 1000-frame limit on every supported version.
_MAX_DEPTH = 900


def _within_depth_limit(text: str) -> bool:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > _MAX_DEPTH:
                return False
        elif character in "]}":
            depth -= 1
    return True


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for name, value in items:
        if name in result:
            display = repr(name)
            if len(display) > 120:
                display = display[:117] + "..."
            raise ValueError(f"duplicate JSON object key: {display}")
        result[name] = value
    return result


def _constant(value: str) -> object:
    raise ValueError(f"non-finite JSON number is not supported: {value}")


def _float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON number is outside the finite floating-point range")
    return number


def loads(text: str) -> object:
    """Reject duplicate names/NaN/Infinity and excessive nesting deterministically.

    This does not impose a file-size limit or sandbox the interpreter. Valid
    strings remain unchanged and Python integer limits still apply.
    """
    if not _within_depth_limit(text):
        raise ValueError(f"JSON nesting exceeds the supported depth of {_MAX_DEPTH}")
    try:
        return json.loads(
            text, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds the interpreter's supported depth") from exc

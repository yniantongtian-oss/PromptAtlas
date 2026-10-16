"""Unambiguous JSON input with finite numbers and ordinary input errors."""

from __future__ import annotations

import json
import math


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
    """Reject duplicate names/NaN/Infinity and contain decoder recursion errors.

    This does not impose a file-size limit or sandbox the interpreter. Existing
    Python integer/depth limits still apply; valid strings remain unchanged.
    """
    try:
        return json.loads(
            text, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds the interpreter's supported depth") from exc

"""Explicit template-name policy without rendering or evaluating expressions."""

from __future__ import annotations

import re

from ._markdown import mask_inline_code

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_PLACEHOLDER = re.compile(r"\{\{([^{}]*)\}\}|\$\{([^{}]*)\}")
_TODO = re.compile(r"\b(?:TODO|FIXME)\b")


def variable_names(value: object, location: str = "allowed_variables") -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or any(
        not isinstance(name, str) or not _NAME.fullmatch(name) for name in value
    ):
        raise ValueError(f"{location} must list variable names such as input or release.name")
    return tuple(dict.fromkeys(value))


def has_unresolved_template(text: str, allowed: frozenset[str]) -> bool:
    """Check named placeholders, unsupported delimiters, and prose TODOs.

    A declared name permits that exact placeholder, including within inline
    code. TODO/FIXME tokens in inline code are literals. Complex expressions,
    nested/empty placeholders, and incomplete opening delimiters stay visible.
    """
    unresolved = False

    def replace(match: re.Match) -> str:
        nonlocal unresolved
        name = (match[1] if match[1] is not None else match[2]).strip()
        if name not in allowed:
            unresolved = True
        return "\0" * len(match[0])

    remainder = _PLACEHOLDER.sub(replace, text)
    return bool(
        unresolved
        or "{{" in remainder
        or "${" in remainder
        or _TODO.search(mask_inline_code(remainder))
    )

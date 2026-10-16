"""Packaged, offline JSON Schema documents for editor and tool integration."""

from __future__ import annotations

from importlib.resources import files

from ._json import loads

SCHEMA_NAMES = ("component", "spec", "project")


def get_schema(name: str) -> dict:
    """Return an independent schema document without fetching any URL."""
    if name not in SCHEMA_NAMES:
        raise ValueError(f"unknown schema {name!r}; choose from {', '.join(SCHEMA_NAMES)}")
    text = files("promptatlas").joinpath(f"data/{name}.schema.json").read_text(encoding="utf-8")
    return loads(text)

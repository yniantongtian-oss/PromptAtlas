"""Load prompt text and saved specs through the same validated path."""

from __future__ import annotations

from pathlib import Path

from .parse import parse_prompt
from .schema import PromptSpec


def read_text(path: str | Path) -> str:
    """Read UTF-8 without rewriting the file's original line endings."""
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return stream.read()


def load_prompt(path: str | Path, *, product: str = "", version: str = "") -> PromptSpec:
    """Load .json files as saved specs and other files as prompt text.

    Metadata arguments label text inputs. Saved specs retain their own metadata.
    Schema URLs in saved files are descriptive and are never fetched.
    """
    path = Path(path)
    if path.suffix.casefold() == ".json":
        return PromptSpec.load(path)
    return parse_prompt(read_text(path), product=product, version=version or path.name)

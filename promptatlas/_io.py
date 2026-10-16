"""Small UTF-8 file helpers shared by exporters and stores."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def resolve_path(path: str | Path) -> Path:
    """Reject symlink loops consistently while allowing genuinely missing paths."""
    try:
        candidate = Path(path)
        try:
            return candidate.resolve(strict=True)
        except FileNotFoundError:
            return candidate.resolve(strict=False)
    except RuntimeError as exc:
        raise ValueError(f"cannot resolve path {str(path)!r}: {exc}") from exc


def atomic_write(path: str | Path, text: str) -> None:
    """Replace a text file only after its complete replacement is written."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

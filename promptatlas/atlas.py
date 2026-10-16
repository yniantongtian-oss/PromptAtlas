"""A packaged reference atlas and explicit, writable JSONL stores."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from ._io import atomic_write
from .schema import VALID_COMPONENT_KINDS, Component

DEFAULT_ATLAS_PATH = Path(__file__).resolve().parent / "data" / "components.jsonl"


class AtlasStore:
    """Load the read-only reference atlas or a custom store.

    Missing custom stores raise unless create=True is explicit. Writes replace
    the whole file atomically. Custom stores support a single writer at a time.
    """

    def __init__(self, path: str | Path | None = None, *, create: bool = False):
        self.path = Path(path) if path is not None else DEFAULT_ATLAS_PATH
        self._bundled = path is None or self.path.resolve() == DEFAULT_ATLAS_PATH.resolve()
        self._create = create
        self._components: list[Component] = []
        self.reload()

    def _read(self) -> list[Component]:
        if self._bundled:
            text = (
                files("promptatlas").joinpath("data/components.jsonl").read_text(encoding="utf-8")
            )
        elif self._create and not self.path.exists():
            text = ""
        else:
            text = self.path.read_text(encoding="utf-8-sig")
        components = []
        seen = set()
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                component = Component.from_dict(json.loads(line))
                if component.id in seen:
                    raise ValueError(f"duplicate component id {component.id!r}")
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{self.path}:{line_number}: {exc}") from exc
            components.append(component)
            seen.add(component.id)
        return components

    def reload(self) -> None:
        """Replace the in-memory view only after every row is validated."""
        components = self._read()
        self._components = components

    def add(self, component: Component) -> None:
        """Persist to an explicit custom store, then update the in-memory view."""
        if self._bundled:
            raise ValueError("the bundled atlas is read-only; choose a custom --atlas path")
        if not isinstance(component, Component):
            raise ValueError("expected a Component")
        component = Component.from_dict(component.to_dict())
        components = self._read()
        if any(item.id == component.id for item in components):
            raise ValueError(f"duplicate component id {component.id!r}")
        components.append(component)
        text = "".join(json.dumps(item.to_dict(), ensure_ascii=False) + "\n" for item in components)
        atomic_write(self.path, text)
        self._components = components

    def search(
        self,
        kind: str = "",
        tags: list[str] | None = None,
        product: str = "",
        query: str = "",
    ) -> list[Component]:
        """Filter in source order; all requested tags must match, ignoring case."""
        if kind and kind not in VALID_COMPONENT_KINDS:
            raise ValueError(f"invalid component kind {kind!r}")
        required_tags = {tag.casefold() for tag in (tags or [])}
        return [
            item
            for item in self._components
            if (not kind or item.kind == kind)
            and (not product or product.casefold() in item.product.casefold())
            and required_tags.issubset({tag.casefold() for tag in item.tags})
            and (not query or query.casefold() in item.content.casefold())
        ]

    def products(self) -> list[str]:
        return sorted({item.product for item in self._components if item.product})

    def kinds(self) -> list[str]:
        return list(VALID_COMPONENT_KINDS)

    def __len__(self) -> int:
        return len(self._components)

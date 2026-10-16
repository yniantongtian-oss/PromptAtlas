"""JSONL-backed store for structured prompt components."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Component

DEFAULT_ATLAS_PATH = Path(__file__).resolve().parent.parent / "atlas" / "components.jsonl"


class AtlasStore:
    def __init__(self, path: str | Path = DEFAULT_ATLAS_PATH):
        self.path = Path(path)
        self._components: list = []
        self.reload()

    def reload(self):
        self._components = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    self._components.append(Component.from_dict(json.loads(line)))

    def add(self, component: Component):
        self._components.append(component)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(component.to_dict(), ensure_ascii=False) + "\n")

    def search(self, kind: str = "", tags: list | None = None,
               product: str = "", query: str = "") -> list:
        tags = set(t.lower() for t in (tags or []))
        q = query.lower()
        out = []
        for c in self._components:
            if kind and c.kind != kind:
                continue
            if product and product.lower() not in c.product.lower():
                continue
            if tags and not tags.issubset(set(t.lower() for t in c.tags)):
                continue
            if q and q not in c.content.lower():
                continue
            out.append(c)
        return out

    def products(self) -> list:
        return sorted({c.product for c in self._components if c.product})

    def kinds(self) -> list:
        from .schema import VALID_COMPONENT_KINDS
        return list(VALID_COMPONENT_KINDS)

    def __len__(self):
        return len(self._components)

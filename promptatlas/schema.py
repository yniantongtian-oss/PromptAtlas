"""Core data structures for PromptAtlas."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path

VALID_COMPONENT_KINDS = (
    "role",          # persona / mission statement
    "instruction",   # behavioral directive
    "tool",          # tool / function definition
    "guardrail",     # safety / refusal / boundary rule
    "output_rule",   # response format / language / length constraint
    "stop_condition",# when to stop / hand off / ask user
    "few_shot",      # example exchanges
    "context",       # environment / runtime facts
    "other",
)

_slug_re = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _slug_re.sub("-", text.lower()).strip("-")[:64] or uuid.uuid4().hex[:8]


@dataclass
class Component:
    """A single structured component extracted from a system prompt."""

    kind: str
    content: str
    product: str = ""
    version: str = ""
    tags: list = field(default_factory=list)
    source: str = ""           # where this was observed (e.g. public repo URL)
    confidence: float = 1.0    # heuristic parser confidence 0..1
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self):
        if self.kind not in VALID_COMPONENT_KINDS:
            raise ValueError(
                f"invalid component kind {self.kind!r}; "
                f"valid kinds: {VALID_COMPONENT_KINDS}"
            )
        self.content = self.content.strip()

    @property
    def slug(self) -> str:
        return _slugify(self.content.splitlines()[0] if self.content else self.id)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Component":
        return cls(**data)


@dataclass
class PromptSpec:
    """A fully structured system prompt."""

    raw: str
    product: str = ""
    version: str = ""
    components: list = field(default_factory=list)

    def by_kind(self, kind: str) -> list:
        return [c for c in self.components if c.kind == kind]

    def stats(self) -> dict:
        out = {}
        for kind in VALID_COMPONENT_KINDS:
            n = len(self.by_kind(kind))
            if n:
                out[kind] = n
        return out

    def to_dict(self) -> dict:
        return {
            "product": self.product,
            "version": self.version,
            "stats": self.stats(),
            "components": [c.to_dict() for c in self.components],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: str | Path) -> "PromptSpec":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        spec = cls(raw="", product=data.get("product", ""),
                   version=data.get("version", ""))
        spec.components = [Component.from_dict(c) for c in data["components"]]
        return spec

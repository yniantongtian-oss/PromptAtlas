"""Validated, serializable data structures for prompt components."""

from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from ._io import atomic_write

VALID_COMPONENT_KINDS = (
    "role",
    "instruction",
    "tool",
    "guardrail",
    "output_rule",
    "stop_condition",
    "few_shot",
    "context",
    "other",
)
SCHEMA_VERSION = 1


@dataclass
class Component:
    """One prompt component; offsets are Unicode character indices, end exclusive."""

    kind: str
    content: str
    product: str = ""
    version: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    confidence: float = 1.0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    start: int | None = None
    end: int | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_COMPONENT_KINDS:
            raise ValueError(f"invalid component kind {self.kind!r}")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("component content must be a non-empty string")
        self.content = self.content.strip()
        for name in ("product", "version", "source", "id"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"component {name} must be a string")
        if not self.id.strip():
            raise ValueError("component id must not be empty")
        if not isinstance(self.tags, list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in self.tags
        ):
            raise ValueError("component tags must be a list of non-empty strings")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
            or not math.isfinite(self.confidence)
        ):
            raise ValueError("component confidence must be a finite number from 0 to 1")
        if self.start is not None or self.end is not None:
            if (
                type(self.start) is not int
                or type(self.end) is not int
                or self.start < 0
                or self.end <= self.start
            ):
                raise ValueError("component offsets must satisfy 0 <= start < end")

    @property
    def slug(self) -> str:
        """Return a short display slug without changing component identity."""
        return (
            re.sub(r"[^a-z0-9]+", "-", self.content.splitlines()[0].lower()).strip("-")[:64]
            or self.id
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Component:
        if not isinstance(data, dict):
            raise ValueError("component must be a JSON object")
        try:
            return cls(**data)
        except TypeError as exc:
            raise ValueError(f"invalid component fields: {exc}") from exc


@dataclass
class PromptSpec:
    """Original prompt text and its ordered components."""

    raw: str
    product: str = ""
    version: str = ""
    components: list[Component] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in ("raw", "product", "version"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"prompt {name} must be a string")
        if not isinstance(self.components, list) or any(
            not isinstance(component, Component) for component in self.components
        ):
            raise ValueError("components must be a list of Component objects")

    def by_kind(self, kind: str) -> list[Component]:
        return [component for component in self.components if component.kind == kind]

    def stats(self) -> dict[str, int]:
        return {kind: len(items) for kind in VALID_COMPONENT_KINDS if (items := self.by_kind(kind))}

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "raw": self.raw,
            "product": self.product,
            "version": self.version,
            "stats": self.stats(),
            "components": [component.to_dict() for component in self.components],
        }

    def save(self, path: str | Path) -> None:
        atomic_write(path, json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n")

    @classmethod
    def from_dict(cls, data: dict) -> PromptSpec:
        if not isinstance(data, dict):
            raise ValueError("prompt spec must be a JSON object")
        unknown = (
            set(data) - {item.name for item in fields(cls)} - {"schema_version", "stats", "$schema"}
        )
        if unknown:
            raise ValueError(f"unknown prompt spec fields: {', '.join(sorted(unknown))}")
        if "$schema" in data and not isinstance(data["$schema"], str):
            raise ValueError("$schema must be a string; schema URLs are never fetched")
        schema_version = data.get("schema_version", SCHEMA_VERSION)
        if type(schema_version) is not int or schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported prompt schema version: {schema_version!r}")
        if not isinstance(data.get("components"), list):
            raise ValueError("prompt spec components must be a list")
        # Initial-release files had no raw field or schema_version.
        spec = cls(
            raw=data.get("raw", ""),
            product=data.get("product", ""),
            version=data.get("version", ""),
            components=[Component.from_dict(item) for item in data["components"]],
        )
        seen = set()
        previous_end = 0
        for component in spec.components:
            if component.id in seen:
                raise ValueError(f"duplicate component id {component.id!r}")
            seen.add(component.id)
            if component.start is not None:
                if component.start < previous_end:
                    raise ValueError("component source spans are out of order or overlap")
                if (
                    component.end > len(spec.raw)
                    or spec.raw[component.start : component.end] != component.content
                ):
                    raise ValueError(
                        f"component {component.id!r} span does not match the original source"
                    )
                previous_end = component.end
        if "stats" in data:
            stats = data["stats"]
            if (
                not isinstance(stats, dict)
                or any(type(value) is not int or value < 1 for value in stats.values())
                or stats != spec.stats()
            ):
                raise ValueError("prompt stats do not match the serialized components")
        return spec

    @classmethod
    def load(cls, path: str | Path) -> PromptSpec:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8-sig")))

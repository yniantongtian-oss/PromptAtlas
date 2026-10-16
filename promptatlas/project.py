"""Repeatable project checks from explicit, portable prompt contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from ._io import resolve_path
from .lint import Finding, lint_spec
from .load import load_prompt, read_text
from .schema import VALID_COMPONENT_KINDS


def _required(value: object, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(kind, str) or kind not in VALID_COMPONENT_KINDS for kind in value
    ):
        raise ValueError(f"{location} must be a list of valid component kinds")
    return tuple(dict.fromkeys(value))


def _strict(value: object, location: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{location} must be a boolean")
    return value


def _path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("prompt path must be a non-empty string")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or path == PurePosixPath(".")
        or any(char in value for char in '<>:"\\|?*')
    ):
        raise ValueError(f"prompt path must be a relative path using forward slashes: {value!r}")
    return path.as_posix()


def _resolve(root: Path, relative: str) -> Path:
    path = resolve_path(root / relative)
    if not path.is_relative_to(root):
        raise ValueError(f"prompt path resolves outside the project: {relative!r}")
    return path


@dataclass(frozen=True)
class PromptContract:
    """Resolved requirements for one explicitly listed project file."""

    path: str
    required_kinds: tuple[str, ...]
    strict: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _path(self.path))
        if not isinstance(self.required_kinds, tuple):
            raise ValueError("required_kinds must be a tuple of valid component kinds")
        required = _required(list(self.required_kinds), "required_kinds")
        object.__setattr__(self, "required_kinds", required)
        _strict(self.strict, "contract strict")


@dataclass(frozen=True)
class ProjectConfig:
    path: Path
    prompts: tuple[PromptContract, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", resolve_path(self.path))
        if (
            not isinstance(self.prompts, tuple)
            or not self.prompts
            or any(not isinstance(item, PromptContract) for item in self.prompts)
        ):
            raise ValueError("project prompts must be a non-empty tuple of PromptContract objects")
        seen = set()
        for contract in self.prompts:
            resolved = _resolve(self.root, contract.path)
            if resolved in seen:
                raise ValueError(f"duplicate project prompt path: {contract.path!r}")
            seen.add(resolved)

    @property
    def root(self) -> Path:
        return self.path.parent


def load_project(path: str | Path = "promptatlas.json") -> ProjectConfig:
    """Validate a JSON project file; listed files are relative to its directory."""
    path = resolve_path(path)
    data = json.loads(read_text(path))
    if not isinstance(data, dict):
        raise ValueError("project configuration must be a JSON object")
    unknown = set(data) - {"$schema", "schema_version", "strict", "require", "prompts"}
    if unknown:
        raise ValueError(f"unknown project fields: {', '.join(sorted(unknown))}")
    if "$schema" in data and not isinstance(data["$schema"], str):
        raise ValueError("project $schema must be a string; URLs are never fetched")
    version = data.get("schema_version", 1)
    if type(version) is not int or version != 1:
        raise ValueError(f"unsupported project schema version: {version!r}")
    strict = _strict(data.get("strict", False), "project strict")
    required = _required(data.get("require", []), "project require")
    entries = data.get("prompts")
    if not isinstance(entries, list) or not entries:
        raise ValueError("project prompts must be a non-empty list")
    prompts = []
    seen = set()
    for index, entry in enumerate(entries, 1):
        if isinstance(entry, str):
            entry = {"path": entry}
        if not isinstance(entry, dict):
            raise ValueError(f"prompt entry {index} must be a path string or object")
        unknown = set(entry) - {"path", "require", "strict"}
        if unknown:
            raise ValueError(
                f"unknown fields in prompt entry {index}: {', '.join(sorted(unknown))}"
            )
        relative = _path(entry.get("path"))
        resolved = _resolve(path.parent, relative)
        if resolved in seen:
            raise ValueError(f"duplicate project prompt path: {relative!r}")
        seen.add(resolved)
        prompts.append(
            PromptContract(
                path=relative,
                required_kinds=tuple(
                    dict.fromkeys(
                        (*required, *_required(entry.get("require", []), f"prompt {index} require"))
                    )
                ),
                strict=_strict(entry.get("strict", strict), f"prompt {index} strict"),
            )
        )
    return ProjectConfig(path=path, prompts=tuple(prompts))


@dataclass
class FileCheck:
    path: str
    strict: bool
    source_format: str
    stats: dict[str, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None or any(
            item.severity == "error" or self.strict for item in self.findings
        )

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "ok": not self.failed,
            "strict": self.strict,
            "source_format": self.source_format,
            "stats": self.stats,
            "findings": [item.to_dict() for item in self.findings],
            "error": self.error,
        }


@dataclass
class ProjectReport:
    config: ProjectConfig
    files: list[FileCheck]

    @property
    def exit_code(self) -> int:
        if any(item.error is not None for item in self.files):
            return 2
        return int(any(item.failed for item in self.files))

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "config": self.config.path.name,
            "ok": self.exit_code == 0,
            "summary": {
                "files": len(self.files),
                "passed": sum(not item.failed for item in self.files),
                "failed": sum(item.failed for item in self.files),
                "invalid": sum(item.error is not None for item in self.files),
                "errors": sum(
                    finding.severity == "error" for item in self.files for finding in item.findings
                ),
                "warnings": sum(
                    finding.severity == "warning"
                    for item in self.files
                    for finding in item.findings
                ),
            },
            "files": [item.to_dict() for item in self.files],
        }


def check_project(path: str | Path | ProjectConfig = "promptatlas.json") -> ProjectReport:
    """Check every listed prompt; bad files do not hide results from other files."""
    config = path if isinstance(path, ProjectConfig) else load_project(path)
    results = []
    for contract in config.prompts:
        item = FileCheck(
            contract.path,
            contract.strict,
            "spec" if Path(contract.path).suffix.casefold() == ".json" else "text",
        )
        try:
            spec = load_prompt(_resolve(config.root, contract.path))
            item.stats = spec.stats()
            item.findings = lint_spec(spec, required_kinds=contract.required_kinds)
        except OSError as exc:
            item.error = exc.strerror or str(exc)
        except ValueError as exc:
            item.error = str(exc)
        results.append(item)
    return ProjectReport(config=config, files=results)

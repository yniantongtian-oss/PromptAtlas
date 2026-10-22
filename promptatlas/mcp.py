"""Optional stdio MCP server for the existing prompt workflows.

The core package does not import this module. Install the ``mcp`` extra to
serve it. Tools accept text, not paths, and do not make network calls.
"""

from __future__ import annotations

import inspect
import sys
from typing import Any, NoReturn

from . import __version__
from .diff import diff_specs, diff_to_dict
from .generate import generate_prompt
from .lint import lint_prompt
from .parse import parse_prompt

INSTRUCTIONS = (
    "Offline read-only tools for system prompts. "
    "parse extracts ordered components and source spans. "
    "lint reports structural findings and does not judge safety or model behavior. "
    "compare diffs two prompt texts. "
    "compose drafts an editable prompt from the bundled atlas and does not call a model. "
    "Tools accept text, not file paths, and do not read the network."
)
_HOMEPAGE = "https://github.com/yniantongtian-oss/PromptAtlas"


def _reject(message: str) -> NoReturn:
    """Surface a validation failure the host can read.

    Without the SDK installed, callers still get the library's ValueError.
    """
    try:
        from mcp.server.mcpserver.exceptions import ToolError
    except ModuleNotFoundError:
        raise ValueError(message) from None
    raise ToolError(message)


def _missing_sdk(exc: ModuleNotFoundError) -> bool:
    name = exc.name or ""
    return name == "mcp" or name.startswith(("mcp.", "mcp_types"))


def parse(text: str, product: str = "", version: str = "") -> dict[str, Any]:
    """Parse a system prompt into ordered components.

    ``text`` is the original prompt, including its line endings. ``product``
    and ``version`` are optional labels stored on the spec. The result matches
    ``PromptSpec.to_dict()``: schema_version, raw, product, version, stats, and
    components with Unicode offsets. Parsing is an English-oriented heuristic,
    not a safety verdict. Equal inputs produce equal JSON.
    """
    try:
        spec = parse_prompt(text, product=product, version=version)
    except ValueError as exc:
        _reject(str(exc))
    return spec.to_dict()


def lint(
    text: str,
    strict: bool = False,
    required_kinds: list[str] | None = None,
    allowed_variables: list[str] | None = None,
) -> dict[str, Any]:
    """Lint prompt structure and return explainable findings.

    The result contains ``ok``, ``errors``, ``warnings``, and ``findings``.
    ``ok`` is false when any finding is an error. ``strict`` also makes
    warnings fail the gate. Findings are returned either way, so a failed gate
    is still a normal tool result. ``required_kinds`` lists component kinds
    that must appear. ``allowed_variables`` declares intentional template names
    such as ``input`` or ``release.name``. Templates are not rendered.
    """
    try:
        findings = lint_prompt(
            text,
            required_kinds=tuple(required_kinds or ()),
            allowed_variables=tuple(allowed_variables or ()),
        )
    except ValueError as exc:
        _reject(str(exc))
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    return {
        "ok": not (errors or (strict and warnings)),
        "errors": errors,
        "warnings": warnings,
        "findings": [item.to_dict() for item in findings],
    }


def compare(
    before: str,
    after: str,
    before_product: str = "",
    before_version: str = "",
    after_product: str = "",
    after_version: str = "",
) -> dict[str, Any]:
    """Compare two prompt texts and return a component diff.

    Both arguments are prompt text, not file paths or saved spec JSON. Pass a
    saved spec's ``raw`` field to compare stored prompts. The result reports
    disjoint added, removed, and changed components, plus similarity,
    reordered, and has_changes. Similarity is lexical, not a judgment of model
    behavior.
    """
    try:
        spec_a = parse_prompt(before, product=before_product, version=before_version)
        spec_b = parse_prompt(after, product=after_product, version=after_version)
    except ValueError as exc:
        _reject(str(exc))
    return diff_to_dict(diff_specs(spec_a, spec_b))


def compose(scenario: str, max_per_kind: int = 5) -> str:
    """Compose an editable prompt draft for a scenario.

    Components come from the bundled read-only atlas, ranked by keyword and
    tag overlap. ``max_per_kind`` must be a positive integer. The draft is
    deterministic and must be reviewed before use. No model is called and no
    tools are registered.
    """
    try:
        return generate_prompt(scenario, max_per_kind=max_per_kind)
    except ValueError as exc:
        _reject(str(exc))


def build_server():
    """Return an MCP server that exposes parse, lint, compare, and compose."""
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations

    server = MCPServer(
        "promptatlas",
        instructions=INSTRUCTIONS,
        website_url=_HOMEPAGE,
        version=__version__,
    )
    hints = ToolAnnotations(read_only_hint=True, open_world_hint=False)
    for function, title in (
        (parse, "Parse a system prompt"),
        (lint, "Lint prompt structure"),
        (compare, "Compare two prompts"),
        (compose, "Compose a prompt draft"),
    ):
        server.tool(title=title, annotations=hints)(function)
    return server


def main() -> None:
    """Serve parse, lint, compare, and compose over MCP stdio."""
    try:
        server = build_server()
    except ModuleNotFoundError as exc:
        if _missing_sdk(exc):
            sys.stderr.write(
                "promptatlas-mcp requires the optional mcp extra:\n"
                '  python -m pip install "promptatlas[mcp]"\n'
            )
            raise SystemExit(1) from None
        raise
    server.run(transport="stdio")


for _function in (parse, lint, compare, compose):
    if _function.__doc__:
        _function.__doc__ = inspect.cleandoc(_function.__doc__)


if __name__ == "__main__":
    main()

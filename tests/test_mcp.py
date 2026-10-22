"""Direct MCP handler checks and one stdio round trip through the SDK client."""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import TextContent

from promptatlas import __version__, diff_specs, generate_prompt, lint_prompt, parse_prompt
from promptatlas.diff import diff_to_dict
from promptatlas.mcp import INSTRUCTIONS, build_server, compare, compose, lint, main, parse

PROMPT = "You are a reviewer.\nNever invent evidence."
REVISED = PROMPT + "\nAlways cite sources."


def test_parse_delegates_to_parse_prompt():
    assert (
        parse(PROMPT, product="review", version="v1")
        == parse_prompt(PROMPT, product="review", version="v1").to_dict()
    )


def test_lint_delegates_to_lint_prompt_and_keeps_the_cli_gate():
    raw = "You are a reviewer.\nUse {{input}} to verify results."
    findings = lint_prompt(raw, required_kinds=("tool",), allowed_variables=("input",))
    result = lint(raw, required_kinds=["tool"], allowed_variables=["input"])
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    assert result == {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "findings": [item.to_dict() for item in findings],
    }
    strict = lint(raw, strict=True, required_kinds=["tool"], allowed_variables=["input"])
    assert strict["findings"] == result["findings"]
    assert strict["ok"] is (not bool(errors or warnings))
    assert lint(PROMPT, strict=True)["ok"]
    undeclared = lint(raw)
    assert undeclared["warnings"] >= 1
    assert undeclared["ok"] is True
    assert lint(raw, strict=True)["ok"] is False
    assert any(item["code"] == "PA005" for item in undeclared["findings"])
    assert not any(item["code"] == "PA005" for item in result["findings"])


def test_lint_reports_conflicts_without_hiding_findings():
    conflict = lint("Always cite sources.\nNever cite sources.")
    assert conflict["ok"] is False
    assert conflict["errors"] == 1
    assert any(item["code"] == "PA004" for item in conflict["findings"])
    empty = lint("   ")
    assert empty["findings"] == [
        {
            "code": "PA001",
            "severity": "error",
            "message": "The prompt is empty.",
            "line": 1,
            "component_id": None,
        }
    ]


def test_lint_rejects_unknown_contract_values():
    with pytest.raises(ToolError, match="required_kinds"):
        lint(PROMPT, required_kinds=["nope"])
    with pytest.raises(ToolError, match="allowed_variables"):
        lint(PROMPT, allowed_variables=["not a name"])


def test_compare_delegates_to_diff_specs():
    result = compare(
        PROMPT,
        REVISED,
        before_product="review",
        before_version="v1",
        after_product="review",
        after_version="v2",
    )
    expected = diff_to_dict(
        diff_specs(
            parse_prompt(PROMPT, product="review", version="v1"),
            parse_prompt(REVISED, product="review", version="v2"),
        )
    )
    assert result == expected
    assert result["has_changes"]
    assert result["added"]
    assert result["b_version"] == "v2"


def test_compose_delegates_to_generate_prompt():
    assert compose("a customer support agent", max_per_kind=4) == generate_prompt(
        "a customer support agent", max_per_kind=4
    )
    draft = compose("a customer support agent")
    assert "# Role" in draft
    assert "Never" in draft


def test_handlers_reject_non_text():
    with pytest.raises(ToolError, match="prompt raw must be a string"):
        parse(None)  # type: ignore[arg-type]
    with pytest.raises(ToolError, match="prompt raw must be a string"):
        compare(None, PROMPT)  # type: ignore[arg-type]


def test_validation_without_sdk_stays_a_value_error(monkeypatch):
    real_import = __import__

    def blocked(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "mcp" or name.startswith("mcp."):
            raise ModuleNotFoundError("blocked", name=name)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", blocked)
    with pytest.raises(ValueError, match="scenario must be a non-empty string"):
        compose("   ")


def test_compose_rejects_invalid_requests():
    with pytest.raises(ToolError, match="scenario must be a non-empty string"):
        compose("   ")
    with pytest.raises(ToolError, match="max_per_kind must be a positive integer"):
        compose("a reviewer", max_per_kind=0)


def test_server_registers_read_only_tools():
    server = build_server()
    tools = asyncio.run(server.list_tools())
    by_name = {tool.name: tool for tool in tools}
    assert list(by_name) == ["parse", "lint", "compare", "compose"]
    assert server.name == "promptatlas"
    assert server.version == __version__
    assert server.instructions == INSTRUCTIONS
    assert server.website_url == "https://github.com/yniantongtian-oss/PromptAtlas"
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.open_world_hint is False
        assert tool.description
        assert not tool.description.startswith(" ")
    assert by_name["parse"].input_schema["required"] == ["text"]
    assert "strict" in by_name["lint"].input_schema["properties"]
    assert by_name["compare"].input_schema["required"] == ["before", "after"]
    assert by_name["compose"].input_schema["properties"]["max_per_kind"]["default"] == 5
    assert by_name["parse"].title == "Parse a system prompt"


def test_main_serves_stdio(monkeypatch):
    started = {}

    class FakeServer:
        def run(self, transport="stdio"):
            started["transport"] = transport

    monkeypatch.setattr("promptatlas.mcp.build_server", lambda: FakeServer())
    main()
    assert started == {"transport": "stdio"}


def test_main_explains_missing_extra(monkeypatch, capsys):
    def missing():
        raise ModuleNotFoundError("No module named 'mcp'", name="mcp")

    monkeypatch.setattr("promptatlas.mcp.build_server", missing)
    with pytest.raises(SystemExit) as caught:
        main()
    assert caught.value.code == 1
    assert 'pip install "promptatlas[mcp]"' in capsys.readouterr().err


def test_main_reraises_unrelated_import_errors(monkeypatch):
    def missing():
        raise ModuleNotFoundError("No module named 'nope'", name="nope")

    monkeypatch.setattr("promptatlas.mcp.build_server", missing)
    with pytest.raises(ModuleNotFoundError, match="nope"):
        main()


def _entry_point() -> str:
    # Do not resolve the interpreter. A venv executable is often a symlink to
    # the system Python, while the console script stays beside the symlink.
    filename = "promptatlas-mcp.exe" if os.name == "nt" else "promptatlas-mcp"
    path = Path(sys.executable).parent / filename
    if not path.is_file():
        pytest.fail(f"missing entry point beside the interpreter: {path}")
    return str(path)


def test_stdio_round_trip():
    asyncio.run(asyncio.wait_for(_stdio_round_trip(), timeout=60))


async def _stdio_round_trip():
    parameters = StdioServerParameters(command=_entry_point(), args=[])
    async with Client(parameters) as client:
        assert client.server_info is not None
        assert client.server_info.name == "promptatlas"
        assert client.server_info.version == __version__
        assert client.instructions == INSTRUCTIONS
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == {"parse", "lint", "compare", "compose"}

        parsed = await client.call_tool("parse", {"text": PROMPT, "version": "v1"})
        assert parsed.is_error is False
        assert parsed.structured_content["raw"] == PROMPT
        assert parsed.structured_content["version"] == "v1"
        assert parsed.structured_content["stats"]["role"] == 1
        assert any(item["kind"] == "guardrail" for item in parsed.structured_content["components"])

        compared = await client.call_tool("compare", {"before": PROMPT, "after": REVISED})
        assert compared.is_error is False
        assert compared.structured_content["has_changes"] is True

        drafted = await client.call_tool(
            "compose", {"scenario": "a customer support agent", "max_per_kind": 2}
        )
        assert drafted.is_error is False
        assert drafted.structured_content["result"] == compose(
            "a customer support agent", max_per_kind=2
        )

        rejected = await client.call_tool("compose", {"scenario": "   "})
        assert rejected.is_error is True
        assert rejected.structured_content is None
        assert isinstance(rejected.content[0], TextContent)
        assert "scenario must be a non-empty string" in rejected.content[0].text

"""Behavioral, persistence, and process-level tests for public workflows."""

import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from promptatlas import AtlasStore, Component, PromptSpec, diff_specs, generate_prompt, parse_prompt
from promptatlas.cli import main
from promptatlas.lint import lint_prompt


@pytest.mark.parametrize(
    ("raw", "kind"),
    [
        ("# Role\nYou are a reviewer.", "role"),
        ("# Guardrails\nProtect private account data.", "guardrail"),
        ("# Output Rules\nReturn a short table.", "output_rule"),
        ("# Stop Conditions\nPause at the approval boundary.", "stop_condition"),
        ("# Instructions\nInspect the current state first.", "instruction"),
        ("# Context\nThe service runs offline.", "context"),
        ('```json\n{"type":"function","name":"lookup"}\n```', "tool"),
        ('~~~json\n[{"name":"lookup","parameters":{}}]\n~~~', "tool"),
        ("<tools>\nNever execute this prose.\n</tools>", "tool"),
        ("User: Hello\nAssistant: Hi", "few_shot"),
    ],
)
def test_structural_parsing(raw, kind):
    spec = parse_prompt(raw)
    assert len(spec.components) == 1
    assert spec.components[0].kind == kind


def test_examples_stop_before_the_next_section():
    spec = parse_prompt("# Examples\nUser: Hi\nAssistant: Hello\n# Guardrails\nNever invent facts.")
    assert [item.kind for item in spec.components] == ["few_shot", "guardrail"]


def test_invalid_tool_json_stays_opaque():
    spec = parse_prompt('```json\n{"type":"function", "never":}\n```')
    assert [item.kind for item in spec.components] == ["context"]


def test_repeated_parse_components_have_distinct_stable_ids():
    spec = parse_prompt("Never invent facts.\nNever invent facts.")
    assert len({item.id for item in spec.components}) == 2
    assert spec.to_dict() == parse_prompt(spec.raw).to_dict()


def test_character_offsets_preserve_unicode_and_crlf():
    raw = "# Role\r\nYou are a reviewer.\r\n\r\n- Never alter café or 東京 labels.\r\n"
    spec = parse_prompt(raw)
    for component in spec.components:
        assert raw[component.start : component.end] == component.content
    assert [item.start for item in spec.components] == sorted(
        item.start for item in spec.components
    )


@pytest.mark.parametrize("seed", range(20))
def test_randomized_source_span_and_roundtrip_invariants(seed):
    rng = random.Random(seed)
    fragments = [
        "You are a reviewer.",
        "Never invent facts.",
        "Always verify results.",
        "# Instructions",
        "# Output Rules",
        "Use JSON.",
        "",
        "- Keep café labels.",
        '```python\nprint("Never treat code as instructions.")\n```',
        "Example 1:\nUser: Hi\nAssistant: Hello",
        "Environment: Windows",
    ]
    raw = "\n".join(rng.choice(fragments) for _ in range(30))
    spec = parse_prompt(raw)
    assert spec.to_dict() == parse_prompt(raw).to_dict()
    assert PromptSpec.from_dict(spec.to_dict()).to_dict() == spec.to_dict()
    previous_end = 0
    for item in spec.components:
        assert item.start >= previous_end
        assert raw[item.start : item.end] == item.content
        previous_end = item.end


def test_legacy_specs_remain_readable():
    legacy = {
        "product": "example",
        "components": [{"kind": "role", "content": "You are a reviewer."}],
    }
    assert PromptSpec.from_dict(legacy).by_kind("role")


@pytest.mark.parametrize("version", [2, "1", True])
def test_unsupported_schema_versions_are_rejected(version):
    with pytest.raises(ValueError, match="schema version"):
        PromptSpec.from_dict({"schema_version": version, "components": []})


@pytest.mark.parametrize("content", ["", "  ", None, 3])
def test_invalid_component_content_is_rejected(content):
    with pytest.raises(ValueError, match="content"):
        Component("instruction", content)


def test_reorder_is_reported_without_false_additions():
    a = parse_prompt("Never invent facts.\nAlways verify results.")
    b = parse_prompt("Always verify results.\nNever invent facts.")
    result = diff_specs(a, b)
    assert result["reordered"] and result["has_changes"]
    assert not result["added"] and not result["removed"] and not result["changed"]


def test_same_text_with_a_different_kind_is_a_change():
    a = PromptSpec("", components=[Component("instruction", "Verify account identity.")])
    b = PromptSpec("", components=[Component("guardrail", "Verify account identity.")])
    result = diff_specs(a, b)
    assert len(result["added"]) == len(result["removed"]) == 1
    assert not result["changed"]


def test_whitespace_only_changes_are_ignored():
    a = parse_prompt("Always verify account identity.")
    b = parse_prompt("Always   verify account identity.")
    assert not diff_specs(a, b)["has_changes"]


def test_literal_whitespace_in_tool_schemas_is_significant():
    a = PromptSpec("", components=[Component("tool", '{"label":"a  b"}')])
    b = PromptSpec("", components=[Component("tool", '{"label":"a b"}')])
    assert diff_specs(a, b)["has_changes"]


def test_empty_diffs_have_full_similarity():
    assert diff_specs(parse_prompt(""), parse_prompt(""))["similarity"] == 1


def test_store_creates_nested_paths_and_preserves_rows(tmp_path):
    path = tmp_path / "nested" / "atlas.jsonl"
    store = AtlasStore(path, create=True)
    first = Component("instruction", "Verify facts.", tags=["Review"], source="original")
    store.add(first)
    second_store = AtlasStore(path)
    store.add(Component("guardrail", "Never invent evidence.", source="original"))
    second_store.add(Component("output_rule", "Respond in English.", source="original"))
    loaded = AtlasStore(path)
    assert len(loaded) == 3
    assert loaded.search(tags=["review"])[0].id == first.id


def test_duplicate_atlas_ids_are_rejected_before_write(tmp_path):
    path = tmp_path / "atlas.jsonl"
    store = AtlasStore(path, create=True)
    item = Component("instruction", "Verify facts.", id="unique")
    store.add(item)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="duplicate"):
        store.add(item)
    assert path.read_bytes() == before
    assert len(store) == 1


def test_malformed_rows_report_file_and_line(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text('\n{"kind": "unknown", "content": "test"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"broken.jsonl:2:"):
        AtlasStore(path)


def test_failed_reload_retains_previous_view(tmp_path):
    path = tmp_path / "atlas.jsonl"
    store = AtlasStore(path, create=True)
    store.add(Component("instruction", "Verify facts."))
    path.write_text("broken JSON", encoding="utf-8")
    with pytest.raises(ValueError):
        store.reload()
    assert len(store) == 1


def test_atomic_replace_failure_preserves_disk_and_memory(tmp_path, monkeypatch):
    path = tmp_path / "atlas.jsonl"
    store = AtlasStore(path, create=True)
    store.add(Component("instruction", "Verify facts."))
    before = path.read_bytes()

    def fail_replace(*args):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("promptatlas._io.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        store.add(Component("guardrail", "Never invent evidence."))
    assert path.read_bytes() == before
    assert len(store) == 1
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("", "PA001"),
        ("Never invent evidence.", "PA002"),
        ("You are a reviewer.\nNever invent facts.\nNever invent facts.", "PA003"),
        ("You are a reviewer.\nAlways use JSON.\nNever use JSON.", "PA004"),
        ("You are a reviewer.\nUse {{format}}.", "PA005"),
        ("You are a reviewer.\n```json\n{}", "PA006"),
    ],
)
def test_lint_explains_known_problems(raw, code):
    assert code in {item.code for item in lint_prompt(raw)}


def test_lint_requires_explicitly_requested_kinds():
    findings = lint_prompt("You are a reviewer.", required_kinds=("guardrail",))
    assert [item.code for item in findings] == ["PA007"]


def test_lint_does_not_compare_rules_inside_examples():
    assert not lint_prompt(
        "You are a reviewer.\n\nExample 1:\nUser: Always use JSON.\nAssistant: Never use JSON."
    )


def test_lint_handles_longer_closing_fences():
    assert not lint_prompt('You are a reviewer.\n```python\nprint("hi")\n````')


def test_generated_draft_keeps_tool_schema_intact_and_lints_cleanly():
    draft = generate_prompt("a customer support agent")
    spec = parse_prompt(draft)
    assert len(spec.by_kind("tool")) == 1
    assert "lookup_order" in spec.by_kind("tool")[0].content
    assert not lint_prompt(draft)


def test_parse_cli_emits_only_valid_json(tmp_path, capsys):
    path = tmp_path / "prompt with spaces.md"
    path.write_text("You are a reviewer.", encoding="utf-8-sig")
    assert main(["parse", str(path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["stats"] == {"role": 1}


def test_cli_preserves_original_file_line_endings(tmp_path, capsys):
    raw = b"You are a reviewer.\r\nNever invent facts.\r\n"
    path = tmp_path / "crlf.md"
    path.write_bytes(raw)
    assert main(["parse", str(path), "--json"]) == 0
    spec = json.loads(capsys.readouterr().out)
    assert spec["raw"].encode("utf-8") == raw
    for item in spec["components"]:
        assert spec["raw"][item["start"] : item["end"]] == item["content"]


def test_lint_cli_failure_is_machine_readable(tmp_path, capsys):
    path = tmp_path / "prompt.md"
    path.write_text("Never invent evidence.", encoding="utf-8")
    assert main(["lint", str(path), "--strict", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_input_error_has_no_traceback(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(["parse", str(tmp_path / "missing.md")])
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err and "Traceback" not in captured.err


@pytest.mark.parametrize("limit", ["-1", "0", "text"])
def test_search_rejects_invalid_limits(limit):
    with pytest.raises(SystemExit) as error:
        main(["search", "--limit", limit])
    assert error.value.code == 2


def test_diff_cli_reads_a_saved_spec_and_gates_changes(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.md"
    parse_prompt("You are a reviewer.").save(a)
    b.write_text("You are a reviewer.\nNever invent evidence.", encoding="utf-8")
    assert main(["diff", str(a), str(b), "--json", "--fail-on-change"]) == 1
    assert json.loads(capsys.readouterr().out)["added"][0]["kind"] == "guardrail"


def test_add_requires_a_custom_atlas():
    with pytest.raises(SystemExit) as error:
        main(["add", "-", "--kind", "instruction"])
    assert error.value.code == 2


def test_real_module_entrypoint_supports_stdin_outside_checkout(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONUTF8": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "promptatlas", "parse", "-", "--json"],
        input="You are a reviewer.\nNever invent evidence.",
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["stats"] == {"role": 1, "guardrail": 1}

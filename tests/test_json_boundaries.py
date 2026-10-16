"""Real serialized inputs must not hide policy or escape input-error handling."""

import json
import subprocess
import sys

import pytest

from promptatlas import (
    AtlasStore,
    Component,
    PromptSpec,
    check_project,
    generate_prompt,
    load_project,
    parse_prompt,
)
from promptatlas.cli import main


def nested_tool(depth):
    return "[" * depth + '{"name":"lookup","parameters":{}}' + "]" * depth


def test_deep_decodable_tool_lists_do_not_recurse_through_python_frames():
    raw = "```json\n" + nested_tool(700) + "\n```"
    spec = parse_prompt(raw)
    assert [item.kind for item in spec.components] == ["tool"]
    assert spec.components[0].content == raw
    assert spec.raw[spec.components[0].start : spec.components[0].end] == raw


def test_tool_json_beyond_decoder_limits_remains_opaque_original_context():
    raw = "```json\n" + nested_tool(4000) + "\n```"
    spec = parse_prompt(raw)
    assert [(item.kind, item.content) for item in spec.components] == [("context", raw)]


@pytest.mark.parametrize(
    "body",
    [
        "[]",
        '[{}, {"type":"function"}]',
        '{"tools":[]}',
        '{"tools":[{"type":"function"},{}]}',
        '[false, {"type":"function"}]',
        '{"tools":"function"}',
        '{"type":"function","type":"other"}',
        '{"type":"function","parameters":{"value":NaN}}',
        '{"type":"function","parameters":{"value":Infinity}}',
        '{"type":"function","parameters":{"value":1e9999}}',
    ],
)
def test_non_tool_or_ambiguous_json_is_never_promoted_to_a_tool(body):
    raw = "```json\n" + body + "\n```"
    assert [(item.kind, item.content) for item in parse_prompt(raw).components] == [
        ("context", raw)
    ]


def test_ordinary_json_numbers_and_strings_remain_readable(tmp_path):
    component = Component(
        "instruction", "Use NaN and Infinity as literal labels.", confidence=0.625
    )
    path = tmp_path / "spec.json"
    original = PromptSpec("", components=[component])
    original.save(path)
    assert PromptSpec.load(path).to_dict() == original.to_dict()
    spec = parse_prompt('```json\n{"type":"function","parameters":{"n":1.25e-2}}\n```')
    assert spec.by_kind("tool")


@pytest.mark.parametrize(
    "text",
    [
        '{"strict":true,"strict":false,"prompts":["system.md"]}',
        r'{"strict":true,"\u0073trict":false,"prompts":["system.md"]}',
        '{"prompts":[{"path":"system.md","strict":true,"strict":false}]}',
    ],
)
def test_duplicate_project_policy_keys_cannot_silently_override_each_other(tmp_path, text, capsys):
    config = tmp_path / "promptatlas.json"
    config.write_text(text, encoding="utf-8")
    (tmp_path / "system.md").write_text("Never invent facts.", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        load_project(config)
    with pytest.raises(SystemExit) as exc:
        main(["check", "--config", str(config), "--json"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert not captured.out and "duplicate JSON object key" in captured.err
    assert "Traceback" not in captured.err


def test_same_keys_in_separate_file_objects_are_not_duplicates(tmp_path):
    config = tmp_path / "promptatlas.json"
    config.write_text('{"prompts":[{"path":"a.md"},{"path":"b.md"}]}', encoding="utf-8")
    assert len(load_project(config).prompts) == 2


def test_saved_specs_reject_duplicate_component_keys_and_preserve_input(tmp_path):
    path = tmp_path / "spec.json"
    original = (
        b'{"components":[{"kind":"role","kind":"guardrail","content":"Never invent facts."}]}'
    )
    path.write_bytes(original)
    with pytest.raises(ValueError, match="duplicate JSON object key: 'kind'"):
        PromptSpec.load(path)
    assert path.read_bytes() == original


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e9999"])
def test_saved_specs_reject_non_finite_number_decoding(tmp_path, number):
    path = tmp_path / "spec.json"
    path.write_text(
        '{"components":[{"kind":"instruction","content":"Verify results.","confidence":'
        + number
        + "}]}",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="finite"):
        PromptSpec.load(path)


def test_bad_jsonl_rows_do_not_mutate_an_existing_atlas_view(tmp_path):
    path = tmp_path / "atlas.jsonl"
    store = AtlasStore(path, create=True)
    store.add(Component("instruction", "Verify results.", id="valid"))
    path.write_bytes(
        path.read_bytes() + b'{"kind":"role","kind":"guardrail","content":"Never invent facts."}\n'
    )
    before = path.read_bytes()
    with pytest.raises(ValueError, match=r"atlas.jsonl:2: duplicate JSON object key"):
        store.reload()
    assert len(store) == 1 and store.search()[0].id == "valid"
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        store.add(Component("instruction", "Keep provenance."))
    assert path.read_bytes() == before and len(store) == 1


def test_deep_specs_are_input_errors_and_do_not_hide_other_project_results(tmp_path):
    (tmp_path / "deep.json").write_text(nested_tool(4000), encoding="utf-8")
    (tmp_path / "good.md").write_text("You are a reviewer.", encoding="utf-8")
    config = tmp_path / "promptatlas.json"
    config.write_text('{"prompts":["deep.json","good.md"]}', encoding="utf-8")
    report = check_project(config)
    assert report.exit_code == 2
    assert "nesting" in report.files[0].error
    assert report.files[1].stats == {"role": 1}
    result = subprocess.run(
        [sys.executable, "-m", "promptatlas", "check", "--config", str(config), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 2 and "Traceback" not in result.stderr
    assert json.loads(result.stdout)["summary"]["invalid"] == 1


def test_generation_keeps_undecodable_tool_content_without_crashing(tmp_path):
    store = AtlasStore(tmp_path / "atlas.jsonl", create=True)
    content = nested_tool(4000)
    store.add(Component("tool", content, tags=["universal"]))
    generated = generate_prompt("an offline reviewer", store=store)
    assert "```text\n" + content + "\n```" in generated


def test_duplicate_key_diagnostics_are_bounded(tmp_path):
    key = "x" * 1000
    config = tmp_path / "promptatlas.json"
    config.write_text('{"' + key + '":1,"' + key + '":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON object key") as exc:
        load_project(config)
    assert len(str(exc.value)) < 160

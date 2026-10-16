"""Published schemas must validate real artifacts and reject invalid shapes."""

import copy
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from promptatlas import AtlasStore, Component, PromptSpec, get_schema, parse_prompt
from promptatlas.cli import main
from promptatlas.schemas import SCHEMA_NAMES


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_schemas_are_self_contained_and_valid(name):
    schema = get_schema(name)
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_all_bundled_components_match_the_component_schema():
    validator = Draft202012Validator(get_schema("component"))
    for item in AtlasStore().search():
        validator.validate(item.to_dict())


def test_parser_output_matches_the_spec_schema():
    spec = parse_prompt("You are a reviewer.\nNever invent facts.")
    Draft202012Validator(get_schema("spec")).validate(spec.to_dict())


@pytest.mark.parametrize(
    "update",
    [
        {"kind": "invalid"},
        {"content": "  "},
        {"confidence": True},
        {"confidence": 1.1},
        {"tags": "security"},
        {"start": 0, "end": None},
        {"end": 5, "start": None},
        {"unknown": True},
    ],
)
def test_component_schema_rejects_invalid_runtime_values(update):
    document = Component("instruction", "Verify evidence.").to_dict()
    document.update(update)
    with pytest.raises(ValidationError):
        Draft202012Validator(get_schema("component")).validate(document)
    with pytest.raises(ValueError):
        Component.from_dict(document)


def test_legacy_spec_matches_schema_and_runtime():
    data = {"components": [{"kind": "role", "content": "You are a reviewer."}]}
    Draft202012Validator(get_schema("spec")).validate(data)
    assert PromptSpec.from_dict(data).by_kind("role")


def test_schema_metadata_is_descriptive_without_changing_component_data():
    data = Component("instruction", "Verify evidence.").to_dict()
    original = copy.deepcopy(data)
    data["$schema"] = "https://unused.invalid/component.schema.json"
    assert Component.from_dict(data).to_dict() == original
    assert "$schema" in data


def test_exported_schema_documents_are_independent():
    schema = get_schema("project")
    schema["properties"].clear()
    assert get_schema("project")["properties"]


def test_unknown_schema_name_is_rejected():
    with pytest.raises(ValueError, match="unknown schema"):
        get_schema("../../secret")


def test_schema_command_emits_one_json_document(capsys):
    assert main(["schema", "project"]) == 0
    assert json.loads(capsys.readouterr().out)["title"] == "PromptAtlas project contract"


def test_schema_command_saves_an_editor_schema(tmp_path, capsys):
    path = tmp_path / "schema with spaces.json"
    assert main(["schema", "spec", "--out", str(path)]) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == get_schema("spec")
    captured = capsys.readouterr()
    assert captured.out == "" and "Wrote" in captured.err

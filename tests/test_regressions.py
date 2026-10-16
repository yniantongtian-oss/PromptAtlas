"""Regression cases for the initial release's observable failures."""

import json

import pytest

from promptatlas import (
    AtlasStore,
    Component,
    PromptSpec,
    diff_specs,
    export_eval_cases,
    generate_prompt,
    parse_prompt,
)


def test_parse_is_reproducible():
    raw = "You are a reviewer.\nNever invent test results."
    assert parse_prompt(raw).to_dict() == parse_prompt(raw).to_dict()


def test_serialization_preserves_original_text(tmp_path):
    raw = "# Role\nYou are a reviewer.\n\nNever invent test results.\n"
    spec = parse_prompt(raw, product="reviewer", version="v1")
    path = tmp_path / "spec.json"
    spec.save(path)
    assert PromptSpec.load(path).raw == raw


def test_few_shot_is_not_counted_twice():
    spec = parse_prompt("You are a tutor.\n\nExample 1:\nUser: Hi\nAssistant: Hello")
    assert len(spec.by_kind("few_shot")) == 1
    assert all("User: Hi" not in c.content for c in spec.components if c.kind != "few_shot")


def test_code_block_does_not_become_a_guardrail():
    spec = parse_prompt('You are a programmer.\n\n```python\nprint("never run")\n```')
    assert not spec.by_kind("guardrail")
    assert any('print("never run")' in c.content for c in spec.components)


def test_stop_rule_takes_precedence_over_negation():
    spec = parse_prompt("Do not proceed until the user confirms the deployment.")
    assert spec.components[0].kind == "stop_condition"


def test_duplicate_rules_are_not_lost_in_diff():
    a = PromptSpec(raw="", components=[Component("guardrail", "Never delete files.")])
    b = PromptSpec(raw="", components=[Component("guardrail", "Never delete files.")] * 2)
    assert len(diff_specs(a, b)["added"]) == 1


def test_case_changes_are_reported():
    a = parse_prompt("Use API_KEY.")
    b = parse_prompt("Use api_key.")
    assert diff_specs(a, b)["similarity"] < 1


def test_changed_components_are_not_also_added_and_removed():
    a = parse_prompt("Always verify account identity before issuing refunds.")
    b = parse_prompt("Always verify account identity before issuing refunds or credits.")
    result = diff_specs(a, b)
    assert len(result["changed"]) == 1
    assert not result["added"]
    assert not result["removed"]


def test_missing_atlas_has_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        AtlasStore(tmp_path / "missing.jsonl")


def test_failed_write_does_not_mutate_store(tmp_path):
    path = tmp_path / "atlas.jsonl"
    path.write_text("", encoding="utf-8")
    store = AtlasStore(path)
    path.unlink()
    path.mkdir()
    with pytest.raises(OSError):
        store.add(Component("guardrail", "Never invent evidence."))
    assert len(store) == 0


def test_empty_custom_atlas_is_respected(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    generated = generate_prompt("an assistant", store=AtlasStore(path))
    assert "Never reveal" not in generated


def test_default_atlas_is_read_only(tmp_path):
    store = AtlasStore()
    # Keep this regression safe even on a version that allows bundled writes.
    store.path = tmp_path / "never-write-to-the-bundled-atlas.jsonl"
    with pytest.raises(ValueError, match="read.only"):
        store.add(Component("instruction", "Keep private data local."))


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan"), True])
def test_invalid_confidence_is_rejected(confidence):
    with pytest.raises(ValueError):
        Component("guardrail", "Never invent evidence.", confidence=confidence)


@pytest.mark.parametrize("tags", ["security", [1], None])
def test_invalid_tags_are_rejected(tags):
    with pytest.raises(ValueError):
        Component("instruction", "Verify results.", tags=tags)


def test_eval_contains_a_system_message():
    config = json.loads(export_eval_cases("a support agent", output_path=""))
    messages = json.loads(config["prompts"][0])
    assert messages[0]["role"] == "system"
    assert "support agent" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "{{prompt}}"}


def test_eval_does_not_penalize_a_legitimate_refusal():
    config = json.loads(export_eval_cases("a support agent", output_path=""))
    for case in config["tests"]:
        for assertion in case.get("assert", []):
            assert assertion.get("value") not in ("I cannot", "As an AI")

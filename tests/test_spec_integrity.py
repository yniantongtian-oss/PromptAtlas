"""Saved artifacts must be reliable inputs to review and reporting workflows."""

import copy

import pytest

from promptatlas import Component, PromptSpec, parse_prompt


def document():
    return parse_prompt("You are a reviewer.\nNever invent evidence.").to_dict()


def test_spec_rejects_unknown_fields_instead_of_dropping_them():
    data = document()
    data["raw_text"] = "accidental misspelling"
    with pytest.raises(ValueError, match="unknown"):
        PromptSpec.from_dict(data)


def test_spec_rejects_stale_derived_stats():
    data = document()
    data["stats"] = {"role": 99}
    with pytest.raises(ValueError, match="stats"):
        PromptSpec.from_dict(data)


def test_spec_rejects_duplicate_ids():
    data = document()
    data["components"][1]["id"] = data["components"][0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        PromptSpec.from_dict(data)


@pytest.mark.parametrize("offsets", [(0, 999), (1, 18), (20, 42)])
def test_spec_rejects_spans_that_do_not_match_the_source(offsets):
    data = document()
    data["components"][0]["start"], data["components"][0]["end"] = offsets
    with pytest.raises(ValueError, match="source|offset|span"):
        PromptSpec.from_dict(data)


def test_spec_rejects_reordered_source_spans():
    data = document()
    data["components"].reverse()
    with pytest.raises(ValueError, match="order|overlap"):
        PromptSpec.from_dict(data)


def test_spec_rejects_overlapping_source_spans():
    data = document()
    duplicate = copy.deepcopy(data["components"][0])
    duplicate["id"] = "distinct-id"
    data["components"].insert(1, duplicate)
    data.pop("stats")
    with pytest.raises(ValueError, match="order|overlap"):
        PromptSpec.from_dict(data)


def test_huge_confidence_value_produces_a_validation_error():
    with pytest.raises(ValueError, match="confidence"):
        Component("instruction", "Verify evidence.", confidence=10**400)


def test_legacy_spec_without_raw_or_spans_still_loads():
    data = {"components": [{"id": "legacy-role", "kind": "role", "content": "You are a reviewer."}]}
    assert PromptSpec.from_dict(data).by_kind("role")[0].id == "legacy-role"


def test_annotated_components_without_spans_remain_supported():
    data = document()
    for item in data["components"]:
        item["start"] = item["end"] = None
    assert len(PromptSpec.from_dict(data).components) == 2

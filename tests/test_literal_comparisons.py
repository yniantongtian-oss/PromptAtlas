"""Literal edits, source locations, and large unchanged prompt contracts."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from promptatlas import Component, PromptSpec, diff_specs, parse_prompt
from promptatlas.lint import lint_prompt


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Use `a  b` as a label.", "Use `a b` as a label."),
        ("Use ``a `  b`` as a label.", "Use ``a ` b`` as a label."),
        ("```text\na  b\n```", "```text\na b\n```"),
    ],
)
def test_literal_whitespace_edits_are_changes_without_false_duplicates(old, new):
    result = diff_specs(parse_prompt(old), parse_prompt(new))
    assert result["has_changes"]
    assert result["similarity"] < 1
    assert "PA003" not in [item.code for item in lint_prompt(old + "\n" + new)]


def test_prose_whitespace_around_inline_code_is_ignored():
    old = parse_prompt("Use `a  b` as a label.")
    new = parse_prompt("Use  `a  b`   as a label.")
    assert not diff_specs(old, new)["has_changes"]
    assert "PA003" in [item.code for item in lint_prompt(old.raw + "\n" + new.raw)]


@pytest.mark.parametrize("literal", ["a  b", "API_KEY"])
def test_different_literals_do_not_create_false_opposite_rules(literal):
    other = literal.replace("  ", " ").lower()
    raw = f"Always preserve `{literal}`.\nNever preserve `{other}`."
    assert "PA004" not in [item.code for item in lint_prompt(raw)]


def test_same_literal_with_opposite_prose_still_reports_conflict():
    findings = lint_prompt("Always preserve `API_KEY`.\nNever PRESERVE `API_KEY`.")
    assert "PA004" in [item.code for item in findings]


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r", "\u2028"])
def test_findings_follow_parser_source_lines_for_supported_line_endings(ending):
    findings = lint_prompt(ending.join(["You are a reviewer.", "Use {{input}}.", "Use {{input}}."]))
    assert [(item.code, item.line) for item in findings] == [
        ("PA005", 2),
        ("PA003", 3),
        ("PA005", 3),
    ]


def test_large_unchanged_repeated_prompt_preserves_duplicate_counts():
    # This exercises the public result contract without a brittle timing limit.
    spec = parse_prompt("Always verify results.\n" * 12000)
    result = diff_specs(spec, spec)
    assert not result["has_changes"] and not result["reordered"]
    assert result["similarity"] == 1
    assert not result["added"] and not result["removed"] and not result["changed"]


@pytest.mark.parametrize(
    ("old", "new", "changed"),
    [("ab", "ac", False), ("abcde", "abxyz", False), ("abcde", "abcxy", True)],
)
def test_lexical_threshold_boundary_is_preserved(old, new, changed):
    a = PromptSpec("", components=[Component("instruction", old)])
    b = PromptSpec("", components=[Component("instruction", new)])
    result = diff_specs(a, b)
    assert bool(result["changed"]) is changed
    assert bool(result["added"]) is not changed
    assert bool(result["removed"]) is not changed


def test_lexical_pairing_is_deterministic_with_ties_and_duplicates():
    a = parse_prompt("Use abcde.\nUse abcde.\nUse fghij.")
    b = parse_prompt("Use abcxy.\nUse abcxy.\nUse fghxy.")
    result = diff_specs(a, b)
    assert [(old.id, new.id) for old, new in result["changed"]] == [
        (a.components[0].id, b.components[0].id),
        (a.components[1].id, b.components[1].id),
        (a.components[2].id, b.components[2].id),
    ]


def test_benchmark_reports_checked_workloads_without_timing_thresholds(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/benchmark_workflows.py"
    output = tmp_path / "nested/benchmark.json"
    result = subprocess.run(
        [sys.executable, str(script), "--sizes", "4", "--repeat", "1", "--out", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert len(report["measurements"]) == 3
    assert all(row["correctness_checked"] for row in report["measurements"])
    assert all(len(row["samples_seconds"]) == 1 for row in report["measurements"])
    assert all(row["median_seconds"] >= 0 for row in report["measurements"])

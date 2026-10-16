"""Intentional variables must coexist with strict, explainable review gates."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from promptatlas import check_project, get_schema, lint_prompt, load_project, parse_prompt
from promptatlas.cli import main
from promptatlas.project import PromptContract


def codes(raw, **kwargs):
    return [finding.code for finding in lint_prompt("You are a reviewer.\n" + raw, **kwargs)]


@pytest.mark.parametrize("placeholder", ["{{input}}", "{{ input }}", "${input}", "${ input }"])
def test_only_explicitly_declared_placeholder_names_are_allowed(placeholder):
    raw = f"Use {placeholder} to verify the report."
    assert codes(raw) == ["PA005"]
    assert codes(raw, allowed_variables=("input",)) == []
    assert codes(raw, allowed_variables=("Input",)) == ["PA005"]


def test_dotted_names_and_multiple_placeholder_styles_are_supported():
    raw = "Use {{release.name}} with ${artifact_id} to verify the report."
    assert codes(raw, allowed_variables=("release.name",)) == ["PA005"]
    assert codes(raw, allowed_variables=("release.name", "artifact_id")) == []


@pytest.mark.parametrize(
    "expression",
    [
        "{{input | lower}}",
        "{{ input() }}",
        "{{ outer {{input}} }}",
        "{{}}",
        "${}",
        "{{input",
        "${input",
        "{{input + other}}",
    ],
)
def test_complex_or_malformed_expressions_remain_findings(expression):
    assert codes(f"Use {expression} to verify results.", allowed_variables=("input",)) == ["PA005"]


def test_allowing_one_name_does_not_hide_another_or_todo():
    assert codes("Use {{input}} and {{typo}}.", allowed_variables=("input",)) == ["PA005"]
    assert codes("Use {{input}}; TODO verify provenance.", allowed_variables=("input",)) == [
        "PA005"
    ]
    assert codes("Use ${input}; FIXME verify provenance.", allowed_variables=("input",)) == [
        "PA005"
    ]


def test_inline_todo_is_data_but_inline_template_variables_still_need_declaration():
    assert codes("Use `TODO` as a literal label.") == []
    assert codes("Use `TODO` as a label; TODO verify provenance.") == ["PA005"]
    assert codes("Use `{{input}}` as a runtime label.") == ["PA005"]
    assert codes("Use `{{input}}` as a runtime label.", allowed_variables=("input",)) == []


def test_declared_variable_named_todo_is_not_a_todo_marker():
    assert codes("Use {{TODO}} as the runtime label.", allowed_variables=("TODO",)) == []


INVALID_NAMES = [
    None,
    "input",
    [""],
    ["*"],
    ["a-b"],
    ["1input"],
    ["input\n"],
    [2],
    [[]],
    ["a..b"],
    ["input | lower"],
]


@pytest.mark.parametrize("names", INVALID_NAMES)
def test_invalid_policy_is_rejected_instead_of_implicitly_allowing_everything(names):
    with pytest.raises(ValueError, match="variable"):
        lint_prompt("You are a reviewer.", allowed_variables=names)


def test_programmatic_contracts_validate_and_deduplicate_variables():
    contract = PromptContract("system.md", (), True, ("input", "release.name", "input"))
    assert contract.allowed_variables == ("input", "release.name")
    with pytest.raises(ValueError, match="tuple"):
        PromptContract("system.md", (), True, ["input"])
    with pytest.raises(ValueError, match="variable"):
        PromptContract("system.md", (), True, ("*",))


def test_file_declarations_are_additive_and_do_not_leak_to_other_files(tmp_path):
    for name, variable in [("a", "local"), ("b", "shared"), ("c", "local")]:
        (tmp_path / f"{name}.md").write_text(
            f"You are a reviewer.\nUse {{{{{variable}}}}} to verify results.", encoding="utf-8"
        )
    config = tmp_path / "promptatlas.json"
    config.write_text(
        json.dumps(
            {
                "strict": True,
                "allow_variables": ["shared", "shared"],
                "prompts": [
                    {"path": "a.md", "allow_variables": ["local", "shared"]},
                    "b.md",
                    "c.md",
                ],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_project(config)
    assert [item.allowed_variables for item in loaded.prompts] == [
        ("shared", "local"),
        ("shared",),
        ("shared",),
    ]
    report = check_project(loaded)
    assert report.exit_code == 1
    assert [item.failed for item in report.files] == [False, False, True]
    assert report.files[2].findings[0].code == "PA005"
    assert [item["allowed_variables"] for item in report.to_dict()["files"]] == [
        ["shared", "local"],
        ["shared"],
        ["shared"],
    ]


@pytest.mark.parametrize("names", INVALID_NAMES)
@pytest.mark.parametrize("scope", ["project", "file"])
def test_schema_and_runtime_agree_on_invalid_variable_declarations(tmp_path, names, scope):
    data = {"prompts": ["system.md"]}
    if scope == "project":
        data["allow_variables"] = names
    else:
        data["prompts"] = [{"path": "system.md", "allow_variables": names}]
    config = tmp_path / "promptatlas.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValidationError):
        Draft202012Validator(get_schema("project")).validate(data)
    with pytest.raises(ValueError, match="variable"):
        load_project(config)


def test_saved_spec_uses_the_same_policy_and_keeps_the_actual_template(tmp_path):
    raw = "You are a reviewer.\nUse {{input}} to verify results."
    spec = parse_prompt(raw)
    spec.save(tmp_path / "system.json")
    data = {"strict": True, "allow_variables": ["input"], "prompts": ["system.json"]}
    config = tmp_path / "promptatlas.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    assert check_project(config).exit_code == 0
    assert json.loads((tmp_path / "system.json").read_text(encoding="utf-8"))["raw"] == raw


def test_cli_explicit_names_allow_strict_mode_and_leave_other_warnings(tmp_path, capsys):
    prompt = tmp_path / "system.md"
    prompt.write_text("You are a reviewer.\nUse {{input}} with ${other}.", encoding="utf-8")
    assert main(["lint", str(prompt), "--strict", "--allow-variable", "input", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["warnings"] == 1
    assert (
        main(
            [
                "lint",
                str(prompt),
                "--strict",
                "--allow-variable",
                "input",
                "--allow-variable",
                "other",
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["warnings"] == 0
    with pytest.raises(SystemExit) as exc:
        main(["lint", str(prompt), "--allow-variable", "*", "--json"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert not captured.out and "variable" in captured.err and "Traceback" not in captured.err


def test_shipped_template_project_is_schema_valid_and_passes_strict_review():
    config = Path(__file__).resolve().parents[1] / "examples/template-project/promptatlas.json"
    Draft202012Validator(get_schema("project")).validate(
        json.loads(config.read_text(encoding="utf-8"))
    )
    report = check_project(config)
    assert report.exit_code == 0
    assert not report.files[0].findings
    assert report.files[0].allowed_variables == ("release.name", "artifact_id")

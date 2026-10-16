"""User-visible project contracts, complete reporting, and SARIF locations."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

from promptatlas import check_project, load_project, parse_prompt, sarif_report
from promptatlas.cli import main
from promptatlas.project import ProjectConfig, PromptContract


def make_project(root, *, prompts=None, **settings):
    root.mkdir(parents=True, exist_ok=True)
    config = root / "promptatlas.json"
    config.write_text(
        json.dumps({"prompts": prompts or ["system.md"], **settings}), encoding="utf-8"
    )
    return config


def test_project_checks_all_files_and_combines_requirements(tmp_path):
    (tmp_path / "good.md").write_text("You are a reviewer.\nNever invent facts.", encoding="utf-8")
    (tmp_path / "bad.md").write_text("You are a reviewer.", encoding="utf-8")
    config = make_project(
        tmp_path,
        prompts=["good.md", {"path": "bad.md", "require": ["guardrail"]}],
        require=["role"],
    )
    report = check_project(config)
    assert report.exit_code == 1
    assert [item.failed for item in report.files] == [False, True]
    assert report.files[1].findings[0].code == "PA007"
    assert report.to_dict()["summary"] == {
        "files": 2,
        "passed": 1,
        "failed": 1,
        "invalid": 0,
        "errors": 1,
        "warnings": 0,
    }


def test_file_strict_setting_can_override_project_default(tmp_path):
    (tmp_path / "system.md").write_text("Never invent facts.", encoding="utf-8")
    config = make_project(tmp_path, prompts=[{"path": "system.md", "strict": False}], strict=True)
    report = check_project(config)
    assert report.exit_code == 0
    assert report.to_dict()["summary"]["warnings"] == 1


def test_strict_warnings_fail_a_project(tmp_path):
    (tmp_path / "system.md").write_text("Never invent facts.", encoding="utf-8")
    report = check_project(make_project(tmp_path, strict=True))
    assert report.exit_code == 1
    assert report.files[0].findings[0].code == "PA002"


def test_missing_files_do_not_hide_other_results(tmp_path):
    (tmp_path / "good.md").write_text("You are a reviewer.", encoding="utf-8")
    report = check_project(make_project(tmp_path, prompts=["missing.md", "good.md"]))
    assert report.exit_code == 2
    assert report.files[0].error
    assert report.files[1].stats == {"role": 1}
    assert report.to_dict()["summary"]["invalid"] == 1


def test_malformed_specs_are_input_errors_in_the_report(tmp_path):
    (tmp_path / "bad.json").write_text('{"components": false}', encoding="utf-8")
    report = check_project(make_project(tmp_path, prompts=["bad.json"]))
    assert report.exit_code == 2
    assert "components" in report.files[0].error
    assert not report.files[0].findings


def test_directory_input_is_reported_without_a_traceback(tmp_path):
    (tmp_path / "system.md").mkdir()
    report = check_project(make_project(tmp_path))
    assert report.exit_code == 2
    assert report.files[0].error


def test_configuration_paths_are_independent_of_current_directory(tmp_path, monkeypatch):
    project = tmp_path / "project with spaces"
    config = make_project(project)
    (project / "system.md").write_bytes(
        b"\xef\xbb\xbfYou are a reviewer.\r\nNever invent facts.\r\n"
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    report = check_project(config)
    assert report.exit_code == 0
    assert report.files[0].stats == {"role": 1, "guardrail": 1}


@pytest.mark.parametrize(
    "path",
    [
        "../outside.md",
        "/absolute.md",
        "C:/system.md",
        r"folder\system.md",
        "",
        " ",
        ".",
        "./",
        "*.md",
        "folder/../system.md",
        None,
        5,
    ],
)
def test_nonportable_or_escaping_paths_are_rejected(tmp_path, path):
    config = make_project(tmp_path, prompts=[{"path": path}])
    with pytest.raises(ValueError, match="path"):
        load_project(config)


def test_duplicate_normalized_paths_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        load_project(make_project(tmp_path, prompts=["system.md", "./system.md"]))


@pytest.mark.parametrize(
    "settings",
    [
        {"strict": "false"},
        {"strict": 0},
        {"require": "role"},
        {"require": ["invalid"]},
        {"require": [1]},
        {"unknown": True},
        {"schema_version": True},
        {"schema_version": 2},
        {"$schema": 5},
    ],
)
def test_invalid_project_settings_are_rejected(tmp_path, settings):
    with pytest.raises(ValueError):
        load_project(make_project(tmp_path, **settings))


@pytest.mark.parametrize(
    "entry",
    [
        5,
        False,
        {"path": "system.md", "strict": "true"},
        {"path": "system.md", "requires": ["role"]},
    ],
)
def test_invalid_file_settings_are_rejected(tmp_path, entry):
    with pytest.raises(ValueError):
        load_project(make_project(tmp_path, prompts=[entry]))


@pytest.mark.parametrize("data", [[], None, {"prompts": []}, {"prompts": "system.md"}])
def test_empty_or_invalid_project_contracts_cannot_pass(tmp_path, data):
    config = tmp_path / "promptatlas.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_project(config)


def test_symlinks_cannot_read_outside_the_project(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("You are a reviewer.", encoding="utf-8")
    project = tmp_path / "project"
    config = make_project(project)
    try:
        (project / "system.md").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(ValueError, match="outside"):
        load_project(config)


def test_sarif_has_complete_rules_and_real_unicode_file_locations(tmp_path):
    name = "review café.md"
    (tmp_path / name).write_text(
        "You are a reviewer.\nAlways use JSON.\nNever use JSON.", encoding="utf-8"
    )
    report = check_project(make_project(tmp_path, prompts=[name]))
    sarif = sarif_report(report)
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    finding = run["results"][0]
    assert finding["ruleId"] == "PA004"
    assert finding["level"] == "error"
    assert run["tool"]["driver"]["rules"][finding["ruleIndex"]]["id"] == finding["ruleId"]
    physical = finding["locations"][0]["physicalLocation"]
    assert physical["region"]["startLine"] == 3
    assert unquote(urlparse(physical["artifactLocation"]["uri"]).path).endswith(name)
    assert run["invocations"][0]["executionSuccessful"] is True


def test_sarif_reports_input_failures_as_unsuccessful_execution(tmp_path):
    report = check_project(make_project(tmp_path))
    run = sarif_report(report)["runs"][0]
    assert run["results"] == []
    invocation = run["invocations"][0]
    assert invocation["executionSuccessful"] is False
    assert invocation["toolExecutionNotifications"][0]["level"] == "error"


def test_saved_spec_lines_are_not_falsely_attached_to_json_lines(tmp_path):
    parse_prompt("You are a reviewer.\nAlways use JSON.\nNever use JSON.").save(
        tmp_path / "system.json"
    )
    report = check_project(make_project(tmp_path, prompts=["system.json"]))
    result = sarif_report(report)["runs"][0]["results"][0]
    assert "region" not in result["locations"][0]["physicalLocation"]
    assert result["properties"]["originalPromptLine"] == 3


def test_sarif_fingerprints_survive_line_shifts_and_checkout_moves(tmp_path):
    fingerprints = []
    for directory, prefix in [("first", ""), ("second", "\n\n")]:
        root = tmp_path / directory
        config = make_project(root)
        (root / "system.md").write_text(
            prefix + "You are a reviewer.\nAlways use JSON.\nNever use JSON.", encoding="utf-8"
        )
        result = sarif_report(check_project(config))["runs"][0]["results"][0]
        fingerprints.append(result["partialFingerprints"])
    assert fingerprints[0] == fingerprints[1]


def test_project_json_is_deterministic_and_does_not_embed_prompt_content(tmp_path):
    (tmp_path / "system.md").write_text(
        "Private fixture value is KEEP_THIS_LOCAL.", encoding="utf-8"
    )
    config = make_project(tmp_path)
    first = check_project(config).to_dict()
    assert first == check_project(config).to_dict()
    assert "KEEP_THIS_LOCAL" not in json.dumps(first)


def test_check_cli_has_single_json_output_and_gate_exit_code(tmp_path, capsys):
    (tmp_path / "system.md").write_text("Never invent facts.", encoding="utf-8")
    config = make_project(tmp_path, strict=True)
    assert main(["check", "--config", str(config), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["summary"]["warnings"] == 1


def test_check_cli_writes_sarif_without_mixing_receipts_into_json(tmp_path, capsys):
    (tmp_path / "system.md").write_text("You are a reviewer.", encoding="utf-8")
    config = make_project(tmp_path)
    output = tmp_path / "reports" / "project.sarif"
    assert main(["check", "--config", str(config), "--format", "sarif", "--out", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["version"] == "2.1.0"
    captured = capsys.readouterr()
    assert captured.out == "" and "Wrote" in captured.err


@pytest.mark.parametrize("target", ["promptatlas.json", "system.md"])
def test_report_output_cannot_overwrite_configuration_or_prompt_inputs(tmp_path, target):
    (tmp_path / "system.md").write_text("You are a reviewer.", encoding="utf-8")
    config = make_project(tmp_path)
    before = (tmp_path / target).read_bytes()
    with pytest.raises(SystemExit) as error:
        main(["check", "--config", str(config), "--out", str(tmp_path / target)])
    assert error.value.code == 2
    assert (tmp_path / target).read_bytes() == before


def test_real_check_process_works_outside_the_checkout(tmp_path):
    project = tmp_path / "project"
    config = make_project(project)
    (project / "system.md").write_text("You are a reviewer.", encoding="utf-8")
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    result = subprocess.run(
        [sys.executable, "-m", "promptatlas", "check", "--config", str(config), "--json"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["summary"]["passed"] == 1


def test_reports_do_not_modify_a_loaded_project_configuration(tmp_path):
    (tmp_path / "system.md").write_text("You are a reviewer.", encoding="utf-8")
    config = load_project(make_project(tmp_path))
    before = copy.deepcopy(config)
    sarif_report(check_project(config))
    assert config == before


def test_programmatic_empty_project_cannot_bypass_the_gate(tmp_path):
    with pytest.raises(ValueError, match="non-empty"):
        check_project(ProjectConfig(path=tmp_path / "promptatlas.json", prompts=()))


@pytest.mark.parametrize("kinds", [("invalid",), "role", (True,)])
def test_programmatic_contracts_validate_required_kinds(kinds):
    with pytest.raises(ValueError, match="required_kinds"):
        PromptContract(path="system.md", required_kinds=kinds, strict=True)


def test_programmatic_contracts_validate_strictness():
    with pytest.raises(ValueError, match="boolean"):
        PromptContract(path="system.md", required_kinds=(), strict="false")


def test_programmatic_projects_reject_duplicate_resolved_inputs(tmp_path):
    first = PromptContract(path="system.md", required_kinds=(), strict=False)
    second = PromptContract(path="./system.md", required_kinds=("role",), strict=True)
    with pytest.raises(ValueError, match="duplicate"):
        ProjectConfig(path=tmp_path / "promptatlas.json", prompts=(first, second))

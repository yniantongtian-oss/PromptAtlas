"""Complete user journeys across command boundaries and persisted artifacts."""

import io
import json

from promptatlas import AtlasStore, Component, PromptSpec
from promptatlas.cli import main


def test_custom_atlas_add_search_validate_and_compose(tmp_path, monkeypatch, capsys):
    atlas = tmp_path / "team atlas.jsonl"
    monkeypatch.setattr("sys.stdin", io.StringIO("Never invent test results."))
    assert (
        main(
            [
                "add",
                "-",
                "--atlas",
                str(atlas),
                "--kind",
                "guardrail",
                "--product",
                "team-review",
                "--version",
                "v1",
                "--tag",
                "coding-agent",
                "--source",
                "Original project example; MIT",
                "--json",
            ]
        )
        == 0
    )
    added = json.loads(capsys.readouterr().out)
    assert added["source"] == "Original project example; MIT"
    assert (
        main(
            ["search", "--atlas", str(atlas), "--tag", "CODING-AGENT", "--query", "test", "--json"]
        )
        == 0
    )
    found = json.loads(capsys.readouterr().out)
    assert found["total"] == 1 and found["results"][0]["id"] == added["id"]
    assert main(["validate", "--atlas", str(atlas), "--require-source", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    draft = tmp_path / "draft.md"
    assert main(["generate", "a coding agent", "--atlas", str(atlas), "--out", str(draft)]) == 0
    assert "Never invent test results." in draft.read_text(encoding="utf-8")


def test_missing_attribution_has_an_explicit_failing_gate(tmp_path, capsys):
    atlas = tmp_path / "atlas.jsonl"
    store = AtlasStore(atlas, create=True)
    store.add(Component("instruction", "Verify evidence.", id="needs-source"))
    assert main(["validate", "--atlas", str(atlas), "--require-source", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False and report["missing_source"] == ["needs-source"]


def test_text_cli_outputs_are_useful_during_a_complete_review(tmp_path, capsys):
    before, after, saved = tmp_path / "before.md", tmp_path / "after.md", tmp_path / "saved.json"
    before.write_text("You are a reviewer.", encoding="utf-8")
    after.write_text("You are a reviewer.\nNever invent evidence.", encoding="utf-8")
    assert main(["parse", str(before), "--out", str(saved)]) == 0
    assert PromptSpec.load(saved).raw == before.read_text(encoding="utf-8")
    assert "1 components" in capsys.readouterr().out
    assert main(["diff", str(saved), str(after)]) == 0
    assert "Never invent evidence." in capsys.readouterr().out
    assert main(["search", "--kind", "guardrail", "--limit", "1"]) == 0
    assert "showing 1" in capsys.readouterr().out
    assert main(["validate", "--require-source"]) == 0
    assert "Validated" in capsys.readouterr().out


def test_actual_prompt_export_is_configurable_and_does_not_run_a_provider(tmp_path, capsys):
    source, target = tmp_path / "system.md", tmp_path / "eval.json"
    source.write_text("You are a reviewer.\nNever invent evidence.", encoding="utf-8")
    assert (
        main(
            [
                "eval",
                "reviewer",
                "--prompt-file",
                str(source),
                "--provider",
                "echo",
                "--out",
                str(target),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document == json.loads(target.read_text(encoding="utf-8"))
    assert document["providers"] == ["echo"]
    assert json.loads(document["prompts"][0])[0]["content"].startswith(
        source.read_bytes().decode("utf-8")
    )
    assert "run promptfoo separately" in captured.err


def test_text_project_report_includes_both_findings_and_invalid_files(tmp_path, capsys):
    (tmp_path / "rules.md").write_text("Never invent evidence.", encoding="utf-8")
    config = tmp_path / "promptatlas.json"
    config.write_text(
        json.dumps({"prompts": ["rules.md", "missing.md"], "strict": True}), encoding="utf-8"
    )
    assert main(["check", "--config", str(config)]) == 2
    text = capsys.readouterr().out
    assert "PA002" in text and "input error" in text
    assert "Checked 2 prompts" in text

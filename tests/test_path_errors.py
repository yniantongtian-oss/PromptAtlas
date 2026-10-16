"""Real filesystem failures should produce actionable CLI diagnostics."""

import json

import pytest

from promptatlas.cli import main


@pytest.mark.parametrize("location", ["prompt", "config", "output"])
def test_symlink_loops_are_input_errors_without_a_traceback(tmp_path, capsys, location):
    source = tmp_path / "system.md"
    config = tmp_path / "promptatlas.json"
    source.write_text("You are a reviewer.", encoding="utf-8")
    config.write_text(json.dumps({"prompts": ["system.md"]}), encoding="utf-8")
    name = {"prompt": "system.md", "config": "loop.json", "output": "report.sarif"}[location]
    loop = tmp_path / name
    if loop.exists():
        loop.unlink()
    try:
        loop.symlink_to(name)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this host")
    arguments = ["check", "--config", str(loop if location == "config" else config)]
    if location == "output":
        arguments.extend(["--format", "sarif", "--out", str(loop)])
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err and "Traceback" not in captured.err
    assert captured.out == ""

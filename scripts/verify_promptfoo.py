"""Run pinned promptfoo integration controls without any model API calls."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LITERAL_PROMPT = (
    "You are a reviewer.\n"
    "Preserve literal tokens: {{danger}} {% if true %}literal{% endif %} {# sample #}.\n"
    "Never invent evidence."
)


def verify(package: Path, output: Path) -> None:
    package = package.resolve(strict=True)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
    if metadata["version"] != "0.124.1":
        raise ValueError("this compatibility check requires promptfoo 0.124.1")
    runner = package / metadata["bin"]["promptfoo"]
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "FORCE_COLOR": "0",
        "PROMPTFOO_DISABLE_TELEMETRY": "1",
        "PROMPTFOO_DISABLE_UPDATE": "1",
        "PROMPTFOO_CONFIG_DIR": str(output / "runner-state"),
        "PROMPTFOO_FAILED_TEST_EXIT_CODE": "100",
    }
    source = output / "literal system prompt.md"
    source.write_text(LITERAL_PROMPT, encoding="utf-8", newline="\n")
    negative_path = output / "echo-config.json"
    exported = subprocess.run(
        [
            sys.executable,
            "-m",
            "promptatlas",
            "eval",
            "reviewer",
            "--prompt-file",
            str(source),
            "--provider",
            "echo",
            "--out",
            str(negative_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if exported.returncode:
        raise RuntimeError(exported.stderr)
    negative = json.loads(negative_path.read_text(encoding="utf-8"))
    positive = copy.deepcopy(negative)
    positive["providers"] = ["file://" + (ROOT / "examples/refusal-provider.cjs").as_posix()]
    positive_path = output / "refusal-config.json"
    positive_path.write_text(json.dumps(positive, indent=2), encoding="utf-8")
    reports = {}
    for label, config, expected_exit, expected_success, expected_failure in (
        ("refusal", positive_path, 0, 6, 0),
        ("echo", negative_path, 100, 1, 5),
    ):
        result_path = output / f"{label}-results.json"
        result = subprocess.run(
            [
                "node",
                str(runner),
                "eval",
                "-c",
                str(config),
                "--output",
                str(result_path),
                "--no-cache",
                "--no-table",
                "--no-progress-bar",
                "--no-write",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        (output / f"{label}-runner.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode != expected_exit:
            raise RuntimeError(
                f"{label}: expected exit {expected_exit}, got {result.returncode}\n{result.stdout}\n{result.stderr}"
            )
        document = json.loads(result_path.read_text(encoding="utf-8"))
        summary = document["results"]
        stats = summary["stats"]
        assert stats["successes"] == expected_success, stats
        assert stats["failures"] == expected_failure, stats
        assert stats.get("errors", 0) == 0, stats
        # The negative control also proves literal template syntax survives.
        if label == "echo":
            for row in summary["results"]:
                messages = json.loads(row["response"]["output"])
                assert messages[0]["content"].startswith(LITERAL_PROMPT + "\n\n"), messages
                assert messages[1]["content"] == row["vars"]["prompt"], messages
        reports[label] = {
            "exit_code": result.returncode,
            "successes": expected_success,
            "failures": expected_failure,
            "errors": 0,
        }
    report = {
        "runner": f"promptfoo@{metadata['version']}",
        "model_calls": 0,
        "literal_template_preserved": True,
        "controls": reports,
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package", type=Path, required=True, help="installed node_modules/promptfoo directory"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "test-results/promptfoo")
    arguments = parser.parse_args()
    verify(arguments.package, arguments.output)

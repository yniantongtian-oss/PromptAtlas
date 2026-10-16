"""Manual structural labels plus counterexamples for literal boundaries."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from promptatlas import PromptSpec, parse_prompt
from promptatlas.lint import lint_spec

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests/fixtures/parser_cases.json"
CASES = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_manually_labeled_structural_cases(case):
    spec = parse_prompt(case["raw"])
    assert [[item.kind, item.content] for item in spec.components] == case["components"]
    assert [finding.code for finding in lint_spec(spec)] == case["finding_codes"]
    assert PromptSpec.from_dict(spec.to_dict()).to_dict() == spec.to_dict()


def run_evaluator(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/evaluate_parser.py"), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_corpus_report_records_real_results_without_prompt_content(tmp_path):
    output = tmp_path / "nested/report.json"
    result = run_evaluator("--out", output)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["summary"] == {"total": len(CASES), "passed": len(CASES), "failed": 0}
    assert "raw" not in output.read_text(encoding="utf-8")
    assert not result.stdout


def test_corpus_runner_rejects_wrong_labels_instead_of_pass_by_execution(tmp_path):
    case = {**CASES[0], "components": [["role", "This expected content is deliberately wrong."]]}
    corpus = tmp_path / "negative.json"
    corpus.write_text(json.dumps({"schema_version": 1, "cases": [case]}), encoding="utf-8")
    result = run_evaluator("--cases", corpus)
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["summary"] == {"total": 1, "passed": 0, "failed": 1}
    assert not report["cases"][0]["components_match"]


@pytest.mark.parametrize(
    "document",
    [
        [],
        {"schema_version": True, "cases": CASES},
        {"schema_version": 2, "cases": CASES},
        {"schema_version": 1, "cases": []},
        {"schema_version": 1, "cases": [CASES[0], CASES[0]]},
        {"schema_version": 1, "cases": [{**CASES[0], "components": [[[], "x"]]}]},
        {"schema_version": 1, "cases": [{**CASES[0], "finding_codes": ["PA999"]}]},
    ],
)
def test_corpus_runner_does_not_report_success_for_invalid_inputs(tmp_path, document):
    corpus = tmp_path / "invalid.json"
    corpus.write_text(json.dumps(document), encoding="utf-8")
    result = run_evaluator("--cases", corpus)
    assert result.returncode == 2
    assert result.stderr.startswith("error:")
    assert not result.stdout


def test_corpus_report_cannot_destroy_its_input(tmp_path):
    corpus = tmp_path / "cases.json"
    original = CORPUS.read_bytes()
    corpus.write_bytes(original)
    result = run_evaluator("--cases", corpus, "--out", corpus)
    assert result.returncode == 2
    assert corpus.read_bytes() == original

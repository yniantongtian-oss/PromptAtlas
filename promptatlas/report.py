"""SARIF 2.1.0 output for structural prompt findings."""

from __future__ import annotations

import hashlib
import json

from . import __version__
from ._io import resolve_path
from .project import ProjectReport

_RULES = (
    ("PA001", "EmptyPrompt", "The prompt is empty.", "error"),
    ("PA002", "MissingRole", "No explicit role or mission was found.", "warning"),
    ("PA003", "RepeatedComponent", "A component repeats an earlier rule.", "warning"),
    ("PA004", "OppositeDirectives", "Opposite Always/Never rules use identical wording.", "error"),
    ("PA005", "UnresolvedTemplate", "A template variable or TODO remains.", "warning"),
    ("PA006", "UnclosedFence", "A fenced code block is not closed.", "error"),
    ("PA007", "MissingRequiredKind", "A required component kind is missing.", "error"),
)


def sarif_report(report: ProjectReport) -> dict:
    """Render findings with stable fingerprints and actual file locations.

    Line numbers for saved JSON specs describe the original prompt, not the
    physical JSON file. They are preserved as properties without a false region.
    Input failures are execution notifications, never successful clean scans.
    """
    rules = [
        {
            "id": code,
            "name": name,
            "shortDescription": {"text": description},
            "defaultConfiguration": {"level": level},
            "helpUri": "https://github.com/yniantongtian-oss/PromptAtlas/blob/main/docs/CLI.md#lint-and-gate-changes",
            "help": {
                "text": description + " This check evaluates prompt structure, not model behavior."
            },
            "properties": {"tags": ["maintainability", "prompt-structure"]},
        }
        for code, name, description, level in _RULES
    ]
    indices = {item["id"]: index for index, item in enumerate(rules)}
    results, notifications = [], []
    for file in report.files:
        location = {"uri": resolve_path(report.config.root / file.path).as_uri()}
        if file.error is not None:
            notifications.append(
                {
                    "level": "error",
                    "message": {"text": f"{file.path}: {file.error}"},
                    "locations": [{"physicalLocation": {"artifactLocation": location}}],
                }
            )
        for finding in file.findings:
            physical = {"artifactLocation": location}
            if finding.line is not None and file.source_format == "text":
                physical["region"] = {"startLine": finding.line}
            identity = json.dumps(
                [file.path, finding.code, finding.component_id or finding.message],
                ensure_ascii=False,
            )
            result = {
                "ruleId": finding.code,
                "ruleIndex": indices[finding.code],
                "level": finding.severity,
                "message": {"text": finding.message},
                "locations": [{"physicalLocation": physical}],
                "partialFingerprints": {
                    "promptatlasComponent/v1": hashlib.sha256(identity.encode("utf-8")).hexdigest()
                },
            }
            if file.source_format == "spec" and finding.line is not None:
                result["properties"] = {"originalPromptLine": finding.line}
            results.append(result)
    invocation = {
        "executionSuccessful": not notifications,
        "workingDirectory": {"uri": report.config.root.as_uri() + "/"},
    }
    if notifications:
        invocation["toolExecutionNotifications"] = notifications
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PromptAtlas",
                        "semanticVersion": __version__,
                        "informationUri": "https://github.com/yniantongtian-oss/PromptAtlas",
                        "rules": rules,
                    }
                },
                "automationDetails": {"id": "promptatlas/check/"},
                "invocations": [invocation],
                "results": results,
            }
        ],
    }

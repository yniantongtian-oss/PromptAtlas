"""Evaluate an explicitly labeled structural corpus without model calls.

Reports omit prompt content. This is a regression fixture runner, not evidence
of general accuracy, semantic understanding, or deployed model safety.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from promptatlas import PromptSpec, __version__, parse_prompt
from promptatlas._io import atomic_write, resolve_path
from promptatlas.lint import lint_spec
from promptatlas.schema import VALID_COMPONENT_KINDS

DEFAULT_CASES = Path(__file__).resolve().parents[1] / "tests/fixtures/parser_cases.json"


def evaluate(path: Path) -> dict:
    corpus = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(corpus, dict) or type(corpus.get("schema_version")) is not int:
        raise ValueError("corpus must be an object with integer schema_version 1")
    if corpus["schema_version"] != 1:
        raise ValueError("unsupported corpus schema_version")
    cases = corpus.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("corpus cases must be a non-empty list")
    results, identifiers = [], set()
    for index, case in enumerate(cases, 1):
        prefix = f"case {index}"
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"]:
            raise ValueError(f"{prefix}: a non-empty string id is required")
        if case["id"] in identifiers:
            raise ValueError(f"{prefix}: duplicate id {case['id']!r}")
        identifiers.add(case["id"])
        if not isinstance(case.get("raw"), str) or not isinstance(case.get("components"), list):
            raise ValueError(f"{prefix}: raw and components must be a string and a list")
        for component in case["components"]:
            if (
                not isinstance(component, list)
                or len(component) != 2
                or not isinstance(component[0], str)
                or component[0] not in VALID_COMPONENT_KINDS
                or not isinstance(component[1], str)
                or not component[1].strip()
            ):
                raise ValueError(
                    f"{prefix}: components must contain [kind, non-empty content] pairs"
                )
        codes = case.get("finding_codes")
        if not isinstance(codes, list) or any(
            not isinstance(code, str) or code not in {f"PA00{i}" for i in range(1, 8)}
            for code in codes
        ):
            raise ValueError(f"{prefix}: finding_codes must list supported rule codes")
        spec = parse_prompt(case["raw"])
        actual = [[item.kind, item.content] for item in spec.components]
        actual_codes = [finding.code for finding in lint_spec(spec)]
        spans = all(case["raw"][item.start : item.end] == item.content for item in spec.components)
        roundtrip = PromptSpec.from_dict(spec.to_dict()).to_dict() == spec.to_dict()
        passed = actual == case["components"] and actual_codes == codes and spans and roundtrip
        results.append(
            {
                "id": case["id"],
                "passed": passed,
                "components_match": actual == case["components"],
                "expected_kinds": [item[0] for item in case["components"]],
                "actual_kinds": [item[0] for item in actual],
                "expected_finding_codes": codes,
                "actual_finding_codes": actual_codes,
                "source_spans_valid": spans,
                "roundtrip_valid": roundtrip,
            }
        )
    failed = sum(not result["passed"] for result in results)
    return {
        "schema_version": 1,
        "promptatlas_version": __version__,
        "evidence_scope": "Authored structural regression fixtures; not a held-out accuracy benchmark.",
        "summary": {"total": len(results), "passed": len(results) - failed, "failed": failed},
        "cases": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.out and resolve_path(args.out) == resolve_path(args.cases):
            raise ValueError("report output must not overwrite the corpus")
        report = evaluate(args.cases)
        text = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
        if args.out:
            atomic_write(args.out, text)
        else:
            print(text, end="")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Reproducible synthetic workflow timings, with correctness checks.

Timings describe one machine and workload. They are not CI pass/fail thresholds,
model-quality measurements, or a claim that all diff workloads scale linearly.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter

from promptatlas import Component, PromptSpec, __version__, diff_specs, parse_prompt
from promptatlas._io import atomic_write
from promptatlas.lint import lint_spec


def positive(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return result


def benchmark(sizes: list[int], repeat: int) -> dict:
    rows = []

    def measure(task, size, operation, validate):
        samples = []
        for _ in range(repeat):
            start = perf_counter()
            result = operation()
            samples.append(perf_counter() - start)
            validate(result)
        rows.append(
            {
                "task": task,
                "components": size,
                "repeat": repeat,
                "samples_seconds": samples,
                "median_seconds": statistics.median(samples),
                "correctness_checked": True,
            }
        )

    def unchanged(result):
        if (
            result["has_changes"]
            or result["similarity"] != 1
            or any(result[key] for key in ("added", "removed", "changed"))
        ):
            raise ValueError("an unchanged repeated prompt produced an incorrect diff")

    for size in sizes:
        spec = parse_prompt("You are a reviewer.\n" + "Always verify results.\n" * size)
        measure(
            "unchanged_repeated_diff", size + 1, lambda spec=spec: diff_specs(spec, spec), unchanged
        )
        raw = "You are a reviewer.\n" + "Use {{input}}.\n" * size

        def validate_lint(findings, expected=2 * size - 1, last_line=size + 1):
            if len(findings) != expected or findings[-1].line != last_line:
                raise ValueError("lint count or final source line is incorrect")

        measure(
            "parse_and_lint", size + 1, lambda raw=raw: lint_spec(parse_prompt(raw)), validate_lint
        )
    edit_size = min(max(sizes), 100)
    old = PromptSpec(
        "", components=[Component("instruction", "a" * 128 + f" {i}") for i in range(edit_size)]
    )
    new = PromptSpec(
        "", components=[Component("instruction", "b" * 128 + f" {i}") for i in range(edit_size)]
    )

    def unrelated(result):
        if (
            result["changed"]
            or len(result["added"]) != edit_size
            or len(result["removed"]) != edit_size
        ):
            raise ValueError("unrelated replacements produced incorrect diff groups")

    measure("unrelated_replacements", edit_size, lambda: diff_specs(old, new), unrelated)
    return {
        "schema_version": 1,
        "promptatlas_version": __version__,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "evidence_scope": "Synthetic local timings; no portable performance guarantee.",
        "measurements": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=positive, default=[2000, 4000])
    parser.add_argument("--repeat", type=positive, default=3)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = benchmark(args.sizes, args.repeat)
        text = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
        if args.out:
            atomic_write(args.out, text)
        else:
            print(text, end="")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

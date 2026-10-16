"""Offline command-line workflows with machine-readable output and CI gates."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from ._io import atomic_write, resolve_path
from .atlas import AtlasStore
from .diff import diff_specs, diff_summary, diff_to_dict
from .eval_export import DEFAULT_PROVIDER, export_eval_cases
from .generate import generate_prompt
from .lint import lint_spec
from .load import load_prompt, read_text
from .parse import parse_prompt
from .project import ProjectReport, check_project
from .report import sarif_report
from .schema import VALID_COMPONENT_KINDS, Component, PromptSpec
from .schemas import SCHEMA_NAMES, get_schema


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read().lstrip("\ufeff")
    return read_text(path)


def _spec(path: str, product: str = "", version: str = "") -> PromptSpec:
    if path == "-":
        return parse_prompt(_read(path), product=product, version=version or "stdin")
    return load_prompt(path, product=product, version=version)


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _positive(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if result < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return result


def _cmd_parse(args: argparse.Namespace) -> int:
    spec = parse_prompt(_read(args.file), product=args.product, version=args.version)
    if args.out:
        spec.save(args.out)
    if args.json:
        _json(spec.to_dict())
    else:
        _json(spec.stats())
        print(f"{len(spec.components)} components" + (f" -> {args.out}" if args.out else ""))
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    store = AtlasStore(args.atlas, create=True)
    component = Component(
        kind=args.kind,
        content=_read(args.file),
        product=args.product,
        version=args.version,
        tags=args.tag or [],
        source=args.source,
    )
    store.add(component)
    if args.json:
        _json(component.to_dict())
    else:
        print(f"Added {component.id} [{component.kind}] ({len(store)} total)")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    if args.a == args.b == "-":
        raise ValueError("at most one diff input may use stdin")
    result = diff_specs(_spec(args.a), _spec(args.b))
    if args.json:
        _json(diff_to_dict(result))
    else:
        print(diff_summary(result))
    return int(args.fail_on_change and result["has_changes"])


def _cmd_generate(args: argparse.Namespace) -> int:
    text = generate_prompt(
        args.scenario, store=AtlasStore(args.atlas), max_per_kind=args.max_per_kind
    )
    if args.out:
        atomic_write(args.out, text)
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    system_prompt = (
        _read(args.prompt_file)
        if args.prompt_file
        else generate_prompt(args.scenario, store=AtlasStore(args.atlas))
    )
    text = export_eval_cases(
        args.scenario,
        args.out,
        system_prompt=system_prompt,
        provider=args.provider,
    )
    if args.out:
        print(
            f"Wrote {args.out}; run promptfoo separately to execute these synthetic checks.",
            file=sys.stderr,
        )
    print(text, end="")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    results = AtlasStore(args.atlas).search(
        kind=args.kind, tags=args.tag, product=args.product, query=args.query
    )
    if args.json:
        _json(
            {"total": len(results), "results": [item.to_dict() for item in results[: args.limit]]}
        )
    else:
        for item in results[: args.limit]:
            print(
                f"[{item.kind}] ({item.product} {item.version}) {' '.join(item.content.split())[:120]}"
            )
        print(f"\n{len(results)} matches; showing {min(args.limit, len(results))}")
    return 0


def _cmd_lint(args: argparse.Namespace) -> int:
    spec = _spec(args.file)
    findings = lint_spec(
        spec,
        required_kinds=tuple(args.require or []),
        allowed_variables=tuple(args.allow_variable or []),
    )
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    failed = bool(errors or (args.strict and warnings))
    if args.json:
        _json(
            {
                "ok": not failed,
                "errors": errors,
                "warnings": warnings,
                "findings": [item.to_dict() for item in findings],
            }
        )
    else:
        for item in findings:
            location = f":{item.line}" if item.line else ""
            print(f"{args.file}{location}: {item.severity} {item.code}: {item.message}")
        print(f"{errors} errors, {warnings} warnings")
    return int(failed)


def _cmd_validate(args: argparse.Namespace) -> int:
    store = AtlasStore(args.atlas)
    components = store.search()
    missing = [item.id for item in components if not item.source.strip()]
    ok = not (args.require_source and missing)
    report = {
        "ok": ok,
        "components": len(store),
        "products": store.products(),
        "missing_source": missing,
    }
    if args.json:
        _json(report)
    else:
        print(f"Validated {len(store)} components across {len(store.products())} products.")
        if missing:
            print(f"{len(missing)} components have no source attribution.")
    return 0 if ok else 1


def _project_text(report: ProjectReport) -> str:
    lines = []
    for file in report.files:
        if file.error is not None:
            lines.append(f"{file.path}: input error: {file.error}")
        for finding in file.findings:
            location = f":{finding.line}" if finding.line is not None else ""
            lines.append(
                f"{file.path}{location}: {finding.severity} {finding.code}: {finding.message}"
            )
    summary = report.to_dict()["summary"]
    lines.append(
        f"Checked {summary['files']} prompts: {summary['passed']} passed, "
        f"{summary['failed']} failed, {summary['invalid']} invalid; "
        f"{summary['errors']} errors, {summary['warnings']} warnings."
    )
    return "\n".join(lines) + "\n"


def _cmd_check(args: argparse.Namespace) -> int:
    report = check_project(args.config)
    if args.format == "text":
        text = _project_text(report)
    else:
        document = sarif_report(report) if args.format == "sarif" else report.to_dict()
        text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        target = resolve_path(args.out)
        inputs = {
            report.config.path,
            *(resolve_path(report.config.root / file.path) for file in report.files),
        }
        if target in inputs:
            raise ValueError(
                "report output must differ from the project configuration and prompt inputs"
            )
        atomic_write(target, text)
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(text, end="")
    return report.exit_code


def _cmd_schema(args: argparse.Namespace) -> int:
    text = json.dumps(get_schema(args.name), indent=2, ensure_ascii=False) + "\n"
    if args.out:
        atomic_write(args.out, text)
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(text, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="promptatlas", description="Offline tools for structured system prompts."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name: str, help_text: str, handler):
        entry = sub.add_parser(name, help=help_text)
        entry.set_defaults(func=handler)
        return entry

    def as_json(entry):
        entry.add_argument("--json", action="store_true", help="emit a single JSON document")

    def atlas_option(entry, *, required=False):
        entry.add_argument(
            "--atlas",
            required=required,
            help="custom JSONL atlas (defaults to bundled read-only examples)",
        )

    entry = command("parse", "parse prompt text into components", _cmd_parse)
    entry.add_argument("file", help="UTF-8 file, or - for stdin")
    entry.add_argument("--product", default="")
    entry.add_argument("--version", default="")
    entry.add_argument("--out")
    as_json(entry)

    entry = command("add", "add one component to a custom atlas", _cmd_add)
    entry.add_argument("file", help="UTF-8 component file, or - for stdin")
    entry.add_argument("--kind", required=True, choices=VALID_COMPONENT_KINDS)
    entry.add_argument("--product", default="")
    entry.add_argument("--version", default="")
    entry.add_argument("--tag", action="append")
    entry.add_argument("--source", default="")
    atlas_option(entry, required=True)
    as_json(entry)

    entry = command("diff", "compare prompt text or saved JSON specs", _cmd_diff)
    entry.add_argument("a")
    entry.add_argument("b")
    entry.add_argument(
        "--fail-on-change", action="store_true", help="exit 1 when ordered components differ"
    )
    as_json(entry)

    entry = command("generate", "compose an editable prompt draft", _cmd_generate)
    entry.add_argument("scenario")
    entry.add_argument("--max-per-kind", type=_positive, default=5)
    entry.add_argument("--out")
    atlas_option(entry)

    entry = command("eval", "export synthetic promptfoo canary checks", _cmd_eval)
    entry.add_argument("scenario")
    entry.add_argument(
        "--prompt-file", help="evaluate this actual system prompt instead of a generated draft"
    )
    entry.add_argument("--provider", default=DEFAULT_PROVIDER)
    entry.add_argument(
        "--out",
        default="promptfoo-eval.json",
        help="output JSON file; use an empty string for stdout only",
    )
    atlas_option(entry)

    entry = command("search", "filter atlas components", _cmd_search)
    entry.add_argument("--kind", choices=VALID_COMPONENT_KINDS, default="")
    entry.add_argument("--tag", action="append")
    entry.add_argument("--product", default="")
    entry.add_argument("--query", default="")
    entry.add_argument("--limit", type=_positive, default=20)
    atlas_option(entry)
    as_json(entry)

    entry = command("lint", "check prompt structure with explainable rules", _cmd_lint)
    entry.add_argument("file", help="prompt text or a saved JSON spec; - reads stdin")
    entry.add_argument("--strict", action="store_true", help="fail on warnings as well as errors")
    entry.add_argument("--require", action="append", choices=VALID_COMPONENT_KINDS)
    entry.add_argument(
        "--allow-variable",
        action="append",
        help="declare an intentional runtime variable; repeatable",
    )
    as_json(entry)

    entry = command("validate", "validate JSONL schema, IDs, and attribution", _cmd_validate)
    entry.add_argument("--require-source", action="store_true")
    atlas_option(entry)
    as_json(entry)

    entry = command("check", "check every prompt in a project contract", _cmd_check)
    entry.add_argument(
        "--config",
        default="promptatlas.json",
        help="project JSON file; prompt paths are relative to it",
    )
    formats = entry.add_mutually_exclusive_group()
    formats.add_argument("--format", choices=("text", "json", "sarif"), default="text")
    formats.add_argument(
        "--json",
        dest="format",
        action="store_const",
        const="json",
        help="emit a single JSON document",
    )
    entry.add_argument("--out", help="write the report atomically to a file")

    entry = command("schema", "export an offline JSON Schema document", _cmd_schema)
    entry.add_argument("name", choices=SCHEMA_NAMES)
    entry.add_argument("--out")

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BrokenPipeError:
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f"promptatlas: error: {exc}\n")
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

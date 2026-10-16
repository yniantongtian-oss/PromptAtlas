"""PromptAtlas command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parse import parse_prompt
from .atlas import AtlasStore
from .diff import diff_specs, diff_summary
from .generate import generate_prompt
from .eval_export import export_eval_cases
from .schema import Component


def _cmd_parse(args):
    raw = Path(args.file).read_text(encoding="utf-8")
    spec = parse_prompt(raw, product=args.product, version=args.version)
    if args.out:
        spec.save(args.out)
    print(json.dumps(spec.stats(), indent=2))
    print(f"\n{len(spec.components)} components -> {args.out or '(not saved)'}")
    return 0


def _cmd_add(args):
    store = AtlasStore(args.atlas)
    comp = Component(kind=args.kind, content=Path(args.file).read_text(
        encoding="utf-8"), product=args.product, version=args.version,
        tags=args.tag or [])
    store.add(comp)
    print(f"added {comp.id} [{comp.kind}] ({len(store)} total)")
    return 0


def _cmd_diff(args):
    spec_a = parse_prompt(Path(args.a).read_text(encoding="utf-8"),
                          version=Path(args.a).name)
    spec_b = parse_prompt(Path(args.b).read_text(encoding="utf-8"),
                          version=Path(args.b).name)
    result = diff_specs(spec_a, spec_b)
    print(diff_summary(result))
    return 0


def _cmd_generate(args):
    store = AtlasStore(args.atlas) if args.atlas else AtlasStore()
    print(generate_prompt(args.scenario, store=store))
    return 0


def _cmd_eval(args):
    text = export_eval_cases(args.scenario, args.out)
    print(text)
    return 0


def _cmd_search(args):
    store = AtlasStore(args.atlas)
    results = store.search(kind=args.kind, tags=args.tag, product=args.product,
                           query=args.query or "")
    for c in results[:args.limit]:
        print(f"[{c.kind}] ({c.product} {c.version}) {c.content[:100]}")
    print(f"\n{len(results)} matches")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="promptatlas",
                                description="Structured atlas of AI system prompts.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("parse", help="structure a raw system prompt")
    s.add_argument("file")
    s.add_argument("--product", default="")
    s.add_argument("--version", default="")
    s.add_argument("--out", default="")
    s.set_defaults(func=_cmd_parse)

    s = sub.add_parser("add", help="add a component to the atlas")
    s.add_argument("file")
    s.add_argument("--kind", required=True,
                   choices=["role", "instruction", "tool", "guardrail",
                            "output_rule", "stop_condition", "few_shot",
                            "context", "other"])
    s.add_argument("--product", default="")
    s.add_argument("--version", default="")
    s.add_argument("--tag", action="append")
    s.add_argument("--atlas", default=None)
    s.set_defaults(func=_cmd_add)

    s = sub.add_parser("diff", help="component-level diff of two prompt versions")
    s.add_argument("a")
    s.add_argument("b")
    s.set_defaults(func=_cmd_diff)

    s = sub.add_parser("generate", help="generate a system prompt for a scenario")
    s.add_argument("scenario")
    s.add_argument("--atlas", default=None)
    s.set_defaults(func=_cmd_generate)

    s = sub.add_parser("eval", help="export promptfoo regression eval")
    s.add_argument("scenario")
    s.add_argument("--out", default="promptfoo-eval.yaml")
    s.set_defaults(func=_cmd_eval)

    s = sub.add_parser("search", help="search the atlas")
    s.add_argument("--kind", default="")
    s.add_argument("--tag", action="append")
    s.add_argument("--product", default="")
    s.add_argument("--query", default="")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--atlas", default=None)
    s.set_defaults(func=_cmd_search)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

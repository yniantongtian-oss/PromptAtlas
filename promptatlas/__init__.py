"""PromptAtlas: a structured atlas of AI system prompts, with parsing, diffing,
generation and regression-evaluation tooling.

Public API:
    PromptSpec, Component        -- core data structures
    parse_prompt()               -- structure a raw system prompt
    AtlasStore                   -- query the component atlas
    diff_specs()                 -- component-level version diff
    generate_prompt()            -- scenario-based prompt assembly
    export_eval_cases()          -- promptfoo-compatible eval export
"""

__version__ = "0.2.0"

from .atlas import AtlasStore
from .diff import diff_specs
from .eval_export import export_eval_cases
from .generate import generate_prompt
from .lint import Finding, lint_prompt, lint_spec
from .parse import parse_prompt
from .schema import Component, PromptSpec

__all__ = [
    "__version__",
    "Component",
    "PromptSpec",
    "parse_prompt",
    "AtlasStore",
    "diff_specs",
    "generate_prompt",
    "export_eval_cases",
    "Finding",
    "lint_prompt",
    "lint_spec",
]

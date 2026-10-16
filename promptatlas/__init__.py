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

__version__ = "0.1.0"

from .schema import Component, PromptSpec
from .parse import parse_prompt
from .atlas import AtlasStore
from .diff import diff_specs
from .generate import generate_prompt
from .eval_export import export_eval_cases

__all__ = [
    "__version__",
    "Component",
    "PromptSpec",
    "parse_prompt",
    "AtlasStore",
    "diff_specs",
    "generate_prompt",
    "export_eval_cases",
]

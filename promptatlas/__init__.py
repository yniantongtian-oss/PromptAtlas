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

__version__ = "0.3.1"

from .atlas import AtlasStore
from .diff import diff_specs
from .eval_export import export_eval_cases
from .generate import generate_prompt
from .lint import Finding, lint_prompt, lint_spec
from .load import load_prompt
from .parse import parse_prompt
from .project import ProjectConfig, ProjectReport, PromptContract, check_project, load_project
from .report import sarif_report
from .schema import Component, PromptSpec
from .schemas import get_schema

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
    "load_prompt",
    "load_project",
    "check_project",
    "ProjectReport",
    "ProjectConfig",
    "PromptContract",
    "sarif_report",
    "get_schema",
]

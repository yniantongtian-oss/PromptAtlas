# PromptAtlas

[![CI](https://github.com/yniantongtian-oss/PromptAtlas/actions/workflows/ci.yml/badge.svg)](https://github.com/yniantongtian-oss/PromptAtlas/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Review system prompts as structured, testable files.**

PromptAtlas is an offline Python library and CLI for extracting prompt components,
checking structural mistakes, comparing versions, and composing editable drafts.
Project contracts check complete prompt collections and export SARIF review reports.
It also exports synthetic checks for [promptfoo](https://www.promptfoo.dev/).
The core has **no runtime dependencies, network calls, model downloads, or API keys**.

Use it when a prompt change needs a readable review: which guardrail disappeared,
whether a rule was repeated, or whether an example was mistaken for an instruction.

```text
system.md -> parse -> components + original source spans
                    |-> lint -> explainable findings + CI exit codes
                    |-> diff -> additions, removals, edits, and reordering
JSONL atlas --------|-> search / compose -> editable prompt draft
system.md -----------> eval -> promptfoo config -> your chosen external runner
```

## Install from source

Python 3.10 or newer is required. Published PyPI availability is not assumed.

```bash
git clone https://github.com/yniantongtian-oss/PromptAtlas.git
cd PromptAtlas
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
promptatlas --version
```

Every command also works as `python -m promptatlas`.

## A five-minute workflow

The repository includes two original example prompts you can use immediately:

```bash
# Parse and preserve the original text, component IDs, and character offsets.
promptatlas parse atlas/versions/example-agent_v1.md --product example-agent --version v1 --out spec.json

# Run a structural check. Repeated --require flags enforce your own contract.
promptatlas lint atlas/versions/example-agent_v2.md --strict --require role --require guardrail

# Review a change; --fail-on-change returns exit code 1 when components differ.
promptatlas diff atlas/versions/example-agent_v1.md atlas/versions/example-agent_v2.md

# Search the bundled, attributed reference components.
promptatlas search --kind guardrail --tag coding-agent --json
promptatlas validate --require-source

# Check every file in the shipped project contract.
promptatlas check --json
promptatlas check --format sarif --out test-results/project.sarif

# Compose an editable draft without calling a model.
promptatlas generate "a customer support agent for an online store" --out draft.md

# Export checks for the prompt you actually plan to use.
promptatlas eval "customer support" --prompt-file atlas/versions/example-agent_v2.md --out promptfoo-eval.json
```

To execute the export separately, install a compatible Node.js runtime and provide
the credentials for the configured provider. For the tested runner:

```bash
npx --yes promptfoo@0.124.1 eval -c promptfoo-eval.json
```

Exporting is offline. Running an external model provider may send prompt text to
that provider and incur charges. Choose another provider with `--provider`.

## What you get

| Workflow | Behavior |
| --- | --- |
| `parse` | Nine component kinds, stable IDs, ordered source spans, opaque fenced code and examples, lossless original text in saved specs |
| `lint` | Empty input, missing role, repeated components, explicit Always/Never conflicts, unresolved variables, unclosed fences, required sections |
| `diff` | Case-sensitive and duplicate-aware comparisons; disjoint added/removed/changed groups; ordering changes; JSON and CI gates |
| `search` | Filter a JSONL atlas by kind, all requested tags, product, or text |
| `generate` | Deterministic keyword and tag retrieval; drafts remain editable and require review |
| `eval` | Actual system/user chat messages, a synthetic disclosure canary, and a non-empty-response check |
| `validate` | Validate every JSONL record, unique IDs, and optional source attribution |
| `check` | Check a complete prompt project with shared/per-file contracts; export text, JSON, or SARIF |
| `schema` | Export packaged JSON Schema documents for components, saved specs, and project contracts |

`parse`, `lint`, `diff`, `search`, `add`, `validate`, and `check` support `--json`.
Text inputs accept `-` for stdin. Exit codes are **0** for success, **1** for a
requested quality gate that fails, and **2** for invalid input or usage.

## Python API

```python
from promptatlas import AtlasStore, PromptSpec, diff_specs, lint_prompt, parse_prompt

before = parse_prompt("You are a reviewer.\nNever invent evidence.", version="v1")
after = parse_prompt(
    "You are a reviewer.\nNever invent evidence.\nAlways cite sources.", version="v2"
)

assert diff_specs(before, after)["has_changes"]
assert not lint_prompt(before.raw)
before.save("spec.json")
assert PromptSpec.load("spec.json").raw == before.raw

for component in AtlasStore().search(kind="guardrail", tags=["coding-agent"]):
    print(component.id, component.source, component.content)
```

To maintain your own atlas, use an explicit writable path:

```bash
promptatlas add my-rule.txt --atlas my-atlas.jsonl --kind guardrail --tag coding-agent --source "Original rule by the project team"
promptatlas validate --atlas my-atlas.jsonl --require-source
```

The bundled atlas is read-only. Custom stores use atomic file replacement and
support one writer at a time. See the [CLI reference](docs/CLI.md) for details.

## Check a complete project

Commit a `promptatlas.json` contract beside your prompt files. Shared requirements
apply to every listed file; individual entries can add required sections or
choose a warning policy. Paths are resolved from the configuration directory.

```json
{
  "schema_version": 1,
  "strict": true,
  "require": ["role", "guardrail"],
  "prompts": ["prompts/reviewer.md", "prompts/support.md"]
}
```

```bash
promptatlas check --config promptatlas.json --json
promptatlas schema project --out project.schema.json
```

Reports cover all listed files, preserve input errors, and cannot overwrite
prompt inputs. SARIF output includes real source locations and stable finding
fingerprints. The repository's CI publishes its report to GitHub and retains a
downloadable artifact. Read the [project workflow](docs/PROJECTS.md) and
[schema contract](docs/SCHEMAS.md) for integration details.

Templates can keep strict warning gates by declaring intentional names through
`allow_variables` in project/file contracts or repeated `lint --allow-variable`
options. Unknown names and TODO markers still warn. Try the complete
[template project](examples/template-project/promptatlas.json) and read the
[policy contract](docs/PROJECTS.md#intentional-template-variables).

JSON inputs reject duplicate object names and non-finite numbers before field
validation, and nesting deeper than 900 levels is rejected on every platform
before decoding. Both are reported as input errors, while fenced data stays
intact. See the [JSON input policy](docs/SCHEMAS.md#json-input-policy).

## Scope and limitations

- Parsing is an English-oriented heuristic. The confidence field is a rule weight,
  not a calibrated probability. Review ambiguous or domain-specific language.
  Supported literal boundaries and the original manually labeled corpus are
  documented in [parsing evidence](docs/PARSING.md).
- Diffs measure text and ordering. They cannot determine whether a model's behavior
  improved; prose whitespace is normalized while code literals stay significant.
  Component edits are paired
  with a documented lexical threshold.
- Lint detects specific structural issues. Passing lint does not establish safety,
  factual accuracy, or resistance to prompt injection.
- Exported evals are a **starter set of synthetic canary checks**. They do not
  cover a comprehensive attack suite, scenario correctness, or encoded disclosure.
- Bundled components are **original MIT-licensed illustrations**, not recovered
  vendor prompts or evidence of production performance. See [data provenance](docs/DATA.md).

## Develop and verify

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=promptatlas --cov-report=term-missing
python examples/quickstart.py
python scripts/evaluate_parser.py --out test-results/parser-corpus.json
python -m build
python -m twine check --strict dist/*
python scripts/verify_distribution.py
```

The distribution verifier uses the sole wheel in a clean `dist/` directory; pass
an explicit wheel path if that directory contains multiple builds.
The [performance workflow](docs/PERFORMANCE.md) includes reproducible synthetic
timings and explains which large-input comparisons can still be expensive.

CI checks supported Python versions on Linux, plus Windows and macOS, and installs
the built wheel in a fresh environment outside the checkout. Changes are checked
before publication; local tests and external model evaluations are separate forms
of evidence. See [validation](docs/VALIDATION.md) for the acceptance procedure.

## Project direction

The focus is a small, inspectable layer between prompt files and evaluation tools.
Read the [research and design rationale](docs/RESEARCH.md),
[architecture](docs/ARCHITECTURE.md), and [changelog](CHANGELOG.md).

Next priorities are a larger independently labeled parser corpus, user-provided
scenario assertions, and reviewable import/export adapters. New features should
bring a concrete use case and an observable acceptance check.

Contributions are welcome; start with [CONTRIBUTING.md](CONTRIBUTING.md).
Report vulnerabilities using [SECURITY.md](SECURITY.md).
Code and bundled original examples are available under the [MIT license](LICENSE).

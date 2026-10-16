# Validation contract

Tests establish the stated software behavior. They do not establish a model's
quality or the security of a deployed application. Run all steps from a clean
checkout with Python 3.10 or newer.

## Core and command-line checks

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=promptatlas --cov-report=term-missing
promptatlas validate --require-source --json
promptatlas check --json
python examples/quickstart.py
python scripts/evaluate_parser.py --out test-results/parser-corpus.json
```

Ruff is pinned to 0.17.1 so local and CI formatting agree, including Python code
blocks in Markdown. Use the project's development environment rather than an
unrelated global Ruff installation.

The regression suite includes failures observed in the initial prototype:
unstable IDs, lost original text, duplicate few-shot parsing, code misclassified
as guardrails, collapsed duplicate diff entries, unreported case changes,
double-counted edits, missing custom stores, failed-write state mutation, empty
custom-store replacement, and an exporter that omitted its system prompt.

Additional cases exercise CRLF and Unicode offsets, deterministic randomized
roundtrips, atomic-write failure injection, malformed-row diagnostics, unchanged
reload state on errors, source attribution, machine-readable CLI output, stdin,
and real module execution from a directory outside the checkout.

The [parser corpus](PARSING.md) contains original, manually labeled structural
cases. Its runner compares full ordered kind/content pairs, findings, source spans,
and saved-spec roundtrips. A deliberately wrong expected label must fail. These
cases are visible during development and cannot establish held-out accuracy.

## Distribution checks

```bash
python -m build
python -m twine check --strict dist/*
python scripts/verify_distribution.py
```

The default build creates an sdist and builds its wheel from that sdist. The
verification script then creates another virtual environment outside the checkout,
installs that wheel without runtime dependencies, and exercises public imports,
the installed executable, reference data, parsing, search, and eval export.
Project checks, SARIF export, and all three packaged schemas are also exercised
from that installed wheel.
The sdist must contain examples and test fixtures as well as package resources.

## External runner compatibility

The compatibility test uses promptfoo 0.124.1, Node.js 22.22 or newer, and local
fixtures only. No API credentials or model calls are required. It checks:

1. The exported configuration loads and renders system/user messages correctly.
2. A fixed refusal response passes every exported assertion.
3. Echoing the complete system prompt fails all five canary probes.
4. Refusal phrasing itself is accepted, and the ordinary non-empty response passes.
5. Literal template syntax in the system prompt survives rendering.

These are positive and negative integration controls. A refusal fixture passing
is not an LLM safety measurement; the Echo failure is intentional evidence that
disclosure assertions detect the target condition.

## CI acceptance

CI runs lint and tests across supported Python versions on Linux and checks
Windows/macOS behavior separately. It builds and inspects distributions, executes
the installed wheel outside the source directory, and runs the pinned external
runner controls. Workflow dependencies are pinned to reviewed commit SHAs, and
workflow tokens use read-only repository permissions except for the dedicated
SARIF upload job, which requests `security-events: write`. That job waits for
GitHub to process the report before it succeeds. Pull requests retain report
artifacts without publishing a new analysis.

Project regressions cover complete multi-file results, strictness overrides,
configuration-relative paths, malformed specs, missing inputs, symlink boundaries,
output overwrite protection, stable fingerprints, and saved-spec line handling.
JSON Schema documents are checked by an independent development validator.
The test coverage floor is 90%.

A successful local run is not a substitute for a successful workflow on the
pushed commit. Inspect the GitHub Actions run associated with the final commit.

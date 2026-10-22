# Contributing

Contributions should solve a concrete problem and include a way to verify the
result. Keep code, documentation, issue reports, and pull requests in English.

## Local setup

```bash
python -m venv .venv
# Activate your environment, then:
python -m pip install -e ".[dev,mcp]"
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=promptatlas --cov-report=term-missing
python examples/quickstart.py
```

Before changing package resources, metadata, or public imports, also build and
exercise the installed wheel:

```bash
python -m build
python -m twine check --strict dist/*
python scripts/verify_distribution.py
```

## Changes that help

- Parser fixes with a minimal input and expected component kinds/source spans.
- Diff regressions involving repeated rules, reordering, or meaningful text edits.
- Lint checks with a stable explanation and a documented false-positive boundary.
- Eval cases whose expected success and failure can both be demonstrated.
- Original, attributed reference components that have a clear reuse basis.
- Documentation that makes a complete workflow easier to run.
- Project contracts and report integrations with verified source locations.

The runtime stays standard-library-only. New dependencies or hosted services need
a use case that justifies their installation, maintenance, and privacy costs.
The MCP server is the optional exception: it depends on the official MCP SDK,
is not imported by the core, and is covered by direct handler tests plus one
stdio client round trip.

## Data contributions

Read [data provenance](docs/DATA.md) before adding records. Include the exact
source and reuse basis. Do not submit leaked prompts, credentials, private user
content, or copyrighted material without permission. Passing schema validation
does not replace human source review.

## Pull requests

Describe the problem, resulting behavior, and checks you ran. Include a failing
regression when fixing a defect. Update affected examples and documentation.
Separate deterministic fixture results from live-model measurements and name the
provider/model/dataset when reporting the latter. Avoid speculative quality,
security, performance, or adoption claims.

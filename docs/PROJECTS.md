# Project contracts and review reports

A prompt collection should have one repeatable check, a clear failure policy,
and a report that points to the file needing attention. A project contract adds
that workflow without a server, model call, or runtime dependency.

## Try the shipped project

From the repository root after installation:

```bash
promptatlas check
promptatlas check --json
promptatlas check --format sarif --out test-results/project.sarif
```

The included `promptatlas.json` checks both original version fixtures. They must
contain a role, guardrails, output rules, and stop conditions. Strict mode also
rejects warnings. A successful report covers every listed file.

## Define your own contract

Create `promptatlas.json` beside your prompt directory. Paths refer to existing
files and are relative to the configuration, independent of the process working
directory:

```json
{
  "$schema": "./project.schema.json",
  "schema_version": 1,
  "strict": true,
  "require": ["role", "guardrail"],
  "prompts": [
    "prompts/reviewer.md",
    {
      "path": "prompts/support.md",
      "require": ["stop_condition"],
      "strict": false
    }
  ]
}
```

Export the editor schema locally:

```bash
promptatlas schema project --out project.schema.json
promptatlas check --config path/to/promptatlas.json --json
```

`require` on a file adds to the project requirements. A file's `strict` setting
overrides the project default. Required kinds are deduplicated. `.json` inputs
are validated saved prompt specs; other files are UTF-8 prompt text.

Files are listed explicitly. Empty projects, unknown settings, duplicate resolved
paths, absolute paths, parent traversal, and symlink escapes are rejected. Use
forward slashes for portable paths. A missing or unreadable prompt is an input
error, not an empty successful scan. Other valid entries are still checked.

## Report and exit-code contract

| Exit | Meaning |
| --- | --- |
| 0 | Every listed file passed its configured requirements |
| 1 | At least one file failed lint or its strict warning policy |
| 2 | Configuration or prompt input was invalid or unreadable |

JSON reports have a schema version, an overall `ok` flag, per-file findings, and
summary counts. Reports do not embed original prompt text. Per-file `stats` are
computed from validated components. JSON output is deterministic for unchanged
inputs; no timestamp is inserted.

Text, JSON, and SARIF reports can be written atomically with `--out`. The target
must differ from the project configuration and every prompt input. A receipt
goes to stderr, so stdout remains suitable for piping.

## SARIF and GitHub integration

The SARIF exporter follows GitHub's documented SARIF 2.1.0 subset. It includes
stable rule IDs, severity, real file URIs, source lines for text prompts, and
fingerprints that remain stable when an unchanged finding moves to another line.

A saved JSON spec stores an original prompt inside a JSON field. Its prompt line
numbers are not physical JSON file lines. Such findings omit the physical region
and retain `originalPromptLine` as a result property. Invalid inputs produce
execution notifications with `executionSuccessful: false`.

This repository's CI generates the report and uploads it through the pinned
`github/codeql-action/upload-sarif` action. GitHub publication runs on main-branch
pushes and manual runs; pull requests still generate a downloadable report.
Only that job requests `security-events: write`.

To integrate another repository, install PromptAtlas, check its project contract,
and upload the resulting SARIF. GitHub documents the supported fields, token
permissions, and repository availability in its [SARIF reference](https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/sarif-support)
and [upload guide](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file).

These are structural review findings. They do not constitute vulnerability
validation or a measurement of a model's behavior.

## Python integration

```python
from promptatlas import check_project, get_schema, sarif_report

report = check_project("promptatlas.json")
print(report.to_dict()["summary"])
assert report.exit_code == 0

sarif = sarif_report(report)
assert sarif["version"] == "2.1.0"
assert get_schema("project")["title"] == "PromptAtlas project contract"
```

`load_project()` validates a contract without running its checks. `load_prompt()`
loads text or a saved JSON spec through the same path used by the CLI.

## JSON Schema documents

```bash
promptatlas schema component
promptatlas schema spec
promptatlas schema project
```

All three JSON Schema 2020-12 documents ship in the wheel and are available without
network access. They use local definitions instead of remote schema references.
An optional `$schema` field in input data is descriptive; PromptAtlas never
fetches it. An editor may use that field according to its own configuration.

Schema validation checks data shape. PromptAtlas additionally validates source
excerpts, non-overlapping ordered spans, unique component IDs, computed counts,
and resolved project path boundaries. Initial specs without raw text or spans
remain readable; those missing locations cannot be reconstructed.

# Command reference

All input files use UTF-8; a UTF-8 BOM is accepted. `python -m promptatlas` is an
alternative to the installed `promptatlas` executable. Run any command with
`--help` for the complete option list.

## Parse

```bash
promptatlas parse system.md --product support --version v2 --out spec.json --json
```

The saved spec includes `schema_version`, `raw`, `product`, `version`, `stats`, and
`components`. Components carry `start` and `end` offsets in Unicode characters;
`end` is exclusive. Offsets refer to the supplied original text, including its
line endings. IDs are hashes of kind, content, and duplicate occurrence index.
Identical inputs yield identical JSON; repeated rules receive distinct IDs.

Nine kinds are recognized: `role`, `instruction`, `tool`, `guardrail`,
`output_rule`, `stop_condition`, `few_shot`, `context`, and `other`.
The heuristic parser leaves fenced code opaque and recognizes valid JSON
function schemas and XML-style tool blocks. Markdown section headings guide
classification. It does not execute content or infer model behavior.

## Lint and gate changes

```bash
promptatlas lint system.md --strict --require role --require guardrail --json
promptatlas lint template.md --strict --allow-variable input --allow-variable release.name --json
promptatlas diff before.md after.md --json --fail-on-change
promptatlas diff before.json after.json
```

| Rule | Severity | Meaning |
| --- | --- | --- |
| PA001 | error | Empty prompt |
| PA002 | warning | No explicit role or mission found |
| PA003 | warning | Same-kind component repeated; prose whitespace is normalized, code stays literal |
| PA004 | error | Opposite Always/Never directives with identical remaining words |
| PA005 | warning | Undeclared template name, unsupported expression/delimiter, or prose TODO/FIXME in a directive |
| PA006 | error | Unclosed fenced code block |
| PA007 | error | A component kind requested with `--require` is absent |

Lint checks prompt structure only. Declare intentional runtime names with repeated
`--allow-variable NAME` options. Names are case-sensitive ASCII identifiers,
optionally separated by dots, such as `input` or `release.name`. Declarations allow
exact `{{ name }}` and `${name}` placeholders without rendering or accessing values.
They do not permit other variables, expressions, incomplete opening delimiters, or
real TODO/FIXME markers. TODO labels in inline code are literal; placeholders in
inline code still require declarations. Opaque context, examples, and tools retain
their existing exemption from PA005. See [template contracts](PROJECTS.md#intentional-template-variables)
for policy scope and limitations.
Default lint fails on errors. Strict mode also fails on warnings.

Diff groups are disjoint. Exact matches consume duplicate occurrences first.
Remaining same-kind candidates with lexical similarity of at least 0.6 are paired
in descending score order; source order resolves ties. Case is significant,
prose whitespace is normalized, and reordered exact matches are flagged separately.
Whitespace inside inline code, tools, examples, and fenced code remains significant.
Opposite-rule checks also preserve case inside inline code identifiers.
The similarity score measures ordered exact matches. All content changes,
including near-identical edits and case changes, remain observable.
See [performance boundaries](PERFORMANCE.md) for repeated and large inputs.

Saved initial-release specs without `raw` or `schema_version` remain readable.
Source locations and raw-text lint checks cannot be reconstructed when absent.

## Atlas operations

```bash
promptatlas search --kind guardrail --tag coding-agent --query destructive --json
promptatlas search --atlas my-atlas.jsonl --product review --limit 10
promptatlas add rule.md --atlas my-atlas.jsonl --kind instruction --tag review --source "Original project rule" --json
promptatlas validate --atlas my-atlas.jsonl --require-source --json
```

Tags use an AND filter and ignore case. Product and content filters are
case-insensitive substrings. Results retain atlas order. `--limit` must be
positive. JSON search output includes the complete match count and the selected
result page; nothing is printed after the JSON document.

`add` requires a custom path and creates missing parent directories. Missing
custom stores fail for read operations; a typo never silently loads the bundled
atlas. Every row is validated before a reload or write. Duplicate IDs are errors.
File replacement is atomic; failed writes preserve the prior file and in-memory
view. This is a single-writer local format, without cross-process locking.

## Compose and export

```bash
promptatlas generate "a coding agent" --max-per-kind 4 --out draft.md
promptatlas eval "a coding agent" --prompt-file draft.md --provider ollama:chat:llama3.2 --out eval.json
```

Generation ranks original atlas components using exact token and tag overlap,
with a small bonus for `universal` components. It makes no LLM calls and does not
register real tools. Tool text in a draft is illustrative; bind actual tools in
your application. Empty custom atlases remain empty.

Export uses JSON, which promptfoo accepts directly. It includes the actual system
prompt, a user-message variable, five synthetic canary disclosure probes, and a
non-empty-response test. A public synthetic canary is appended to the test copy.
The default provider is `openai:chat:gpt-4o-mini`; set `--provider` to choose yours.
Default assertions check literal canary disclosure and do not ban refusal phrases.
Review or extend assertions before treating these cases as a domain regression suite.
Exporting does not execute tests. `sharing` is disabled in the exported config.

## Project checks and schemas

```bash
promptatlas check --config promptatlas.json
promptatlas check --json
promptatlas check --format sarif --out test-results/project.sarif
promptatlas schema project --out project.schema.json
promptatlas schema spec
promptatlas schema component
```

Project checks evaluate every explicitly listed file against shared and per-file
requirements. An invalid input remains visible while other files are checked.
Reports never overwrite the selected configuration or prompt inputs. See the
[project guide](PROJECTS.md) for the complete manifest and SARIF contract.

`schema` exports packaged JSON Schema 2020-12 documents. Metadata URLs are not
fetched; runtime loading additionally validates source excerpts, ordered spans,
unique IDs, and derived counts. See [schema invariants](SCHEMAS.md).

## Process contract

| Exit | Meaning |
| --- | --- |
| 0 | Command completed or requested gate passed |
| 1 | Lint/attribution/project gate failed, or `diff --fail-on-change` detected changes |
| 2 | Invalid input, missing file, malformed JSON, or usage error |
| 130 | Interrupted during command execution |

`parse`, `lint`, `add`, and either diff text input accept `-` for stdin. Both diff
inputs cannot simultaneously consume stdin. Input errors go to stderr without a
traceback. Normal `--json` results are a single JSON document on stdout.

## MCP server

```bash
python -m pip install "promptatlas[mcp]"
promptatlas-mcp
```

`python -m promptatlas.mcp` starts the same server. The process speaks MCP over
stdio and waits for a host; do not type at it. It uses the official MCP Python
SDK. The core install does not include that SDK. If the extra is missing, the
process exits with status 1 and installation instructions instead of a traceback.

The server exposes the library functions as read-only tools. Arguments are
prompt text. The server does not open prompt files, custom atlases, or the
network.

| Tool | Parameters | Result |
| --- | --- | --- |
| `parse` | `text`, optional `product` and `version` | `PromptSpec.to_dict()` |
| `lint` | `text`, optional `strict`, `required_kinds`, `allowed_variables` | `ok`, `errors`, `warnings`, and `findings`. `strict` fails the gate on warnings. Findings are included either way |
| `compare` | `before`, `after`, optional product and version labels for each side | `diff_specs` as JSON. Pass prompt text, or the `raw` field of a saved spec |
| `compose` | `scenario`, optional `max_per_kind` (default 5) | Editable draft from the bundled atlas. No model is called |

`compose` requires a non-empty scenario and a positive `max_per_kind`. Unknown
lint kinds and invalid variable names are tool errors. A lint gate of `ok:
false` is a successful tool call so the host can read the findings.

Claude Code (`.mcp.json`):

```json
{
  "mcpServers": {
    "promptatlas": {
      "type": "stdio",
      "command": "promptatlas-mcp"
    }
  }
}
```

```bash
claude mcp add --transport stdio promptatlas -- promptatlas-mcp
```

Cursor (`.cursor/mcp.json` or `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "promptatlas": {
      "type": "stdio",
      "command": "promptatlas-mcp"
    }
  }
}
```

Use the full path to `promptatlas-mcp`, or `python` with args `["-m",
"promptatlas.mcp"]`, when the console script is not on the host's `PATH`.

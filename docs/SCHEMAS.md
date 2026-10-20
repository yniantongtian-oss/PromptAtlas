# Interoperability schemas

PromptAtlas publishes three self-contained JSON Schema 2020-12 documents:

| Name | Packaged document | Data represented |
| --- | --- | --- |
| `component` | `promptatlas/data/component.schema.json` | One annotated prompt component |
| `spec` | `promptatlas/data/spec.schema.json` | A saved prompt and its ordered components |
| `project` | `promptatlas/data/project.schema.json` | Explicit files, required kinds, strictness, and allowed variable names |

Use `promptatlas schema NAME --out schema.json` to export one into a project.
The Python equivalent is `get_schema(NAME)`, which returns an independent dict.
Both operations read packaged resources and make no network requests.

Schemas are tested with an independent JSON Schema validator in development.
The runtime uses standard-library validation and has no validator dependency.
The [2020-12 specification](https://json-schema.org/draft/2020-12/json-schema-core)
defines the schema vocabulary; `schema_version: 1` identifies PromptAtlas's own
data contract and is a separate version.

## Runtime invariants

A generic schema validator cannot express all source relationships. Loading a
saved spec additionally rejects duplicate IDs, mismatched derived `stats`,
out-of-range source spans, incorrect source excerpts, and overlapping or
out-of-order spans. Hand annotations may omit spans. Legacy specs without raw
text remain supported when they do not claim unavailable source locations.

Component confidence must be finite and between zero and one. Booleans and huge
out-of-range integers are rejected with a validation error. Unknown component,
spec, and project fields are errors rather than silently discarded metadata.
Descriptive `$schema` strings are allowed and never fetched.

Project checks additionally normalize paths, reject duplicate resolved inputs,
and prevent symlinks from selecting files outside the configuration directory.
Reports cannot overwrite their own prompt inputs or configuration.
Project and per-file `allow_variables` declarations use the same identifier grammar
in the packaged schema and runtime. Runtime validation combines additive scopes
and removes repeated names. It never renders a template or fetches variable values.

These invariants make exported reports reviewable. They do not establish that
an annotated classification is correct or that an LLM will follow a prompt.

## JSON input policy

Runtime loaders for projects, saved specs, JSONL rows, and tool-content recognition
share one decoder policy. Object member names must be unique after JSON string
decoding: an escaped spelling cannot override the same literal key. Repeating an
array value, such as an allowed variable name, remains valid and is handled by
that field's normal contract. The same key may appear in separate objects.

NaN/Infinity constants are rejected. JSON floating-point numbers must decode to
finite Python floats; an exponent that overflows that range is an input error.
Ordinary numbers and strings containing words such as `NaN` remain supported.
These checks happen before field/schema validation and cannot be recovered by a
generic validator after a permissive decoder has discarded duplicate names.

Inputs nested deeper than 900 levels are rejected before decoding, so the same
input fails identically on every platform instead of depending on the
interpreter's stack-size-derived recursion limit. Decoder recursion failures that
still occur become `ValueError` input diagnostics. Project reports continue
checking other files, and the CLI retains exit code 2 for invalid input. A fenced
block that cannot be decoded or identified as a tool stays unchanged as opaque
context. Tool recognition uses an iterative worklist within that supported depth.
Neither step executes code or raises the interpreter's limits.

This policy does not impose a file-size limit, bound all CPU/memory consumption,
or sandbox JSON processing. Python's existing integer limits remain in effect.
Review unusually large external files before loading them.

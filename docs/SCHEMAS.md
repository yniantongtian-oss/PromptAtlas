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

# Architecture

PromptAtlas has a standard-library-only runtime. Every operation is local and
inspectable. External evaluation is an exported configuration, not an implicit
network request.

| Module | Responsibility |
| --- | --- |
| `schema.py` | Validate components and versioned, lossless prompt specs |
| `parse.py` | Scan ordered source spans; preserve code, examples, and tool blocks |
| `lint.py` | Return stable rule codes and explainable structural findings |
| `diff.py` | Compare ordered components without collapsing duplicates |
| `atlas.py` | Read packaged examples and explicit custom JSONL stores |
| `generate.py` | Rank components by keyword/tag overlap and compose drafts |
| `eval_export.py` | Export actual chat prompts and synthetic canary assertions |
| `_io.py` | Write complete UTF-8 files before atomic replacement |
| `cli.py` | File/stdin handling, JSON output, errors, and CI exit codes |

## Design decisions

Parsing returns original text plus ordered components. Fenced blocks and examples
are opaque to sentence classification; text inside them cannot create an extra
rule. Known Markdown headings supply section context. Stable hashes make equal
inputs reproducible, while duplicate occurrence indices preserve repeated rules.
Offsets identify content without rewriting the original prompt.

Diffing first matches exact normalized kind/content pairs one occurrence at a
time. Remaining edits are paired only within the same kind. Added, removed, and
changed groups do not overlap. Reordering is distinct from a content edit.

Bundled examples live under `promptatlas/data/` and are read through
`importlib.resources`. They ship in wheels and source distributions. User writes
require an explicit custom path; package resources remain read-only. Writes
validate all rows and replace the file atomically. Multiple concurrent writers
are not supported.

The package never runs tools described in a prompt, imports prompt-specified
code, reads credentials, or calls an LLM. A generated draft is plain text. An
evaluation file becomes executable only when the user chooses an external runner.

## Extension boundaries

New parser rules need labeled examples and a regression case. New lint rules need
a stable code, an explanation, and a clear false-positive boundary. Exporters
must include the prompt under evaluation and distinguish fixtures from live model
results. Data additions require provenance and a clear reuse basis.

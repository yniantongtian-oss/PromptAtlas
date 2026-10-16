# Architecture

PromptAtlas has a standard-library-only runtime. Every operation is local and
inspectable. External evaluation is an exported configuration, not an implicit
network request.

| Module | Responsibility |
| --- | --- |
| `schema.py` | Validate components and versioned, lossless prompt specs |
| `parse.py` | Scan ordered source spans; preserve code, examples, and tool blocks |
| `_markdown.py` | Share fence and inline-code boundaries without rewriting text |
| `_text.py` | Normalize prose for comparisons while preserving code literals |
| `lint.py` | Return stable rule codes and explainable structural findings |
| `load.py` | Share lossless text and validated-spec loading across workflows |
| `project.py` | Validate file contracts and aggregate complete per-file checks |
| `report.py` | Export SARIF with accurate locations and stable fingerprints |
| `schemas.py` | Export packaged, self-contained JSON Schema documents |
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

Inline code on a single source line is hidden from sentence-boundary and keyword
classification while remaining unchanged in component content. Fenced code within
an example remains part of that example even when it contains headings or blank
lines. See [parsing evidence and boundaries](PARSING.md) for the supported subset.

Diffing first matches exact normalized kind/content pairs one occurrence at a
time. Remaining edits are paired only within the same kind. Added, removed, and
changed groups do not overlap. Reordering is distinct from a content edit.
Exact duplicate queues consume occurrences in constant time. Identical normalized
sequences have similarity 1 without quadratic sequence matching. Changed-pair
candidates retain the same threshold and source-order tie breaking, using cached
indexes and safe similarity upper bounds. Edited repetitive sequences can still
require quadratic work; see [performance evidence](PERFORMANCE.md).

Bundled examples live under `promptatlas/data/` and are read through
`importlib.resources`. They ship in wheels and source distributions. User writes
require an explicit custom path; package resources remain read-only. Writes
validate all rows and replace the file atomically. Multiple concurrent writers
are not supported.

The package never runs tools described in a prompt, imports prompt-specified
code, reads credentials, or calls an LLM. A generated draft is plain text. An
evaluation file becomes executable only when the user chooses an external runner.

## Project and interchange boundaries

Project contracts resolve paths relative to the configuration and bind every
input explicitly. Invalid files are recorded alongside valid results. Shared
requirements combine with per-file settings; gate outcomes remain distinct from
execution errors. SARIF uses text-file locations directly and avoids mapping raw
prompt lines onto the unrelated physical lines of a saved JSON document.

JSON Schema documents describe structural interchange. Runtime checks additionally
validate source excerpts, ordering, duplicate IDs, counts, and resolved paths.
These relationships stay in the core instead of depending on a remote schema
service or a runtime validator library.

## Extension boundaries

New parser rules need labeled examples and a regression case. New lint rules need
a stable code, an explanation, and a clear false-positive boundary. Exporters
must include the prompt under evaluation and distinguish fixtures from live model
results. Data additions require provenance and a clear reuse basis.

# Changelog

## 0.5.0

### Added

- Optional `mcp` extra and `promptatlas-mcp` stdio server. The `parse`, `lint`,
  `compare`, and `compose` tools call the existing library functions. The core
  package does not import the server and still has no runtime dependencies.

## 0.4.1

### Fixed

- Reject duplicate JSON object names before they can silently override project
  policies, saved components, or atlas records, including escaped duplicate names.
- Reject non-standard NaN/Infinity constants and floating-point overflow in JSON
  input while preserving ordinary numeric values and literal strings.
- Turn JSON decoder recursion failures into input errors; undecodable fenced
  content remains opaque context and generator output keeps the original text.
- Enforce a deterministic 900-level JSON nesting limit before decoding, so deep
  inputs fail the same way on Windows, Linux, and macOS rather than depending on
  the interpreter's stack-size-derived recursion limit.
- Recognize decodable nested tool lists iteratively instead of recursing through
  Python frames, and bound duplicate-key diagnostic length.

### Changed

- Share the JSON input policy across runtime loaders and the labeled-corpus runner.
- Exercise ambiguous-policy and deep-input controls from installed wheels.

## 0.4.0

### Added

- Explicit runtime variable declarations through `lint --allow-variable`, Python
  `allowed_variables`, and project/per-file `allow_variables` settings.
- Effective variable policies in per-file JSON reports, schema validation, and a
  complete strict template-project example.
- Installed-wheel positive/negative checks for intentional and undeclared variables.

### Fixed

- Allow declared placeholders without disabling strict warning gates.
- Keep undeclared names, unsupported expressions, incomplete delimiters, and
  genuine TODO/FIXME markers visible under the same PA005 rule.
- Treat inline-code TODO/FIXME labels as literals while still checking template
  placeholders inside inline code. Template contents are never rendered.

## 0.3.2

### Fixed

- Preserve inline-code whitespace in diffs and duplicate checks, and preserve
  literal case/whitespace when detecting opposite directives.
- Report CR, CRLF, LF, and other parser-recognized line boundaries consistently.

### Changed

- Use constant-time duplicate queues and bypass ordered sequence matching for
  identical normalized inputs.
- Reuse same-kind candidate indexes and reject only candidates whose similarity
  upper bounds fall below the existing threshold.
- Precompute source line offsets instead of rescanning each component prefix.
- Add a reproducible synthetic benchmark with correctness checks and explicit
  limits; edited repetitive sequences retain the existing comparison semantics.

## 0.3.1

### Fixed

- Keep same-line inline code intact during sentence splitting and classification.
- Preserve fenced code and its internal headings/blank lines inside examples.
- Share fence recognition between parsing and linting; inline triple-backtick
  spans no longer trigger false unclosed-fence findings.

### Added

- A manually labeled, original structural corpus and an offline report runner
  with mismatched-label negative controls and explicit evidence limitations.
- Include the corpus in source distributions and run it across the CI matrix.

## 0.3.0

### Added

- Project contracts with shared/per-file required sections and warning policies.
- Complete text, JSON, and SARIF reports across explicitly listed prompt files.
- GitHub report publication with stable fingerprints and accurate file locations.
- Packaged JSON Schema documents for components, saved specs, and project contracts.
- Public project, shared loading, schema, and SARIF APIs.

### Fixed

- Reject mismatched source spans, duplicate IDs, unknown fields, and stale counts
  when loading saved prompt specifications.
- Convert huge invalid confidence values into clear validation errors.
- Preserve original prompt line numbers without attaching them to JSON file lines.
- Prevent report outputs from overwriting prompt inputs or project configuration.
- Make the external runner's literal-text fixture consistent across line endings.
- Report cyclic project, prompt, and output symlinks as input errors without an
  unexpected traceback.

### Changed

- Raise the CI test coverage floor to 90%.
- Exercise project workflows and packaged schemas in clean installed-wheel checks.
- Discover a sole distribution wheel automatically, with explicit paths supported
  when multiple builds exist.

## 0.2.0

### Added

- Structural lint with stable rule codes, required sections, and strict CI gates.
- JSON output, stdin inputs, saved-spec comparisons, and documented exit codes.
- Atlas validation with unique IDs and optional provenance requirements.
- Module entry point, clean installed-wheel verification, and cross-platform CI.
- Positive and negative promptfoo fixture controls and English workflow references.

### Fixed

- Ship the reference atlas inside both wheels and source distributions.
- Preserve original prompt text, stable parser IDs, and source character offsets.
- Keep code, examples, and tool schemas intact without duplicate classification.
- Preserve repeated rules and case-sensitive edits in disjoint diff groups.
- Respect explicitly empty custom atlases and persist writes atomically.
- Evaluate the actual system prompt; allow legitimate refusal responses.

### Changed

- Python 3.10 or newer is required.
- `add` requires an explicit custom atlas path; bundled examples are read-only.
- Eval exports use JSON and configurable providers with narrow synthetic assertions.
- Documentation states heuristic and evaluation limitations explicitly.
- Canonical reference data moved to `promptatlas/data/components.jsonl`.

## 0.1.0

- Initial local prototype: parsing, diffing, draft composition, and eval export.

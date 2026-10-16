# Changelog

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

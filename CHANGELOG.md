# Changelog

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

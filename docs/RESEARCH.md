# Research and product decisions

Research date: 2026-10-16. This document records engineering choices and the
primary sources that informed them. It does not claim market share, adoption,
or superior model performance.

## The useful boundary

[Langfuse](https://github.com/langfuse/langfuse) combines observability,
evaluation, and prompt management. Its [experiment comparison guidance](https://langfuse.com/docs/evaluation/experiments/compare-experiments)
emphasizes keeping dataset versions and evaluator definitions comparable.
PromptAtlas should complement this workflow with reviewable local component
artifacts rather than introduce a second hosted registry.

The [PromptG CLI](https://github.com/promptg/cli) manages and renders prompt
collections, including variable inputs. [promptdiff](https://github.com/ManasVardhan/promptdiff)
provides versioning and diff workflows. These repositories demonstrate overlap
in prompt storage and templating. They do not establish comparative accuracy.
Our product decision is to concentrate on ordered component parsing, source
locations, explainable lint findings, and deterministic review gates.

## Evaluation must test the actual prompt

The [promptfoo chat format](https://www.promptfoo.dev/docs/configuration/prompts/)
supports explicit system and user messages. The exporter therefore attaches the
actual supplied prompt instead of evaluating only an attack string. Users choose
the provider, and generation never executes a paid evaluation implicitly.

The [deterministic assertion reference](https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic/)
provides literal-output checks. We use a public synthetic canary to give a narrow,
observable failure condition. Refusal wording is not treated as a defect. These
checks cannot establish general injection resistance, especially for paraphrased
or encoded leakage; scenario-specific tests remain necessary.

The [Echo provider](https://www.promptfoo.dev/docs/providers/echo/) returns the
rendered input without an external model call. It supports a useful negative
control: an implementation that echoes the canary must fail the disclosure
assertions. A second fixture provider emits a known refusal and must pass. Both
controls validate configuration plumbing and assertion polarity, not model safety.

## Reproducibility includes installed packages

[Setuptools' data-file guidance](https://setuptools.pypa.io/en/latest/userguide/datafiles.html)
recommends package-contained resources and `importlib.resources`. PromptAtlas now
ships its atlas in the wheel and keeps it read-only. A clean virtual environment
outside the checkout tests public imports, the installed CLI, bundled search, and
eval export. Source-tree tests alone would miss the initial missing-data defect.

## Priorities and acceptance checks

| Priority | Decision | Observable acceptance |
| --- | --- | --- |
| P0 | Preserve prompt text, ordering, and repeated rules | Roundtrip, source-span, and duplicate-diff tests |
| P0 | Export real chat messages with sensible assertions | Real promptfoo positive and negative fixture controls |
| P0 | Make installation usable outside the repository | Build from sdist; clean wheel installation and CLI smoke test |
| P1 | Make failures useful in CI | Single JSON outputs and documented 0/1/2 exit codes |
| P1 | Keep data traceable | Validate all records, unique IDs, and source fields |
| P1 | Give users an immediate complete example | Run the quickstart using only shipped original fixtures |
| P2 | Broaden parser evidence | Independent labeled prompts and transparent accuracy reports |
| P2 | Add integrations only where users need them | A concrete input/output contract and a runnable compatibility test |

## Deliberately bounded claims

Heuristic scores are not confidence calibration. Lexical diff similarity is not
semantic equivalence. A passing fixture suite is not a live-model result. Public
availability is not treated as a license to redistribute vendor prompts. No
vendor prompt corpus or speculative adoption claim is bundled with this release.

## Literal text boundaries

The [CommonMark code-span rules](https://spec.commonmark.org/0.31.2/#code-spans)
use equal-length backtick runs; the
[fenced-block rules](https://spec.commonmark.org/0.31.2/#fenced-code-blocks)
exclude backticks from backtick-fence info strings. This distinction matters:
literal words inside inline code must not create extra prompt directives, and a
code span at the start of a line must not become a false unclosed block.

PromptAtlas uses these boundaries in a deliberately limited scanner, not a full
CommonMark renderer. Same-line inline code and fenced examples have original,
manually labeled regression cases. Multiline inline spans, list-container
semantics, indented code, and general prose understanding require separate work.
The [corpus report](PARSING.md) makes that scope explicit instead of presenting
development fixtures as independent accuracy evidence.

## Scaling without changing review meaning

The [Python SequenceMatcher documentation](https://docs.python.org/3/library/difflib.html#sequence-matcher-objects)
describes cached second-sequence indexes and upper bounds for lexical similarity.
PromptAtlas uses both to avoid unnecessary candidate comparisons while retaining
its 0.6 threshold and deterministic pairing order. Disabling the automatic junk
heuristic remains necessary for repeated prompt components to stay observable.

An identical normalized component sequence has a known score of 1 and bypasses
the ordered matcher. Source-line offsets are indexed once. These improvements
target observed repeated-input costs without substituting a new diff metric.
The standard matcher can still take quadratic time on edited repetitive inputs;
the [benchmark](PERFORMANCE.md) reports synthetic workload timings, not a general
complexity or production-speed guarantee.

## Templates need an explicit review policy

The [promptfoo configuration guide](https://www.promptfoo.dev/docs/configuration/guide/)
documents variable substitution and richer Nunjucks constructs. Those constructs
belong to the external renderer. A local structural check should acknowledge
intentional names without evaluating expressions or inspecting runtime values.

PromptAtlas therefore accepts exact declared names in simple placeholders, keeps
strict checks active for other findings, and reports effective per-file policy.
Unknown names and unsupported expressions remain warnings. This narrower contract
does not claim to validate an entire template language or guarantee that a later
renderer has received correct values.

## JSON must not silently change a policy

[RFC 8259 section 4](https://www.rfc-editor.org/rfc/rfc8259#section-4) recommends
unique object names and describes inconsistent handling of duplicates. The
[Python JSON interoperability documentation](https://docs.python.org/3/library/json.html#standard-compliance-and-interoperability)
explains that its default decoder keeps the last duplicate and accepts non-finite
number extensions. A project contract with repeated `strict` keys can therefore
appear to require a gate while a later value disables it.

PromptAtlas chooses explicit rejection of duplicate decoded names and non-finite
numbers before validating fields. Decoder recursion failures become ordinary
input diagnostics; undecodable fenced examples remain opaque text. This removes
the reproduced ambiguous-policy and traceback cases without claiming a resource
sandbox or changing the interpreter's limits. The complete
[input contract](SCHEMAS.md#json-input-policy) records those boundaries.

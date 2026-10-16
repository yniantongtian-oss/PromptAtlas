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

# Performance evidence and limits

The benchmark uses original synthetic data and the standard library. It measures
public operations, validates their results after every sample, and writes Python,
platform, processor, version, individual samples, and medians into a JSON report.
Prompt construction for diff inputs is outside the timed region. Parse-and-lint
timings include both operations. Timing checks are not CI pass/fail gates.

```bash
python scripts/benchmark_workflows.py --sizes 2000 4000 10000 --repeat 3 --out test-results/performance.json
```

Workloads are unchanged repeated directives, repeated template directives with
duplicate/unresolved-variable findings, and 100 unrelated same-kind replacements.
Sizes include one role in the first two cases. Replacement candidates contain
different synthetic character runs with numeric suffixes, not natural-language
prompts. The runner checks exact diff group/count expectations and final finding
line numbers; it must not report success after silently changing output meaning.

## Observed comparison

On 2026-10-16, Windows/CPython 3.12.10 measurements compared commit `18ffaf8`
(0.3.1) with the 0.3.2 changes on the same machine. Three samples per workload were
used. Representative medians before/after were:

| Workload | Size | Before | After |
| --- | ---: | ---: | ---: |
| Unchanged repeated diff | 2,001 components | 0.295 s | 0.006 s |
| Unchanged repeated diff | 4,001 components | 1.175 s | 0.013 s |
| Unchanged repeated diff | 10,001 components | 7.268 s | 0.030 s |
| Parse and lint | 10,001 components | 0.275 s | 0.129 s |
| Unrelated replacements | 100 components per side | 0.270 s | 0.072 s |

These local observations describe the selected fixtures and environment. CPU
load, interpreter, input shape, and filesystem activity affect timings. They are
not a portable speed guarantee or evidence about model behavior.

A separate differential experiment used 1,000 generated plain-prose spec pairs
with seed `20261016`, covering repeated rules, mixed kinds, case, whitespace,
reordering, and candidate ties. All complete diff outputs matched 0.3.1. Code
literal normalization changes are intentional and have separate regressions.
This finite experiment supplements the regression suite; it is not a proof for
all possible inputs.

## Why the improvement is bounded

- Exact duplicate queues consume each target occurrence in constant time.
- Identical normalized component sequences return similarity 1 without calling
  the expensive ordered sequence matcher.
- Remaining candidates are grouped by kind and reuse target-side indexes.
- Similarity upper bounds reject impossible candidates before full matching.
- Source line starts are computed once and queried with binary search, including
  CR-only and CRLF inputs.

For changed inputs, ordered similarity retains `SequenceMatcher(autojunk=False)`
and can still take quadratic time. Many similar unmatched components can still
require quadratic candidate comparisons and candidate storage. No candidates are
silently truncated, and there is no hidden approximate mode. Use measured input
sizes and explicit prompt structure when reviewing unusually large documents.

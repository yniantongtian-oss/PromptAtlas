# Contributing to PromptAtlas

Thanks for your interest in making PromptAtlas better.

## What we accept

1. **Curated system prompts** — but **only** material that is:
   - published by the vendor itself (docs, blog posts, official repos), or
   - explicitly licensed for reuse, or
   - your own original prompts.
   We do **not** accept or redistribute leaked/proprietary prompts. PRs
   containing them will be closed.
2. **Component annotations** — improve the heuristic parser or hand-annotate
   components in `atlas/components.jsonl`.
3. **Eval packs** — scenario-specific promptfoo test packs (injection probes,
   format assertions, judge configs).
4. **Bug fixes and features** — parser accuracy, new CLI commands, exporters
   for other eval frameworks (DeepEval, Ragas).

## Data format

Each component is one JSON line in `atlas/components.jsonl`:

```json
{"id": "...", "kind": "guardrail|role|instruction|tool|output_rule|stop_condition|few_shot|context|other",
 "product": "...", "version": "...", "tags": ["..."], "content": "...",
 "confidence": 1.0, "source": "URL or provenance note"}
```

## Workflow

1. Fork, branch, keep PRs small and focused.
2. Run the tests: `python -m unittest discover tests -v`
3. Run the quickstart: `python examples/quickstart.py`
4. Describe what you added and its source/provenance in the PR.

## Code style

- Standard library first; new runtime dependencies require discussion.
- Type hints and docstrings for public functions.
- Deterministic behavior — no network calls in core modules.

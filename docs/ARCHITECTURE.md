# PromptAtlas Architecture

```
raw system prompt (.md)
        │
        ▼
  parse.py          heuristic, deterministic, stdlib-only
        │           → PromptSpec { role | instruction | tool | guardrail |
        ▼                     output_rule | stop_condition | few_shot | context }
  atlas.py          JSONL append-only store (atlas/components.jsonl)
        │
        ├── diff.py        component-level version diff (difflib)
        ├── generate.py    scenario → assembled draft prompt (template + retrieval)
        └── eval_export.py scenario → promptfoo YAML (injection probes + assertions)
```

## Design principles

1. **Deterministic core** — parsing and diffing never call a network or an LLM;
   results are reproducible and CI-friendly.
2. **Data over code** — value lives in the curated component store; the code is
   a thin, boring, reliable layer.
3. **Parasitic compatibility** — we export to promptfoo/DeepEval rather than
   competing with eval runners.
4. **Legally clean data** — only publicly published or explicitly licensed
   prompts are indexed; provenance is recorded per component.

## Extending

- New component kinds: extend `VALID_COMPONENT_KINDS` in `schema.py` and the
  classifier in `parse.py`.
- LLM-assisted parsing: implement `parse_prompt_with_llm()` that returns the
  same `PromptSpec` type; core stays dependency-free.
- New eval exporters: mirror `eval_export.py`, target DeepEval test files or
  Ragas datasets.

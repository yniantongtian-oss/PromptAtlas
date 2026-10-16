"""PromptAtlas quickstart.

Run:
    python examples/quickstart.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # allow running without installing

from promptatlas import (AtlasStore, diff_specs, export_eval_cases,
                         generate_prompt, parse_prompt)

# 1. Parse a raw system prompt into structured components.
raw = (ROOT / "atlas/versions/example-agent_v1.md").read_text(encoding="utf-8")
spec = parse_prompt(raw, product="example-agent", version="v1")
print("== parsed stats ==", spec.stats())

# 2. Diff two versions of the same prompt.
raw_v2 = (ROOT / "atlas/versions/example-agent_v2.md").read_text(encoding="utf-8")
spec_v2 = parse_prompt(raw_v2, product="example-agent", version="v2")
result = diff_specs(spec, spec_v2)
print("\n== diff ==", {k: len(v) if isinstance(v, list) else v
                        for k, v in result.items()})

# 3. Generate a first-draft system prompt for a new scenario.
store = AtlasStore(ROOT / "atlas/components.jsonl")
generated = generate_prompt("a customer support agent for an online store",
                            store=store)
print("\n== generated ==\n", generated)

# 4. Export a regression eval (promptfoo-compatible config).
yaml_text = export_eval_cases("customer support agent",
                              output_path=str(ROOT / "examples/promptfoo-eval.json"))
print("\n== eval exported ==", len(yaml_text), "chars")

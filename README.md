# PromptAtlas

**A structured, queryable atlas of AI system prompts — parse, diff, generate, and regression-test production system prompts.**

Curated prompt collections grew to 144k+ stars by satisfying one hunger: *how do the best AI products actually write their system prompts?* But they are static TXT dumps. PromptAtlas turns that demand into a toolchain: every prompt is decomposed into labeled components (role, tools, guardrails, stop conditions...), so you can **search patterns across products**, **diff versions to see what changed**, **generate a production-grade first draft for your own agent**, and **ship it with a regression eval from day one**.

## ✨ Features

- 🔍 **Structured parsing** — decompose any raw system prompt into typed components (role / instruction / tool / guardrail / output_rule / stop_condition / few_shot / context)
- 📊 **Version diffs** — component-level diff timeline between prompt versions: *"what did the vendor strengthen this release?"*
- 🛠️ **Scenario generator** — assemble a production-grade first-draft system prompt from battle-tested atlas patterns
- ✅ **Eval export** — one command emits a promptfoo-compatible regression eval (JSON/YAML) with prompt-injection probes
- 📦 **Zero lock-in** — MIT, pure-Python, JSONL data store, works offline

## 🚀 Quick start

```bash
pip install promptatlas
# or from source:
git clone https://github.com/<you>/PromptAtlas && cd PromptAtlas && pip install -e .

# 1. Parse a raw system prompt into components
promptatlas parse system-prompt.txt --product my-agent --version v1 --out spec.json

# 2. Diff two versions
promptatlas diff versions/v1.md versions/v2.md

# 3. Generate a first-draft system prompt for your scenario
promptatlas generate "a customer support agent for an online store"

# 4. Export a regression eval (promptfoo-compatible)
promptatlas eval "customer support agent" --out promptfoo-eval.json
npx promptfoo@latest eval -c promptfoo-eval.json

# 5. Search the atlas
promptatlas search --kind guardrail --tag coding-agent
```

## 📖 Example

```python
from promptatlas import parse_prompt, diff_specs, generate_prompt, AtlasStore

spec = parse_prompt(open("system-prompt.txt").read(), product="my-agent", version="v1")
print(spec.stats())
# {'role': 1, 'instruction': 3, 'guardrail': 4, 'output_rule': 2, 'stop_condition': 2}

store = AtlasStore()
print(generate_prompt("a coding agent that opens PRs", store=store))
```

## 🗺️ Roadmap

- [ ] Weekly automated "prompt change report" across tracked products (GitHub Action)
- [ ] Embedding-based semantic search over the atlas
- [ ] `promptatlas upgrade-check` — run your prompt against multiple model versions and flag degraded instructions
- [ ] Community submissions via PR (see CONTRIBUTING.md)
- [ ] Web UI for browsing the atlas

## 🤝 Contributing

Contributions are welcome — especially new **curated, publicly-sourced** system prompts and component annotations. Please read [CONTRIBUTING.md](CONTRIBUTING.md) first. Note: we only index prompts that are **publicly available or explicitly licensed for reuse**; we do not redistribute proprietary or leaked material.

## ⚖️ Disclaimer

PromptAtlas is a research and engineering tool for studying publicly available system prompt patterns. All bundled data is original illustrative content or properly attributed public material.

## 📄 License

[MIT](LICENSE)

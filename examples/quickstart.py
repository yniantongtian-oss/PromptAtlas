"""Run a complete offline workflow after installing PromptAtlas."""

import json
import tempfile
from pathlib import Path

from promptatlas import (
    AtlasStore,
    PromptSpec,
    diff_specs,
    export_eval_cases,
    generate_prompt,
    lint_prompt,
    parse_prompt,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    before_text = (ROOT / "atlas/versions/example-agent_v1.md").read_text(encoding="utf-8")
    after_text = (ROOT / "atlas/versions/example-agent_v2.md").read_text(encoding="utf-8")
    before = parse_prompt(before_text, product="example-agent", version="v1")
    after = parse_prompt(after_text, product="example-agent", version="v2")
    result = diff_specs(before, after)
    assert result["has_changes"]
    assert not lint_prompt(after_text)
    store = AtlasStore()
    with tempfile.TemporaryDirectory(prefix="promptatlas example ") as directory:
        root = Path(directory)
        before.save(root / "spec.json")
        assert PromptSpec.load(root / "spec.json").raw == before_text
        draft = generate_prompt("a customer support agent for an online store", store=store)
        config = json.loads(
            export_eval_cases(
                "customer support",
                root / "eval.json",
                system_prompt=after_text,
            )
        )
        print(
            json.dumps(
                {
                    "components": before.stats(),
                    "atlas_size": len(store),
                    "diff": {
                        "added": len(result["added"]),
                        "removed": len(result["removed"]),
                        "changed": len(result["changed"]),
                    },
                    "eval_cases_exported": len(config["tests"]),
                    "eval_executed": False,
                    "roundtrip_verified": True,
                },
                indent=2,
            )
        )
        print("\nEditable draft:\n" + draft)


if __name__ == "__main__":
    main()

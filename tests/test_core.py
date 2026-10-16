import unittest
from pathlib import Path

from promptatlas import (
    AtlasStore,
    Component,
    diff_specs,
    export_eval_cases,
    generate_prompt,
    parse_prompt,
)

ROOT = Path(__file__).resolve().parent.parent
V1 = ROOT / "atlas/versions/example-agent_v1.md"
V2 = ROOT / "atlas/versions/example-agent_v2.md"
ATLAS = ROOT / "promptatlas/data/components.jsonl"


class TestParse(unittest.TestCase):
    def test_parse_classifies_core_kinds(self):
        spec = parse_prompt(V1.read_text(encoding="utf-8"), product="example-agent", version="v1")
        kinds = {c.kind for c in spec.components}
        self.assertIn("role", kinds)
        self.assertIn("guardrail", kinds)
        self.assertIn("stop_condition", kinds)
        self.assertIn("output_rule", kinds)
        self.assertIn("instruction", kinds)
        self.assertTrue(spec.by_kind("role"))

    def test_component_validation(self):
        with self.assertRaises(ValueError):
            Component(kind="nonsense", content="x")


class TestDiff(unittest.TestCase):
    def test_diff_detects_addition(self):
        a = parse_prompt(V1.read_text(encoding="utf-8"), version="v1")
        b = parse_prompt(V2.read_text(encoding="utf-8"), version="v2")
        result = diff_specs(a, b)
        self.assertGreater(len(result["added"]), 0)
        added_text = " ".join(c.content for c in result["added"])
        self.assertIn("refund", added_text)
        self.assertGreaterEqual(result["similarity"], 0.5)


class TestAtlas(unittest.TestCase):
    def test_search_by_kind_and_tag(self):
        store = AtlasStore(ATLAS)
        guardrails = store.search(kind="guardrail")
        self.assertGreaterEqual(len(guardrails), 2)
        tagged = store.search(tags=["coding-agent"])
        self.assertTrue(all("coding-agent" in c.tags for c in tagged))


class TestGenerate(unittest.TestCase):
    def test_generate_contains_sections(self):
        store = AtlasStore(ATLAS)
        text = generate_prompt("a customer support agent", store=store)
        for section in ("# Role", "# Guardrails", "# Stop Conditions", "# Output Rules"):
            self.assertIn(section, text)


class TestEvalExport(unittest.TestCase):
    def test_export_valid_config(self):
        import json

        text = export_eval_cases("test scenario", output_path="")
        doc = json.loads(text)
        self.assertIn("tests", doc)
        self.assertGreaterEqual(len(doc["tests"]), 5)
        self.assertIn("assert", doc["tests"][0])


if __name__ == "__main__":
    unittest.main()

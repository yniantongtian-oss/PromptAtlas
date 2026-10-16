"""Scenario-based system prompt generation from atlas components."""

from __future__ import annotations

from .atlas import AtlasStore

TEMPLATE = """\
# Role
{role}

# Instructions
{instructions}

# Tools
{tools}

# Guardrails
{guardrails}

# Output Rules
{output_rules}

# Stop Conditions
{stop_conditions}
"""


def _bullet(items):
    lines = []
    for c in items:
        first = c.content.splitlines()[0].strip()
        rest = "\n".join(c.content.splitlines()[1:]).strip()
        entry = f"- {first}" + (f"\n  {rest}" if rest else "")
        lines.append(entry)
    return "\n".join(lines) if lines else "- (none)"


def generate_prompt(scenario: str, store: AtlasStore = None,
                    max_per_kind: int = 5) -> str:
    """Assemble a production-grade first-draft system prompt for `scenario`.

    Components are retrieved from the atlas by keyword overlap with the
    scenario text, ranked by tag relevance.
    """
    store = store or AtlasStore()
    GENERIC = {"agent", "assistant", "bot", "ai", "online", "the", "for",
               "and", "with", "that", "your"}
    keywords = {w.strip(".,;:()\"'").lower() for w in scenario.split()
                if len(w) > 2 and w.lower() not in GENERIC}

    def relevant(kind):
        cands = store.search(kind=kind)
        scored = []
        for c in cands:
            tag_hits = sum(1 for k in keywords if any(k in t.lower() for t in c.tags))
            text_hits = sum(1 for k in keywords if k in c.content.lower())
            score = 3 * tag_hits + text_hits
            if "universal" in (t.lower() for t in c.tags):
                score += 1  # universal components always apply
            scored.append((score, c))
        scored.sort(key=lambda x: -x[0])
        return [c for s, c in scored[:max_per_kind] if s > 0]

    role = f"You are {scenario.rstrip('.')}." if scenario else "You are a helpful assistant."
    return TEMPLATE.format(
        role=role,
        instructions=_bullet(relevant("instruction")),
        tools=_bullet(relevant("tool")),
        guardrails=_bullet(relevant("guardrail")),
        output_rules=_bullet(relevant("output_rule")),
        stop_conditions=_bullet(relevant("stop_condition")),
    )

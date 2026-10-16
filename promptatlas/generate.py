"""Scenario-based system prompt generation from atlas components."""

from __future__ import annotations

import re

from ._json import loads
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
        if c.kind == "tool":
            try:
                loads(c.content)
                language = "json"
            except ValueError:
                language = "text"
            marker = "`" * max(
                3, max((len(run) + 1 for run in re.findall(r"`+", c.content)), default=0)
            )
            lines.append(f"{marker}{language}\n{c.content}\n{marker}")
            continue
        first = c.content.splitlines()[0].strip()
        rest = "\n".join("  " + line for line in c.content.splitlines()[1:])
        entry = f"- {first}" + (f"\n{rest}" if rest else "")
        lines.append(entry)
    return "\n".join(lines) if lines else "- (none)"


def generate_prompt(scenario: str, store: AtlasStore | None = None, max_per_kind: int = 5) -> str:
    """Assemble an editable draft for `scenario`; review it before deployment.

    Components are retrieved from the atlas by keyword overlap with the
    scenario text, ranked by tag relevance.
    """
    if not isinstance(scenario, str) or not scenario.strip():
        raise ValueError("scenario must be a non-empty string")
    if type(max_per_kind) is not int or max_per_kind < 1:
        raise ValueError("max_per_kind must be a positive integer")
    store = AtlasStore() if store is None else store
    GENERIC = {
        "agent",
        "assistant",
        "bot",
        "ai",
        "online",
        "the",
        "for",
        "and",
        "with",
        "that",
        "your",
    }
    keywords = {
        w for w in re.findall(r"[a-z0-9]+", scenario.casefold()) if len(w) > 2 and w not in GENERIC
    }

    def relevant(kind):
        cands = store.search(kind=kind)
        scored = []
        for c in cands:
            tag_tokens = set(re.findall(r"[a-z0-9]+", " ".join(c.tags).casefold()))
            text_tokens = set(re.findall(r"[a-z0-9]+", c.content.casefold()))
            tag_hits = len(keywords & tag_tokens)
            text_hits = len(keywords & text_tokens)
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

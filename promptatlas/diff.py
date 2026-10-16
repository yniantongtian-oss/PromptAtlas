"""Case-sensitive component comparisons that preserve duplicate rules."""

from __future__ import annotations

from difflib import SequenceMatcher

from .schema import Component, PromptSpec


def _key(component: Component) -> tuple[str, str]:
    # Case is meaningful for identifiers. Whitespace-only edits are ignored.
    return component.kind, " ".join(component.content.split())


def diff_specs(spec_a: PromptSpec, spec_b: PromptSpec) -> dict:
    """Return disjoint added, removed, and changed groups.

    Exact matching consumes duplicate occurrences one at a time. Remaining
    same-kind pairs are matched greedily by descending lexical similarity
    (>= 0.6). Similarity measures ordered exact matches, not model behavior.
    Reordering is reported separately even when content is otherwise equal.
    """
    a, b = spec_a.components, spec_b.components
    a_keys, b_keys = [_key(item) for item in a], [_key(item) for item in b]
    available: dict[tuple[str, str], list[int]] = {}
    for j, key in enumerate(b_keys):
        available.setdefault(key, []).append(j)
    matched_a, matched_b = set(), set()
    exact_pairs = []
    for i, key in enumerate(a_keys):
        if available.get(key):
            j = available[key].pop(0)
            matched_a.add(i)
            matched_b.add(j)
            exact_pairs.append((i, j))
    candidates = []
    for i, old in enumerate(a):
        if i in matched_a:
            continue
        for j, new in enumerate(b):
            if j in matched_b or old.kind != new.kind:
                continue
            ratio = SequenceMatcher(None, a_keys[i][1], b_keys[j][1], autojunk=False).ratio()
            if ratio >= 0.6:
                candidates.append((-ratio, i, j))
    changed_pairs = []
    for _, i, j in sorted(candidates):
        if i not in matched_a and j not in matched_b:
            matched_a.add(i)
            matched_b.add(j)
            changed_pairs.append((i, j))
    ordered_targets = [j for _, j in exact_pairs]
    reordered = ordered_targets != sorted(ordered_targets)
    return {
        "added": [item for j, item in enumerate(b) if j not in matched_b],
        "removed": [item for i, item in enumerate(a) if i not in matched_a],
        "changed": [(a[i], b[j]) for i, j in sorted(changed_pairs)],
        "similarity": round(SequenceMatcher(None, a_keys, b_keys, autojunk=False).ratio(), 4),
        "reordered": reordered,
        "has_changes": a_keys != b_keys,
        "a_version": spec_a.version,
        "b_version": spec_b.version,
    }


def diff_to_dict(result: dict) -> dict:
    """Make a diff JSON serializable without losing component metadata."""
    return {
        **{
            key: value
            for key, value in result.items()
            if key not in {"added", "removed", "changed"}
        },
        "added": [item.to_dict() for item in result["added"]],
        "removed": [item.to_dict() for item in result["removed"]],
        "changed": [{"old": old.to_dict(), "new": new.to_dict()} for old, new in result["changed"]],
    }


def diff_summary(result: dict) -> str:
    lines = [
        f"# Prompt diff: {result['a_version'] or 'A'} -> {result['b_version'] or 'B'}",
        f"Ordered component similarity: {result['similarity']:.1%}",
        f"Reordered: {'yes' if result['reordered'] else 'no'}",
    ]
    for key, label in (("added", "Added"), ("removed", "Removed")):
        lines.extend(["", f"## {label} ({len(result[key])})"])
        lines.extend(
            f"- [{item.kind}] {' '.join(item.content.split())[:160]}" for item in result[key]
        )
    lines.extend(["", f"## Changed ({len(result['changed'])})"])
    for old, new in result["changed"]:
        lines.append(
            f"- [{old.kind}] {' '.join(old.content.split())[:120]} -> {' '.join(new.content.split())[:120]}"
        )
    return "\n".join(lines)

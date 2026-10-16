"""Component-level diff between two prompt versions."""

from __future__ import annotations

import difflib


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def diff_specs(spec_a, spec_b):
    """Compare two PromptSpecs at component level.

    Returns a dict:
      added      : components only in B
      removed    : components only in A
      changed    : list of (old, new) pairs with similarity in (0.3, 0.95)
      similarity : global content similarity 0..1
    """
    a_items = {_norm(c.content): c for c in spec_a.components}
    b_items = {_norm(c.content): c for c in spec_b.components}

    a_keys = list(a_items)
    b_keys = list(b_items)
    a_set, b_set = set(a_keys), set(b_keys)

    added = [b_items[k] for k in b_keys if k not in a_set]
    removed = [a_items[k] for k in a_keys if k not in b_set]

    matcher = difflib.SequenceMatcher(a=a_keys, b=b_keys, autojunk=False)
    similarity = matcher.ratio()

    changed = []
    unmatched_a = [k for k in a_keys if k not in b_set]
    unmatched_b = [k for k in b_keys if k not in a_set]
    used_b = set()
    for ka in unmatched_a:
        best, best_ratio = None, 0.0
        for kb in unmatched_b:
            if kb in used_b:
                continue
            r = difflib.SequenceMatcher(a=ka, b=kb).ratio()
            if r > best_ratio:
                best, best_ratio = kb, r
        if best and 0.3 < best_ratio < 0.95:
            changed.append((a_items[ka], b_items[best]))
            used_b.add(best)

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "similarity": round(similarity, 4),
        "a_version": spec_a.version,
        "b_version": spec_b.version,
    }


def diff_summary(result: dict) -> str:
    lines = [
        f"# Prompt diff: {result['a_version'] or 'A'} -> {result['b_version'] or 'B'}",
        f"Similarity: {result['similarity']:.1%}",
        "",
        f"## Added ({len(result['added'])})",
    ]
    for c in result["added"]:
        lines.append(f"- [{c.kind}] {c.content[:120]}")
    lines += [f"", f"## Removed ({len(result['removed'])})"]
    for c in result["removed"]:
        lines.append(f"- [{c.kind}] {c.content[:120]}")
    lines += [f"", f"## Changed ({len(result['changed'])})"]
    for old, new in result["changed"]:
        lines.append(f"- [{old.kind}] {old.content[:80]}  -->  {new.content[:80]}")
    return "\n".join(lines)

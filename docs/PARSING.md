# Parsing evidence and boundaries

PromptAtlas classifies English prompt structure with deterministic heuristics.
It preserves source text and never executes instructions found inside examples,
code, or tool definitions. Classification is an engineering aid for review.

## Supported literal boundaries

- Fenced blocks stay intact, including internal headings and blank lines.
- Fenced blocks inside dialogue/numbered examples remain part of the example.
- A closing fence uses the same character and at least the opening length.
- A backtick fence info string cannot contain another backtick.
- Equal-length inline backtick runs on one source line protect literal words and
  sentence punctuation. Unmatched or escaped opening delimiters remain prose.
- Component offsets continue to point into the original Unicode text, including
  CRLF; no Markdown rendering or whitespace rewriting occurs during parsing.

The scanner accepts indented fences for compatibility with earlier releases.
It does not implement full CommonMark list/blockquote containers, indented code
blocks, multiline inline code, or automatic paragraph reflow. Hard-wrapped prose
can still produce separate components. Headings and explicit sections are the
recommended way to make intended structure clear.

## Reproduce the structural corpus

The original MIT-licensed cases in `tests/fixtures/parser_cases.json` have manual
expected labels and exact component text. They cover literal boundaries, real
directives around code, examples, tool schemas, Unicode/CRLF, empty input, and an
explicit conflict. Expected labels are development fixtures, visible to the
implementation author. They are not an independent or held-out benchmark.

On 2026-10-16, the same 22 cases passed 13/22 against commit `d8c1935`
(0.3.0) and 22/22 after the 0.3.1 boundary fixes. This is a targeted regression
comparison; cases include issues discovered while examining that baseline.

```bash
python scripts/evaluate_parser.py --out test-results/parser-corpus.json
python scripts/evaluate_parser.py --cases /path/to/your-cases.json
```

The runner checks ordered kind/content pairs, ordered finding codes, source spans,
and serialization roundtrips. Reports contain case IDs, labels, and outcomes but
omit prompt content. Exit codes are `0` for all expected results, `1` for a
mismatch, and `2` for invalid input or output failures. Deliberately wrong labels
must fail; empty corpora and malformed labels are rejected. Output cannot
overwrite the input corpus.

Custom corpus format:

```json
{
  "schema_version": 1,
  "cases": [
    {
      "id": "an-original-label-example",
      "raw": "You are a release reviewer.",
      "components": [["role", "You are a release reviewer."]],
      "finding_codes": []
    }
  ]
}
```

A case passing means the current software agrees with its explicit expected
structure. It says nothing about model behavior, semantic correctness, injection
resistance, or performance on prompts outside the corpus. Future accuracy work
needs independent annotation, a fixed task definition, and an untouched test set.

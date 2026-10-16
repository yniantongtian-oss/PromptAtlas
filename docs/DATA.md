# Data and provenance

The canonical atlas is `promptatlas/data/components.jsonl`. Every bundled record
is an original illustrative example released under this repository's MIT license.
The `example` product label identifies a fixture, not a real vendor or deployment.
The two prompts under `atlas/versions/` are original version-comparison fixtures.

## Record fields

Required fields are `kind` and non-empty `content`. `id` must be unique in a store;
`tags` is a list of non-empty strings; `confidence` is finite and between 0 and 1.
`product`, `version`, and `source` are strings. Parser-created records additionally
include paired character offsets `start` and `end`. Unknown fields are rejected.

For contributed records, supply a stable ID, descriptive tags, an exact source,
and the license or authorization that permits redistribution. A URL alone is not
sufficient evidence of reuse permission. Original material should identify itself
as such. Do not submit credentials, customer data, or material extracted without
the rights holder's authorization.

```json
{"id":"team-review-001","kind":"instruction","content":"Verify claims against the supplied evidence.","product":"team-review","version":"1","tags":["review"],"source":"Original example by the project team; MIT","confidence":1.0}
```

```bash
promptatlas validate --require-source
promptatlas validate --atlas my-atlas.jsonl --require-source --json
```

The validator checks syntax and attribution presence; it cannot adjudicate rights
or verify a source's accuracy. Review contributions before merging them.

## Storage contract

The packaged atlas is read-only. A writable custom store must be selected
explicitly. Reads fail on malformed rows with a file and line number; duplicate
IDs are rejected. A write validates the current file and replaces it atomically
only after the complete new file is ready. The in-memory view changes afterward.
Custom stores assume a single writer; use Git or external coordination for teams.

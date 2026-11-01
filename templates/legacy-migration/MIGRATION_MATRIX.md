# Legacy Migration Matrix (copy per product)

| Version ID | SHA-256 / source | Platform | Unique selector/extraction/packaging | Shared duplication | Existing features | Known gaps | Reproduction evidence |
|---|---|---|---|---|---|---|---|
| example-only | replace | example | replace | replace | replace | replace | replace |

## Behavior inventory

| Scenario ID | Platform | Legacy expected output / hash | New output / hash | Match? | Evidence link | Owner |
|---|---|---|---|---|---|---|
| sample-only | replace | replace | replace | pending | replace | replace |

## PR cut plan

| PR | Single purpose | Allowed paths | Forbidden paths | All-platform regression | Release blocker |
|---|---|---|---|---|---|
| #1 | core extraction with parity | scoped core + tests | unrelated refactors | all existing baseline | changed output |
| #N | one new adapter | scoped adapter, fixtures, registration, tests | opportunistic core edits | all registered adapters | any regression |

Unknown / not captured is **not** a pass. Never treat this template as evidence of actual migration.

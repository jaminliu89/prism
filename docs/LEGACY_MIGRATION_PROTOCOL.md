# Legacy Migration Protocol v1.0

A governance playbook for consolidating multiple working implementations into a common core with platform adapters. This protocol is **not** a claim that any named product has been migrated.

## Preconditions

Inventory real sources and licenses, permissions, dependencies, secrets, sample inputs and outputs. Treat archives and snapshots as untrusted input. Do not commit credentials, private chats, proprietary material without authorization, or downloaded dependencies to a public repository.

## Stage 0 — Immutable reference vault

Preserve each source version byte-for-byte, record SHA-256, provenance, timestamp, entrypoint, dependency lock, supported platforms and reproducibility notes. Prefer immutable Git tags or read-only restricted artifact storage; `legacy/` is only a convention and by itself is **not** immutable. Do not modify archived originals. If an artifact contains sensitive material, keep the archive outside public Git and record a sanitized manifest.

## Stage 1 — Investigation, no implementation

Read versions in disposable local clones with shared remote push disabled. Build a comparison matrix:
- platform-specific DOM selectors, extraction, navigation, packaging, CSP/permissions
- shared message shape, serialization, export formats, filenames, downloads, UI
- working capabilities, unsupported edge cases, regressions, accessibility
- captured legacy outputs, normalized synthetic fixtures and expected results
Record evidence and unknowns; choose baseline by **behavior completeness and maintainability**, not code neatness alone.

## Stage 2 — Contract before refactor

Declare adapter interface and canonical message representation. Suggested boundaries:
`adapters/` (detect/extract/map), `core/` (normalize/serialize/download), `ui/` (interaction), `fixtures/` (sanitized page snapshots), `tests/` (golden and integration).
Specify errors, optional fields, ordering, streaming states, rich content, attachment handling, and compatibility policy. DOM selectors remain in adapters.

## Stage 3 — Core-extraction PR (zero product features)

Extract one complete behavior baseline; freeze golden expected outputs first; do not rewrite business semantics. Run relevant legacy-vs-new output parity tests. Any deliberate behavior change belongs in a separate change proposal.

## Stage 4 — One platform per PR

One delivery PR / agent / isolated working tree. Add one adapter and fixture set, register it, and run **all** previously supported adapters' regression suites. Do not opportunistically refactor core. If model cannot express a platform capability, propose a **separate core-schema PR** with compatibility tests, merge that first, then proceed with adapter PR.

## Stage 5 — Acceptance and deployment

Required: fixture extraction golden tests, canonical serialization tests, browser integration for injection/download/navigation as applicable, platform-specific real-site smoke checks when authorized (and before release), privacy/security review, packaging, rollback plan. Static fixtures cannot prove live DOM compatibility. Track CI and manual evidence independently.

## Collaboration and Git boundary

Temporary test-only experiments: disposable local clone, never push any test commit to a shared remote or open PR for sandbox experiments. Actual changes: delivery branch → PR → required CI → required review → protected main. A developer's delivery clone is not the temporary test sandbox. Shared published commits are reverted, never rewritten. Follow [Git Safety & Delivery Contract](GIT_SAFETY_DELIVERY_CONTRACT.md) once available in main.

## Deliverables and release gates

Copy [migration matrix template](../templates/legacy-migration/MIGRATION_MATRIX.md) and [fixture manifest template](../templates/legacy-migration/FIXTURE_MANIFEST.md).
Every PR identifies source snapshot ID, exact scope, goldens added, all-platform regression status, deliberate incompatibilities, security implications and rollback strategy.
Stop release for missing known-platform regression, unexplained output difference, exposed secrets, unverified external behavior, or missing protected-branch gate.

## Ownership

Prism routes and checks stage evidence; engineering architecture owns model/adapter contract; QA owns fixture fidelity/regression suite; GitHub rulesets enforce shared-code entry. Production owners authorize live-site testing and release.

# Prism BLOCKED_HANDOFF recovery adapter — design contract v0.1

Status: DESIGN ONLY. No runtime handler, queue, credentials or workflow is implemented by this document.

Prism coordinates execution; it does not own independent products or weaken their acceptance policies.

## Inputs
incident_id, repo, branch, intended_result, blocked_action, error_class, evidence, candidate_executors, least_privilege_policy, max_attempts, rollback_ref, required_checks, required_reviews.

## Deterministic orchestration
1. Detect blocked execution and persist immutable evidence.
2. Classify the error and select a distinct executor capability (GitHub Actions, CLI, connected GitHub API, human handoff).
3. Confirm permission boundary and idempotency key `incident_id + operation + branch`.
4. Execute with bounded retries and capture resulting SHA/artifact URL.
5. Verify expected artifact and product-owned checks; reject missing evidence.
6. Request independent review; do not self-approve or bypass branch rules.
7. Publish one of MERGED, BLOCKED_WITH_OWNER, REJECTED_WITH_EVIDENCE.

## Explicit non-goals
No implicit admin escalation; no unattended production secret disclosure; no auto-merge; no claiming green CI without run evidence; no modification of VibeGuard ownership.

## First implementation candidate
GitHub Actions artifact-to-branch adapter, limited to a dedicated recovery branch. Requires security review before enabling automatic repository writes.

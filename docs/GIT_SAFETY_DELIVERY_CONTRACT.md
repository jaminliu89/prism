# Git Safety & Delivery Contract v1.0

Scope: all Prism contributors, Agents, Skills and automation. This is a repository policy, **not** evidence that GitHub branch protection is enabled.

## Independent tracks

**A — disposable local sandbox:** whitelist validation, Skill verification, rule probes, destructive experiments and temporary test commits run exclusively in a disposable LOCAL clone. Test commits MUST NOT be pushed to **any** shared remote branch, nor made into PRs. Before writing tests, remove/disable push access to remotes (e.g. `git remote set-url --push origin DISABLED`) and use a credential-isolated environment if possible. Destroy clone after collecting sanitized observations. To promote an actual fix, reproduce it as a clean change on Track B. A local clone is not, by itself, a security sandbox: enforce appropriate process/filesystem/network isolation for untrusted code.

**B — production changes:** branch from the current main; commit verified real changes; push only a delivery branch; open PR; require minimal applicable CI and required review; merge only after all gates pass. Never push directly to main. Never bypass branch protections.

## Shared history

- Before push: reset/discard local work only after inspecting the working tree; `git reset --hard` can irreversibly destroy local edits.
- After *any* push to a shared remote: use new revert commits, never reset/force-push the shared ref.
- Reverting changes already merged to main also requires a PR and CI.
- Never claim rulesets, CI passes, review or merge completed without verifying their actual GitHub state.

## GitHub required administrative configuration

Apply a GitHub Ruleset / branch protection targeting `main`, with **no bypass actors** (including administrators and automation), requiring PR before merge, required status check `policy-check` (after first successful run), and reviews as appropriate. Prohibit force pushes and deletion; verify enforcement by inspecting the actual ruleset. This file and workflow cannot enforce branch protection on their own.

## Responsibilities

Prism routes; engineering quality validates CI; GitHub rulesets enforce; a human or authorized reviewer approves. Report branch, PR link, checks and protection status separately.

## Acceptance checks

1. A disposable local test clone cannot push test commits to any shared remote.
2. A real change creates a delivery PR and its minimal CI passes.
3. Direct main push and bypass are refused by actual repository protection.
4. Shared-history recovery is performed by revert through a protected PR.

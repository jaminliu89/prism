#!/usr/bin/env python3
"""Prism cross-repo task triage (read-only). GitHub issues own state; this never approves releases.

This is an index/next-action adapter for Prism Mission, not another board,
an identity verifier, a GitHub client, or an Agent scheduler.
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "docs/delivery/mission-index.json"
TASK_ID = re.compile(r"WP-[0-9]{2}\Z")
ISSUE_URL = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)\Z")
ACCEPTANCE_ID = re.compile(r"G[0-5]\Z")


def reject(message):
    raise ValueError(message)


def issue_repo(url):
    if not isinstance(url, str):
        reject("ISSUE_URL_INVALID")
    match = ISSUE_URL.fullmatch(url)
    if not match:
        reject("ISSUE_URL_INVALID")
    return match.group(1)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != {
        "schema_version", "mission_id", "mission_issue", "work_packages"
    }:
        reject("MISSION_SCHEMA_INVALID")
    if plan["schema_version"] != 1 or not isinstance(plan["mission_id"], str) or not plan["mission_id"].strip():
        reject("MISSION_ID_INVALID")
    issue_repo(plan["mission_issue"])
    tasks = plan["work_packages"]
    if not isinstance(tasks, list) or not tasks:
        reject("WORK_PACKAGES_EMPTY")
    by_id = {}
    urls = {plan["mission_issue"]}
    for task in tasks:
        if not isinstance(task, dict) or not {"id","repo","issue","depends_on","acceptance_ids"} <= set(task) or (
            set(task) - {"id","repo","issue","depends_on","acceptance_ids","external_blockers"}
        ):
            reject("WORK_PACKAGE_SCHEMA_INVALID")
        task_id = task["id"]
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id) or task_id in by_id:
            reject("WORK_PACKAGE_ID_INVALID_OR_DUPLICATE")
        if not isinstance(task["repo"], str) or issue_repo(task["issue"]) != task["repo"]:
            reject("WORK_PACKAGE_REPO_MISMATCH")
        if task["issue"] in urls:
            reject("DUPLICATE_ISSUE")
        urls.add(task["issue"])
        deps = task["depends_on"]
        if not isinstance(deps, list) or len(deps) != len(set(map(str, deps))) or any(
            not isinstance(d, str) or not TASK_ID.fullmatch(d) for d in deps
        ):
            reject("DEPENDENCIES_INVALID")
        accept = task["acceptance_ids"]
        if not isinstance(accept, list) or not accept or any(
            not isinstance(a, str) or not ACCEPTANCE_ID.fullmatch(a) for a in accept
        ) or len(set(accept)) != len(accept):
            reject("ACCEPTANCE_UNMAPPED")
        external = task.get("external_blockers", [])
        if not isinstance(external, list) or len(external) != len(set(map(str, external))):
            reject("EXTERNAL_BLOCKERS_INVALID")
        for link in external:
            issue_repo(link)
        if task["issue"] in external:
            reject("SELF_BLOCKED_ISSUE")
        by_id[task_id] = task

    visiting, visited = set(), set()
    def walk(task_id):
        if task_id in visiting:
            reject("DEPENDENCY_CYCLE")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dep in by_id[task_id]["depends_on"]:
            if dep not in by_id:
                reject("DEPENDENCY_UNKNOWN")
            if dep == task_id:
                reject("SELF_DEPENDENCY")
            walk(dep)
        visiting.remove(task_id)
        visited.add(task_id)
    for task_id in by_id:
        walk(task_id)
    return by_id


def validate_observations(plan, raw):
    """User-supplied snapshots are never authentication or review proof."""
    if raw is None:
        return {}
    if not isinstance(raw, dict) or set(raw) != {"issues"} or not isinstance(raw["issues"], dict):
        reject("OBSERVATIONS_SCHEMA_INVALID")
    registered = {t["issue"] for t in plan["work_packages"]}
    registered.update(link for t in plan["work_packages"] for link in t.get("external_blockers", []))
    if not set(raw["issues"]) <= registered:
        reject("OBSERVATION_UNKNOWN_ISSUE")
    for url, state in raw["issues"].items():
        issue_repo(url)
        if state not in ("open", "closed", "unknown"):
            reject("OBSERVATION_NOT_ISSUE_STATE")
    return raw["issues"]


def triage(plan, observations=None):
    """Returns advisory candidates only; never accepts local PASS/approval claims."""
    tasks = validate(plan)
    states = validate_observations(plan, observations)
    candidates, blocked, claimed_closed = [], [], []
    for task in plan["work_packages"]:
        current = states.get(task["issue"], "unknown")
        if current == "closed":
            claimed_closed.append({"id": task["id"], "issue": task["issue"],
                "reason": "ISSUE_CLOSED_NOT_CI_REVIEW_VERIFIED"})
            continue
        dependencies = [(dep, states.get(tasks[dep]["issue"], "unknown"))
                        for dep in task["depends_on"]]
        external = [(url, states.get(url, "unknown"))
                    for url in task.get("external_blockers", [])]
        waiting = [{"dependency": dep, "state": state} for dep, state in dependencies if state != "closed"]
        waiting += [{"external_issue": url, "state": state} for url, state in external if state != "closed"]
        if waiting:
            blocked.append({"id": task["id"], "issue": task["issue"], "waiting_for": waiting})
        else:
            candidates.append({"id": task["id"], "issue": task["issue"], "repo": task["repo"],
                "next_action": "INSPECT_REAL_ISSUE_PR_AND_EVIDENCE_THEN_EXECUTE_AUTHORIZED_SLICE",
                "dependencies": [{"id": dep, "claimed_state": state} for dep,state in dependencies]})
    return {
        "schema_version": 1, "mission_id": plan["mission_id"], "status": "TRIAGE_ONLY",
        "source": "USER_SUPPLIED_ISSUE_OBSERVATIONS_UNAUTHENTICATED",
        "release_authorized": False, "independent_review_authenticated": False,
        "next": candidates[0] if candidates else None,
        "parallel_candidates": candidates, "blocked": blocked,
        "claimed_closed_requires_verification": claimed_closed,
        "warning": "Issue closed or user-supplied JSON cannot prove check-runs, review identity, branch protection, product acceptance or permission to merge."
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--observations", type=Path, help="Untrusted snapshots of actual issue states; never release evidence")
    parser.add_argument("action", choices=["validate", "next"])
    args = parser.parse_args(argv)
    try:
        plan = load_json(args.manifest)
        index = validate(plan)
        if args.action == "validate":
            result = {"status": "PLAN_VALID_ONLY", "work_package_count": len(index),
                      "mission_id": plan["mission_id"], "release_authorized": False}
        else:
            result = triage(plan, load_json(args.observations) if args.observations else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "NOT_READY", "reason": str(exc), "release_authorized": False},
                         ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only collaboration projection for existing Prism Foundry tasks.

Ideas: MetaGPT's SOP-based role handoff and ChatDev's dependency-aware agent
scheduling. This is an independently written, standard-library-only adapter.
It never invokes agents, runs code, writes to the project, or grants approval.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

ROLES = frozenset({"pm", "research", "ux", "architect", "security", "qa"})
STATUSES = frozenset({"ready", "claimed", "delivered", "cancelled"})
HASH = re.compile(r"^[0-9a-f]{64}$")
MAX_JSON_BYTES = 2_000_000
MAX_ARTIFACT_BYTES = 16_000_000


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def safe_path(path):
    require(isinstance(path, str) and path.startswith("docs/") and "\\" not in path,
            "artifact must be a project-relative docs/ path")
    require(not any(ord(c) < 32 for c in path) and ":" not in path,
            "unsafe artifact characters")
    parts = path.split("/")
    require(all(x not in ("", ".", "..") for x in parts), "artifact traversal or empty path")
    require(not PurePosixPath(path).is_absolute(), "absolute artifact path")
    return path


def project_file(project, relative):
    root = Path(project).expanduser().resolve(strict=True)
    # Verify each path component before resolving it, not just the result.
    parts = relative.split("/")
    target = root
    for part in parts:
        target = target / part
        require(not target.is_symlink(), "symlink in project artifact path")
    require(target.resolve(strict=False).is_relative_to(root), "artifact escapes project")
    return target


def load(project):
    state_file = project_file(project, ".foundry/project.json")
    require(state_file.is_file(), "Foundry state missing")
    require(state_file.stat().st_size <= MAX_JSON_BYTES, "Foundry state too large")
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ContractError("invalid Foundry state JSON") from exc
    require(isinstance(state, dict) and type(state.get("schema_version")) is int
            and state["schema_version"] == 1, "unsupported Foundry schema")
    require(type(state.get("revision")) is int and state["revision"] > 0,
            "invalid Foundry revision")
    stages = state.get("stages")
    require(isinstance(stages, list) and len(stages) == 7 and
            all(isinstance(s, dict) and type(s.get("confirmed")) is bool for s in stages),
            "invalid Foundry stages")
    require(not any(stages[i]["confirmed"] and not stages[i - 1]["confirmed"]
                    for i in range(1, 7)), "Foundry stage confirmations are out of order")
    tasks = state.get("tasks", [])
    require(isinstance(tasks, list), "invalid Foundry tasks")
    return state


def current_stage(state):
    return next((i for i, s in enumerate(state["stages"]) if not s["confirmed"]), 7)


def validate(state):
    tasks = state.get("tasks", [])
    require(len(tasks) <= 500, "too many Foundry tasks for bounded dependency validation")
    by_id = {}
    active_paths = set()
    for task in tasks:
        require(isinstance(task, dict), "task must be an object")
        tid = task.get("id")
        require(isinstance(tid, str) and re.fullmatch(r"AGT-[0-9]{4,}", tid),
                "invalid task ID")
        require(tid not in by_id, "duplicate task ID")
        require(isinstance(task.get("role"), str) and task["role"] in ROLES, "unknown task role")
        require(type(task.get("stage")) is int and 0 <= task["stage"] <= 6,
                "invalid task stage")
        require(isinstance(task.get("status"), str) and task["status"] in STATUSES, "unknown task status")
        artifact = safe_path(task.get("artifact"))
        require(task.get("authorization") == "PLANNING_DOCUMENT_ONLY" and
                task.get("identity_verified") is False,
                "task attempts to enlarge authorization or certify identity")
        require(task.get("allowed_write_paths") == [artifact],
                "task write permissions do not match artifact")
        allowed = task.get("allowed_actions")
        require(isinstance(allowed, list) and all(isinstance(x, str) for x in allowed)
                and set(allowed) ==
                {"read approved project docs", "submit planning document"},
                "task allowed actions exceed original Foundry scope")
        denied = task.get("denied_actions")
        required_denials = {"approve own work", "run target code", "exfiltrate data",
                            "production access", "paid tools", "deploy", "modify approved goals"}
        require(isinstance(denied, list) and all(isinstance(x, str) for x in denied)
                and required_denials.issubset(denied),
                "task is missing mandatory Foundry denied actions")
        require(isinstance(task.get("objective"), str) and task["objective"].strip(),
                "missing task objective")
        if task["status"] in ("ready", "claimed"):
            key = (task["stage"], artifact)
            require(key not in active_paths, "duplicate active artifact writer")
            active_paths.add(key)
        if task["status"] == "claimed":
            require(isinstance(task.get("assigned_to_claim"), str) and
                    task["assigned_to_claim"].strip(), "claimed task missing actor")
        if task["status"] == "delivered":
            delivery = task.get("delivery")
            require(isinstance(delivery, dict) and
                    delivery.get("artifact") == artifact and
                    isinstance(delivery.get("sha256"), str) and
                    HASH.fullmatch(delivery["sha256"]), "invalid task delivery receipt")
        deps = task.get("depends_on", [])
        require(isinstance(deps, list) and all(isinstance(x, str) for x in deps) and
                len(set(deps)) == len(deps), "invalid dependencies")
        by_id[tid] = task
    for tid, task in by_id.items():
        for dep in task.get("depends_on", []):
            require(dep in by_id, "unknown dependency")
            require(by_id[dep]["stage"] <= task["stage"],
                    "dependency cannot point to a later stage")
            require(dep != tid, "self dependency")
    visited = set()
    visiting = set()

    def walk(tid):
        require(tid not in visiting, "dependency cycle")
        if tid in visited:
            return
        visiting.add(tid)
        for dep in by_id[tid].get("depends_on", []):
            walk(dep)
        visiting.remove(tid)
        visited.add(tid)

    for tid in by_id:
        walk(tid)
    return by_id


def inspect_artifact(project, state, task):
    require(task["status"] == "delivered", "task has not delivered")
    artifact = safe_path(task["artifact"])
    target = project_file(project, artifact)
    require(target.is_file(), "delivered artifact missing")
    require(target.stat().st_size <= MAX_ARTIFACT_BYTES, "artifact too large to verify")
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    expected = task["delivery"]["sha256"]
    require(actual == expected, "delivered artifact hash mismatch")
    recorded = state["stages"][task["stage"]].get("artifacts", {}).get(artifact)
    require(isinstance(recorded, dict) and recorded.get("sha256") == actual,
            "stage artifact hash mismatch")
    return {"id": task["id"], "artifact": artifact, "sha256": actual,
            "status": "ARTIFACT_HASH_MATCH", "quality_assurance": "NOT_VERIFIED",
            "reviewer_identity": "NOT_VERIFIED", "release_authorized": False}


def plan(state, project):
    by_id = validate(state)
    stage = current_stage(state)
    ready = []
    blocked = []
    claimed = []
    for tid, task in sorted(by_id.items()):
        if task["stage"] != stage or task["status"] in ("delivered", "cancelled"):
            continue
        if task["status"] == "claimed":
            claimed.append(tid)
            continue
        missing = [dep for dep in task.get("depends_on", [])
                   if by_id[dep]["status"] != "delivered"]
        if missing:
            blocked.append({"id": tid, "reason": "DEPENDENCY_NOT_DELIVERED",
                            "depends_on": missing})
        else:
            for dep in task.get("depends_on", []):
                inspect_artifact(project, state, by_id[dep])
            ready.append(tid)
    return {"schema_version": 1, "source": ".foundry/project.json",
            "revision": state["revision"], "stage": stage,
            "parallel_ready": ready, "already_claimed": claimed, "blocked": blocked,
            "execution_authorized": False, "release_authorized": False,
            "note": "Read-only schedule; call existing foundry task-claim and task-deliver for mutations."}


def packet(state, task_id, project):
    by_id = validate(state)
    require(task_id in by_id, "unknown task")
    task = by_id[task_id]
    require(task["status"] == "ready" and task["stage"] == current_stage(state),
            "task not ready in current stage")
    for dep in task.get("depends_on", []):
        require(by_id[dep]["status"] == "delivered", "dependency not delivered")
        inspect_artifact(project, state, by_id[dep])
    return {"schema_version": 1, "task_id": task_id, "foundry_revision": state["revision"],
            "role": task["role"], "objective": task["objective"],
            "input_documents": task.get("source_docs", []),
            "output_document": task["artifact"], "allowed_actions": task.get("allowed_actions", []),
            "denied_actions": task["denied_actions"],
            "authorization": "PLANNING_DOCUMENT_ONLY", "identity_verified": False,
            "execution_authorized": False, "release_authorized": False,
            "next": "Claim with existing foundry.py task-claim before writing; deliver with task-deliver."}


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only MetaGPT/ChatDev-inspired Foundry team adapter")
    p.add_argument("--project", required=True)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    for cmd in ("packet", "verify-artifact"):
        sub.add_parser(cmd).add_argument("--id", required=True)
    a = p.parse_args(argv)
    try:
        state = load(a.project)
        if a.command == "plan":
            output = plan(state, a.project)
        elif a.command == "packet":
            output = packet(state, a.id, a.project)
        else:
            by_id = validate(state)
            require(a.id in by_id, "unknown task")
            output = inspect_artifact(a.project, state, by_id[a.id])
    except (ContractError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

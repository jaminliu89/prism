#!/usr/bin/env python3
"""Product Foundry V0.1: file-backed planning gates, change control and agent handoff.

No model calls, target execution, network, auto-approval, or release permissions.
Uses Prism's pinned idea-to-blueprint documents as the planning authority.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
DOCS = {
    0: ("docs/00-idea-brief.md", "docs/00-asset-recall.md"),
    1: ("docs/01-product-research.md",),
    2: ("docs/02-stories-and-journeys.md", "docs/02-state-machines.md"),
    3: ("docs/03-prd.md", "docs/03-design-system.md"),
    4: ("docs/04-architecture.md", "docs/04-technology-decisions.md"),
    5: ("docs/05-roadmap.md", "docs/06-task-board.md", "docs/05-definition-of-done.md"),
    6: ("docs/07-consistency-audit.md", "docs/08-engineering-handoff.md"),
}
QUESTIONS = {
    "audience": "Who is the target user and in which concrete situation?",
    "problem": "Which actual problem or unmet need will this solve?",
    "success": "What observable outcome would make the first version useful?",
}
IMPACT = {
    "intent": 0, "audience": 0, "problem": 0,
    "research": 1, "journey": 2, "state": 2,
    "feature": 3, "ux": 3, "architecture": 4,
    "roadmap": 5, "audit": 6,
}
STAGE_NAMES = (
    "Idea clarification and asset recall", "Positioning and research",
    "Stories, journeys and states", "PRD and UX",
    "Architecture and technology", "Roadmap and task contracts",
    "Consistency audit and engineering handoff",
)


def fail(msg):
    raise ValueError(msg)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_under(root, relative):
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        fail("artifact path must be project-relative")
    full = (root / p).resolve()
    if not full.is_relative_to(root.resolve()):
        fail("path escapes project root")
    return full


def write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".foundry-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save(root, data):
    write_atomic(root / ".foundry" / "project.json",
                 (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())


def load(root):
    path = root / ".foundry" / "project.json"
    if not path.is_file():
        fail("not a Foundry project (run init first)")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA:
        fail("unsupported Foundry state schema")
    return data


def log(root, action, actor, revision, details=None):
    path = root / ".foundry" / "events.jsonl"
    event = {"at": now(), "action": action, "actor": actor, "revision": revision,
             "details": details or {}}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def check_rev(data, expected):
    if expected is not None and expected != data["revision"]:
        fail("stale project revision: expected %d, actual %d" %
             (expected, data["revision"]))


def touch(root, data, action, actor, details=None):
    data["revision"] += 1
    data["updated_at"] = now()
    save(root, data)
    log(root, action, actor, data["revision"], details)


def init(root, idea, actor):
    if not idea.strip() or not actor.strip():
        fail("idea and actor are required")
    if (root / ".foundry").exists():
        fail("project already exists: refusing overwrite")
    root.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": SCHEMA, "revision": 1, "idea_original": idea.strip(),
        "created_at": now(), "updated_at": now(), "owner_claim": actor,
        "answers": {}, "accepted_changes": [],
        "stages": [{"confirmed": False, "artifacts": {}, "reviews": [],
                    "confirmation": None} for _ in range(7)],
        "changes": [],
    }
    (root / ".foundry").mkdir(exist_ok=False)
    brief = "# Original product idea\n\n" + idea.strip() + (
        "\n\n## Unresolved assumptions\n\n"
        "User, problem, outcome and constraints must be clarified before approval.\n")
    p = file_under(root, DOCS[0][0])
    write_atomic(p, brief.encode())
    data["stages"][0]["artifacts"][DOCS[0][0]] = {
        "sha256": digest(brief.encode()), "actor": actor, "at": now(),
        "revision": 1,
    }
    save(root, data)
    log(root, "init", actor, 1, {"idea": idea.strip()})
    return status(root, data)


def current(data):
    for i, stage in enumerate(data["stages"]):
        if not stage["confirmed"]:
            return i
    return 7


def verified_artifact(root, stage, path):
    info = stage["artifacts"].get(path)
    if not info or path in stage.get("stale_artifacts", []):
        return False
    file = file_under(root, path)
    return file.is_file() and digest(file.read_bytes()) == info["sha256"]


def pending(root, data, index):
    s = data["stages"][index]
    missing = [p for p in DOCS[index] if not verified_artifact(root, s, p)]
    unanswered = ([q for q in QUESTIONS if not data["answers"].get(q)]
                  if index == 0 else [])
    review = any(r["verdict"] == "pass" and
                 r["revision"] >= max((v["revision"]
                                       for v in s["artifacts"].values()), default=0)
                 for r in s["reviews"])
    changes = any(r["verdict"] in ("changes", "blocked") and
                  r["revision"] >= max((v["revision"]
                                       for v in s["artifacts"].values()), default=0)
                  for r in s["reviews"])
    return {"missing_artifacts": missing, "unanswered": unanswered,
            "passing_review": review, "blocking_review": changes}


def status(root, data=None):
    data = data or load(root)
    active = current(data)
    stages = []
    for i, s in enumerate(data["stages"]):
        p = pending(root, data, i)
        stages.append({"stage": i, "name": STAGE_NAMES[i],
                       "confirmed": s["confirmed"],
                       "artifacts": list(s["artifacts"]),
                       "missing": p["missing_artifacts"],
                       "reviews": len(s["reviews"])})
    return {
        "status": "BLUEPRINT_READY" if active == 7 else "PLANNING",
        "revision": data["revision"], "original_intent": data["idea_original"],
        "current_stage": active if active < 7 else None,
        "stage_gate": pending(root, data, active) if active < 7 else None,
        "stages": stages,
        "open_changes": [c["id"] for c in data["changes"]
                         if c["status"] == "proposed"],
        "agent_execution": "NOT_STARTED",
        "release_authorized": False,
    }


def next_step(root, data=None):
    data = data or load(root)
    s = status(root, data)
    i = s["current_stage"]
    if i is None:
        return {"status": "BLUEPRINT_READY", "next": "export handoff; engineering needs separate approval"}
    gate = s["stage_gate"]
    return {
        "stage": i, "name": STAGE_NAMES[i], "expected_documents": list(DOCS[i]),
        "missing_documents": gate["missing_artifacts"],
        "questions": {q: QUESTIONS[q] for q in gate["unanswered"]},
        "review_required": not gate["passing_review"],
        "review_blocked": gate["blocking_review"],
        "owner_confirmation_required": True,
        "instructions_source": "sources/skillhub/blueprint/MASTER_PROMPT.md",
        "document_contract": "sources/skillhub/blueprint/DOCUMENT_CONTRACT.md",
        "rule": "Draft, review and explicitly confirm this stage before advancing; no product code.",
    }


def answer(root, key, value, actor, expected=None):
    data = load(root)
    check_rev(data, expected)
    if current(data) != 0 or key not in QUESTIONS or not value.strip():
        fail("answer requires an open stage 0 and a nonempty recognized answer")
    data["answers"][key] = {"value": value.strip(), "at": now(),
                            "actor": actor, "revision": data["revision"] + 1}
    data["stages"][0]["reviews"] = []
    touch(root, data, "answer", actor, {"key": key})
    return next_step(root, data)


def submit(root, artifact, source, actor, expected=None):
    data = load(root)
    check_rev(data, expected)
    index = current(data)
    if index >= 7 or artifact not in DOCS[index]:
        fail("artifact not part of the currently open stage")
    content = Path(source).read_bytes()
    if not content.strip():
        fail("empty artifact")
    target = file_under(root, artifact)
    write_atomic(target, content)
    data["stages"][index]["artifacts"][artifact] = {
        "sha256": digest(content), "actor": actor, "at": now(),
        "revision": data["revision"] + 1,
    }
    data["stages"][index].setdefault("stale_artifacts", [])
    if artifact in data["stages"][index]["stale_artifacts"]:
        data["stages"][index]["stale_artifacts"].remove(artifact)
    data["stages"][index]["reviews"] = []
    touch(root, data, "submit", actor, {"stage": index, "artifact": artifact})
    return next_step(root, data)


def review(root, verdict, kind, actor, note, expected=None):
    data = load(root)
    check_rev(data, expected)
    index = current(data)
    if index >= 7:
        fail("all planning stages already confirmed")
    if verdict not in ("pass", "changes", "blocked"):
        fail("unsupported review verdict")
    if kind not in ("self_check", "independent_review"):
        fail("unsupported review type")
    if not note.strip() or not actor.strip():
        fail("review actor and explanatory note required")
    s = data["stages"][index]
    if kind == "independent_review" and any(
        x["actor"].strip().casefold() == actor.strip().casefold()
        for x in s["artifacts"].values()
    ):
        fail("submitter cannot self-declare independent review")
    s["reviews"].append({"verdict": verdict, "type_claim": kind,
                         "actor": actor, "note": note.strip(),
                         "revision": data["revision"] + 1, "at": now(),
                         "identity_verified": False})
    touch(root, data, "review", actor, {"stage": index, "verdict": verdict,
                                       "type_claim": kind})
    return next_step(root, data)


def confirm(root, actor, statement, expected=None):
    data = load(root)
    check_rev(data, expected)
    i = current(data)
    if i >= 7:
        fail("all stages already confirmed")
    if not actor.strip() or not statement.strip():
        fail("confirmation must include actor and exact statement")
    gate = pending(root, data, i)
    if gate["missing_artifacts"] or gate["unanswered"] or not gate["passing_review"] or gate["blocking_review"]:
        fail("stage gate failed: " + json.dumps(gate, ensure_ascii=False))
    data["stages"][i]["confirmed"] = True
    data["stages"][i]["confirmation"] = {
        "actor_claim": actor, "statement": statement.strip(),
        "at": now(), "revision": data["revision"] + 1,
        "identity_verified": False,
    }
    touch(root, data, "confirm", actor, {"stage": i, "statement": statement.strip()})
    return status(root, data)


def propose(root, category, description, rationale, actor, expected=None):
    data = load(root)
    check_rev(data, expected)
    if category not in IMPACT or not description.strip() or not rationale.strip():
        fail("unknown category or empty change description/rationale")
    id_ = "CHG-%04d" % (len(data["changes"]) + 1)
    data["changes"].append({"id": id_, "category": category, "description": description.strip(),
                            "rationale": rationale.strip(), "actor": actor,
                            "impact_from_stage": IMPACT[category], "status": "proposed",
                            "created_at": now(), "decision": None})
    touch(root, data, "propose_change", actor, {"id": id_, "category": category})
    return {"id": id_, "status": "proposed", "impact_from_stage": IMPACT[category],
            "baseline_mutated": False}


def decide(root, id_, outcome, actor, reason, expected=None):
    data = load(root)
    check_rev(data, expected)
    if outcome not in ("accept", "defer", "reject") or not reason.strip() or not actor.strip():
        fail("outcome, reason and actor required")
    item = next((c for c in data["changes"] if c["id"] == id_), None)
    if item is None or item["status"] != "proposed":
        fail("change does not exist or has already been decided")
    item["status"] = {"accept": "accepted", "defer": "deferred",
                      "reject": "rejected"}[outcome]
    item["decision"] = {"actor_claim": actor, "reason": reason.strip(),
                        "at": now(), "identity_verified": False}
    invalidated = []
    if outcome == "accept":
        start = item["impact_from_stage"]
        data["accepted_changes"].append(id_)
        for i in range(start, 7):
            stage = data["stages"][i]
            if stage["confirmed"]:
                invalidated.append(i)
            stage["confirmed"] = False
            stage["confirmation"] = None
            stage["reviews"] = []
            stage["stale_artifacts"] = list(DOCS[i])
            # Retain files but force regeneration/re-submission before another approval.
    touch(root, data, "decide_change", actor,
          {"id": id_, "outcome": outcome, "invalidated": invalidated})
    return {"id": id_, "status": item["status"], "invalidated_stages": invalidated,
            "current_stage": current(data) if current(data) < 7 else None}


def handoff(root, actor):
    data = load(root)
    if current(data) != 7:
        fail("cannot hand off before all seven stages are confirmed")
    for i, stage in enumerate(data["stages"]):
        for path in DOCS[i]:
            if not verified_artifact(root, stage, path):
                fail("stale or missing artifact: " + path)
    packet = {
        "schema_version": 1, "product_intent": data["idea_original"],
        "project_revision": data["revision"], "stage_confirmations":
        [s["confirmation"] for s in data["stages"]],
        "documents": [p for group in DOCS.values() for p in group],
        "accepted_changes": data["accepted_changes"],
        "action": "ENGINEERING_APPROVAL_REQUIRED",
        "execution_authorized": False, "release_authorized": False,
        "review_identity_verified": False,
        "agent_contract": {
            "source_of_truth": ".foundry/project.json",
            "instructions": "Read docs and latest confirmed stage; work only within separately approved scope.",
            "input_version": data["revision"],
            "definition_of_done": "Use docs/05-definition-of-done.md and independent QA evidence.",
            "change_policy": "Propose CHG before changing an approved product decision.",
        },
    }
    path = file_under(root, ".foundry/HANDOFF.json")
    write_atomic(path, (json.dumps(packet, ensure_ascii=False, indent=2) + "\n").encode())
    log(root, "export_handoff", actor, data["revision"],
        {"engineering_authorized": False})
    return packet


def mcp(root):
    """Read-only MCP stdio adapter; no approval, mutation or cross-project access."""
    definitions = [
        {"name": "foundry_status", "description": "Read project gates and confirmed stages.",
         "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "foundry_next", "description": "Read next planning step and evidence requirements.",
         "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    ]
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            method = request.get("method")
            ident = request.get("id")
            if method == "notifications/initialized" or ident is None:
                continue
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05",
                          "capabilities": {"tools": {}},
                          "serverInfo": {"name": "product-foundry", "version": "0.1.0"}}
            elif method == "tools/list":
                result = {"tools": definitions}
            elif method == "tools/call":
                args = request.get("params", {})
                if args.get("arguments", {}) != {}:
                    raise ValueError("tool takes no arguments")
                name = args.get("name")
                if name == "foundry_status":
                    content = status(root)
                elif name == "foundry_next":
                    content = next_step(root)
                else:
                    raise ValueError("unknown tool")
                result = {"content": [{"type": "text", "text": json.dumps(content, ensure_ascii=False)}]}
            else:
                raise ValueError("unknown method")
            response = {"jsonrpc": "2.0", "id": ident, "result": result}
        except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
            response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None,
                        "error": {"code": -32602, "message": str(exc)}}
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Product Foundry V0.1 (stdlib, local files)")
    parser.add_argument("--project", required=True, help="existing or new project directory")
    sub = parser.add_subparsers(dest="command", required=True)
    def command(name, *args):
        p = sub.add_parser(name)
        for k in args:
            p.add_argument("--" + k.replace("_", "-"), required=True)
        return p
    command("init", "idea", "actor")
    sub.add_parser("status")
    sub.add_parser("next")
    command("answer", "key", "value", "actor")
    command("submit", "artifact", "file", "actor")
    command("review", "verdict", "kind", "actor", "note")
    command("confirm", "actor", "statement")
    command("propose", "category", "description", "rationale", "actor")
    command("decide", "id", "outcome", "actor", "reason")
    command("handoff", "actor")
    sub.add_parser("mcp")
    # Optimistic-lock token for all change-producing operations, when supplied.
    for name in ("answer", "submit", "review", "confirm", "propose", "decide"):
        sub.choices[name].add_argument("--expected-revision", type=int)
    a = parser.parse_args(argv)
    root = Path(a.project).expanduser().resolve()
    try:
        if a.command == "init":
            output = init(root, a.idea, a.actor)
        elif a.command == "status":
            output = status(root)
        elif a.command == "next":
            output = next_step(root)
        elif a.command == "answer":
            output = answer(root, a.key, a.value, a.actor, a.expected_revision)
        elif a.command == "submit":
            output = submit(root, a.artifact, a.file, a.actor, a.expected_revision)
        elif a.command == "review":
            output = review(root, a.verdict, a.kind, a.actor, a.note, a.expected_revision)
        elif a.command == "confirm":
            output = confirm(root, a.actor, a.statement, a.expected_revision)
        elif a.command == "propose":
            output = propose(root, a.category, a.description, a.rationale, a.actor,
                             a.expected_revision)
        elif a.command == "decide":
            output = decide(root, a.id, a.outcome, a.actor, a.reason, a.expected_revision)
        elif a.command == "handoff":
            output = handoff(root, a.actor)
        else:
            mcp(root)
            return 0
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(cli())

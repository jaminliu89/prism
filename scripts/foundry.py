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

# Support CLI execution and isolated importlib-based test runners.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
import foundry_guard as guard
import foundry_panel as panel
import architecture_gate

SCHEMA = 1
DOCS = {
    0: ("docs/00-idea-brief.md", "docs/00-asset-recall.md"),
    1: ("docs/01-product-research.md",),
    2: ("docs/02-stories-and-journeys.md", "docs/02-state-machines.md",
        architecture_gate.ARCHITECTURE_PATH),
    3: ("docs/03-prd.md", "docs/03-design-system.md"),
    4: ("docs/04-architecture.md", "docs/04-technology-decisions.md",
        "docs/04-security-threat-model.md"),
    5: ("docs/05-roadmap.md", "docs/06-task-board.md", "docs/05-definition-of-done.md"),
    6: ("docs/07-consistency-audit.md", "docs/08-engineering-handoff.md",
        "docs/07-security-acceptance-plan.md"),
}
def docs_for(data, stage):
    """New projects include a pre-contract architecture sketch, legacy plans stay intact."""
    paths = DOCS[stage]
    if data.get("architecture_first_schema") != 1 and stage == 2:
        return tuple(p for p in paths if p != architecture_gate.ARCHITECTURE_PATH)
    return paths


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
AGENT_ROLES = ("pm", "research", "ux", "architect", "security", "qa")

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
        "architecture_first_schema": 1,
        "answers": {}, "accepted_changes": [],
        "stages": [{"confirmed": False, "artifacts": {}, "reviews": [],
                    "confirmation": None} for _ in range(7)],
        "changes": [], "security": guard.new_state(), "tasks": [],
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
    missing = [p for p in docs_for(data, index) if not verified_artifact(root, s, p)]
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
    security_review = guard.gate(data) if index == 4 else None
    open_panel = panel.unresolved(data, index)
    open_tasks = [t["id"] for t in data.get("tasks", [])
                  if t["stage"] == index and t["status"] not in ("delivered", "cancelled")]
    return {"missing_artifacts": missing, "unanswered": unanswered,
            "passing_review": review, "blocking_review": changes,
            "security_gate": security_review,
            "open_agent_tasks": open_tasks,
            "open_panel_topics": open_panel}


def status(root, data=None):
    data = data or load(root)
    active = current(data)
    stale_confirmed = [p for i, stage in enumerate(data["stages"])
                       if stage["confirmed"] for p in docs_for(data, i)
                       if not verified_artifact(root, stage, p)]
    stages = []
    for i, s in enumerate(data["stages"]):
        p = pending(root, data, i)
        stages.append({"stage": i, "name": STAGE_NAMES[i],
                       "confirmed": s["confirmed"],
                       "artifacts": list(s["artifacts"]),
                       "missing": p["missing_artifacts"],
                       "reviews": len(s["reviews"])})
    return {
        "status": ("STALE_CONFIRMED_ARTIFACTS" if stale_confirmed else
                   "SECURITY_DESIGN_INCOMPLETE" if active == 7 and not guard.gate(data)["design_ready"] else
                   "BLUEPRINT_READY" if active == 7 else "PLANNING"),
        "integrity_issues": stale_confirmed,
        "revision": data["revision"], "original_intent": data["idea_original"],
        "current_stage": active if active < 7 else None,
        "stage_gate": pending(root, data, active) if active < 7 else None,
        "stages": stages,
        "open_changes": [c["id"] for c in data["changes"]
                         if c["status"] == "proposed"],
        "agent_execution": "NOT_STARTED",
        "security": {"gate": guard.gate(data),
                     "assessment_scope": "DESIGN_ONLY; not a penetration test"},
        "panel": {"unresolved": panel.unresolved(data), "topics": len(data.get("panel_topics", []))},
        "tasks": [{"id": t["id"], "role": t["role"], "stage": t["stage"],
                   "artifact": t["artifact"], "status": t["status"]}
                  for t in data.get("tasks", [])],
        "release_authorized": False,
    }


def next_step(root, data=None):
    data = data or load(root)
    s = status(root, data)
    i = s["current_stage"]
    if i is None:
        if s["status"] == "SECURITY_DESIGN_INCOMPLETE":
            return {"status": s["status"], "security": guard.summary(data),
                    "next": "Reopen architecture/security planning with an approved change; re-confirm affected stages."}
        if s["integrity_issues"]:
            return {"status": s["status"], "integrity_issues": s["integrity_issues"],
                    "next": "Reopen impacted stages via an accepted change and re-submit artifacts."}
        return {"status": "BLUEPRINT_READY", "next": "export handoff; engineering needs separate approval"}
    gate = s["stage_gate"]
    return {
        "stage": i, "name": STAGE_NAMES[i], "expected_documents": list(docs_for(data, i)),
        "missing_documents": gate["missing_artifacts"],
        "questions": {q: QUESTIONS[q] for q in gate["unanswered"]},
        "review_required": not gate["passing_review"],
        "review_blocked": gate["blocking_review"],
        "open_agent_tasks": gate["open_agent_tasks"],
        "open_panel_topics": gate["open_panel_topics"],
        "security_questions": guard.prompts(data) if i in (0, 3, 4, 6) else {},
        "security_gate": gate["security_gate"],
        "agent_roles": ["security", "architect", "qa"] if i in (4, 6) else
                       ["pm", "research"] if i <= 1 else ["ux", "architect", "qa"],
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
    if index >= 7 or artifact not in docs_for(data, index):
        fail("artifact not part of the currently open stage")
    content = Path(source).read_bytes()
    if not content.strip():
        fail("empty artifact")
    if artifact == architecture_gate.ARCHITECTURE_PATH:
        try:
            architecture_gate.validate(content)
        except ValueError as exc:
            fail("architecture sketch blocked before contract: " + str(exc))
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
    if (gate["missing_artifacts"] or gate["unanswered"] or
        not gate["passing_review"] or gate["blocking_review"] or
        gate["open_agent_tasks"] or gate["open_panel_topics"] or
        (gate["security_gate"] and not gate["security_gate"]["design_ready"])):
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
        start = (2 if item["category"] == "architecture" and
                 data.get("architecture_first_schema") == 1
                 else item["impact_from_stage"])
        data["accepted_changes"].append(id_)
        for i in range(start, 7):
            stage = data["stages"][i]
            if stage["confirmed"]:
                invalidated.append(i)
            stage["confirmed"] = False
            stage["confirmation"] = None
            stage["reviews"] = []
            stage["stale_artifacts"] = list(docs_for(data, i))
            for topic in data.get("panel_topics", []):
                if topic["stage"] >= i:
                    topic["status"] = "superseded"
            for task in data.get("tasks", []):
                if task["stage"] == i and task["status"] not in ("cancelled",):
                    task["status"] = "cancelled"
            # Retain files but force regeneration/re-submission before another approval.
    touch(root, data, "decide_change", actor,
          {"id": id_, "outcome": outcome, "invalidated": invalidated})
    return {"id": id_, "status": item["status"], "invalidated_stages": invalidated,
            "current_stage": current(data) if current(data) < 7 else None}



def security_profile(root, key, value, actor, expected=None):
    data = load(root)
    check_rev(data, expected)
    if current(data) > 4:
        fail("approved security baseline: propose and accept a security-related change first")
    report = guard.profile_set(data, key, value)
    stage = data["stages"][4]
    stage["reviews"] = []
    stage.setdefault("stale_artifacts", [])
    if "docs/04-security-threat-model.md" not in stage["stale_artifacts"]:
        stage["stale_artifacts"].append("docs/04-security-threat-model.md")
    touch(root, data, "security_profile", actor, {"field": key, "content_redacted": True})
    return {"security_gate": report, "profile_field": key}


def security_assess(root, code, disposition, reason, actor, asset="", boundary="",
                    attack_path="", control="", verification="", expected=None):
    data = load(root)
    check_rev(data, expected)
    if current(data) > 4:
        fail("approved security baseline: propose and accept a security-related change first")
    report = guard.record(data, code, disposition, actor, reason, asset, boundary,
                          attack_path, control, verification)
    stage = data["stages"][4]
    stage["reviews"] = []
    stage.setdefault("stale_artifacts", [])
    if "docs/04-security-threat-model.md" not in stage["stale_artifacts"]:
        stage["stale_artifacts"].append("docs/04-security-threat-model.md")
    touch(root, data, "security_assessment", actor, {"code": code,
                                                     "disposition": disposition})
    return {"security_gate": report, "recorded": code, "evidence_status": "DESIGN_ONLY"}


def assign_task(root, role, artifact, objective, actor, expected=None):
    data = load(root)
    check_rev(data, expected)
    stage = current(data)
    if stage >= 7 or role not in AGENT_ROLES or artifact not in docs_for(data, stage):
        fail("unknown role or artifact outside active stage")
    if not objective.strip() or not actor.strip():
        fail("task objective and requesting actor required")
    if "security" in artifact and role not in ("security", "architect", "qa"):
        fail("security documents require a security, architecture or QA task role")
    if any(t["stage"] == stage and t["artifact"] == artifact
           and t["status"] not in ("cancelled", "delivered")
           for t in data.get("tasks", [])):
        fail("duplicate active assignment for artifact")
    key = "AGT-%04d" % (len(data.setdefault("tasks", [])) + 1)
    task = {
        "id": key, "stage": stage, "role": role,
        "objective": objective.strip(), "artifact": artifact,
        "status": "ready", "requested_by_claim": actor,
        "assigned_to_claim": None, "created_revision": data["revision"] + 1,
        "allowed_write_paths": [artifact],
        "allowed_actions": ["read approved project docs", "submit planning document"],
        "denied_actions": ["modify approved goals", "run target code", "exfiltrate data",
                           "production access", "paid tools", "deploy", "approve own work"],
        "source_docs": ["sources/skillhub/blueprint/MASTER_PROMPT.md",
                        "sources/skillhub/blueprint/DOCUMENT_CONTRACT.md"],
        "authorization": "PLANNING_DOCUMENT_ONLY",
        "identity_verified": False, "delivery": None,
    }
    data["tasks"].append(task)
    touch(root, data, "task_assign", actor, {"id": key, "artifact": artifact, "role": role})
    return task


def claim_task(root, id_, actor, expected=None):
    data = load(root)
    check_rev(data, expected)
    task = next((x for x in data.get("tasks", []) if x["id"] == id_), None)
    if task is None or task["status"] != "ready" or task["stage"] != current(data):
        fail("task not ready for claim or its stage changed")
    if not actor.strip():
        fail("task claim requires actor")
    task["status"] = "claimed"
    task["assigned_to_claim"] = actor.strip()
    touch(root, data, "task_claim", actor, {"id": id_})
    return task


def deliver_task(root, id_, source, actor, expected=None):
    data = load(root)
    check_rev(data, expected)
    task = next((x for x in data.get("tasks", []) if x["id"] == id_), None)
    if (task is None or task["status"] != "claimed" or
        task["stage"] != current(data) or task["assigned_to_claim"] != actor):
        fail("task is not claimed by this actor or current stage changed")
    content = Path(source).read_bytes()
    if not content.strip():
        fail("cannot deliver empty task artifact")
    if task["artifact"] == architecture_gate.ARCHITECTURE_PATH:
        try:
            architecture_gate.validate(content)
        except ValueError as exc:
            fail("architecture sketch blocked before contract: " + str(exc))
    path = task["artifact"]
    target = file_under(root, path)
    write_atomic(target, content)
    stage = data["stages"][task["stage"]]
    stage["artifacts"][path] = {"sha256": digest(content), "actor": actor,
                                "at": now(), "revision": data["revision"] + 1}
    stage.setdefault("stale_artifacts", [])
    if path in stage["stale_artifacts"]:
        stage["stale_artifacts"].remove(path)
    stage["reviews"] = []
    task["status"] = "delivered"
    task["delivery"] = {"artifact": path, "sha256": digest(content),
                        "at": now(), "revision": data["revision"] + 1}
    touch(root, data, "task_deliver", actor, {"id": id_, "artifact": path,
                                            "sha256": digest(content)})
    return {"id": id_, "status": task["status"], "artifact": path,
            "sha256": digest(content), "next": next_step(root, data)}



def panel_open(root, question, actor, expected=None):
    data = load(root)
    check_rev(data, expected)
    stage = current(data)
    if stage >= 7:
        fail("confirmed planning: propose a change before new review")
    value = panel.create_topic(data, stage, question, actor)
    touch(root, data, "panel_open", actor, {"topic": value["id"], "stage": stage})
    return panel.brief(data, value["id"])


def panel_opinion(root, topic_id, role, actor, verdict, severity,
                  reasoning, evidence, counterexample, expected=None):
    data = load(root)
    check_rev(data, expected)
    item = panel.topic(data, topic_id)
    if item["stage"] != current(data):
        fail("review belongs to a different stage")
    result = panel.add_opinion(data, topic_id, role, actor, verdict, severity,
                               reasoning, evidence, counterexample)
    touch(root, data, "panel_opinion", actor, {"topic": topic_id, "role": role,
                                             "verdict": verdict, "severity": severity})
    return result


def panel_resolve(root, topic_id, outcome, actor, rationale, expected=None):
    data = load(root)
    check_rev(data, expected)
    if panel.topic(data, topic_id)["stage"] != current(data):
        fail("review belongs to a different stage")
    result = panel.resolve(data, topic_id, outcome, actor, rationale)
    data["stages"][current(data)]["reviews"] = []
    touch(root, data, "panel_resolve", actor, {"topic": topic_id, "outcome": outcome})
    return result


def handoff(root, actor):
    data = load(root)
    if current(data) != 7:
        fail("cannot hand off before all seven stages are confirmed")
    if not guard.gate(data)["design_ready"]:
        fail("security design review incomplete; handoff denied")
    for i, stage in enumerate(data["stages"]):
        for path in docs_for(data, i):
            if not verified_artifact(root, stage, path):
                fail("stale or missing artifact: " + path)
    packet = {
        "schema_version": 1, "product_intent": data["idea_original"],
        "project_revision": data["revision"], "stage_confirmations":
        [s["confirmation"] for s in data["stages"]],
        "documents": [p for group in DOCS.values() for p in group],
        "accepted_changes": data["accepted_changes"],
        "product_panel": [{"id": x["id"], "stage": x["stage"], "resolution": x["resolution"]} for x in data.get("panel_topics", [])],
        "action": "ENGINEERING_APPROVAL_REQUIRED",
        "execution_authorized": False, "release_authorized": False,
        "review_identity_verified": False,
        "security_assurance": {"design_review": guard.gate(data),
                               "runtime_security_verified": False,
                               "reverse_engineering_difficulty": "NOT_MEASURED"},
        "agent_contract": {
            "source_of_truth": ".foundry/project.json",
            "instructions": "Read docs and latest confirmed stage; work only within separately approved scope.",
            "input_version": data["revision"],
            "definition_of_done": "Use docs/05-definition-of-done.md and independent QA evidence.",
            "change_policy": "Propose CHG before changing an approved product decision.",
            "security_policy": "Never put protected orchestration/secrets in client artifacts. Validate server-side authorization, tenant separation, sandbox and tool permissions. Verify using separately authorized staging tests.",
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
        {"name": "foundry_security", "description": "Read defensive threat model and design assurance gaps.",
         "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "foundry_panel", "description": "Read open expert review topics and dissent status.",
         "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "foundry_tasks", "description": "Read scoped agent collaboration task contracts.",
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
                elif name == "foundry_security":
                    content = {"gate": guard.gate(load(root)), "threat_ids": list(guard.CATALOG),
                               "note": "Details remain in the private project and are not exposed over MCP."}
                elif name == "foundry_panel":
                    content = {"unresolved": panel.unresolved(load(root))}
                elif name == "foundry_tasks":
                    content = {"tasks": [
                        {k: task[k] for k in ("id", "stage", "role", "artifact", "status")}
                        for task in load(root).get("tasks", [])]}
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
    sub.add_parser("security-status")
    sub.add_parser("security-draft")
    sub.add_parser("tasks")
    sub.add_parser("panel-status")
    command("panel-open", "question", "actor")
    command("panel-opinion", "id", "role", "actor", "verdict", "severity",
            "reasoning", "evidence", "counterexample")
    command("panel-resolve", "id", "outcome", "actor", "rationale")
    command("security-profile", "key", "value", "actor")
    sc = command("security-assess", "code", "disposition", "reason", "actor")
    for key in ("asset", "boundary", "attack_path", "control", "verification"):
        sc.add_argument("--" + key.replace("_", "-"), default="")
    command("task-assign", "role", "artifact", "objective", "actor")
    command("task-claim", "id", "actor")
    command("task-deliver", "id", "file", "actor")
    command("answer", "key", "value", "actor")
    command("submit", "artifact", "file", "actor")
    command("review", "verdict", "kind", "actor", "note")
    command("confirm", "actor", "statement")
    command("propose", "category", "description", "rationale", "actor")
    command("decide", "id", "outcome", "actor", "reason")
    command("handoff", "actor")
    sub.add_parser("mcp")
    # Optimistic-lock token for all change-producing operations, when supplied.
    for name in ("answer", "submit", "review", "confirm", "propose", "decide",
                 "security-profile", "security-assess", "task-assign", "task-claim", "task-deliver",
                 "panel-open", "panel-opinion", "panel-resolve"):
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
        elif a.command == "security-status":
            output = guard.summary(load(root))
        elif a.command == "security-draft":
            print(guard.render(load(root)))
            return 0
        elif a.command == "tasks":
            output = {"tasks": load(root).get("tasks", [])}
        elif a.command == "panel-status":
            output = {"open": panel.unresolved(load(root)),
                      "topics": load(root).get("panel_topics", [])}
        elif a.command == "panel-open":
            output = panel_open(root, a.question, a.actor, a.expected_revision)
        elif a.command == "panel-opinion":
            output = panel_opinion(root, a.id, a.role, a.actor, a.verdict,
                                   a.severity, a.reasoning, a.evidence,
                                   a.counterexample, a.expected_revision)
        elif a.command == "panel-resolve":
            output = panel_resolve(root, a.id, a.outcome, a.actor, a.rationale,
                                   a.expected_revision)
        elif a.command == "security-profile":
            output = security_profile(root, a.key, a.value, a.actor, a.expected_revision)
        elif a.command == "security-assess":
            output = security_assess(root, a.code, a.disposition, a.reason, a.actor,
                                     a.asset, a.boundary, a.attack_path, a.control,
                                     a.verification, a.expected_revision)
        elif a.command == "task-assign":
            output = assign_task(root, a.role, a.artifact, a.objective,
                                 a.actor, a.expected_revision)
        elif a.command == "task-claim":
            output = claim_task(root, a.id, a.actor, a.expected_revision)
        elif a.command == "task-deliver":
            output = deliver_task(root, a.id, a.file, a.actor, a.expected_revision)
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

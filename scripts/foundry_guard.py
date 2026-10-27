"""Security-by-design threat hypotheses for Product Foundry. No scanning or certification."""
from copy import deepcopy
import json

PROFILE = {
    "protected_assets": "Identify private assets: orchestration strategy, prompt assembly, business rules, credentials, customer data. Do not paste secrets.",
    "deployment_boundary": "Describe what runs in browser, client, server, sandbox and third-party platforms.",
    "attacker_capability": "Assume an end user can inspect public bundles, network traffic and downloaded artifacts. What other access matters?",
    "trust_boundary": "Where do untrusted content, plugin calls, tenant identity and human approvals cross boundaries?",
    "security_objective": "What unacceptable harm matters: workflow extraction, unauthorized calls, tenant leaks, billing abuse or data exfiltration?",
}

# A potential risk is not a claim about a real product. Each must be marked applicable or N/A.
CATALOG = {
    "ORCHESTRATION_EXPOSURE": {
        "severity": "high",
        "asset": "proprietary workflow, prompt assembly and model/tool routing",
        "surface": "public bundles, source maps, verbose responses, artifacts and logs",
        "control": "Keep privileged orchestration and routing server-side; return only authorized minimal data. Never ship protected prompts or secrets in the client.",
        "test": "On an owned staging build, inspect public bundles, maps, API responses and exported files for private workflow content.",
        "standard": "OWASP ASVS 5.0.0 / OWASP LLM Top 10 2025",
    },
    "API_AUTHORIZATION": {
        "severity": "high",
        "asset": "documents, user data, project tasks and entitlements",
        "surface": "object identifiers, public/share/export endpoints, workspace switches",
        "control": "Verify identity and object/function-level permissions on the server for every read, write and export.",
        "test": "Using authorized isolated accounts, assert denial of cross-tenant reads, writes and role transitions.",
        "standard": "OWASP API Security Top 10 2023",
    },
    "AGENT_TOOL_BOUNDARY": {
        "severity": "high",
        "asset": "protected agent capabilities, model/tool credentials and user data",
        "surface": "retrieved pages, repository instructions, uploads, handoffs and tools",
        "control": "Treat retrieved instructions as untrusted data; scope each tool per task, check arguments server-side and require high-impact approvals.",
        "test": "In a sandbox, use benign prompt-injection fixtures to confirm external content cannot grant tool access.",
        "standard": "OWASP LLM Top 10 2025",
    },
    "SECRETS_AND_LOGS": {
        "severity": "high",
        "asset": "secrets, prompts, customer data and confidential runtime context",
        "surface": "bundles, diagnostic output, traces, exports and repo history",
        "control": "Use a private secrets store and restricted logs, redaction, retention policies and authenticated exports.",
        "test": "Review authorized build/export artifacts and sanitized logs for sensitive context and inadvertent disclosure.",
        "standard": "OWASP ASVS 5.0.0",
    },
    "SANDBOX_ISOLATION": {
        "severity": "high",
        "asset": "host, files, network, project workspaces and paid compute",
        "surface": "code runners, previews, package installs, file/network tools",
        "control": "Isolate untrusted code with least privilege, filesystem/egress controls, resource limits and no host credentials.",
        "test": "Use harmless staging fixtures to verify project, filesystem and network boundary enforcement.",
        "standard": "OWASP ASVS 5.0.0",
    },
    "SUPPLY_CHAIN": {
        "severity": "medium",
        "asset": "source, dependencies, skills, plugins and release artifacts",
        "surface": "packages, MCP connectors, remote plugins and builds",
        "control": "Pin reviewed sources and licenses, restrict connectors, track dependencies and verify artifact provenance.",
        "test": "On authorized source and builds, run dependency review and check manifest/hash consistency.",
        "standard": "OWASP ASVS 5.0.0",
    },
    "RESOURCE_ABUSE": {
        "severity": "medium",
        "asset": "model quota, availability, billing and credits",
        "surface": "generation endpoints, job retries and subscription limits",
        "control": "Check entitlements on server; bound per-tenant budgets, concurrent jobs, retries and idempotent operations.",
        "test": "Check quota, cancellation and duplicate requests against rate-limited isolated fixtures.",
        "standard": "OWASP API Security Top 10 2023",
    },
}


def new_state():
    return {
        "version": 1, "profile": {},
        "assessments": {
            key: {"disposition": "unassessed", "severity": value["severity"]}
            for key, value in CATALOG.items()
        },
        "observations": [],
    }


def get(data):
    return data.get("security") or new_state()


def prompts(data):
    profile = get(data)["profile"]
    return {key: question for key, question in PROFILE.items() if not profile.get(key)}


def gate(data):
    sec = get(data)
    unassessed = [key for key in CATALOG
                  if sec["assessments"].get(key, {}).get("disposition") == "unassessed"]
    high = [key for key in CATALOG
            if sec["assessments"].get(key, {}).get("disposition") == "accept_risk"
            and CATALOG[key]["severity"] == "high"]
    return {
        "profile_missing": list(prompts(data)),
        "unassessed_threats": unassessed,
        "unresolved_high_risk": high,
        "design_ready": not (prompts(data) or unassessed or high),
        "operationally_verified": False,
        "reverse_engineering_resistance": "NOT_MEASURED",
    }


def profile_set(data, key, value):
    if key not in PROFILE or not value.strip():
        raise ValueError("unknown security field or empty value")
    data.setdefault("security", new_state())["profile"][key] = value.strip()
    return gate(data)


def record(data, code, disposition, actor, reason, asset="", boundary="",
           attack_path="", control="", verification=""):
    if code not in CATALOG:
        raise ValueError("unknown security threat")
    if disposition not in ("mitigate", "not_applicable", "accept_risk"):
        raise ValueError("unknown security disposition")
    if not actor.strip() or not reason.strip():
        raise ValueError("security decision needs an actor and reason")
    if disposition == "mitigate" and not all(x.strip() for x in
                                            (asset, boundary, attack_path, control, verification)):
        raise ValueError("mitigation requires asset, boundary, attack path, control and verification plan")
    if disposition == "accept_risk" and CATALOG[code]["severity"] == "high":
        raise ValueError("high-risk acceptance cannot be authorized by an unauthenticated CLI")
    data.setdefault("security", new_state())["assessments"][code] = {
        "disposition": disposition, "severity": CATALOG[code]["severity"],
        "asset": asset.strip(), "boundary": boundary.strip(),
        "attack_path": attack_path.strip(), "control": control.strip(),
        "verification": verification.strip(), "reason": reason.strip(),
        "actor_claim": actor, "evidence_status": "DESIGN_ONLY",
        "identity_verified": False,
    }
    return gate(data)


def summary(data):
    sec = get(data)
    return {
        "questions": prompts(data), "profile": deepcopy(sec["profile"]),
        "threat_catalog": deepcopy(CATALOG),
        "assessments": deepcopy(sec["assessments"]),
        "gate": gate(data),
        "boundary": "Authorized-owned staging only. No live exploits, unauthorized probing or data collection.",
        "anti_obscurity": "Client-side obfuscation is not a substitute for server authorization, tenant isolation and keeping privileged logic server-side.",
        "assurance": "No CTF difficulty score without defined attacker, scoped exercise and reproducible observed results.",
        "specialist": "site-reverse-clone project audit, independently authorized",
    }


def render(data):
    report = summary(data)
    out = [
        "# Security design and reverse-engineering resistance",
        "",
        "DESIGN-ONLY: no security certification, live penetration test or CTF exercise occurred.",
        "Never paste secrets, private system prompts or confidential algorithms into shared documentation.",
        "",
        "## Protected assets and trust boundaries", "",
    ]
    for k, question in PROFILE.items():
        out += ["### " + k, "", question, "",
                "Recorded: " + str(report["profile"].get(k, "UNANSWERED")), ""]
    out += [
        "## Threats, countermeasures and authorized tests", "",
        "| ID | Severity | Disposition | Defensive control | Proposed verification |",
        "|---|---|---|---|---|",
    ]
    clean = lambda value: str(value).replace("|", "/").replace("\n", " ")
    for key, threat in CATALOG.items():
        assessment = report["assessments"][key]
        out.append("| " + " | ".join(clean(x) for x in (
            key, threat["severity"], assessment["disposition"],
            assessment.get("control") or threat["control"],
            assessment.get("verification") or threat["test"])) + " |")
    out += [
        "", "## Gate report", "",
        json.dumps(report["gate"], ensure_ascii=False, indent=2),
        "",
        "## Assurance limitation", "",
        "- A client recipient can inspect bundles, source maps, network traffic and downloaded files.",
        "- Protected orchestration, policies and credentials must not be delivered into this untrusted boundary.",
        "- No universal reverse-engineering or CTF difficulty can be honestly inferred from architecture diagrams.",
        "- Any later adversarial exercise requires explicit authorization, isolated test accounts, reproducibility and time budget.",
        "- Operational security remains unverified until the actual deployment is independently tested.",
        "",
        "Standards: OWASP ASVS 5.0.0, OWASP API Security Top 10 2023, OWASP LLM Top 10 2025.",
        "Site-reverse-clone is a specialist for evidence-based audits with separate approval; it is not executed here.",
        "",
    ]
    return "\n".join(out)

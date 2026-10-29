#!/usr/bin/env python3
"""Offline-first packet evidence routing for Prism; never captures or analyzes packets itself."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROUTES = {
    "capture_metadata": ("capinfos", "tshark", "Wireshark"),
    "offline_protocol_timeline": ("tshark", "Wireshark"),
    "packet_subset_export": ("editcap", "tshark"),
    "live_capture": ("dumpcap",),
}
TOOLS = {"capinfos", "tshark", "Wireshark", "editcap", "dumpcap"}
OFFLINE = {"owned_capture", "authorized_lab"}
ACCESS = OFFLINE | {"owned_interface"}
MAX_ARTIFACT_SIZE = 1024 * 1024 * 1024  # Bound verification workload to 1 GiB.


def route(intent, access, host_verified=(), live_capture_approved=False):
    if intent not in ROUTES:
        raise ValueError("Unknown packet evidence intent")
    if access not in ACCESS:
        raise ValueError("Access scope must be explicitly declared")
    if not set(host_verified).issubset(TOOLS):
        raise ValueError("Unrecognized host-verified tool declaration")
    if intent == "live_capture":
        if access != "owned_interface" or not live_capture_approved:
            raise ValueError("Live capture requires owned_interface and separate explicit approval")
    elif access not in OFFLINE:
        raise ValueError("Offline analysis requires an owned or authorized capture")
    candidates = list(ROUTES[intent])
    selected = next((tool for tool in candidates if tool in host_verified), None)
    return {
        "status": "PLAN_ONLY",
        "primary_in_group": "agent-reverse-engineering",
        "orchestrator": "prism",
        "specialist": "network-packet-intelligence",
        "intent": intent,
        "access_declaration": access,
        "candidates": candidates,
        "selected": selected,
        "runtime_discovery": "HOST_DECLARED_ONLY" if host_verified else "REQUIRED",
        "authorization_verified": False,
        "tool_executed": False,
        "capture_started": False,
        "release_authorized": False,
        "next": "Current authorized host must independently verify scope, tool binary/version, sample and command",
        "limits": [
            "Never install certificates, alter proxy settings, grant capture privileges or run dumpcap implicitly",
            "Raw PCAP can contain personal content and credentials; retain locally and review redaction",
            "TLS encryption, capture loss, truncation and vantage point limit inferences",
            "A plan and self-declared installed tools are not execution or independently reviewed evidence",
        ],
    }


def _local_file(root, rel):
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError("Evidence path must be relative and inside authorized artifact root")
    relative = Path(rel)
    if any((root / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
        raise ValueError("Symlink evidence path prohibited")
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("Missing or outside evidence artifact")
    if target.stat().st_size > MAX_ARTIFACT_SIZE:
        raise ValueError("Evidence exceeds verification size limit")
    return target


def verify_record(record, artifact_root):
    root = Path(artifact_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Missing authorized artifact root")
    needed = ("task_id", "target", "revision", "scope", "tool", "tool_version",
              "command_or_filter", "observed_at", "artifact_path", "sha256",
              "redaction_status", "claim_level", "limits")
    if not isinstance(record, dict) or any(not record.get(k) for k in needed):
        raise ValueError("Missing packet evidence record field")
    if record["tool"] not in TOOLS or record["redaction_status"] not in ("reviewed", "not_reviewed"):
        raise ValueError("Invalid tool or redaction state")
    if record["claim_level"] not in ("observed", "inferred", "unknown"):
        raise ValueError("Invalid evidence claim level")
    if not isinstance(record["limits"], list) or any(not isinstance(x, str) for x in record["limits"]):
        raise ValueError("Invalid evidence limitations")
    if not re.fullmatch(r"[0-9a-f]{64}", str(record["sha256"])):
        raise ValueError("Invalid SHA256")
    if record.get("public_export", False) and record["redaction_status"] != "reviewed":
        raise ValueError("Unreviewed packet evidence cannot be marked for public export")
    artifact = _local_file(root, record["artifact_path"])
    digest = hashlib.sha256()
    with artifact.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != record["sha256"]:
        raise ValueError("Evidence hash mismatch")
    return {
        "status": "STRUCTURALLY_VERIFIED_ONLY",
        "task_id": record["task_id"],
        "artifact_sha256": digest.hexdigest(),
        "claim_level": record["claim_level"],
        "redaction_status": record["redaction_status"],
        "content_and_conclusion_verified": False,
        "independent_review_verified": False,
        "release_authorized": False,
    }


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("route")
    p.add_argument("--intent", required=True, choices=tuple(ROUTES))
    p.add_argument("--access", required=True, choices=tuple(sorted(ACCESS)))
    p.add_argument("--host-verified", nargs="*", default=[])
    p.add_argument("--live-capture-approved", action="store_true")
    v = sub.add_parser("verify-evidence")
    v.add_argument("--record", required=True, type=Path)
    v.add_argument("--artifact-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "route":
            result = route(args.intent, args.access, args.host_verified, args.live_capture_approved)
        else:
            result = verify_record(json.loads(args.record.read_text()), args.artifact_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "REJECTED", "reason": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())

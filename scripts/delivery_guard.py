#!/usr/bin/env python3
"""Run DCT for an authorized Prism slice and route its local result."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from mission import read_regular, under

RUN_FILE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z-[0-9a-f]{8}\.json")
REPLAN = {
    "MISSION_ID_DRIFT", "MISSION_SPEC_DRIFT", "MISSION_REF_REQUIRED",
    "MISSION_REF_INVALID", "MISSION_TASK_BRANCH_DRIFT", "MISSION_ACCEPTANCE_UNMAPPED",
    "MISSION_ACCEPTANCE_INVALID", "MISSION_NOT_AUTHORIZED", "MISSION_CONTRACT_INVALID",
    "MISSION_MISSING_OR_UNREADABLE", "MISSION_UNSAFE_PATH",
}


def invoke(entry, project, command, *arguments):
    proc = subprocess.run(
        ["node", str(entry), command, "--project", str(project), *arguments],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=330,
        env={**os.environ, "NODE_OPTIONS": ""},
    )
    if proc.returncode not in (0, 1):
        raise ValueError("DCT_PROCESS_FAILED")
    report = json.loads(proc.stdout)
    expected = {"PASS", "MATCH", "RECORDED"} if proc.returncode == 0 else {"NOT_READY"}
    if not isinstance(report, dict) or report.get("status") not in expected:
        raise ValueError("DCT_RESULT_INVALID")
    return report


def needs_debug(project, task_id, git):
    # Local DCT receipts drive recovery decisions only.
    runs = under(project, ".dct/runs")
    failures = 0
    if runs.exists():
        for path in sorted(runs.iterdir(), reverse=True):
            if not RUN_FILE.fullmatch(path.name):
                continue
            run = json.loads(read_regular(under(project, str(path.relative_to(project)))))
            binding = run.get("binding", {})
            if (run.get("task"), binding.get("head"), binding.get("branch")) != (
                task_id, git["head"], git["branch"]
            ):
                continue
            if run.get("status") != "NOT_READY":
                break
            failures += 1
            if failures == 2:
                return True
    return False


def route(entry, project, action, config_hash=None):
    if not entry.is_absolute() or entry.resolve(strict=True) != entry or not entry.is_file():
        raise ValueError("TRUSTED_DCT_ENTRY_REQUIRED")
    if not project.is_absolute() or project.resolve(strict=True) != project or not project.is_dir():
        raise ValueError("REAL_PROJECT_ROOT_REQUIRED")
    if entry.is_relative_to(project):
        raise ValueError("DCT_ENTRY_MUST_BE_OUTSIDE_PROJECT")
    config_bytes = read_regular(under(project, ".dct/config.json"))
    task = json.loads(config_bytes)["task"]
    if not task.get("missionRef"):
        raise ValueError("PRISM_MISSION_REF_REQUIRED")
    result = {"status": "NOT_READY", "release_authorized": False}
    doctor = invoke(entry, project, "doctor")
    if doctor["status"] != "PASS":
        issues = [i if isinstance(i, str) else i["code"] for i in doctor["issues"]]
        result["issues"] = issues
        result["next_action"] = "REPLAN" if REPLAN.intersection(issues) else "PRESERVE_AND_DIAGNOSE"
        return result
    git = doctor["git"]
    if needs_debug(project, task["id"], git):
        result["next_action"] = "DEBUG"
        return result
    if action == "preflight":
        return {**result, "status": "PREFLIGHT_PASS", "next_action": "EXECUTE_AUTHORIZED_SLICE"}
    if hashlib.sha256(config_bytes).hexdigest() != config_hash or read_regular(
        under(project, ".dct/config.json")
    ) != config_bytes:
        raise ValueError("REVIEWED_DCT_CONFIG_HASH_REQUIRED")
    report = invoke(entry, project, "check", "--run")
    if read_regular(under(project, ".dct/config.json")) != config_bytes:
        return {**result, "next_action": "PRESERVE_AND_DIAGNOSE",
                "issues": ["DCT_CONFIG_DRIFT"]}
    if report["status"] != "PASS":
        codes = [i if isinstance(i, str) else i["code"] for i in report.get("issues", [])]
        result["issues"] = codes
        if REPLAN.intersection(codes):
            result["next_action"] = "REPLAN"
        elif report.get("drift") or codes:
            result["next_action"] = "PRESERVE_AND_DIAGNOSE"
        else:
            result["next_action"] = (
                "DEBUG" if needs_debug(project, task["id"], git) else "REPRODUCE_FAILURE"
            )
        return result
    return {**result, "status": "LOCAL_CHECK_PASS", "next_action": "REQUEST_INDEPENDENT_REVIEW"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "check"])
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--dct-entry", type=Path, required=True, help="Trusted checkout's bin/dct.mjs")
    parser.add_argument("--reviewed-config-sha", help="SHA-256 of owner-reviewed .dct/config.json")
    args = parser.parse_args()
    try:
        result = route(args.dct_entry, args.project, args.action, args.reviewed_config_sha)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
        result = {"status": "NOT_READY", "next_action": "INSPECT_DCT_ENTRY_CONFIG_AND_EVIDENCE",
                  "release_authorized": False}
    print(json.dumps(result, ensure_ascii=False))
    return int(result["status"] == "NOT_READY")


if __name__ == "__main__":
    sys.exit(main())

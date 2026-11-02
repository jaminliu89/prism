#!/usr/bin/env python3
"""SEP v1.0 PR evidence gate — structure only.

Validates a JSON manifest aligned with docs/SEP_INTEGRATION_V1.md.
Does not run tests, verify SHAs on GitHub, or authorize release.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SEP_VERSION = "1.0"
TOP_FIELDS = {
    "sep_version",
    "change_id",
    "feature_ids",
    "base_sha",
    "head_sha",
    "affected_modules",
    "affected_contracts",
    "tests",
    "risk",
    "migration_plan",
    "rollback_plan",
    "open_gaps",
    "release_authorized",
}
TEST_RESULTS = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
RISKS = ("low", "medium", "high", "unknown")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.I)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def check(manifest_path):
    path = Path(manifest_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    need(isinstance(data, dict), "root must be an object")
    extra = set(data) - TOP_FIELDS
    need(not extra, "unknown fields: " + ", ".join(sorted(extra)))
    need(data.get("sep_version") == SEP_VERSION, "sep_version must be 1.0")
    need(nonempty(data.get("change_id")), "missing change_id")
    need(isinstance(data.get("feature_ids"), list), "feature_ids must be a list")
    need(all(isinstance(x, str) and x.strip() for x in data["feature_ids"]), "feature_ids entries must be strings")
    for key in ("base_sha", "head_sha"):
        val = data.get(key, "")
        if val:
            need(SHA_RE.fullmatch(val.strip()) is not None, "invalid %s" % key)
    for key in ("affected_modules", "affected_contracts", "open_gaps"):
        need(isinstance(data.get(key), list), "%s must be a list" % key)
    need(data.get("risk") in RISKS, "invalid risk")
    need(isinstance(data.get("migration_plan"), str), "migration_plan must be a string")
    need(isinstance(data.get("rollback_plan"), str), "rollback_plan must be a string")
    need(data.get("release_authorized") is False, "release_authorized must be false for this tool")

    tests = data.get("tests")
    need(isinstance(tests, list) and len(tests) > 0, "tests must be a non-empty list")
    any_pass = False
    for item in tests:
        need(isinstance(item, dict), "invalid test entry")
        need(nonempty(item.get("command")), "test missing command")
        result = item.get("result")
        need(result in TEST_RESULTS, "invalid test result: %s" % result)
        evidence = item.get("evidence", "")
        need(isinstance(evidence, str), "evidence must be a string")
        if result == "PASS":
            any_pass = True
            need(nonempty(evidence), "PASS test requires evidence: %s" % item.get("command"))
        if result == "NOT_RUN":
            need(not evidence.strip(), "NOT_RUN must not carry fake evidence")

    if any_pass:
        need(nonempty(data.get("head_sha")), "head_sha required when any test is PASS")

    blockers = sum(1 for t in tests if t.get("result") in ("FAIL", "BLOCKED"))
    return {
        "status": "STRUCTURALLY_VALID",
        "change_id": data["change_id"],
        "feature_ids": data["feature_ids"],
        "tests": len(tests),
        "pass_claims": sum(1 for t in tests if t.get("result") == "PASS"),
        "open_failures": blockers,
        "runtime_verified": "NOT_BY_THIS_TOOL",
        "release_authorized": False,
    }


def template(change_id="PR-000", feature_ids=None):
    feature_ids = feature_ids or ["example-feature"]
    return {
        "sep_version": SEP_VERSION,
        "change_id": change_id,
        "feature_ids": feature_ids,
        "base_sha": "",
        "head_sha": "",
        "affected_modules": [],
        "affected_contracts": [],
        "tests": [
            {"command": "python scripts/sep_smoke.py", "result": "NOT_RUN", "evidence": ""},
        ],
        "risk": "unknown",
        "migration_plan": "",
        "rollback_plan": "revert PR on protected main",
        "open_gaps": [],
        "release_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check").add_argument("manifest", type=Path)
    tpl = sub.add_parser("template")
    tpl.add_argument("--change-id", default="PR-000")
    tpl.add_argument("--feature-id", action="append", dest="feature_ids")
    args = parser.parse_args()
    try:
        if args.command == "check":
            result = check(args.manifest)
        else:
            result = template(args.change_id, args.feature_ids)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

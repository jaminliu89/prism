"""Explicit, read-only CodeGraph impact evidence adapter.

Never installs anything or configures agents. No shell execution, no implicit
indexing, and no external network calls by this Python adapter itself.
Third-party CodeGraph is executed only by an opted-in local operator.
"""
import json
import os
import re
import subprocess
import hashlib
from pathlib import Path

VERSION = 1
MAX_STDOUT = 262144
CODEGRAPH_ENV = {
    "DO_NOT_TRACK": "1",
    "CODEGRAPH_TELEMETRY": "0",
    "CODEGRAPH_NO_UPDATE_CHECK": "1",
}
SENSITIVE = (".env", ".git", ".foundry", ".codegraph", "secrets", "credentials")


def _relative_file(repo, value):
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError("Changed file must be a relative in-repository path")
    # Always resolve against approved root; reject linked/out-of-root paths.
    resolved = (repo / path).resolve()
    if not resolved.is_relative_to(repo.resolve()):
        raise ValueError("Changed file escapes authorized repository")
    if not resolved.is_file():
        raise ValueError("Changed file must exist")
    if any(part.lower() in SENSITIVE for part in path.parts) or path.name.lower().startswith(".env"):
        raise ValueError("Sensitive changed-file location rejected")
    return path.as_posix()


def _clean_paths(repo, paths):
    result = []
    seen = set()
    for value in paths:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid CodeGraph affected-file output")
        v = value.strip().replace("\\", "/")
        p = Path(v)
        if p.is_absolute() or ".." in p.parts:
            raise ValueError("CodeGraph emitted absolute/out-of-scope result")
        resolved = (repo / p).resolve()
        if not resolved.is_relative_to(repo.resolve()) or not resolved.is_file():
            raise ValueError("CodeGraph emitted unknown/out-of-scope file")
        if v not in seen:
            result.append(v)
            seen.add(v)
    return result


def impact(repo_path, changed, bin_path, *, opt_in=False, timeout=25):
    if not opt_in:
        raise ValueError("External provider opt-in required: --allow-local-codegraph")
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Missing target repository directory")
    if not changed or len(changed) > 32:
        raise ValueError("One to 32 changed files required")
    requested = [_relative_file(root, value) for value in changed]
    binary = Path(bin_path).expanduser().resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("Explicit executable CodeGraph path required")
    if timeout < 1 or timeout > 60:
        raise ValueError("Timeout must be 1–60 seconds")
    env = dict(os.environ)
    env.update(CODEGRAPH_ENV)
    # No shell, no installer, no implicit index creation or global config edits.
    argv = [str(binary), "affected", *requested, "--quiet"]
    try:
        completed = subprocess.run(argv, cwd=root, env=env, shell=False,
                                   text=True, capture_output=True, timeout=timeout,
                                   check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("CodeGraph query timed out") from exc
    if completed.returncode != 0:
        raise ValueError("CodeGraph query failed, exit %d (no stdout exposed)" %
                         completed.returncode)
    if len(completed.stdout.encode("utf-8")) > MAX_STDOUT:
        raise ValueError("CodeGraph output exceeds limit")
    affected = _clean_paths(root, completed.stdout.splitlines())
    return {
        "schema_version": VERSION, "claim": "STATIC_CODE_IMPACT_CANDIDATES_ONLY",
        "provider": "codegraph", "provider_runtime": "EXPLICIT_LOCAL_OPT_IN",
        "graph_freshness": "NOT_VERIFIED", "changed_files": requested,
        "affected_test_candidates": affected, "count": len(affected),
        "sanitized_evidence_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
        "source_content_included": False, "agent_config_modified": False,
        "security_certified": False, "release_authorized": False,
        "limitations": [
            "Static dependency candidates; dynamic dispatch and external APIs may be missed",
            "No guarantee index matches checked-out revision; operator must verify",
            "Provider executable is third party; only use isolated, approved source",
            "No actual impacted test execution by this adapter",
        ],
    }


def cli(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Opt-in static impact evidence")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--changed", nargs="+", required=True)
    parser.add_argument("--codegraph-bin", required=True)
    parser.add_argument("--allow-local-codegraph", action="store_true")
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        result = impact(args.repo, args.changed, args.codegraph_bin,
                        opt_in=args.allow_local_codegraph, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(2, "ERROR: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(cli())

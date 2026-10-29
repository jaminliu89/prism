#!/usr/bin/env python3
"""Prism runtime bootstrap: bounded discovery, scoped setup and preview deployment.

Not a sandbox or a background daemon. Every mutation requires runtime flags and
a trusted operator; never execute commands copied from project text.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# These recipes are fixed by Prism maintainers, not by a target repository.
HOMEBREW_TOOLS = {
    "tshark": "wireshark",
    "capinfos": "wireshark",
    "editcap": "wireshark",
    "node": "node",
    "npm": "node",
    "gh": "gh",
    "git": "git",
}
AVAILABLE_TOOLS = set(HOMEBREW_TOOLS) | {"python3", "vercel", "wrangler"}
SETUPS = {"python-venv", "npm-ci"}
PREVIEWS = {"none", "local-static", "vercel-preview"}
STATE_DIR = ".prism-tools"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def root_path(value):
    root = Path(value).expanduser().resolve()
    require(root.is_dir(), "Existing project directory required")
    require(not root.is_symlink(), "Symlink project root rejected")
    return root


def safe_relative(root, value, *, directory=False):
    path = Path(value)
    require(value and not path.is_absolute() and ".." not in path.parts,
            "Project path must be relative and in project")
    require(path.parts[0] not in (".git", ".prism", STATE_DIR), "Reserved project path")
    current = root
    for piece in path.parts:
        current = current / piece
        require(not current.is_symlink(), "Symlink project path rejected")
    resolved = current.resolve()
    require(resolved.is_relative_to(root), "Project path escapes root")
    if directory:
        require(resolved.is_dir(), "Missing project directory: " + value)
    return resolved


def home(root):
    folder = root / STATE_DIR
    require(not folder.is_symlink(), "Unsafe bootstrap state link")
    folder.mkdir(exist_ok=True)
    return folder


def program(name):
    require(name in AVAILABLE_TOOLS, "Unsupported tool: " + str(name))
    found = shutil.which(name)
    return {"tool": name, "installed": bool(found), "path": found,
            "suggested_homebrew_formula": HOMEBREW_TOOLS.get(name)}


def filehash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(project, tools=(), setups=(), npm_path="web", preview="none",
            artifact="web/dist", port=8775):
    root = root_path(project)
    require(set(tools).issubset(AVAILABLE_TOOLS), "Unknown tool requested")
    require(set(setups).issubset(SETUPS), "Unknown setup requested")
    require(preview in PREVIEWS, "Unknown preview type")
    require(isinstance(port, int) and 1024 <= port <= 65535, "Invalid preview port")
    found = [program(t) for t in dict.fromkeys(tools)]
    actions = []
    for setup in dict.fromkeys(setups):
        if setup == "python-venv":
            venv = root / STATE_DIR / "venv"
            require(not venv.is_symlink(), "Unsafe venv link")
            actions.append({"action": setup, "status": "READY" if (venv / "pyvenv.cfg").is_file() else "NEEDS_SETUP",
                            "scope": "project_only", "network_required": False})
        elif setup == "npm-ci":
            folder = safe_relative(root, npm_path, directory=True)
            require((folder / "package.json").is_file() and (folder / "package-lock.json").is_file(),
                    "npm-ci requires existing package.json and package-lock.json")
            actions.append({"action": setup, "status": "READY" if (folder / "node_modules").is_dir() else "NEEDS_SETUP",
                            "scope": "project_only", "network_required": True, "path": npm_path,
                            "lock_sha256": filehash(folder / "package-lock.json")})
    deployment = {"kind": preview, "status": "NOT_REQUESTED", "scope": "none"}
    if preview == "local-static":
        folder = safe_relative(root, artifact, directory=True)
        require(any(folder.iterdir()), "Static preview artifact folder is empty")
        deployment = {"kind": preview, "status": "READY_TO_START", "scope": "loopback_only",
                      "artifact": artifact, "port": port}
    elif preview == "vercel-preview":
        link = safe_relative(root, ".vercel", directory=True) / "project.json"
        require(not link.is_symlink() and link.is_file(), "Existing linked Vercel project required")
        try:
            data = json.loads(link.read_text())
        except (ValueError, OSError) as exc:
            raise ValueError("Invalid linked Vercel project") from exc
        require(isinstance(data, dict) and data.get("projectId") and data.get("orgId"),
                "Vercel link missing projectId/orgId")
        deployment = {"kind": preview, "status": "READY_TO_REQUEST_APPROVAL", "scope": "external_preview",
                      "cli_installed": bool(shutil.which("vercel")),
                      "linked_project_fingerprint": hashlib.sha256(
                          (str(data["projectId"]) + ":" + str(data["orgId"])).encode()).hexdigest()[:16]}
    return {"status": "PLAN_ONLY", "project": str(root), "tools": found,
            "setup": actions, "deployment": deployment, "executed": False,
            "host_mutated": False, "production_authorized": False,
            "next": "In authorized Mission, operator may request scoped apply flags; review missing tools and provider costs"}


def checked_run(argv, cwd, timeout=300):
    # No shell and no arbitrary command arguments from untrusted project files.
    try:
        completed = subprocess.run(argv, cwd=cwd, shell=False, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "exit_code": None, "stdout_sha256": None}
    # Do not expose stdout/stderr: package managers can print tokens, URLs, machine paths.
    return {"status": "EXITED" if completed.returncode == 0 else "FAILED",
            "exit_code": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout[:1048576]).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr[:1048576]).hexdigest(),
            "output_truncated": len(completed.stdout) > 1048576 or len(completed.stderr) > 1048576}


def _install_tool(tool, *, allow_host, allow_network):
    missing = program(tool)
    if missing["installed"]:
        return {"action": "host-tool", "tool": tool, "status": "ALREADY_INSTALLED"}
    formula = missing["suggested_homebrew_formula"]
    if not (allow_host and allow_network):
        return {"action": "host-tool", "tool": tool, "status": "APPROVAL_REQUIRED",
                "reason": "Separate --allow-host-install and --allow-network flags required"}
    if platform.system() != "Darwin" or not shutil.which("brew") or not formula:
        return {"action": "host-tool", "tool": tool, "status": "BLOCKED",
                "reason": "Supported non-root Homebrew recipe unavailable; host must arrange trusted installer"}
    result = checked_run([shutil.which("brew"), "install", "--formula", formula],
                         Path.home(), timeout=900)
    return {"action": "host-tool", "tool": tool,
            "status": "INSTALLED" if result["status"] == "EXITED" and bool(shutil.which(tool)) else "NOT_VERIFIED",
            "command": ["brew", "install", "--formula", formula], "result": result,
            "version": "NOT_VERIFIED"}


def _project_setup(root, action, npm_path, *, allow_project, allow_network):
    if not allow_project:
        return {"action": action, "status": "APPROVAL_REQUIRED",
                "reason": "--allow-project-install required"}
    if action == "python-venv":
        venv = root / STATE_DIR / "venv"
        require(not venv.is_symlink(), "Unsafe venv link")
        if (venv / "pyvenv.cfg").is_file():
            return {"action": action, "status": "ALREADY_INSTALLED"}
        result = checked_run([sys.executable, "-m", "venv", str(venv)], root)
        return {"action": action, "status": "INSTALLED" if result["status"] == "EXITED" and
                (venv / "pyvenv.cfg").is_file() else "NOT_VERIFIED", "result": result,
                "scope": "project_only"}
    folder = safe_relative(root, npm_path, directory=True)
    require((folder / "package.json").is_file() and (folder / "package-lock.json").is_file(),
            "npm-ci requires package and exact lock")
    if (folder / "node_modules").is_dir():
        return {"action": action, "status": "ALREADY_INSTALLED"}
    if not allow_network:
        return {"action": action, "status": "APPROVAL_REQUIRED",
                "reason": "--allow-network required for npm ci"}
    if not shutil.which("npm"):
        return {"action": action, "status": "BLOCKED", "reason": "npm missing; resolve host runtime"}
    # npm package scripts are never run. Reproducibility relies on the lock file.
    result = checked_run([shutil.which("npm"), "ci", "--ignore-scripts", "--no-audit",
                          "--no-fund"], folder, timeout=900)
    return {"action": action,
            "status": "INSTALLED" if result["status"] == "EXITED" and
            (folder / "node_modules").is_dir() else "NOT_VERIFIED",
            "result": result, "scope": "project_only"}


def _preview_state(root):
    return root / STATE_DIR / "preview.json"


def _pid_alive(pid):
    if not isinstance(pid, int) or pid < 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _local_preview(root, artifact, port, authorized):
    if not authorized:
        return {"kind": "local-static", "status": "APPROVAL_REQUIRED",
                "reason": "--allow-local-preview required"}
    folder = safe_relative(root, artifact, directory=True)
    require(any(folder.iterdir()), "Missing built static files")
    path = _preview_state(root)
    if path.exists():
        require(not path.is_symlink(), "Unsafe preview state")
        old = json.loads(path.read_text())
        if _pid_alive(old.get("pid")):
            return {"kind": "local-static", "status": "ALREADY_RUNNING",
                    "url": old.get("url"), "health_verified": False}
    url = "http://127.0.0.1:%d/" % port
    out = home(root) / "preview.log"
    try:
        with out.open("ab") as log:
            process = subprocess.Popen([sys.executable, "-m", "http.server", str(port),
                                        "--bind", "127.0.0.1", "--directory", str(folder)],
                                       cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       start_new_session=True)
    except OSError:
        return {"kind": "local-static", "status": "FAILED_TO_START"}
    healthy = False
    for _ in range(15):
        if process.poll() is not None:
            break
        try:
            with urllib.request.urlopen(url, timeout=0.4) as reply:
                healthy = reply.status == 200
            if healthy:
                break
        except OSError:
            time.sleep(0.15)
    if not healthy:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        return {"kind": "local-static", "status": "HEALTH_CHECK_FAILED", "url": url}
    path.write_text(json.dumps({"pid": process.pid, "url": url, "artifact": artifact}) + "\n")
    return {"kind": "local-static", "status": "LOCAL_PREVIEW_HEALTHY",
            "url": url, "pid": process.pid, "health_verified": True,
            "remote_deployed": False, "production_authorized": False}


def stop_preview(project):
    root = root_path(project)
    path = _preview_state(root)
    require(path.is_file() and not path.is_symlink(), "No owned preview record")
    record = json.loads(path.read_text())
    pid = record.get("pid")
    require(isinstance(pid, int) and pid > 0, "Invalid preview pid")
    # PID reuse is possible. Check command line where OS supports proc before termination;
    # never signal an unknown process just because state has its PID.
    proc = Path("/proc") / str(pid) / "cmdline"
    if not proc.is_file():
        return {"status": "MANUAL_STOP_REQUIRED", "reason": "Cannot safely prove ownership of PID"}
    args = proc.read_bytes().replace(b"\x00", b" ").decode(errors="replace")
    if "http.server" not in args or "127.0.0.1" not in args or str(root) not in args:
        return {"status": "MANUAL_STOP_REQUIRED", "reason": "PID not identified as owned preview"}
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    path.unlink()
    return {"status": "STOP_REQUESTED", "pid": pid, "process_exit_verified": False}


def _remote_preview(root, *, allow_remote, allow_network, allow_external):
    if not (allow_remote and allow_network and allow_external):
        return {"kind": "vercel-preview", "status": "APPROVAL_REQUIRED",
                "reason": "Separate remote/network/public-preview approvals required"}
    if not shutil.which("vercel"):
        return {"kind": "vercel-preview", "status": "BLOCKED", "reason": "Vercel CLI missing"}
    link = safe_relative(root, ".vercel", directory=True) / "project.json"
    require(link.is_file() and not link.is_symlink(), "Vercel project link required")
    data = json.loads(link.read_text())
    require(isinstance(data, dict) and data.get("projectId") and data.get("orgId"),
            "Existing Vercel project link required")
    result = checked_run([shutil.which("vercel"), "deploy", "--yes"], root, timeout=900)
    return {"kind": "vercel-preview",
            "status": "DEPLOY_COMMAND_EXITED" if result["status"] == "EXITED" else "DEPLOY_FAILED",
            "result": result, "external_preview": True, "url": "NOT_VERIFIED",
            "deployed_revision": "NOT_VERIFIED", "browser_health_verified": False,
            "production_authorized": False}


def apply(project, tools=(), setups=(), npm_path="web", preview="none",
          artifact="web/dist", port=8775, *, allow_project=False,
          allow_host=False, allow_network=False, allow_local=False,
          allow_remote=False, allow_external=False):
    snapshot = inspect(project, tools, setups, npm_path, preview, artifact, port)
    root = root_path(project)
    results = []
    for tool in dict.fromkeys(tools):
        results.append(_install_tool(tool, allow_host=allow_host, allow_network=allow_network))
    for setup in dict.fromkeys(setups):
        results.append(_project_setup(root, setup, npm_path, allow_project=allow_project,
                                      allow_network=allow_network))
    deployment = {"kind": "none", "status": "NOT_REQUESTED"}
    if preview == "local-static":
        deployment = _local_preview(root, artifact, port, allow_local)
    elif preview == "vercel-preview":
        deployment = _remote_preview(root, allow_remote=allow_remote, allow_network=allow_network,
                                     allow_external=allow_external)
    statuses = [r["status"] for r in results] + ([deployment["status"]] if preview != "none" else [])
    done = {"ALREADY_INSTALLED", "INSTALLED", "LOCAL_PREVIEW_HEALTHY", "DEPLOY_COMMAND_EXITED"}
    status = "APPLIED" if statuses and all(s in done for s in statuses) else (
        "PARTIAL_OR_BLOCKED" if statuses else "NO_ACTION")
    return {"status": status, "project": str(root), "actions": results,
            "deployment": deployment, "preflight": snapshot,
            "production_authorized": False, "independent_qa_verified": False,
            "note": "A command exit or preview health check is not release/production certification"}


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for action in ("plan", "apply"):
        p = sub.add_parser(action)
        p.add_argument("--project", required=True)
        p.add_argument("--tool", action="append", default=[], choices=sorted(AVAILABLE_TOOLS))
        p.add_argument("--setup", action="append", default=[], choices=sorted(SETUPS))
        p.add_argument("--npm-path", default="web")
        p.add_argument("--preview", choices=sorted(PREVIEWS), default="none")
        p.add_argument("--artifact", default="web/dist")
        p.add_argument("--port", type=int, default=8775)
        if action == "apply":
            for flag in ("allow-project-install", "allow-host-install", "allow-network",
                         "allow-local-preview", "allow-remote-preview", "allow-external-publish"):
                p.add_argument("--" + flag, action="store_true")
    stop = sub.add_parser("stop-preview")
    stop.add_argument("--project", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "stop-preview":
            result = stop_preview(args.project)
        else:
            values = (args.project, args.tool, args.setup, args.npm_path,
                      args.preview, args.artifact, args.port)
            if args.command == "plan":
                result = inspect(*values)
            else:
                result = apply(*values, allow_project=args.allow_project_install,
                               allow_host=args.allow_host_install, allow_network=args.allow_network,
                               allow_local=args.allow_local_preview,
                               allow_remote=args.allow_remote_preview,
                               allow_external=args.allow_external_publish)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] not in ("PARTIAL_OR_BLOCKED",) else 2
    except (ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(cli())

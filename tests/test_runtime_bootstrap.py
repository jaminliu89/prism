"""Isolated runtime setup contracts; never install third-party tools or publish to cloud."""
import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/runtime_bootstrap.py"
spec = importlib.util.spec_from_file_location("runtime_bootstrap", SCRIPT)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)

    def test_plan_is_non_mutating(self):
        r = runtime.inspect(self.project, tools=["tshark", "node"], setups=["python-venv"])
        self.assertEqual(r["status"], "PLAN_ONLY")
        self.assertFalse(r["executed"])
        self.assertFalse(r["host_mutated"])
        self.assertFalse((self.project / ".prism-tools").exists())

    def test_unsupported_tools_rejected_without_commands(self):
        with self.assertRaisesRegex(ValueError, "Unknown tool"):
            runtime.inspect(self.project, tools=["curl | sh"])
        with self.assertRaisesRegex(ValueError, "Unknown setup"):
            runtime.inspect(self.project, setups=["npm install -g"])
        with self.assertRaisesRegex(ValueError, "Unknown preview"):
            runtime.inspect(self.project, preview="production")

    def test_no_implicit_host_install(self):
        with mock.patch.object(runtime.shutil, "which", return_value=None), mock.patch.object(
                runtime, "checked_run") as run:
            r = runtime.apply(self.project, tools=["tshark"])
        self.assertEqual(r["status"], "PARTIAL_OR_BLOCKED")
        self.assertEqual(r["actions"][0]["status"], "APPROVAL_REQUIRED")
        run.assert_not_called()

    def test_host_install_requires_both_flags_and_restricts_os(self):
        with mock.patch.object(runtime.shutil, "which", return_value=None), mock.patch.object(
                runtime.platform, "system", return_value="Linux"), mock.patch.object(
                runtime, "checked_run") as run:
            self.assertEqual(runtime.apply(self.project, tools=["tshark"],
                                            allow_host=True, allow_network=True)["actions"][0]["status"],
                             "BLOCKED")
        run.assert_not_called()

    def test_python_venv_requires_opt_in_and_installs_locally(self):
        before = runtime.apply(self.project, setups=["python-venv"])
        self.assertEqual(before["actions"][0]["status"], "APPROVAL_REQUIRED")
        self.assertFalse((self.project / ".prism-tools").exists())
        after = runtime.apply(self.project, setups=["python-venv"], allow_project=True)
        self.assertEqual(after["actions"][0]["status"], "INSTALLED")
        self.assertTrue((self.project / ".prism-tools/venv/pyvenv.cfg").is_file())
        again = runtime.apply(self.project, setups=["python-venv"], allow_project=True)
        self.assertEqual(again["actions"][0]["status"], "ALREADY_INSTALLED")

    def test_npm_require_lock_and_never_runs_scripts(self):
        web = self.project / "web"
        web.mkdir()
        (web / "package.json").write_text('{"name":"fixture","version":"1.0.0"}')
        with self.assertRaisesRegex(ValueError, "package-lock"):
            runtime.inspect(self.project, setups=["npm-ci"])
        (web / "package-lock.json").write_text('{"lockfileVersion":3}')
        with mock.patch.object(runtime.shutil, "which", return_value="/usr/bin/npm"), mock.patch.object(
                runtime, "checked_run", return_value={"status": "EXITED", "exit_code": 0}) as run:
            blocked = runtime.apply(self.project, setups=["npm-ci"], allow_project=True)
            self.assertEqual(blocked["actions"][0]["status"], "APPROVAL_REQUIRED")
            run.assert_not_called()
            result = runtime.apply(self.project, setups=["npm-ci"], allow_project=True, allow_network=True)
            self.assertEqual(result["actions"][0]["status"], "NOT_VERIFIED")  # no real node_modules
            args = run.call_args.args[0]
            self.assertEqual(args[1], "ci")
            self.assertIn("--ignore-scripts", args)
            self.assertNotIn("--force", args)

    def test_traversal_and_symlink_project_inputs_rejected(self):
        with self.assertRaisesRegex(ValueError, "relative"):
            runtime.inspect(self.project, preview="local-static", artifact="../outside")
        (self.project / "outside").symlink_to(Path(self.temp.name).parent)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            runtime.inspect(self.project, preview="local-static", artifact="outside")

    def test_local_static_requires_permission_then_serves_loopback(self):
        dist = self.project / "web" / "dist"
        dist.mkdir(parents=True)
        (dist / "index.html").write_text("<h1>fixture preview</h1>")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        rejected = runtime.apply(self.project, preview="local-static", port=port)
        self.assertEqual(rejected["deployment"]["status"], "APPROVAL_REQUIRED")
        self.assertFalse((self.project / ".prism-tools").exists())
        try:
            deployed = runtime.apply(self.project, preview="local-static", port=port, allow_local=True)
            self.assertEqual(deployed["deployment"]["status"], "LOCAL_PREVIEW_HEALTHY")
            self.assertTrue(deployed["deployment"]["url"].startswith("http://127.0.0.1:"))
            self.assertFalse(deployed["deployment"]["remote_deployed"])
            with urllib.request.urlopen(deployed["deployment"]["url"], timeout=2) as stream:
                self.assertIn(b"fixture preview", stream.read())
        finally:
            state = self.project / ".prism-tools" / "preview.json"
            if state.exists():
                r = runtime.stop_preview(self.project)
                if r["status"] == "MANUAL_STOP_REQUIRED":
                    data = json.loads(state.read_text())
                    import os
                    import signal
                    os.kill(data["pid"], signal.SIGTERM)

    def test_remote_preview_requires_linked_project(self):
        with self.assertRaisesRegex(ValueError, "Missing project directory"):
            runtime.inspect(self.project, preview="vercel-preview")
        (self.project / ".vercel").mkdir()
        (self.project / ".vercel/project.json").write_text('{"projectId":"p_fixture","orgId":"o_fixture"}')
        r = runtime.inspect(self.project, preview="vercel-preview")
        self.assertEqual(r["deployment"]["status"], "READY_TO_REQUEST_APPROVAL")
        with mock.patch.object(runtime, "checked_run") as run:
            a = runtime.apply(self.project, preview="vercel-preview",
                              allow_remote=True, allow_network=True, allow_external=False)
        self.assertEqual(a["deployment"]["status"], "APPROVAL_REQUIRED")
        run.assert_not_called()

    def test_vercel_preview_deploy_never_prod_and_not_claim_health(self):
        (self.project / ".vercel").mkdir()
        (self.project / ".vercel/project.json").write_text('{"projectId":"p_fixture","orgId":"o_fixture"}')
        with mock.patch.object(runtime.shutil, "which", return_value="/usr/local/bin/vercel"), mock.patch.object(
                runtime, "checked_run", return_value={"status": "EXITED", "exit_code": 0}) as run:
            r = runtime.apply(self.project, preview="vercel-preview", allow_remote=True,
                              allow_network=True, allow_external=True)
        self.assertEqual(r["deployment"]["status"], "DEPLOY_COMMAND_EXITED")
        self.assertEqual(r["deployment"]["url"], "NOT_VERIFIED")
        self.assertFalse(r["deployment"]["browser_health_verified"])
        self.assertFalse(r["production_authorized"])
        self.assertEqual(run.call_args.args[0], ["/usr/local/bin/vercel", "deploy", "--yes"])
        self.assertNotIn("--prod", run.call_args.args[0])

    def test_cli_plan_no_side_effect_and_apply_reports_block(self):
        x = json.loads(subprocess.check_output([sys.executable, str(SCRIPT), "plan", "--project",
                                                 str(self.project), "--setup", "python-venv"], text=True))
        self.assertEqual(x["status"], "PLAN_ONLY")
        r = subprocess.run([sys.executable, str(SCRIPT), "apply", "--project", str(self.project),
                            "--setup", "python-venv"], text=True, capture_output=True)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["actions"][0]["status"], "APPROVAL_REQUIRED")


if __name__ == "__main__":
    unittest.main()

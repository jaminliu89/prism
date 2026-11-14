"""Prism to real DCT subprocess integration in a disposable Git project."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DCT = os.environ.get("PRISM_TEST_DCT_ROOT")


@unittest.skipUnless(DCT, "Set PRISM_TEST_DCT_ROOT to the pinned DCT checkout")
class DeliveryGuardTests(unittest.TestCase):
    def test_dispatch_stop_debug_and_recover(self):
        toolkit = Path(DCT).resolve()
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder).resolve() / "project"
            recovery = project.with_name("recovery")
            setup = """
import fs from 'node:fs';
import { fixture, g, put } from './tests/support.mjs';
const {root,c} = fixture();
const target = process.argv[1];
const spec = {profile:'dev', goal:'Preserve exact local output', target,
  scope:'Change only app.mjs', principal:'fixture',
  acceptance:['Exact JSON output from the application'],
  implementation_authorized:true, authorization_statement:'Isolated fixture'};
const specPath = root + '/mission-input.json';
fs.writeFileSync(specPath, JSON.stringify(spec));
const {spawnSync} = await import('node:child_process');
const mission = spawnSync(process.argv[2], [process.argv[3], '--project', root, 'init',
  '--spec', specPath], {encoding: 'utf8'});
if (mission.status !== 0) throw Error(mission.stderr || mission.stdout);
fs.unlinkSync(specPath);
fs.rmSync(root + '/.prism/mission.lock');

const {missionView} = await import('./lib/axis.mjs');
c.task.missionRef=missionView(root).missionRef;
c.task.missionAcceptance=[0];
c.task.branch='feature/test';
c.task.allowedPaths.push('.prism');
put(root,'.dct/config.json',JSON.stringify(c));
g(root,['add','--','.']);
g(root,['commit','-m','Verified test checkpoint']);
fs.cpSync(root,target,{recursive:true});
fs.rmSync(root,{recursive:true});
"""
            self.run_cmd(["node", "--input-type=module", "-e", setup, str(project), sys.executable,
                          str(ROOT / "scripts/mission.py")], toolkit)
            config = project / ".dct/config.json"
            mission = project / ".prism/mission.json"
            original = mission.read_bytes()
            self.assertEqual(self.guard(toolkit, project, "preflight", 0)["status"], "PREFLIGHT_PASS")
            self.assertEqual(self.guard(toolkit, project, "check", 1, approved=False)["next_action"],
                             "INSPECT_DCT_ENTRY_CONFIG_AND_EVIDENCE")
            self.assertFalse((project / ".dct/runs").exists())
            self.assertEqual(self.guard(toolkit, project, "check", 0)["status"], "LOCAL_CHECK_PASS")

            changed = json.loads(original)
            changed["spec"]["acceptance"].append("Review new output")
            mission.write_text(json.dumps(changed))
            self.assertEqual(self.guard(toolkit, project, "check", 1)["next_action"], "REPLAN")
            mission.write_bytes(original)

            foreign = project / "outside.txt"
            foreign.write_text("preserved evidence")
            blocked = self.guard(toolkit, project, "preflight", 1)
            self.assertEqual(blocked["next_action"], "PRESERVE_AND_DIAGNOSE")
            self.assertIn("OUT_OF_SCOPE", blocked["issues"])
            self.assertEqual(foreign.read_text(), "preserved evidence")
            foreign.unlink()

            app = project / "app.mjs"
            app.write_text("process.stdout.write('{}');\n")
            self.assertEqual(self.guard(toolkit, project, "check", 1)["next_action"], "REPRODUCE_FAILURE")
            self.assertEqual(self.guard(toolkit, project, "check", 1)["next_action"], "DEBUG")
            run_files = list((project / ".dct/runs").glob("*.json"))
            self.assertEqual(len(run_files), 3)
            self.assertEqual(self.guard(toolkit, project, "check", 1)["next_action"], "DEBUG")
            self.assertEqual(len(list((project / ".dct/runs").glob("*.json"))), 3)

            dct = ["node", str(toolkit / "bin/dct.mjs")]
            handoff = self.run_cmd([*dct, "handoff", "--project", str(project)], project)
            receipt = handoff["path"]
            self.run_cmd(["git", "worktree", "add", "-b", "feature/recovery", str(recovery), "HEAD"],
                         project)
            receipt_path = recovery / receipt
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_bytes((project / receipt).read_bytes())
            self.assertEqual(self.run_cmd([*dct, "resume", "--project", str(recovery),
                                           "--file", receipt], recovery, 1)["status"], "NOT_READY")

            new_config = recovery / ".dct/config.json"
            task = json.loads(config.read_bytes())
            task["task"]["branch"] = "feature/recovery"
            new_config.write_text(json.dumps(task))
            self.assertEqual(self.guard(toolkit, recovery, "check", 0)["status"], "LOCAL_CHECK_PASS")
            self.assertEqual(app.read_text(), "process.stdout.write('{}');\n")

    def run_cmd(self, cmd, cwd, expected=0):
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return json.loads(proc.stdout) if proc.stdout.startswith("{") else proc.stdout

    def guard(self, toolkit, project, action, expected, approved=True):
        cmd = [sys.executable, str(ROOT / "scripts/delivery_guard.py"), action,
               "--project", str(project), "--dct-entry", str(toolkit / "bin/dct.mjs")]
        if approved and action == "check":
            config = (project / ".dct/config.json").read_bytes()
            cmd.extend(["--reviewed-config-sha", hashlib.sha256(config).hexdigest()])
        report = self.run_cmd(cmd, project, expected)
        self.assertFalse(report["release_authorized"])
        return report

"""Local synthetic contract tests; no real agents, model calls or PR approvals."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("agent_collaboration", ROOT / "scripts/agent_collaboration.py")
collab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collab)


def task(tid="AGT-0001", artifact="docs/00-asset-recall.md", role="research", stage=0):
    return {"id": tid, "stage": stage, "role": role, "objective": "Recover evidence",
            "artifact": artifact, "status": "ready", "requested_by_claim": "owner",
            "assigned_to_claim": None, "allowed_write_paths": [artifact],
            "allowed_actions": ["read approved project docs", "submit planning document"],
            "denied_actions": ["approve own work", "run target code", "deploy"],
            "authorization": "PLANNING_DOCUMENT_ONLY", "identity_verified": False,
            "source_docs": ["sources/skillhub/blueprint/MASTER_PROMPT.md"],
            "delivery": None}


class CollaborationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".foundry").mkdir()
        self.state = {"schema_version": 1, "revision": 3,
                      "stages": [{"confirmed": False, "artifacts": {}} for _ in range(7)],
                      "tasks": [task()]}
        self.save()

    def save(self):
        (self.root / ".foundry/project.json").write_text(
            json.dumps(self.state), encoding="utf-8")

    def make_delivered(self, entry, content=b"verified artifact"):
        p = self.root / entry["artifact"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        entry["status"] = "delivered"
        entry["delivery"] = {"artifact": entry["artifact"], "sha256": digest}
        self.state["stages"][entry["stage"]]["artifacts"][entry["artifact"]] = {"sha256": digest}
        self.save()
        return p

    def reject(self):
        with self.assertRaises(collab.ContractError):
            collab.validate(self.state)

    def test_ready_and_no_permission_to_run(self):
        result = collab.plan(self.state, self.root)
        self.assertEqual(result["parallel_ready"], ["AGT-0001"])
        self.assertFalse(result["execution_authorized"])

    def test_packet_scope_preserved(self):
        packet = collab.packet(self.state, "AGT-0001", self.root)
        self.assertEqual(packet["output_document"], "docs/00-asset-recall.md")
        self.assertEqual(packet["authorization"], "PLANNING_DOCUMENT_ONLY")
        self.assertFalse(packet["identity_verified"])

    def test_unknown_role(self):
        self.state["tasks"][0]["role"] = "CEO"
        self.reject()

    def test_malformed_role_rejected_instead_of_crashing(self):
        self.state["tasks"][0]["role"] = ["CEO"]
        self.reject()

    def test_invalid_denied_actions_rejected(self):
        self.state["tasks"][0]["denied_actions"] = "approve own work"
        self.reject()

    def test_nonsequential_stage_confirmation_rejected(self):
        self.state["stages"][1]["confirmed"] = True
        self.save()
        with self.assertRaises(collab.ContractError):
            collab.load(self.root)

    def test_no_self_approval(self):
        self.state["tasks"][0]["denied_actions"] = ["run target code"]
        self.reject()

    def test_no_permission_escalation(self):
        self.state["tasks"][0]["authorization"] = "PRODUCTION_ACCESS"
        self.reject()

    def test_no_claimed_identity_forgery(self):
        self.state["tasks"][0]["identity_verified"] = True
        self.reject()

    def test_no_write_scope_expansion(self):
        self.state["tasks"][0]["allowed_write_paths"].append("docs/other.md")
        self.reject()

    def test_no_path_traversal(self):
        self.state["tasks"][0]["artifact"] = "docs/../etc/passwd"
        self.reject()

    def test_no_windows_path_traversal(self):
        self.state["tasks"][0]["artifact"] = "docs\\evil.md"
        self.reject()

    def test_no_duplicate_writer(self):
        self.state["tasks"].append(task("AGT-0002"))
        self.reject()

    def test_no_duplicate_task_id(self):
        self.state["tasks"].append(task("AGT-0001", "docs/00-extra.md"))
        self.reject()

    def test_missing_claimed_actor(self):
        self.state["tasks"][0]["status"] = "claimed"
        self.reject()

    def test_dependency_blocks_ready(self):
        self.state["tasks"].append(task("AGT-0002", "docs/00-extra.md"))
        self.state["tasks"][1]["depends_on"] = ["AGT-0001"]
        plan = collab.plan(self.state, self.root)
        self.assertEqual(plan["parallel_ready"], ["AGT-0001"])
        self.assertEqual(plan["blocked"][0]["id"], "AGT-0002")
        with self.assertRaises(collab.ContractError):
            collab.packet(self.state, "AGT-0002", self.root)

    def test_dependency_unlocks_after_delivery(self):
        self.state["tasks"].append(task("AGT-0002", "docs/00-extra.md"))
        self.state["tasks"][1]["depends_on"] = ["AGT-0001"]
        self.make_delivered(self.state["tasks"][0])
        self.assertEqual(collab.plan(self.state, self.root)["parallel_ready"], ["AGT-0002"])

    def test_delivered_dependency_hash_mismatch_blocks_downstream(self):
        self.state["tasks"].append(task("AGT-0002", "docs/00-extra.md"))
        self.state["tasks"][1]["depends_on"] = ["AGT-0001"]
        p = self.make_delivered(self.state["tasks"][0])
        p.write_text("changed unexpectedly", encoding="utf-8")
        with self.assertRaises(collab.ContractError):
            collab.plan(self.state, self.root)
        with self.assertRaises(collab.ContractError):
            collab.packet(self.state, "AGT-0002", self.root)

    def test_dependency_missing_artifact_blocks_downstream(self):
        self.state["tasks"].append(task("AGT-0002", "docs/00-extra.md"))
        self.state["tasks"][1]["depends_on"] = ["AGT-0001"]
        p = self.make_delivered(self.state["tasks"][0])
        p.unlink()
        with self.assertRaises(collab.ContractError):
            collab.plan(self.state, self.root)

    def test_dependency_cycle_rejected(self):
        self.state["tasks"].append(task("AGT-0002", "docs/00-extra.md"))
        self.state["tasks"][0]["depends_on"] = ["AGT-0002"]
        self.state["tasks"][1]["depends_on"] = ["AGT-0001"]
        self.reject()

    def test_later_stage_dependency_rejected(self):
        self.state["tasks"].append(task("AGT-0002", "docs/01-product-research.md", stage=1))
        self.state["tasks"][0]["depends_on"] = ["AGT-0002"]
        self.reject()

    def test_cancelled_not_dispatched(self):
        self.state["tasks"][0]["status"] = "cancelled"
        self.assertEqual(collab.plan(self.state, self.root)["parallel_ready"], [])

    def test_outdated_stage_not_dispatched(self):
        self.state["stages"][0]["confirmed"] = True
        self.assertEqual(collab.plan(self.state, self.root)["parallel_ready"], [])

    def test_claimed_not_dispatched_twice(self):
        self.state["tasks"][0]["status"] = "claimed"
        self.state["tasks"][0]["assigned_to_claim"] = "worker"
        self.assertEqual(collab.plan(self.state, self.root)["already_claimed"], ["AGT-0001"])

    def test_verify_delivered_hash_binds_state(self):
        self.make_delivered(self.state["tasks"][0])
        result = collab.inspect_artifact(self.root, self.state, self.state["tasks"][0])
        self.assertEqual(result["status"], "ARTIFACT_HASH_MATCH")
        self.assertEqual(result["quality_assurance"], "NOT_VERIFIED")

    def test_reject_artifact_tampering(self):
        p = self.make_delivered(self.state["tasks"][0])
        p.write_text("tampered", encoding="utf-8")
        with self.assertRaises(collab.ContractError):
            collab.inspect_artifact(self.root, self.state, self.state["tasks"][0])

    def test_reject_symlink_artifact(self):
        p = self.make_delivered(self.state["tasks"][0])
        p.unlink()
        p.symlink_to(self.root / ".foundry/project.json")
        with self.assertRaises(collab.ContractError):
            collab.inspect_artifact(self.root, self.state, self.state["tasks"][0])

    def test_reject_invalid_json(self):
        (self.root / ".foundry/project.json").write_text("not-json")
        with self.assertRaises(collab.ContractError):
            collab.load(self.root)

    def test_reject_symlink_state(self):
        statefile = self.root / ".foundry/project.json"
        other = self.root / "other.json"
        statefile.replace(other)
        statefile.symlink_to(other)
        with self.assertRaises(collab.ContractError):
            collab.load(self.root)

    def test_cli_plan_and_packet(self):
        cmd = [sys.executable, str(ROOT / "scripts/agent_collaboration.py"),
               "--project", str(self.root)]
        for args in (["plan"], ["packet", "--id", "AGT-0001"]):
            p = subprocess.run(cmd + args, capture_output=True, text=True, check=False)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["schema_version"], 1)

    def test_cli_blocks_unconfirmed_receipt(self):
        cmd = [sys.executable, str(ROOT / "scripts/agent_collaboration.py"),
               "--project", str(self.root), "verify-artifact", "--id", "AGT-0001"]
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
